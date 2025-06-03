// Utility to show/hide sections
function showSection(sectionId) {
  document.getElementById(sectionId).classList.remove('hidden');
}
function hideSection(sectionId) {
  document.getElementById(sectionId).classList.add('hidden');
}

const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const urlInput = document.getElementById('urlInput');
const summarySection = document.getElementById('summarySection');
const summaryContent = document.getElementById('summaryContent');
const refreshSummaryBtn = document.getElementById('refreshSummaryBtn');
const qaSection = document.getElementById('qaSection');
const qaForm = document.getElementById('qaForm');
const questionInput = document.getElementById('questionInput');
const answersDiv = document.getElementById('answers');

let currentDocId = null; // Track the current document/context

uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  // Reset
  summaryContent.textContent = '';
  answersDiv.innerHTML = '';
  hideSection('summarySection');
  hideSection('qaSection');
  currentDocId = null;

  const file = fileInput.files[0];
  const url = urlInput.value.trim();

  if (!file && !url) {
    alert('Please select a file or provide a URL.');
    return;
  }

  let formData = new FormData();
  if (file) formData.append('file', file);
  if (url) formData.append('url', url);

  try {
    // Example: POST /api/upload, expects { doc_id }
    const response = await fetch('/api/upload', { method: 'POST', body: formData });
    if (!response.ok) throw new Error('Upload failed');
    const data = await response.json();
    currentDocId = data.doc_id;
    showSection('summarySection');
    showSection('qaSection');
    loadSummary();
  } catch (err) {
    alert('Failed to upload: ' + err.message);
  }
});

async function loadSummary() {
  if (!currentDocId) return;
  summaryContent.textContent = 'Generating summary...';
  try {
    // Example: GET /api/summary?doc_id=...
    const response = await fetch(`/api/summary?doc_id=${encodeURIComponent(currentDocId)}`);
    if (!response.ok) throw new Error('Could not get summary');
    const data = await response.json();
    summaryContent.textContent = data.summary || 'No summary available.';
  } catch (err) {
    summaryContent.textContent = 'Error loading summary: ' + err.message;
  }
}

refreshSummaryBtn.addEventListener('click', loadSummary);

qaForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question || !currentDocId) return;

  // Show user's question
  const userBubble = document.createElement('div');
  userBubble.textContent = question;
  userBubble.className = 'answer-bubble user-bubble';
  answersDiv.appendChild(userBubble);

  // Show loading bubble for AI's answer
  const aiBubble = document.createElement('div');
  aiBubble.textContent = 'Thinking...';
  aiBubble.className = 'answer-bubble';
  answersDiv.appendChild(aiBubble);

  // Scroll to bottom
  answersDiv.scrollTop = answersDiv.scrollHeight;

  try {
    // Example: POST /api/ask, expects { answer }
    const resp = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: currentDocId, question })
    });
    if (!resp.ok) throw new Error('Could not get answer');
    const data = await resp.json();
    aiBubble.textContent = data.answer || 'No answer available.';
  } catch (err) {
    aiBubble.textContent = 'Error: ' + err.message;
  }

  questionInput.value = '';
});