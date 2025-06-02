import logging
from flask import Blueprint, request, jsonify
from utils.validators import validate_question

logger = logging.getLogger(__name__)

# Create blueprint
question_bp = Blueprint('question', __name__)


@question_bp.route('/ask', methods=['POST'])
def ask_question():
    """
    Ask a question about the analyzed document
    """
    try:
        # Import here to avoid circular imports
        from app import get_document_store

        # Get request data
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        question = data.get('question', '').strip()

        # Validate question
        if not question:
            return jsonify({'error': 'Question is required'}), 400

        if not validate_question(question):
            return jsonify({'error': 'Invalid question format'}), 400

        # Check if document has been processed
        doc_store = get_document_store()

        if doc_store['retrieval_chain'] is None:
            return jsonify({
                'error': 'No document has been analyzed yet. Please analyze a URL or PDF first.'
            }), 400

        logger.info(f"Processing question: {question[:100]}...")

        try:
            # Get answer from retrieval chain
            answer = doc_store['retrieval_chain'].run(question)

            # Get relevant context for transparency
            context = doc_store['retrieval_chain'].get_relevant_context(question, max_docs=2)

            response_data = {
                'question': question,
                'answer': answer,
                'context_used': len(context),
                'source_metadata': doc_store.get('document_metadata', {}),
                'context_preview': context[:1] if context else []  # Show first context for transparency
            }

            logger.info("Successfully generated answer")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return jsonify({
                'error': 'Failed to generate answer',
                'details': str(e)
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in ask endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@question_bp.route('/context', methods=['POST'])
def get_relevant_context():
    """
    Get relevant context for a question without generating an answer
    """
    try:
        from app import get_document_store

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        question = data.get('question', '').strip()
        max_contexts = data.get('max_contexts', 3)

        if not question:
            return jsonify({'error': 'Question is required'}), 400

        if not validate_question(question):
            return jsonify({'error': 'Invalid question format'}), 400

        # Check if document has been processed
        doc_store = get_document_store()

        if doc_store['retrieval_chain'] is None:
            return jsonify({
                'error': 'No document has been analyzed yet'
            }), 400

        try:
            # Get relevant contexts
            contexts = doc_store['retrieval_chain'].get_relevant_context(
                question,
                max_docs=min(max_contexts, 5)  # Limit to max 5 contexts
            )

            return jsonify({
                'question': question,
                'contexts': contexts,
                'total_contexts': len(contexts)
            })

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return jsonify({'error': 'Failed to retrieve context'}), 500

    except Exception as e:
        logger.error(f"Error in context endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@question_bp.route('/suggest', methods=['GET'])
def suggest_questions():
    """
    Suggest questions based on the analyzed document
    """
    try:
        from app import get_document_store

        doc_store = get_document_store()

        if not doc_store['document_text']:
            return jsonify({'error': 'No document has been analyzed'}), 400

        # Generate basic question suggestions based on document metadata
        metadata = doc_store.get('document_metadata', {})
        source_type = metadata.get('source_type', 'document')

        suggestions = []

        # Generic suggestions
        suggestions.extend([
            "What is the main topic of this document?",
            "Can you summarize the key points?",
            "What are the most important findings mentioned?"
        ])

        # Source-specific suggestions
        if source_type == 'pdf':
            suggestions.extend([
                "What is the purpose of this document?",
                "Are there any conclusions or recommendations?",
                "What methodology was used?"
            ])
        elif source_type == 'url':
            if metadata.get('title'):
                suggestions.append(f"What does this article say about {metadata['title']}?")
            suggestions.extend([
                "What is the author's main argument?",
                "Are there any statistics or data mentioned?",
                "What examples are provided?"
            ])

        return jsonify({
            'suggestions': suggestions[:6],  # Limit to 6 suggestions
            'source_type': source_type,
            'document_info': {
                'word_count': len(doc_store['document_text'].split()),
                'char_count': len(doc_store['document_text'])
            }
        })

    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        return jsonify({'error': 'Failed to generate suggestions'}), 500