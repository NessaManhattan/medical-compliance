
from flask import Flask, jsonify, render_template, request
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from werkzeug.utils import secure_filename
import json

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solders.signature import Signature

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "clarity.db"

RPC_URL = "https://api.devnet.solana.com"
KEY_FILE = BASE_DIR / "devnet-keypair.json"

MEMO_PROGRAM = Pubkey.from_string(
    "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
)


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS checklist (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
        """)

        count = connection.execute(
            "SELECT COUNT(*) FROM checklist"
        ).fetchone()[0]

        if count == 0:
            example_items = [
                (
                    "Review employee access rights",
                    "Check who can access systems and sensitive information.",
                    "Access control",
                ),
                (
                    "Review backup and recovery procedures",
                    "Check that backups exist and recovery procedures are documented.",
                    "Business continuity",
                ),
                (
                    "Document security awareness training",
                    "Keep a record of relevant staff security training.",
                    "Staff awareness",
                ),
            ]

            connection.executemany("""
                INSERT INTO checklist (title, description, category)
                VALUES (?, ?, ?)
            """, example_items)

        # Create the evidence table, including the memo field.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS evidence_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                blockchain_status TEXT NOT NULL DEFAULT 'Not recorded',
                tx_signature TEXT,
                memo TEXT NOT NULL DEFAULT ''
            )
        """)

        # Add memo to existing databases without deleting records.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(evidence_records)"
            ).fetchall()
        }

        if "memo" not in columns:
            connection.execute("""
                ALTER TABLE evidence_records
                ADD COLUMN memo TEXT NOT NULL DEFAULT ''
            """)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/checklist", methods=["GET"])
def get_checklist():
    with get_db_connection() as connection:
        rows = connection.execute("""
            SELECT id, title, description, category, completed
            FROM checklist
            ORDER BY id
        """).fetchall()

    items = [dict(row) for row in rows]

    for item in items:
        item["completed"] = bool(item["completed"])

    return jsonify(items)


@app.route("/api/checklist/<int:item_id>", methods=["PATCH"])
def update_checklist_item(item_id):
    data = request.get_json(silent=True) or {}
    completed = data.get("completed")

    if not isinstance(completed, bool):
        return jsonify({
            "error": "completed must be true or false"
        }), 400

    with get_db_connection() as connection:
        cursor = connection.execute(
            "UPDATE checklist SET completed = ? WHERE id = ?",
            (int(completed), item_id),
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Checklist item not found"
            }), 404

    return jsonify({
        "id": item_id,
        "completed": completed,
        "saved": True,
    })


@app.route("/api/evidence", methods=["GET"])
def get_evidence():
    with get_db_connection() as connection:
        rows = connection.execute("""
            SELECT id, filename, sha256, created_at,
                   blockchain_status, tx_signature, memo
            FROM evidence_records
            ORDER BY id DESC
        """).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/evidence-records")
def evidence_records_page():
    return render_template("evidence_records.html")


