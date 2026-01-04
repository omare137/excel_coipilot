import matplotlib
matplotlib.use('Agg')

import os
import json
import base64
import pandas as pd
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import matplotlib.pyplot as plt
from datetime import datetime
import uuid

# Import our existing backend logic
from backend.gpt_agent import get_code_from_gpt
from backend.code_executor import execute_code
from backend.data_utils import clean_dataframe
from backend.archetecture import AgentRouter 


# Initialize Flask App
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# In-memory conversation storage (in production, use a database)
conversations = {}

def get_or_create_conversation(session_id):
    """Get or create a conversation for the given session ID"""
    if session_id not in conversations:
        conversations[session_id] = {
            'id': session_id,
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'current_agent': 'assistant'
        }
    return conversations[session_id]

def add_message_to_conversation(session_id, role, content, agent=None):
    """Add a message to the conversation history"""
    conversation = get_or_create_conversation(session_id)
    message = {
        'id': str(uuid.uuid4()),
        'role': role,  # 'user' or 'assistant'
        'content': content,
        'timestamp': datetime.now().isoformat(),
        'agent': agent
    }
    conversation['messages'].append(message)
    if agent:
        conversation['current_agent'] = agent
    return message

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/test', methods=['POST'])
def test_endpoint():
    """Simple test endpoint to check if requests are reaching the server"""
    try:
        data = request.get_json()
        return jsonify({
            "status": "success",
            "message": "Test endpoint working",
            "received_data": data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversation/<session_id>', methods=['GET'])
def get_conversation(session_id):
    """Get conversation history for a session"""
    try:
        conversation = get_or_create_conversation(session_id)
        return jsonify(conversation)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversation/<session_id>/messages', methods=['POST'])
def add_message(session_id):
    """Add a message to conversation history"""
    try:
        data = request.get_json()
        role = data.get('role', 'user')
        content = data.get('content', '')
        agent = data.get('agent')
        
        message = add_message_to_conversation(session_id, role, content, agent)
        return jsonify(message)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversation/<session_id>/clear', methods=['POST'])
def clear_conversation(session_id):
    """Clear conversation history for a session"""
    try:
        if session_id in conversations:
            conversations[session_id]['messages'] = []
            conversations[session_id]['current_agent'] = 'assistant'
        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """
    API endpoint to receive data from the Excel add-in,
    run the AI analysis, and return the result.
    """
    # 1) Parse JSON strictly and return clear errors (no broad try around parsing)
    raw_body = request.get_data(as_text=True)
    parsed = request.get_json(silent=True)
    if parsed is None:
        try:
            parsed = json.loads(raw_body)
        except Exception as parse_err:
            return jsonify({"error": f"Invalid JSON payload: {str(parse_err)}", "body": raw_body[:200]}), 400

    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except Exception as parse_err:
            return jsonify({"error": f"Invalid JSON envelope (string): {str(parse_err)}"}), 400

    if not isinstance(parsed, dict):
        return jsonify({"error": "JSON payload must be an object with keys 'prompt' and 'data'."}), 400

    prompt = parsed.get('prompt')
    data_json = parsed.get('data')  # May be a string or an array
    selected_agent = parsed.get('agent', 'assistant')  # Default to assistant
    session_id = parsed.get('session_id', 'default')  # Session ID for conversation history
    skip_ai = bool(parsed.get('skip_ai', False))

    if not prompt or data_json is None:
        return jsonify({"error": "Prompt and data are required."}), 400

    # 2) Convert data to DataFrame
    try:
        if isinstance(data_json, str):
            df_data = json.loads(data_json)
        else:
            df_data = data_json
        
        # Handle empty or invalid data
        if not df_data or len(df_data) == 0:
            return jsonify({
                "result": "No data selected. Please select some data in Excel first, or ask me a general question about Excel.",
                "agent": "assistant"
            })
        
        # Handle single row data (just headers)
        if len(df_data) == 1:
            return jsonify({
                "result": "Only headers selected. Please select data rows as well.",
                "agent": "assistant"
            })
        
        # Create DataFrame with proper error handling
        try:
            df = pd.DataFrame(df_data[1:], columns=df_data[0])
            df = clean_dataframe(df)
        except (IndexError, KeyError) as e:
            return jsonify({
                "result": "Invalid data format. Please select a proper data range in Excel.",
                "agent": "assistant"
            })

        # Fast path for testing without AI calls
        if skip_ai:
            preview = df.head(5).to_dict(orient='records')
            return jsonify({
                "result": {
                    "rows": int(df.shape[0]),
                    "cols": int(df.shape[1]),
                    "preview": preview
                },
                "agent": "Bypass (skip_ai)"
            })

        # Add user message to conversation history
        add_message_to_conversation(session_id, 'user', prompt, selected_agent)
        
        # Process with selected agent directly
        router = AgentRouter()
        result = router.process_with_agent(selected_agent, prompt, df)
        agent_name = router.get_agent_display_name(selected_agent)

        # Normalize result into a dict
        if isinstance(result, str):
            normalized = {"result": result}
        elif isinstance(result, dict):
            normalized = result
        else:
            normalized = {"result": str(result)}

        if isinstance(normalized, dict) and 'error' in normalized:
            return jsonify({"error": normalized['error']}), 500

        # Add assistant response to conversation history
        if plt.get_fignums():
            # Chart was created
            buf = BytesIO()
            plt.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close('all')
            
            response_text = "Chart created and inserted into your spreadsheet!"
            add_message_to_conversation(session_id, 'assistant', response_text, selected_agent)
            
            return jsonify({
                "image": image_base64, 
                "agent": agent_name,
                "result": response_text,
                "session_id": session_id
            })
        else:
            # If no chart, return any text result
            text_result = normalized.get('result', 'Analysis complete, but no specific output was generated.')
            add_message_to_conversation(session_id, 'assistant', text_result, selected_agent)
            
            return jsonify({
                "result": str(text_result), 
                "agent": agent_name,
                "session_id": session_id
            })

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    # Running in debug mode is convenient for development
    # Serve over HTTPS to avoid mixed-content when the taskpane is https
    cert_path = os.environ.get('SSL_CERT_PATH', 'server.pem')
    ssl_context = None
    if os.path.exists(cert_path):
        ssl_context = (cert_path, cert_path)
    app.run(port=5001, debug=True, ssl_context=ssl_context)