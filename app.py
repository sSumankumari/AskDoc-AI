import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import get_config
from routes.analyze import analyze_bp
from routes.question import question_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)

    # Validate configuration
    try:
        config_class.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Enable CORS
    CORS(app, origins=['*'])

    # Register blueprints
    app.register_blueprint(analyze_bp, url_prefix='/api')
    app.register_blueprint(question_bp, url_prefix='/api')

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'Document Analyzer API',
            'version': '1.0.0'
        })

    # Global error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'The requested resource was not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File too large', 'message': 'The uploaded file is too large'}), 413

    return app


# Global variables for document state
document_store = {
    'retrieval_chain': None,
    'document_text': '',
    'document_metadata': {}
}


def get_document_store():
    """Get the global document store"""
    return document_store


def set_document_store(retrieval_chain, document_text, metadata=None):
    """Update the global document store"""
    document_store['retrieval_chain'] = retrieval_chain
    document_store['document_text'] = document_text
    document_store['document_metadata'] = metadata or {}


if __name__ == '__main__':
    app = create_app()
    config = get_config()

    logger.info(f"Starting Document Analyzer API on {config.HOST}:{config.PORT}")
    logger.info(f"Debug mode: {config.DEBUG}")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )