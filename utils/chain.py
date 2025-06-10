import os
import logging
from typing import Dict, Any, List, Optional
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema import Document
from utils.groq_llm import GroqLLM
from config import get_config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Enhanced document processing with better chunking and retrieval
    """

    def __init__(self):
        config = get_config()
        self.chunk_size = config.CHUNK_SIZE
        self.chunk_overlap = config.CHUNK_OVERLAP
        self.embedding_model_name = config.EMBEDDING_MODEL
        self.vector_store_path = config.VECTOR_STORE_PATH
        self.groq_api_key = config.GROQ_API_KEY

        # Initialize components
        self.embeddings = None
        self.text_splitter = None
        self.groq_llm = None

        self._initialize_components()

    def _initialize_components(self):
        """
        Initialize the processing components
        """
        try:
            # Initialize embeddings
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

            # Initialize Groq LLM
            self.groq_llm = GroqLLM(api_key=self.groq_api_key)

            logger.info("Successfully initialized all components")

        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise

    def process_document(self, document_text: str, metadata: Dict[str, Any] = None) -> 'EnhancedRetrievalQA':
        """
        Process document and create retrieval chain
        """
        try:
            logger.info(f"Processing document with {len(document_text)} characters")

            # Create document object
            doc = Document(
                page_content=document_text,
                metadata=metadata or {}
            )

            # Split document into chunks
            chunks = self.text_splitter.split_documents([doc])
            logger.info(f"Split document into {len(chunks)} chunks")

            # Create vector store
            vectorstore = FAISS.from_documents(chunks, self.embeddings)

            # Create enhanced retrieval chain
            qa_chain = EnhancedRetrievalQA(
                llm=self.groq_llm,
                retriever=vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 4}
                ),
                document_metadata=metadata or {}
            )

            logger.info("Successfully created retrieval chain")
            return qa_chain

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    def get_document_summary(self, document_text):
        """Generate a detailed, structured summary for the document."""
        prompt = (
            "You are an expert document summarizer. Read the following text and generate a rich, detailed summary. "
            "The summary should:\n"
            "- Cover all major sections and key points.\n"
            "- Use clear, concise language.\n"
            "- Organize information as bullet points (use '-' or '*' for bullets) for clarity.\n"
            "- If possible, group bullets under section headers.\n"
            "- Avoid generic statements; be specific to the content.\n\n"
            "Document:\n"
            f"{document_text}\n\n"
            "Summary:"
        )
        # Replace this with your actual LLM/groq call
        response = self.llm_generate(prompt, max_tokens=500)
        return response.strip()

    def llm_generate(self, prompt, max_tokens=500):
        # This should call your LLM API (Groq, OpenAI, etc.)
        import requests
        api_key = os.getenv("GROQ_API_KEY") or self.groq_api_key
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            data = response.json()
            # Check for errors in the API response
            if response.status_code != 200:
                logger.error(f"LLM API error (status {response.status_code}): {data.get('error', data)}")
                logger.error(f"LLM API full response: {response.text}")
                raise RuntimeError(f"LLM API error: {data.get('error', data)}")
            if "choices" not in data or not data["choices"]:
                logger.error(f"LLM API response missing 'choices': {data}")
                logger.error(f"LLM API full response: {response.text}")
                raise RuntimeError(f"LLM API response missing 'choices': {data}")
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Exception during LLM call: {str(e)}")
            raise RuntimeError(f"Exception during LLM call: {str(e)}")


class EnhancedRetrievalQA:
    """
    Enhanced retrieval QA chain with better context handling
    """

    def __init__(self, llm, retriever, document_metadata: Dict[str, Any] = None):
        self.llm = llm
        self.retriever = retriever
        self.document_metadata = document_metadata or {}

    def run(self, question: str) -> str:
        """
        Run the QA chain with enhanced context
        """
        try:
            logger.info(f"Processing question: {question[:100]}...")

            # Retrieve relevant documents
            relevant_docs = self.retriever.get_relevant_documents(question)

            if not relevant_docs:
                return "I couldn't find relevant information to answer your question."

            # Combine context from retrieved documents
            context_parts = []
            for i, doc in enumerate(relevant_docs):
                context_parts.append(f"Context {i + 1}: {doc.page_content}")

            context = "\n\n".join(context_parts)

            # Generate answer using the LLM
            answer = self.llm.generate_with_context(question, context)

            logger.info("Successfully generated answer")
            return answer

        except Exception as e:
            logger.error(f"Error in QA chain: {str(e)}")
            return f"I encountered an error while processing your question: {str(e)}"

    def get_relevant_context(self, question: str, max_docs: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant context without generating answer
        """
        try:
            relevant_docs = self.retriever.get_relevant_documents(question)

            contexts = []
            for i, doc in enumerate(relevant_docs[:max_docs]):
                contexts.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'relevance_rank': i + 1
                })

            return contexts

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []


# Convenience function for backward compatibility
def get_retrieval_chain(document_text: str) -> EnhancedRetrievalQA:
    """
    Simple function to create retrieval chain
    """
    processor = DocumentProcessor()
    return processor.process_document(document_text)