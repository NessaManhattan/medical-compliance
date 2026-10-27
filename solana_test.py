import hashlib
import json
from pathlib import Path

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction

BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "devnet-keypair.json"
SAMPLE_FILE = BASE_DIR / "sample-evidence.txt"

RPC_URL = "https://api.devnet.solana.com"
MEMO_PROGRAM = Pubkey.from_string(
    "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
)

def load_or_create_wallet():
    if KEY_FILE.exists():
        secret = json.loads(KEY_FILE.read_text())
        return Keypair.from_bytes(bytes(secret))

    wallet = Keypair()
    KEY_FILE.write_text(json.dumps(list(bytes(wallet))))
    return wallet

def main():
    # Create Harmless Demonstration Evidence
    if not SAMPLE_FILE.exists():
        SAMPLE_FILE.write_text(
            "Clarity Demo: sample security review completed."
        )

    # Fingerprint the file. The file itself stays local
    file_hash = hashlib.sha256(SAMPLE_FILE.read_bytes()).hexdigest()
    print("SHA-256:", file_hash)

    client = Client(RPC_URL)
    wallet = load_or_create_wallet()
    print("Devnet wallet:", wallet.pubkey())

    # Obtain test SOL only if the wallet needs it
    balance = client.get_balance(wallet.pubkey()).value

    if balance < 10_000_000:
        print("Requesting Devnet test SOL...")
        airdrop = client.request_airdrop(
            wallet.pubkey(), 100_000_000
        )
        client.confirm_transaction(airdrop.value)
        print("Test SOL received.")

    # Record the fingerprint in a public Devnet memo
    memo = f"CLARITY-SHA256:{file_hash}"

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

    result = client.send_transaction(transaction)
    signature = result.value
    client.confirm_transaction(signature)

    print("\nSUCCESS! Hash recorded on Solana Devnet.")
    print("Transaction signature:", signature)
    print(
        "View transaction:",
        f"https://explorer.solana.com/tx/{signature}?cluster=devnet",
    )

if __name__ == "__main__":
    main()