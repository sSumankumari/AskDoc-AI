document.addEventListener("DOMContentLoaded", () => {
    // Configuration
    const API_BASE_URL = window.location.origin;

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

    // New Chat button logic
    const newChatBtn = document.getElementById("new-chat-btn");
    newChatBtn.addEventListener("click", () => {
        // Clear summary, chat, suggestions, and reset placeholders
        clearSummary();
        clearChat();
        clearSuggestions();
    });

    function clearSummary() {
        document.getElementById("summary-content").innerHTML = `
            <div class="summary-placeholder" id="summary-placeholder">
                <i class="fas fa-file-alt"></i>
                <p>No document analyzed yet.<br>Upload or specify a document to see its summary here.</p>
            </div>
            <div class="summary-loading hidden">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Generating summary...</span>
            </div>
        `;
        document.getElementById("document-info").textContent = "";
    }
    function clearChat() {
        document.getElementById("chat-messages").innerHTML = "";
        document.getElementById("chat-placeholder").classList.remove("hidden");
    }
    function clearSuggestions() {
        document.getElementById("suggestions").innerHTML = "";
        document.getElementById("suggestions").classList.add("hidden");
    }

    // Status handling
    function showStatus(message) {
        document.getElementById("status-text").textContent = message;
        document.getElementById("status-section").classList.remove("hidden");
        document.getElementById("progress-fill").style.width = "0%";
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 90) {
                clearInterval(interval);
                return;
            }
            width += Math.random() * 10;
            document.getElementById("progress-fill").style.width = Math.min(width, 90) + "%";
        }, 200);
    }
    function hideStatus() {
        document.getElementById("progress-fill").style.width = "100%";
        setTimeout(() => {
            document.getElementById("status-section").classList.add("hidden");
        }, 500);
    }

    // Show summary
    function showSummary(markdownContent, metadata = {}) {
        const summaryContent = document.getElementById("summary-content");
        const documentInfo = document.getElementById("document-info");
        summaryContent.innerHTML = marked.parse(markdownContent || "No summary available.");
        document.getElementById("summary-placeholder")?.classList.add("hidden");
        let infoText = '';
        if (metadata.source_type) infoText += `Source: ${metadata.source_type.toUpperCase()} • `;
        if (metadata.word_count) infoText += `Words: ${metadata.word_count.toLocaleString()} • `;
        if (metadata.content_length) infoText += `Characters: ${metadata.content_length.toLocaleString()}`;
        if (metadata.filename) infoText += ` • File: ${metadata.filename}`;
        if (metadata.title && metadata.source_type === 'url') infoText += ` • Title: ${metadata.title}`;
        documentInfo.textContent = infoText;
    }

    // Show chat
    function showQASection() {
        // Only reveal placeholder if not yet chatting
        document.getElementById("chat-placeholder").classList.remove("hidden");
    }

    // PDF/URL upload logic (unchanged function names)
    async function handlePDFUpload(file) {
        if (!file || file.type !== "application/pdf") {
            showError("Please upload a valid PDF file.");
            return;
        }
        if (file.size > 16 * 1024 * 1024) {
            showError("File size exceeds 16MB limit.");
            return;
        }
        showStatus("Processing PDF document...");
        try {
            const formData = new FormData();
            formData.append('pdf', file);
            const response = await fetch(`${API_BASE_URL}/api/analyze`, { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to process PDF');
            hideStatus();
            showSummary(result.summary_markdown, result.metadata);
            showQASection();
            await loadSuggestedQuestions();
        } catch (error) {
            hideStatus();
            showError(`Failed to process PDF: ${error.message}`);
        }
    }

    // URL Submit logic
    const urlForm = document.getElementById("url-form");
    const urlInput = document.getElementById("url-input");
    urlForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;
        showStatus("Fetching and analyzing the web page...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to analyze URL');
            hideStatus();
            showSummary(result.summary_markdown, result.metadata);
            showQASection();
            await loadSuggestedQuestions();
        } catch (error) {
            hideStatus();
            showError(`Failed to analyze URL: ${error.message}`);
        }
    });

    // Q&A Section logic
    const questionForm = document.getElementById("question-form");
    const questionInput = document.getElementById("question-input");
    const chatMessages = document.getElementById("chat-messages");

    questionForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;
        // Add user message
        appendMessage("user", question);
        questionInput.value = "";
        document.getElementById("chat-placeholder").classList.add("hidden");
        // Show typing indicator
        const typingId = showTypingIndicator();
        try {
            const response = await fetch(`${API_BASE_URL}/api/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question })
            });
            const result = await response.json();
            removeTypingIndicator(typingId);
            if (!response.ok) throw new Error(result.error || 'Failed to get answer');
            appendMessage("ai", result.answer);
            if (result.context_used > 0) appendContextInfo(result.context_used);
        } catch (error) {
            removeTypingIndicator(typingId);
            appendMessage("ai", `Sorry, I encountered an error: ${error.message}`);
        }
    });

    // Suggested Questions logic
    const suggestBtn = document.getElementById("suggest-questions");
    const suggestionsBox = document.getElementById("suggestions");
    const suggestQuestion = document.getElementById("question-input");

    // Hide suggestions by default on load
    suggestionsBox.classList.add("hidden");

    suggestBtn.addEventListener("click", async () => {
        // Toggle behavior: show if hidden, hide if visible
        if (!suggestionsBox.classList.contains("hidden")) {
            suggestionsBox.classList.add("hidden");
            return;
        }
        await loadSuggestedQuestions();
        suggestionsBox.classList.remove("hidden");
    });

    // Hide suggestions when user focuses or types in the input
    suggestQuestion.addEventListener("focus", () => {
        suggestionsBox.classList.add("hidden");
    });
    suggestQuestion.addEventListener("input", () => {
        suggestionsBox.classList.add("hidden");
    });

    async function loadSuggestedQuestions() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/suggest`);
            const result = await response.json();
            if (response.ok && result.suggestions) {
                suggestionsBox.innerHTML = result.suggestions.map(q =>
                    `<button class="suggestion">${q}</button>`
                ).join("");
                // Add click handlers for new suggestions
                document.querySelectorAll(".suggestion").forEach(btn => {
                    btn.addEventListener("click", () => {
                        suggestQuestion.value = btn.textContent;
                        suggestionsBox.classList.add("hidden");
                        suggestQuestion.focus();
                    });
                });
            }
        } catch (error) {
            console.error('Failed to load suggestions:', error);
        }
    }

    // Message handling
    function appendMessage(sender, text) {
        const msg = document.createElement("div");
        msg.classList.add("message", sender);
        msg.innerHTML = sender === "ai" ? marked.parse(text) : `<p>${text}</p>`;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    function showTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const msg = document.createElement("div");
        msg.classList.add("message", "ai", "typing");
        msg.id = typingId;
        msg.innerHTML = `<p><i class="fas fa-spinner fa-spin"></i> Thinking...</p>`;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return typingId;
    }
    function removeTypingIndicator(typingId) {
        const element = document.getElementById(typingId);
        if (element) element.remove();
    }
    function appendContextInfo(contextCount) {
        const info = document.createElement("div");
        info.classList.add("context-info");
        info.innerHTML = `<small><i class="fas fa-info-circle"></i> Used ${contextCount} relevant document sections</small>`;
        chatMessages.appendChild(info);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Refresh summary
    document.getElementById("refresh-summary").addEventListener("click", async () => {
        showStatus("Refreshing summary...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/analyze/summary`);
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to refresh summary');
            hideStatus();
            showSummary(result.summary_markdown, result.metadata);
        } catch (error) {
            hideStatus();
            showError(`Failed to refresh summary: ${error.message}`);
        }
    });

    // Error modal handling
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
        if (e.target === errorModal) errorModal.classList.add("hidden");
    });

    // Check if document is already loaded on page load
    checkDocumentStatus();
    async function checkDocumentStatus() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/analyze/status`);
            const result = await response.json();
            if (response.ok && result.ready) {
                const summaryResponse = await fetch(`${API_BASE_URL}/api/analyze/summary`);
                const summaryResult = await summaryResponse.json();
                if (summaryResponse.ok) {
                    showSummary(summaryResult.summary_markdown, summaryResult.metadata);
                    showQASection();
                    await loadSuggestedQuestions();
                }
            }
        } catch (error) {
            // Silently handle
            console.log('No document currently loaded');
        }
    }

    // Utility function to check backend health
    async function checkBackendHealth() {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            if (!response.ok) throw new Error('Backend not responding');
            return true;
        } catch (error) {
            showError('Backend server is not available. Please make sure the Flask server is running.');
            return false;
        }
    }
    checkBackendHealth();
});