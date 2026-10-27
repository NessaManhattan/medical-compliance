# Clarity: Medical Compliance Evidence Prototype

Clarity is a lightweight prototype exploring how small medical practices can organize compliance-related tasks and maintain verifiable records of supporting evidence.

The project combines a compliance checklist, SHA-256 document fingerprinting, local evidence storage and a planned blockchain verification workflow using Solana.

## The Problem

Small medical practices may have limited IT security and compliance resources. Keeping track of compliance-related tasks and maintaining reliable evidence can be challenging.

Clarity explores how a simple dashboard and blockchain-based fingerprints could help organize evidence and make document changes easier to detect.

## Features

- **Compliance checklist:** Track compliance-related tasks and their completion status
- **Evidence uploads:** Upload a document and generate its SHA-256 fingerprint
- **Evidence records:** Store filenames, fingerprints, timestamps and blockchain transaction information in a local SQLite database
- **Privacy-conscious workflow:** Uploaded document contents are not retained by the current evidence-recording workflow
- **Solana integration:** Designed to record evidence fingerprints in Solana Devnet transaction memos so that recorded hashes can be independently checked

## Technology Stack

- Python
- Flask
- SQLite
- HTML, CSS and JavaScript
- SHA-256 hashing
- Solana Devnet
- Solana Python SDK and Solders

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip
- A Solana Devnet wallet for testing blockchain transactions

### 1. Clone the Repository

```bash
git clone https://github.com/NessaManhattan/medical-compliance
cd medical-compliance
```

### 2. Create a Virtual Environment

On Windows, open PowerShell in the project directory and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the Application

```powershell
python app.py
```

Open the following address in your browser:

http://127.0.0.1:5000

## How It Works

1. The user opens the Clarity dashboard and reviews the compliance checklist
2. The user uploads an evidence document
3. Clarity calculates the document's SHA-256 fingerprint
4. The fingerprint and associated metadata are stored in the local SQLite database
5. The blockchain workflow is intended to record the fingerprint in a Solana transaction memo
6. After a transaction is successfully confirmed, its signature can be used to inspect the transaction on Solana Explorer

A SHA-256 fingerprint can help detect whether a document has changed since its fingerprint was recorded. It does not, by itself, prove that a document is authentic or that a medical practice complies with applicable regulations.
## Current Project Status

The dashboard, compliance checklist, evidence upload, hash generation and local database functionality are implemented.

The Solana transaction workflow is implemented in the project but still requires a successful on-chain transaction to be demonstrated.

Clarity is an experimental prototype, not a certified compliance solution.

## Privacy and Security

- Uploaded evidence documents are not retained by the current evidence-recording workflow
- The local database stores evidence metadata and document fingerprints
- Never publish private keys, wallet keypair files, credentials, or sensitive medical documents
- Use sample documents and test accounts during development
- Blockchain transactions are publicly inspectable. Only record information suitable for public disclosure

## Future Improvements

- Complete and demonstrate on-chain fingerprint recording
- Improve document integrity verification and transaction status reporting
- Explore the workflow with small medical practices

## Project Purpose

Clarity explores how blockchain technology can support evidence integrity in healthcare-related compliance workflows. The goal is to provide a simple, understandable tool for small practices without requiring them to manage a complex compliance platform.

