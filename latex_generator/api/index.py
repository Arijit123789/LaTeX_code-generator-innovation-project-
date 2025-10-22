import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Gemini / Generative Language Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Use a current, recommended Gemini model.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0-pro-latest")

# NOTE:
# The correct REST endpoint for the current Google AI Gemini API (v1beta) is:
#   POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}
BASE_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_API_URL = f"{BASE_GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"


@app.route('/api/list-models', methods=['GET'])
def list_models():
    """
    Helper endpoint to list available models from the Generative Language API.
    This can help debug "model not found" issues.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    try:
        # Use the v1beta endpoint for listing models
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

    if not prompt:
        return jsonify({"error": "Prompt is missing"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    try:
        # Build a request payload matching the v1beta generateContent API
        # The structure is {"contents": [{"parts": [{"text": ...}]}]}
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            # Optional tuning params (naming is also different)
            "generationConfig": {
                "temperature": float(data.get("temperature", 0.2)),
                "maxOutputTokens": int(data.get("maxOutputTokens", 800))
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_data = response.json()

        # Robust parsing for the Gemini API (v1beta) response shape.
        raw_latex = None
        try:
            # The text is in candidates[0].content.parts[0].text
            raw_latex = response_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            # If the structure is not as expected, return an error
            error_details = response_data.get("error", response_data)
            return jsonify({
                "error": f"API response format unexpected. Parsing failed: {e}", 
                "details": error_details
            }), 500

        if not raw_latex:
            # If model returns an informative error, include it
            msg = response_data.get("error") or response_data
            return jsonify({"error": "API response format unexpected or empty output.", "details": msg}), 500

        # Clean up markdown/code fences if present
        raw_latex = raw_latex.strip()
        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex[len("```latex"):].strip()
        if raw_latex.startswith("```"):
            raw_latex = raw_latex[len("```"):].strip()
        if raw_latex.endswith("```"):
            raw_latex = raw_latex[:-3].strip()

        final_response = {
            "latexCode": raw_latex,
        }
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        status_code = None
        error_text = str(e)
        if e.response is not None:
            status_code = e.response.status_code
            try:
                body = e.response.json()
                error_text = body.get("error", {}).get("message", body)
            except Exception:
                error_text = e.response.text or error_text
        
        hint = ""
        if status_code == 404:
             hint = "The model name might be wrong or the API endpoint is incorrect."
        elif status_code == 400:
             hint = "The request payload (JSON) is likely malformed. Check the 'contents' structure."
        elif status_code == 429:
             hint = "You have exceeded your API quota. Check your Google AI Studio billing."

        return jsonify({"error": f"API Request Error: {status_code} - {error_text}", "hint": hint}), 502

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500


@app.route('/api/render', methods=['POST'])
def render_diagram():
    data = request.json or {}
    latex_code = data.get('latexCode')

    if not latex_code:
        return jsonify({"error": "No LaTeX code provided"}), 400

    # This rendering service endpoint seems correct
    RENDER_SERVICE_URL = "[https://latex.yt/api/savetex](https://latex.yt/api/savetex)"

    try:
        full_document = (
            "\\documentclass{article}\n"
            "\\usepackage{tikz}\n"
            "\\usepackage{amsmath}\n"
            "\\pagestyle{empty}\n"
            "\\begin{document}\n"
            f"{latex_code}\n"
            "\\end{document}"
        )

        payload = {
            "tex": full_document,
            "resolution": 200,
            "dev": "svg"
        }

        response = requests.post(RENDER_SERVICE_URL, json=payload, timeout=30)
        response.raise_for_status()

        svg_image_data = response.json().get('result')

        if not svg_image_data:
            return jsonify({"error": "Rendering service failed to return an image.", "details": response.json()}), 500

        return jsonify({"svgImage": svg_image_data})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to rendering service: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"An internal rendering error occurred: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
