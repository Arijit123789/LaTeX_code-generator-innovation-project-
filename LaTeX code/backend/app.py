import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS  # <-- The fix is here

# Load the API key from the .env file
load_dotenv()

# --- Configuration ---
# Set up the Flask app
app = Flask(__name__)
CORS(app)  # <-- And the fix is here

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# AI Model Configuration
generation_config = {
  "temperature": 0.7,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

# This is the main instruction for the AI. It sets the context for all conversations.
SYSTEM_INSTRUCTION = """You are an expert AI assistant specializing in LaTeX. 
Your primary goal is to help users generate clean, correct, and well-formatted LaTeX code.
When a user asks for a visual diagram (like a flowchart, graph, or mind map), you MUST generate the code using Mermaid syntax.
When a user asks for a document, like a resume or an article, generate the complete LaTeX code.
When a user asks for a mathematical formula, generate the standard LaTeX math code.
Always be helpful and accurate. Enclose Mermaid code in ```mermaid ... ``` blocks.
"""

# Initialize the generative model
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",  # <-- This is the new, correct name
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION
)

# --- API Endpoint ---
@app.route('/api/generate', methods=['POST'])
def generate_content():
    data = request.json
    prompt = data.get('prompt')
    history = data.get('history', [])

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        chat_session = model.start_chat(history=history)
        response = chat_session.send_message(prompt)
        return jsonify({
            'response': response.text,
            'history': chat_session.history
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# --- Run the server ---
if __name__ == '__main__':
    # Make sure your script.js is fetching from the same port!
    app.run(port=5001, debug=True)