from app import get_db_connection

evidence_hash = (
    "fd783b5527453b8e60032d3f52d6c05d23eb03d20dcd5a74b0c1f81a0fbb5798"
)

signature = (
    "EPrgu6SaesApbviPqb9zLwadEE6b7uekfysG2Keovff2P4Eemdt4L2pc7UtpgZsHZV78pjv9FW57oCvVBzZcCJC"
)

with get_db_connection() as connection:
    result = connection.execute(
        """
        UPDATE evidence_records
        SET blockchain_status = ?, tx_signature = ?
        WHERE sha256 = ?
        """,
        ("Recorded on Solana Devnet", signature, evidence_hash),
    )

    print(f"Updated {result.rowcount} evidence record(s).")
