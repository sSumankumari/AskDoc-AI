import requests
import json
import logging
from typing import Optional, List, Dict, Any
from langchain.llms.base import LLM
from config import get_config

logger = logging.getLogger(__name__)


class GroqLLM(LLM):
    """
    Custom LangChain LLM implementation for Groq API
    Uses the OpenAI-compatible chat completions endpoint
    """

    api_key: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    api_url: Optional[str] = None

    def __init__(self, **kwargs):
        config = get_config()

        # Provide defaults if not passed explicitly
        if 'model' not in kwargs or kwargs['model'] is None:
            kwargs['model'] = config.GROQ_MODEL
        if 'max_tokens' not in kwargs or kwargs['max_tokens'] is None:
            kwargs['max_tokens'] = config.MAX_TOKENS
        if 'api_url' not in kwargs or kwargs['api_url'] is None:
            kwargs['api_url'] = config.GROQ_API_URL

        super().__init__(**kwargs)

        if not self.api_key:
            raise ValueError("Groq API key is required")

    @property
    def _llm_type(self) -> str:
        return "groq_llm"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """
        Make a call to the Groq API
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Enhanced system prompt for best-quality, well-formatted responses
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a highly intelligent, accurate, and helpful AI assistant. "
                        "Always provide clear, concise, and well-structured answers using proper markdown formatting. "
                        "Use bullet points, code blocks, and tables where appropriate. "
                        "If you reference code or examples, format them using markdown. "
                        "Explain your reasoning when needed. "
                        "If you cannot answer based on the given context, respond with: "
                        "\"I don't have enough information to answer this question based on the provided context.\""
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": 0.7,
                "top_p": 1,
                "stream": False
            }

            if stop:
                data["stop"] = stop

            logger.info(f"Making Groq API request with model: {self.model}")

            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"Groq API error ({response.status_code}): {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            result = response.json()

            # Extract the generated text
            if 'choices' in result and len(result['choices']) > 0:
                generated_text = result['choices'][0]['message']['content']
                logger.info("Successfully received response from Groq API")
                return generated_text.strip()
            else:
                raise Exception("No response generated from Groq API")

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error calling Groq API: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from Groq API: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Unexpected error in Groq API call: {str(e)}")
            raise

    def generate_with_context(self, question: str, context: str) -> str:
        """
        Generate answer with specific context
        """
        prompt = (
            f"## Context\n"
            f"{context}\n\n"
            f"## Question\n"
            f"{question}\n\n"
            "### Instructions\n"
            "- Answer the question based strictly on the provided context.\n"
            "- If code is needed, use markdown code blocks.\n"
            "- Use bullet points and tables if appropriate.\n"
            "- Provide a clear and well-formatted response.\n"
            "- If the answer is not in the context, reply with:\n"
            "  > I don't have enough information to answer this question based on the provided context.\n\n"
            "## Answer"
        )

        return self._call(prompt)

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "api_url": self.api_url,
            "type": self._llm_type
        }