@app.route("/api/evidence", methods=["POST"])
def create_evidence():
    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "error": "Please select a file."
        }), 400

    # Read the file into memory; do not save its contents.
    file_bytes = uploaded_file.read()

    if not file_bytes:
        return jsonify({
            "error": "The selected file is empty."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        filename = "evidence-file"

    # Calculate the SHA-256 fingerprint.
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    created_at = datetime.now(timezone.utc).isoformat()

    # Read the memo sent with the upload.
    memo = (request.form.get("memo") or "").strip()

    if len(memo) > 1000:
        return jsonify({
            "error": "Memo must be 1,000 characters or fewer."
        }), 400

    # Save the filename, hash, timestamp, memo and status.
    with get_db_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO evidence_records
                (filename, sha256, created_at,
                 blockchain_status, memo)
            VALUES (?, ?, ?, ?, ?)
        """, (
            filename,
            file_hash,
            created_at,
            "Hash created - not recorded on Solana",
            memo,
        ))

        record_id = cursor.lastrowid

    return jsonify({
        "id": record_id,
        "filename": filename,
        "sha256": file_hash,
        "created_at": created_at,
        "blockchain_status": "Hash created - not recorded on Solana",
        "memo": memo,
    }), 201


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "File too large. Maximum size is 10 MB."
    }), 413


@app.route("/api/evidence/<int:record_id>/record", methods=["POST"])
def record_evidence_on_solana(record_id):
    # Retrieve the saved evidence hash.
    with get_db_connection() as connection:
        evidence = connection.execute("""
            SELECT id, filename, sha256, tx_signature
            FROM evidence_records
            WHERE id = ?
        """, (record_id,)).fetchone()

    if evidence is None:
        return jsonify({
            "error": "Evidence record not found."
        }), 404

    if evidence["tx_signature"]:
        signature = evidence["tx_signature"]

        return jsonify({
            "message": "This record already has a transaction.",
            "signature": signature,
            "explorer_url": (
                f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
            ),
        })

    # Use the existing wallet; do not generate a new one.
    if not KEY_FILE.exists():
        return jsonify({
            "error": "Devnet wallet file not found."
        }), 500

    try:
        secret = json.loads(KEY_FILE.read_text())
        wallet = Keypair.from_bytes(bytes(secret))
        client = Client(RPC_URL)

        balance = client.get_balance(wallet.pubkey()).value

        if balance < 10_000_000:
            return jsonify({
                "error": (
                    f"Wallet balance is {balance / 1_000_000_000:.4f} SOL. "
                    "Devnet SOL is needed to submit the transaction. "
                    "No transaction was sent."
                )
            }), 400

        memo = f"CLARITY-SHA256:{evidence['sha256']}"

        instruction = Instruction(
            MEMO_PROGRAM,
            memo.encode("utf-8"),
            [
                AccountMeta(
                    wallet.pubkey(),
                    is_signer=True,
                    is_writable=False,
                )
            ],
        )

        blockhash = client.get_latest_blockhash().value.blockhash

        transaction = Transaction.new_signed_with_payer(
            [instruction],
            wallet.pubkey(),
            [wallet],
            blockhash,
        )

        signature = str(
            client.send_transaction(transaction).value
        )

        # Confirm before updating the local status.
        client.confirm_transaction(Signature.from_string(str(signature)))

        with get_db_connection() as connection:
            connection.execute("""
                UPDATE evidence_records
                SET blockchain_status = ?, tx_signature = ?
                WHERE id = ?
            """, (
                "Recorded on Solana Devnet",
                signature,
                record_id,
            ))

        return jsonify({
            "message": "Evidence hash recorded on Solana Devnet.",
            "signature": signature,
            "explorer_url": (
                f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
            ),
        })

    except Exception:
        app.logger.exception("Solana evidence transaction failed")

        return jsonify({
            "error": (
                "The Solana transaction failed. "
                "Check the Flask terminal for details."
            )
        }), 502

    
def decode_base58(value):
    """Decode a Base58-encoded Solana instruction's data."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0

    for char in value:
        number = number * 58 + alphabet.index(char)

    decoded = (
        number.to_bytes((number.bit_length() + 7) // 8, "big")
        if number
        else b""
    )

    leading_zeros = len(value) - len(value.lstrip("1"))
    return b"\x00" * leading_zeros + decoded


@app.route("/api/evidence/<int:record_id>/verify", methods=["POST"])
def verify_evidence(record_id):
    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Please select a file to verify."}), 400

    # Read the selected file temporarily; do not save its contents
    file_bytes = uploaded_file.read()

    if not file_bytes:
        return jsonify({"error": "The selected file is empty."}), 400

    calculated_hash = hashlib.sha256(file_bytes).hexdigest()

    with get_db_connection() as connection:
        evidence = connection.execute("""
            SELECT id, filename, sha256, tx_signature
            FROM evidence_records
            WHERE id = ?
        """, (record_id,)).fetchone()

    if evidence is None:
        return jsonify({"error": "Evidence record not found."}), 404

    expected_hash = evidence["sha256"]
    integrity_match = calculated_hash == expected_hash
    signature = evidence["tx_signature"]

    result = {
        "filename": evidence["filename"],
        "integrity_match": integrity_match,
        "calculated_hash": calculated_hash,
        "expected_hash": expected_hash,
        "blockchain_status": "Not verified",
        "blockchain_verified": False,
        "signature": signature,
    }

    if not signature:
        result["blockchain_status"] = (
            "No Solana transaction is linked to this record."
        )
        return jsonify(result)

    try:
        client = Client(RPC_URL)
        tx_signature = Signature.from_string(signature)

        response = client.get_transaction(
            tx_signature,
            encoding="json",
            max_supported_transaction_version=0,
        )

        tx = response.value

        if tx is None:
            result["blockchain_status"] = (
                "Transaction not found on Devnet."
            )
            return jsonify(result)

        if tx.transaction.meta is None or tx.transaction.meta.err is not None:
            result["blockchain_status"] = (
                "Transaction failed or has no execution metadata."
            )
            return jsonify(result)

        message = tx.transaction.transaction.message
        account_keys = message.account_keys
        memo_found = False

        for instruction in message.instructions:
            program_index = instruction.program_id_index
            program_id = str(account_keys[program_index])

            if program_id != str(MEMO_PROGRAM):
                continue

            memo_data = decode_base58(instruction.data).decode(
                "utf-8", errors="replace"
            )

            if memo_data == f"CLARITY-SHA256:{expected_hash}":
                memo_found = True
                break

        if memo_found:
            result["blockchain_status"] = (
                "Transaction succeeded and the expected hash was found."
            )
            result["blockchain_verified"] = True
        else:
            result["blockchain_status"] = (
                "Transaction succeeded, but the expected hash "
                "was not found in its Memo Program instructions."
            )

    except Exception:
        app.logger.exception("Evidence verification failed")
        result["blockchain_status"] = (
            "Could not verify the blockchain record. "
            "Check the Flask terminal for details."
        )

    return jsonify(result)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "application": "Clarity Practice Security",
    })


init_db()

if __name__ == "__main__":
    app.run(debug=True)