import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# The Flask app instance must be named 'app' for Vercel
app = Flask(__name__)
CORS(app)

# On Vercel, the API key is set as an Environment Variable in the dashboard
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

@app.route('/api/generate', methods=['POST'])
def generate_latex():
    data = request.json
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "Prompt is missing"}), 400
    
    if not CLAUDE_API_KEY:
        # This error will show up in Vercel logs if the key is not set
        return jsonify({"error": "CLAUDE_API_KEY is not configured on the server."}), 500

    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1024,
            "system": "You are a LaTeX expert. Given a user's prompt, provide only the raw LaTeX code required to represent their request. Do not include any explanations, surrounding text, or markdown code fences.",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        raw_latex = response_data['content'][0]['text']

        # We only need to send the raw code now, the frontend will handle rendering
        final_response = {
            "latexCode": raw_latex,
        }
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API Request Error: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

# Note: The if __name__ == '__main__': block is not needed for Vercel
# but is useful for local testing with the Vercel CLI.