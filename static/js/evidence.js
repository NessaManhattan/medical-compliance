
async function showRecords() {
    const container = document.getElementById("records");

    try {
        const response = await fetch("/api/evidence");

        if (!response.ok) {
            throw new Error("Could not load evidence records.");
        }

        const records = await response.json();
        container.replaceChildren();

        if (records.length === 0) {
            container.textContent = "No evidence records found.";
            return;
        }

        records.forEach(record => {
            const card = document.createElement("section");
            card.className = "record";

            const heading = document.createElement("h2");
            heading.textContent = record.filename;

            const date = document.createElement("p");
            date.textContent =
                "Created: " +
                new Date(record.created_at).toLocaleString();

            const memo = document.createElement("p");
            memo.textContent = "Memo: " + (record.memo || "No memo added.");

            const hashLabel = document.createElement("p");
            hashLabel.textContent = "SHA-256 fingerprint:";

            const hash = document.createElement("code");
            hash.textContent = record.sha256;

            const status = document.createElement("p");
            status.textContent =
                "Blockchain status: " + record.blockchain_status;

            card.append(heading, date, memo, hashLabel, hash, status);

            if (record.tx_signature) {
                const signature = document.createElement("p");
                signature.textContent =
                    "Transaction signature: " + record.tx_signature;

                const link = document.createElement("a");
                link.href =
                    "https://explorer.solana.com/tx/" +
                    encodeURIComponent(record.tx_signature) +
                    "?cluster=devnet";
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = "View transaction on Solana Explorer";

                card.append(signature, link);
            }

            const verifyHeading = document.createElement("h3");
            verifyHeading.textContent = "Verify file integrity";

            const fileInput = document.createElement("input");
            fileInput.type = "file";
            fileInput.setAttribute(
                "aria-label",
                "Choose a file to verify against " + record.filename
            );

            const verifyButton = document.createElement("button");
            verifyButton.type = "button";
            verifyButton.textContent = "Verify file";

            const result = document.createElement("div");
            result.className = "verification-result";
            result.setAttribute("aria-live", "polite");

            verifyButton.addEventListener("click", async () => {
                if (!fileInput.files.length) {
                    result.textContent = "Please select a file first.";
                    return;
                }

                const formData = new FormData();
                formData.append("file", fileInput.files[0]);

                verifyButton.disabled = true;
                result.textContent = "Verifying file and blockchain record...";

                try {
                    const verifyResponse = await fetch(
                        `/api/evidence/${record.id}/verify`,
                        {
                            method: "POST",
                            body: formData
                        }
                    );

                    const data = await verifyResponse.json();

                    if (!verifyResponse.ok) {
                        throw new Error(
                            data.error || "Verification request failed."
                        );
                    }

                    result.replaceChildren();

                    const integrity = document.createElement("p");
                    integrity.textContent = data.integrity_match
                        ? "File integrity: MATCH"
                        : "File integrity: MISMATCH";

                    const blockchain = document.createElement("p");
                    blockchain.textContent =
                        "Blockchain: " + data.blockchain_status;

                    const calculated = document.createElement("p");
                    calculated.textContent =
                        "Calculated SHA-256: " + data.calculated_hash;

                    result.append(integrity, blockchain, calculated);

                    if (data.signature) {
                        const link = document.createElement("a");
                        link.href =
                            "https://explorer.solana.com/tx/" +
                            encodeURIComponent(data.signature) +
                            "?cluster=devnet";
                        link.target = "_blank";
                        link.rel = "noopener noreferrer";
                        link.textContent = "Inspect transaction";
                        result.appendChild(link);
                    }
                } catch (error) {
                    result.textContent = error.message;
                } finally {
                    verifyButton.disabled = false;
                }
            });

            card.append(
                document.createElement("hr"),
                verifyHeading,
                fileInput,
                verifyButton,
                result
            );

            container.appendChild(card);
        });
    } catch (error) {
        container.textContent = error.message;
    }
}

showRecords();