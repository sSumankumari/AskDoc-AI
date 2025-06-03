document.addEventListener("DOMContentLoaded", () => {
    // Tab switching logic
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanels.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(`${btn.dataset.tab}-panel`).classList.add("active");
        });
    });

    // PDF Upload logic
    const uploadArea = document.getElementById("upload-area");
    const pdfInput = document.getElementById("pdf-input");

    uploadArea.addEventListener("click", () => pdfInput.click());

    uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadArea.classList.add("dragging");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("dragging");
    });

    uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadArea.classList.remove("dragging");
        const file = e.dataTransfer.files[0];
        handlePDFUpload(file);
    });

    pdfInput.addEventListener("change", () => {
        const file = pdfInput.files[0];
        handlePDFUpload(file);
    });

    function handlePDFUpload(file) {
        if (!file || file.type !== "application/pdf") {
            showError("Please upload a valid PDF file.");
            return;
        }

        if (file.size > 16 * 1024 * 1024) {
            showError("File size exceeds 16MB limit.");
            return;
        }

        showStatus("Processing document...");
        simulateProcessing(() => {
            showSummary("This is a sample summary generated from the uploaded PDF.");
            showQASection();
        });
    }

    // URL Submit logic
    const urlForm = document.getElementById("url-form");
    const urlInput = document.getElementById("url-input");

    urlForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        showStatus("Fetching and analyzing the web page...");
        simulateProcessing(() => {
            showSummary(`This is a summary of the content from <a href="${url}" target="_blank">${url}</a>.`);
            showQASection();
        });
    });

    // Status handling
    function showStatus(message) {
        document.getElementById("status-text").textContent = message;
        document.getElementById("status-section").classList.remove("hidden");
        document.getElementById("progress-fill").style.width = "0%";
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) clearInterval(interval);
            width += 5;
            document.getElementById("progress-fill").style.width = width + "%";
        }, 100);
    }

    // Simulate processing (replace with actual fetch)
    function simulateProcessing(callback) {
        setTimeout(() => {
            document.getElementById("status-section").classList.add("hidden");
            callback();
        }, 2000);
    }

    // Summary handling
    function showSummary(content) {
        const summarySection = document.getElementById("summary-section");
        const summaryContent = document.getElementById("summary-content");

        summaryContent.innerHTML = `<p>${content}</p>`;
        summarySection.classList.remove("hidden");
    }

    // Q&A Section
    function showQASection() {
        document.getElementById("qa-section").classList.remove("hidden");
    }

    const questionForm = document.getElementById("question-form");
    const questionInput = document.getElementById("question-input");
    const chatMessages = document.getElementById("chat-messages");

    questionForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;

        appendMessage("user", question);
        questionInput.value = "";

        setTimeout(() => {
            appendMessage("ai", `This is a generated answer for: "${question}"`);
        }, 1000);
    });

    // Suggested Questions
    const suggestBtn = document.getElementById("suggest-questions");
    const suggestionsBox = document.getElementById("suggestions");

    suggestBtn.addEventListener("click", () => {
        const suggestions = [
            "What is the main topic of the document?",
            "Summarize the key points.",
            "What are the conclusions?",
            "What are the key statistics mentioned?"
        ];

        suggestionsBox.innerHTML = suggestions.map(q =>
            `<button class="suggestion">${q}</button>`).join("");
        suggestionsBox.classList.remove("hidden");

        document.querySelectorAll(".suggestion").forEach(btn => {
            btn.addEventListener("click", () => {
                questionInput.value = btn.textContent;
            });
        });
    });

    // Append message to chat
    function appendMessage(sender, text) {
        const msg = document.createElement("div");
        msg.classList.add("message", sender);
        msg.innerHTML = `<p>${text}</p>`;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Refresh summary
    document.getElementById("refresh-summary").addEventListener("click", () => {
        showStatus("Refreshing summary...");
        simulateProcessing(() => {
            showSummary("This is an updated summary of the document.");
        });
    });

    // Error modal
    const errorModal = document.getElementById("error-modal");
    const errorMessage = document.getElementById("error-message");
    const closeModal = document.getElementById("close-modal");

    function showError(msg) {
        errorMessage.textContent = msg;
        errorModal.classList.remove("hidden");
    }

    closeModal.addEventListener("click", () => {
        errorModal.classList.add("hidden");
    });

    window.addEventListener("click", (e) => {
        if (e.target === errorModal) {
            errorModal.classList.add("hidden");
        }
    });
});
