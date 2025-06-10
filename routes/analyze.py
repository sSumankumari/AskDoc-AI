import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from utils.scraper import WebScraper
from utils.pdf_reader import PDFProcessor
from utils.chain import DocumentProcessor
from utils.validators import validate_url, validate_file
from config import get_config

logger = logging.getLogger(__name__)

# Create blueprint
analyze_bp = Blueprint('analyze', __name__)

# Initialize processors
web_scraper = WebScraper()
pdf_processor = PDFProcessor()
doc_processor = DocumentProcessor()


@analyze_bp.route('/analyze', methods=['POST'])
def analyze_document():
    """
    Analyze a document from URL or PDF upload
    """
    try:
        config = get_config()

        # Import here to avoid circular imports
        from app import get_document_store, set_document_store

        document_data = None
        source_type = None

        # Check if PDF file was uploaded
        if 'pdf' in request.files:
            pdf_file = request.files['pdf']

            if pdf_file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            # Validate file
            if not validate_file(pdf_file, ['pdf']):
                return jsonify({'error': 'Invalid PDF file'}), 400

            logger.info(f"Processing PDF upload: {pdf_file.filename}")

            try:
                # Process PDF
                pdf_data = pdf_processor.read_pdf_content(pdf_file)
                document_data = {
                    'content': pdf_data['content'],
                    'metadata': {
                        **pdf_data['metadata'],
                        'source_type': 'pdf',
                        'filename': secure_filename(pdf_file.filename),
                        'file_size': pdf_data.get('char_count', 0)
                    }
                }
                source_type = 'pdf'

            except Exception as e:
                logger.error(f"PDF processing error: {str(e)}")
                return jsonify({'error': f'Failed to process PDF: {str(e)}'}), 400

        # Check if URL was provided
        elif request.is_json:
            data = request.get_json()
            url = data.get('url', '').strip()

            if not url:
                return jsonify({'error': 'No URL provided'}), 400

            # Validate URL
            if not validate_url(url):
                return jsonify({'error': 'Invalid URL format'}), 400

            logger.info(f"Processing URL: {url}")

            try:
                # Scrape URL content
                url_data = web_scraper.scrape_url_content(url)
                document_data = {
                    'content': url_data['content'],
                    'metadata': {
                        **url_data['metadata'],
                        'source_type': 'url',
                        'title': url_data.get('title', 'Untitled'),
                        'word_count': url_data.get('word_count', 0)
                    }
                }
                source_type = 'url'

            except Exception as e:
                logger.error(f"URL scraping error: {str(e)}")
                return jsonify({'error': f'Failed to scrape URL: {str(e)}'}), 400

        else:
            return jsonify({'error': 'No URL or PDF file provided'}), 400

        # Validate document content
        if not document_data['content'].strip():
            return jsonify({'error': 'No readable content found in the document'}), 400

        # Process document and create retrieval chain
        try:
            logger.info("Creating retrieval chain...")
            retrieval_chain = doc_processor.process_document(
                document_data['content'],
                document_data['metadata']
            )

            # Store in global state
            set_document_store(
                retrieval_chain,
                document_data['content'],
                document_data['metadata']
            )

            # Generate summary (returns markdown with bullets/sections)
            summary_markdown = doc_processor.get_document_summary(document_data['content'])

            # Prepare response
            response_data = {
                'success': True,
                'message': f'Successfully analyzed {source_type.upper()}',
                'summary_markdown': summary_markdown,
                'metadata': {
                    'source_type': source_type,
                    'content_length': len(document_data['content']),
                    'word_count': len(document_data['content'].split()),
                    **document_data['metadata']
                },
                'ready_for_questions': True
            }

            logger.info(f"Successfully processed {source_type} document")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            return jsonify({'error': f'Failed to process document: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@analyze_bp.route('/analyze/status', methods=['GET'])
def get_analysis_status():
    """
    Get current analysis status
    """
    try:
        from app import get_document_store

        doc_store = get_document_store()

        if doc_store['retrieval_chain'] is None:
            return jsonify({
                'ready': False,
                'message': 'No document has been analyzed yet'
            })

        metadata = doc_store.get('document_metadata', {})

        return jsonify({
            'ready': True,
            'message': 'Document is ready for questions',
            'metadata': {
                'source_type': metadata.get('source_type', 'unknown'),
                'content_length': len(doc_store.get('document_text', '')),
                'processed_at': metadata.get('processed_at'),
                **metadata
            }
        })

    except Exception as e:
        logger.error(f"Error getting analysis status: {str(e)}")
        return jsonify({'error': 'Failed to get status'}), 500


@analyze_bp.route('/analyze/summary', methods=['GET'])
def get_document_summary():
    """
    Get document summary (as markdown, for pointer/bullet formatting)
    """
    try:
        from app import get_document_store

        doc_store = get_document_store()

        if not doc_store['document_text']:
            return jsonify({'error': 'No document has been analyzed'}), 404

        # Generate summary with markdown bullets/sections
        summary_markdown = doc_processor.get_document_summary(doc_store['document_text'])
        metadata = doc_store.get('document_metadata', {})

        return jsonify({
            'summary_markdown': summary_markdown,
            'metadata': metadata,
            'statistics': {
                'total_characters': len(doc_store['document_text']),
                'total_words': len(doc_store['document_text'].split()),
                'summary_length': len(summary_markdown)
            }
        })

    except Exception as e:
        logger.error(f"Error getting document summary: {str(e)}")
        return jsonify({'error': 'Failed to get summary'}), 500
