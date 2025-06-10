import io
import logging
from typing import Dict, Any, Optional
from PyPDF2 import PdfReader
import magic

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Enhanced PDF processor with better text extraction and validation
    """

    def __init__(self):
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        self.allowed_mime_types = [
            'application/pdf',
            'application/x-pdf',
            'application/acrobat',
            'applications/vnd.pdf',
            'text/pdf',
            'text/x-pdf'
        ]

    def validate_pdf_file(self, file_obj) -> bool:
        """
        Validate PDF file type and size
        """
        try:
            # Check file size
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(0)  # Reset to beginning

            if file_size > self.max_file_size:
                raise ValueError(f"File size ({file_size} bytes) exceeds maximum allowed size")

            # Check file type using python-magic
            file_content = file_obj.read(1024)  # Read first 1KB for type detection
            file_obj.seek(0)  # Reset to beginning

            # Use magic instance to detect MIME type
            magic_instance = magic.Magic(mime=True)
            mime_type = magic_instance.from_buffer(file_content)

            if mime_type not in self.allowed_mime_types:
                raise ValueError(f"Invalid file type: {mime_type}. Expected PDF file.")

            return True

        except Exception as e:
            logger.error(f"PDF validation error: {str(e)}")
            raise


    def read_pdf_content(self, file_obj) -> Dict[str, Any]:
        """
        Enhanced PDF reading with metadata extraction
        """
        try:
            # Validate the PDF file
            self.validate_pdf_file(file_obj)

            # Create PDF reader
            pdf_reader = PdfReader(file_obj)

            # Extract metadata
            metadata = self._extract_pdf_metadata(pdf_reader)

            # Extract text from all pages
            text_content = []
            page_count = len(pdf_reader.pages)

            logger.info(f"Processing PDF with {page_count} pages")

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        # Clean up the text
                        cleaned_text = self._clean_text(page_text)
                        if cleaned_text:
                            text_content.append(f"[Page {page_num}]\n{cleaned_text}")
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                    continue

            if not text_content:
                raise ValueError("No readable text found in the PDF file")

            full_text = '\n\n'.join(text_content)

            result = {
                'content': full_text,
                'metadata': metadata,
                'page_count': page_count,
                'word_count': len(full_text.split()),
                'char_count': len(full_text)
            }

            logger.info(f"Successfully extracted {result['char_count']} characters from PDF")
            return result

        except Exception as e:
            logger.error(f"Error reading PDF: {str(e)}")
            raise Exception(f"Failed to process PDF file: {str(e)}")

    def _extract_pdf_metadata(self, pdf_reader: PdfReader) -> Dict[str, Any]:
        """
        Extract metadata from PDF
        """
        metadata = {}

        try:
            if pdf_reader.metadata:
                # Standard PDF metadata fields
                metadata_fields = {
                    '/Title': 'title',
                    '/Author': 'author',
                    '/Subject': 'subject',
                    '/Creator': 'creator',
                    '/Producer': 'producer',
                    '/CreationDate': 'creation_date',
                    '/ModDate': 'modification_date'
                }

                for pdf_field, meta_field in metadata_fields.items():
                    if pdf_field in pdf_reader.metadata:
                        value = pdf_reader.metadata[pdf_field]
                        if value:
                            metadata[meta_field] = str(value)

            # Add technical metadata
            metadata['page_count'] = len(pdf_reader.pages)
            metadata['is_encrypted'] = pdf_reader.is_encrypted

        except Exception as e:
            logger.warning(f"Error extracting PDF metadata: {str(e)}")
            metadata['extraction_error'] = str(e)

        return metadata

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]

        # Remove empty lines
        lines = [line for line in lines if line]

        # Join lines with single newlines
        cleaned = '\n'.join(lines)

        # Remove excessive spaces
        import re
        cleaned = re.sub(r' +', ' ', cleaned)

        return cleaned.strip()

    def get_pdf_info(self, file_obj) -> Dict[str, Any]:
        """
        Get basic information about a PDF without full text extraction
        """
        try:
            self.validate_pdf_file(file_obj)
            pdf_reader = PdfReader(file_obj)

            return {
                'page_count': len(pdf_reader.pages),
                'is_encrypted': pdf_reader.is_encrypted,
                'metadata': self._extract_pdf_metadata(pdf_reader)
            }
        except Exception as e:
            logger.error(f"Error getting PDF info: {str(e)}")
            raise


# Convenience function for backward compatibility
def read_pdf_content(file_obj) -> str:
    """
    Simple function that returns just the content text
    """
    processor = PDFProcessor()
    result = processor.read_pdf_content(file_obj)
    return result['content']