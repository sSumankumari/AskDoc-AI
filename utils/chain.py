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

    def get_document_summary(self, document_text: str, max_length: int = 500) -> str:
        """
        Generate a summary of the document
        """
        try:
            if len(document_text) <= max_length:
                return document_text

            # Take first part and add ellipsis
            summary = document_text[:max_length].rsplit(' ', 1)[0]
            return summary + "..."

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return document_text[:max_length] + "..."


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