// Display Date
document.getElementById("today").textContent =
    new Intl.DateTimeFormat("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric"
    }).format(new Date());

const checkboxes = document.querySelectorAll(".task-check");

// Update Dashboard's Progress Display
function updateProgress() {
    const completed = [...checkboxes].filter(box => box.checked).length;
    const total = checkboxes.length;
    const remaining = total - completed;
    const percentage = total === 0 ? 0 : (completed / total) * 100;

    document.getElementById("completed-count").textContent = completed;
    document.getElementById("remaining-count").textContent = remaining;
    document.getElementById("progress-fill").style.width =
        percentage + "%";

    document.getElementById("progress-caption").textContent =
        completed === total
            ? "All demonstration tasks completed."
            : completed === 0
                ? "A first step towards better security."
                : "You're making progress. Keep going.";

    checkboxes.forEach(box => {
        const id = box.id.split("-")[1];
        const card = document.querySelector(`[data-task="${id}"]`);
        const status = document.getElementById(`status-${id}`);

        if (card) {
            card.classList.toggle("completed", box.checked);
        }

        if (status) {
            status.textContent = box.checked
                ? "Completed · Demo only"
                : "Not completed";
            status.classList.toggle("done", box.checked);
        }
    });
}

// Load Saved Checklist from Flask & SQLite
async function loadChecklist() {
    const response = await fetch("/api/checklist");

    if (!response.ok) {
        throw new Error("Could not load the checklist.");
    }

    const items = await response.json();

    items.forEach(item => {
        const checkbox = document.getElementById(`task-${item.id}`);

        if (checkbox) {
            checkbox.checked = item.completed;
            checkbox.dataset.savedChecked = String(item.completed);
        }
    });

    updateProgress();
}

// Save Checkbox Change to Database
checkboxes.forEach(box => {
    box.addEventListener("change", async () => {
        const completed = box.checked;
        const id = box.id.split("-")[1];

        // Update Screen Immediately
        updateProgress();

        try {
            const response = await fetch(`/api/checklist/${id}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ completed })
            });

            if (!response.ok) {
                throw new Error("The change could not be saved.");
            }

            // Remember Last Successfully Saved Value
            box.dataset.savedChecked = String(completed);
        } catch (error) {
            // Restore Previous Value if Saving Failed
            box.checked = box.dataset.savedChecked === "true";
            updateProgress();

            alert(
                "Could not save your change. Please check that Flask is running and try again."
            );

            console.error("Checklist save failed:", error);
        }
    });
});

// Expand & Collapse Task Guidance
document.querySelectorAll("[data-guidance]").forEach(button => {
    button.addEventListener("click", () => {
        const id = button.dataset.guidance;
        const panel = document.getElementById(`guidance-${id}`);
        const isOpen = panel.classList.toggle("open");

        button.textContent = isOpen ? "Hide guidance ↑" : "View guidance ↓";
        button.setAttribute("aria-expanded", String(isOpen));
    });
});

// Navigation Links
document.querySelectorAll(".nav-item").forEach(link => {
    link.addEventListener("click", event => {
        const href = link.getAttribute("href");

        if (href && href.startsWith("#") &&
            document.querySelector(href)) {
            event.preventDefault();

            document.querySelectorAll(".nav-item").forEach(item =>
                item.classList.remove("active")
            );

            link.classList.add("active");

            document.querySelector(href).scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }
    });
});

// Load Saved Data
loadChecklist().catch(error => {
    console.error("Checklist loading failed:", error);
    updateProgress();
    alert("Could not load saved checklist data. Please check Flask.");
});

// Load Evidence Records
const evidenceFile = document.getElementById("evidence-file");
const evidenceButton = document.getElementById("create-evidence-button");
const evidenceMessage = document.getElementById("evidence-message");
const evidenceResult = document.getElementById("evidence-result");
const evidenceList = document.getElementById("evidence-list");

async function loadEvidenceRecords() {
    const response = await fetch("/api/evidence");
    if (!response.ok) throw new Error("Could not load evidence records.");

    const records = await response.json();
    document.getElementById("evidence-count").textContent = records.length;
    evidenceList.replaceChildren();

    if (records.length === 0) {
        evidenceList.textContent = "No evidence records created yet.";
        return;
    }

    records.forEach(record => {
        const card = document.createElement("article");
        const title = document.createElement("h4");
        const memo = document.createElement("p");
        const hash = document.createElement("code");
        const status = document.createElement("p");
        const button = document.createElement("button");

        title.textContent = record.filename;
        memo.textContent = "Memo: " + (record.memo || "No memo added.");
        hash.textContent = record.sha256;
        hash.className = "evidence-hash";
        status.textContent =
            "Status: " + record.blockchain_status +
            " · Created: " + new Date(record.created_at).toLocaleString();

        button.textContent = record.tx_signature
            ? "View Solana transaction"
            : "Record hash on Solana Devnet";

        button.addEventListener("click", async () => {
            if (record.tx_signature) {
                window.open(
                    "https://explorer.solana.com/tx/" +
                    encodeURIComponent(record.tx_signature) +
                    "?cluster=devnet",
                    "_blank",
                    "noopener,noreferrer"
                );
                return;
            }

            button.disabled = true;
            button.textContent = "Submitting...";
            status.textContent = "Checking wallet and submitting transaction...";

            try {
                const result = await fetch(
                    `/api/evidence/${record.id}/record`,
                    { method: "POST" }
                );
                const data = await result.json();

                if (!result.ok) {
                    throw new Error(data.error || "Transaction failed.");
                }

                status.textContent = data.message;

                if (data.explorer_url) {
                    const link = document.createElement("a");
                    link.href = data.explorer_url;
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";
                    link.textContent = "View confirmed transaction";
                    card.appendChild(link);
                }

                await loadEvidenceRecords();
            } catch (error) {
                status.textContent = error.message;
                button.disabled = false;
                button.textContent = "Retry Solana recording";
            }
        });

        card.append(title, memo, hash, status, button);
        evidenceList.appendChild(card);
    });
}

evidenceButton.addEventListener("click", async () => {
    const file = evidenceFile.files[0];

    if (!file) {
        evidenceMessage.textContent = "Please select a file first.";
        return;
    }

    evidenceButton.disabled = true;
    evidenceMessage.textContent = "Calculating hash and saving record...";
    evidenceResult.hidden = true;

    try {
        const formData = new FormData();
        formData.append("file", file);
        const evidenceMemo = document.getElementById("evidence-memo");
        formData.append("memo", evidenceMemo.value.trim());

        const response = await fetch("/api/evidence", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not create the record.");
        }

        document.getElementById("evidence-filename").textContent =
            result.filename;
        document.getElementById("evidence-hash").textContent =
            result.sha256;
        document.getElementById("evidence-blockchain-status").textContent =
            result.blockchain_status;

        evidenceResult.hidden = false;
        evidenceMessage.textContent =
            "Evidence record saved successfully.";
        await loadEvidenceRecords();
    } catch (error) {
        evidenceMessage.textContent = error.message;
    } finally {
        evidenceButton.disabled = false;
    }
});

loadEvidenceRecords().catch(error => {
    evidenceList.textContent = error.message;
});