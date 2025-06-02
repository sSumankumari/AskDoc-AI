# AskDoc-AI

**Smart AI-powered tool to summarize and interact with web content and documents using LangChain, FAISS, and LLaMA 3 via Groq.**

## Features

- 📄 **PDF Processing** - Upload and analyze PDF documents
- 🌐 **Web Content Analysis** - Extract and summarize content from URLs
- 🤖 **AI-Powered Q&A** - Ask questions about your documents using LLaMA 3
- 🔍 **Vector Search** - FAISS-powered semantic search for accurate answers
- ⚡ **Fast Processing** - Groq API for lightning-fast AI responses

## Tech Stack

- **LangChain** - Document processing and AI workflows
- **FAISS** - Vector database for semantic search
- **Groq API** - LLaMA 3 model access
- **PyPDF2** - PDF text extraction

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/AskDoc-AI.git
cd AskDoc-AI
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment**
```bash
# Create .env file and add your Groq API key
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```

4. **Run the application**
```bash
python main.py
```

## Usage

1. Run the script with a URL or PDF file path
2. The AI will process and summarize the content
3. Ask questions interactively via command line
4. Get AI-powered answers with source references

## Requirements

- Python 3.8+
- Groq API key (free at [groq.com](https://groq.com))

## Conclusion
AskDoc-AI provides a powerful and efficient way to analyze, summarize, and interact with documents and web content using advanced AI technologies. Explore its features and customize it to fit your workflow.
