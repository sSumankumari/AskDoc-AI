import os
import logging
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from config import get_config
from routes.analyze import analyze_bp
from routes.question import question_bp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for document state
document_store = {
    'retrieval_chain': None,
    'document_text': '',
    'document_metadata': {}
}

def get_document_store():
    return document_store

def set_document_store(retrieval_chain, document_text, metadata=None):
    document_store['retrieval_chain'] = retrieval_chain
    document_store['document_text'] = document_text
    document_store['document_metadata'] = metadata or {}

def create_app():
    # Set static_folder and template_folder to match your structure
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )
    config_class = get_config()
    app.config.from_object(config_class)

    try:
        config_class.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    # Enable CORS for all origins (adjust in production!)
    CORS(app, origins="*")

    # Register API blueprints
    app.register_blueprint(analyze_bp, url_prefix='/api')
    app.register_blueprint(question_bp, url_prefix='/api')

    # Health check
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'Document Analyzer API',
            'version': '1.0.0'
        })

    # Serve frontend (index.html) for root and any non-API path
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path.startswith("api/") or path.startswith("static/"):
            # Let Flask serve API and static requests normally
            return abort(404)
        return render_template('index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    config = get_config()
    host = getattr(config, "HOST", "0.0.0.0")
    port = getattr(config, "PORT", 5000)
    debug = getattr(config, "DEBUG", True)

    logger.info(f"Starting Document Analyzer API on {host}:{port}")
    logger.info(f"Debug mode: {debug}")

    app.run(
        host=host,
        port=port,
        debug=debug
    )