import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback # Import traceback for logging

# --- App Setup ---
app = Flask(__name__)
CORS(app)

# --- Gemini / Generative Language Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# This is the correct model name from your API list
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

BASE_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_API_URL = f"{BASE_GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"


@app.route('/api/list-models', methods=['GET'])
def list_models():
    """
    Helper endpoint to list available models from the Generative Language API.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to call ListModels: {e}"}), 502


@app.route('/api/generate', methods=['POST'])
def generate_latex():
    data = request.json or {}
    prompt = data.get('prompt')

    # This line MUST be at the same indentation level as the line above
    if not prompt:
        return jsonify({"error": "Prompt is missing"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    # --- NEW System Prompt Logic ---
    # System instruction to guide the model
    system_instruction = (
        "You are an expert LaTeX assistant. "
        "The user will provide a description of a diagram, equation, or table. "
        "You must respond with ONLY the raw LaTeX code required to generate it. "
        "Do not include any introductory text, explanations, markdown, or code fences like 'Here is the code:' or '```latex'. "
        "Your response should be only the valid LaTeX code itself and nothing else."
    )
    
    # Combine the system instruction with the user's prompt
    full_prompt = f"{system_instruction}\n\nUSER REQUEST: {prompt}\n\nLATEX CODE:"
    # --- End of new logic ---

    try:
        # Build a request payload matching the v1beta generateContent API
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            # Use the new 'full_prompt' here
                            "text": full_prompt 
                        }
                    ]
                }
            ],
            # Optional tuning params
            "generationConfig": {
                "temperature": float(data.get("temperature", 0.2)),
                # Increased token limit
                "maxOutputTokens": int(data.get("maxOutputTokens", 15000))
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=500)
        response.raise_for_status()
        response_data = response.json()

        # --- ROBUST PARSING LOGIC ---
        raw_latex = None
        try:
            # Check if candidates list exists and is not empty
            if not response_data.get("candidates"):
                prompt_feedback = response_data.get("promptFeedback")
                if prompt_feedback:
                    block_reason = prompt_feedback.get("blockReason", "Unknown")
                    safety_ratings = prompt_feedback.get("safetyRatings", "N/A")
                    return jsonify({
                        "error": f"Prompt was blocked by API.",
                        "details": f"Reason: {block_reason}. Safety Ratings: {safety_ratings}"
                    }), 400
                return jsonify({"error": "API returned an empty response with no candidates.", "details": response_data}), 500

            candidate = response_data["candidates"][0]
            finish_reason = candidate.get("finishReason")
            if finish_reason and finish_reason != "STOP":
                # Handle MAX_TOKENS error
                if finish_reason == "MAX_TOKENS":
                     return jsonify({
                        "error": "Generation stopped: The model's response was too long.",
                        "details": f"Reason: {finish_reason}. Try a more specific prompt."
                    }), 500
                
                safety_ratings = candidate.get("safetyRatings", "N/A")
                return jsonify({
                    "error": f"Generation stopped for reason: {finish_reason}",
                    "details": f"Safety Ratings: {safety_ratings}"
                }), 500

            if (
                candidate.get("content") and
                candidate["content"].get("parts") and
                len(candidate["content"]["parts"]) > 0 and
                candidate["content"]["parts"][0].get("text")
            ):
                raw_latex = candidate["content"]["parts"][0]["text"]
            else:
                return jsonify({
                    "error": "API response format unexpected: 'text' part is missing.",
                    "details": candidate
                }), 500

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            error_details = response_data.get("error", response_data)
            return jsonify({
                "error": f"API response parsing failed unexpectedly: {e}",
                "details": error_details
            }), 500
        # --- END OF PARSING LOGIC ---

        if not raw_latex:
            return jsonify({"error": "API returned no text output.", "details": response_data}), 500

        # Clean up markdown/code fences if present
        raw_latex = raw_latex.strip()
        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex[len("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1

Push this clean code to GitHub and Vercel will boot it up perfectly!
