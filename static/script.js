document.addEventListener("DOMContentLoaded", () => {
    // Configuration
    const API_BASE_URL = window.location.origin; // Adjust if backend is on different port
    
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

            const response = await fetch(`${API_BASE_URL}/api/analyze`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to process PDF');
            }

            hideStatus();
            showSummary(result.summary, result.metadata);
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
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to analyze URL');
            }

            hideStatus();
            showSummary(result.summary, result.metadata);
            showQASection();
            await loadSuggestedQuestions();

        } catch (error) {
            hideStatus();
            showError(`Failed to analyze URL: ${error.message}`);
        }
    });

    // Status handling
    function showStatus(message) {
        document.getElementById("status-text").textContent = message;
        document.getElementById("status-section").classList.remove("hidden");
        document.getElementById("progress-fill").style.width = "0%";
        
        // Animate progress bar
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 90) { // Don't complete until actual response
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

    // Summary handling
    function showSummary(content, metadata = {}) {
        const summarySection = document.getElementById("summary-section");
        const summaryContent = document.getElementById("summary-content");
        const documentInfo = document.getElementById("document-info");

        summaryContent.innerHTML = `<p>${content}</p>`;
        
        // Display document metadata
        let infoText = '';
        if (metadata.source_type) {
            infoText += `Source: ${metadata.source_type.toUpperCase()} • `;
        }
        if (metadata.word_count) {
            infoText += `Words: ${metadata.word_count.toLocaleString()} • `;
        }
        if (metadata.content_length) {
            infoText += `Characters: ${metadata.content_length.toLocaleString()}`;
        }
        if (metadata.filename) {
            infoText += ` • File: ${metadata.filename}`;
        }
        if (metadata.title && metadata.source_type === 'url') {
            infoText += ` • Title: ${metadata.title}`;
        }
        
        documentInfo.textContent = infoText;
        summarySection.classList.remove("hidden");
    }

    // Q&A Section
    function showQASection() {
        document.getElementById("qa-section").classList.remove("hidden");
    }

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

        // Show typing indicator
        const typingId = showTypingIndicator();

        try {
            const response = await fetch(`${API_BASE_URL}/api/ask`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: question })
            });

            const result = await response.json();

            // Remove typing indicator
            removeTypingIndicator(typingId);

            if (!response.ok) {
                throw new Error(result.error || 'Failed to get answer');
            }

            // Add AI response
            appendMessage("ai", result.answer);

            // Show context info if available
            if (result.context_used > 0) {
                appendContextInfo(result.context_used);
            }

        } catch (error) {
            removeTypingIndicator(typingId);
            appendMessage("ai", `Sorry, I encountered an error: ${error.message}`);
        }
    });

    // Suggested Questions
    const suggestBtn = document.getElementById("suggest-questions");
    const suggestionsBox = document.getElementById("suggestions");

    suggestBtn.addEventListener("click", async () => {
        await loadSuggestedQuestions();
    });

    async function loadSuggestedQuestions() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/suggest`);
            const result = await response.json();

            if (response.ok && result.suggestions) {
                suggestionsBox.innerHTML = result.suggestions.map(q =>
                    `<button class="suggestion">${q}</button>`
                ).join("");
                suggestionsBox.classList.remove("hidden");

                // Add click handlers for suggestions
                document.querySelectorAll(".suggestion").forEach(btn => {
                    btn.addEventListener("click", () => {
                        questionInput.value = btn.textContent;
                        suggestionsBox.classList.add("hidden");
                        questionInput.focus();
                    });
                });
            }
        } catch (error) {
            console.error('Failed to load suggestions:', error);
        }
    }

    // Message handling functions
    function appendMessage(sender, text) {
        const msg = document.createElement("div");
        msg.classList.add("message", sender);
        msg.innerHTML = `<p>${text}</p>`;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const msg = document.createElement("div");
        msg.classList.add("message", "ai", "typing");
        msg.id = typingId;
        msg.innerHTML = `
            <p>
                <i class="fas fa-spinner fa-spin"></i> 
                Thinking...
            </p>
        `;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return typingId;
    }

    function removeTypingIndicator(typingId) {
        const element = document.getElementById(typingId);
        if (element) {
            element.remove();
        }
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

            if (!response.ok) {
                throw new Error(result.error || 'Failed to refresh summary');
            }

            hideStatus();
            showSummary(result.summary, result.metadata);

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
        if (e.target === errorModal) {
            errorModal.classList.add("hidden");
        }
    });

    // Check if document is already loaded on page load
    checkDocumentStatus();

    async function checkDocumentStatus() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/analyze/status`);
            const result = await response.json();

            if (response.ok && result.ready) {
                // Document is already loaded, show summary and Q&A
                const summaryResponse = await fetch(`${API_BASE_URL}/api/analyze/summary`);
                const summaryResult = await summaryResponse.json();
                
                if (summaryResponse.ok) {
                    showSummary(summaryResult.summary, summaryResult.metadata);
                    showQASection();
                    await loadSuggestedQuestions();
                }
            }
        } catch (error) {
            // Silently handle - probably no document loaded yet
            console.log('No document currently loaded');
        }
    }

    // Utility function to check backend health
    async function checkBackendHealth() {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            if (!response.ok) {
                throw new Error('Backend not responding');
            }
            return true;
        } catch (error) {
            showError('Backend server is not available. Please make sure the Flask server is running.');
            return false;
        }
    }

    // Check backend health on page load
    checkBackendHealth();
});