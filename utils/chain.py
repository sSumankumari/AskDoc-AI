import os
import time
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
        """
        Generate a detailed, structured summary for the document using chunked summarization to avoid token limit errors.
        """
        # Split the document into manageable chunks for summarization (e.g., 2000-3000 characters or less)
        doc = Document(page_content=document_text)
        chunks = self.text_splitter.split_documents([doc])

        chunk_summaries = []
        max_chunks = 12  # To avoid hitting token limits, you may wish to limit total number of chunks summarized

        logger.info(f"Summarizing {min(len(chunks), max_chunks)} chunks out of {len(chunks)} for summary.")

        for idx, chunk in enumerate(chunks[:max_chunks]):
            prompt = (
                "Read the following section of a document and generate a concise bullet-point summary. "
                "Use '-' or '*' for bullets. Be specific to the content. Keep the summary under 120 words.\n\n"
                f"Section {idx + 1}:\n{chunk.page_content}\n\nSummary:"
            )
            try:
                chunk_summary = self.llm_generate(prompt, max_tokens=350)
                chunk_summaries.append(chunk_summary.strip())
            except Exception as e:
                logger.error(f"Error summarizing chunk {idx + 1}: {e}")

        # Combine all chunk summaries into a final summary
        combined_summaries = "\n\n".join(chunk_summaries)
        final_prompt = (
            "You are an expert document summarizer. Combine the following summaries into a single, detailed, bullet-point summary "
            "with section headers if appropriate. Avoid repetition and capture all main points.\n\n"
            f"{combined_summaries}\n\n"
            "Final Summary:"
        )
        try:
            final_summary = self.llm_generate(final_prompt, max_tokens=600)
            return final_summary.strip()
        except Exception as e:
            logger.error(f"Error during final summary combination: {e}")
            # As fallback, return joined chunk summaries
            return combined_summaries.strip()

    def llm_generate(self, prompt, max_tokens=500, max_retries=5):
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
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                data = response.json()
                # Handle rate limit (429) with Groq-specific retry logic
                if response.status_code == 429:
                    msg = data.get("error", {}).get("message", "")
                    logger.error(f"LLM API error (429): {msg}")
                    # Try to extract "Please try again in Xs." or "in Xms."
                    wait_match = re.search(r"Please try again in ([\d\.]+)(ms|s)", msg)
                    if wait_match:
                        wait_time = float(wait_match.group(1))
                        unit = wait_match.group(2)
                        if unit == "ms":
                            wait_time = wait_time / 1000.0
                        logger.warning(f"Rate limit hit, sleeping for {wait_time + 0.1:.2f} seconds...")
                        time.sleep(wait_time + 0.1)  # Add a small buffer
                        continue  # Retry after waiting
                    else:
                        # If we can't parse, default to 1.5s and try again
                        logger.warning("Rate limit hit, couldn't parse wait time, sleeping for 1.5s")
                        time.sleep(1.5)
                        continue
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
                logger.error(f"Exception during LLM call (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Exception during LLM call after {max_retries} retries: {str(e)}")
                else:
                    time.sleep(2)  # Fallback wait before retry


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