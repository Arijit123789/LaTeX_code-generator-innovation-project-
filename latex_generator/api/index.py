import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Gemini / Generative Language Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Allow overriding the model via env var; default to a widely-available model
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "text-bison-001")

# NOTE:
# The correct REST endpoint for the Google Generative Language API follows this pattern:
#   POST https://generativelanguage.googleapis.com/v1/models/{model}:generate?key={API_KEY}
# Some older or different clients used `:generateContent` which is not supported for all models.
BASE_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models"
GEMINI_API_URL = f"{BASE_GEMINI_API_URL}/{GEMINI_MODEL}:generate?key={GEMINI_API_KEY}"


@app.route('/api/list-models', methods=['GET'])
def list_models():
    """
    Helper endpoint to list available models from the Generative Language API.
    This can help debug "model not found" issues.
    """
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    try:
        url = f"{BASE_GEMINI_API_URL}?key={GEMINI_API_KEY}"
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
        # Build a request payload matching the v1 REST API for text generation models.
        # Many models accept a 'prompt' object with a 'text' field; tune temperature/maxOutputTokens as needed.
        payload = {
            "prompt": {
                "text": prompt
            },
            # optional tuning params
            "temperature": float(data.get("temperature", 0.2)),
            "maxOutputTokens": int(data.get("maxOutputTokens", 800))
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        response_data = response.json()

        # Robust parsing for different response shapes across models / API versions.
        raw_latex = None

        # Common structure: response_data["candidates"][0]["output"]
        candidates = response_data.get("candidates") or []
        if candidates:
            first = candidates[0]
            # Known keys that may carry the generated text across different models/versions:
            if isinstance(first, dict):
                raw_latex = first.get("output") or first.get("text")
                # older/other shape: first["content"]["parts"][0]["text"]
                if not raw_latex and "content" in first:
                    try:
                        parts = first["content"].get("parts") if isinstance(first["content"], dict) else None
                        if parts and len(parts) > 0 and isinstance(parts[0], dict):
                            raw_latex = parts[0].get("text")
                    except Exception:
                        raw_latex = None
        else:
            # Some responses put generated text at top-level keys
            raw_latex = response_data.get("output") or response_data.get("text")

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
        # Provide useful debugging hints when the model isn't found or supported
        status_code = None
        try:
            status_code = e.response.status_code
        except Exception:
            pass

        # If the error text mentions "not found" or "generateContent", surface a helpful hint
        error_text = str(e)
        if e.response is not None:
            try:
                body = e.response.json()
                error_text = body.get("error", body)
            except Exception:
                error_text = e.response.text or error_text

        hint = ""
        if "not found" in error_text or "generateContent" in error_text or (status_code == 404):
            hint = (
                "The selected model or method is not available for the v1 generate endpoint. "
                "Try calling /api/list-models to see available models, or set GEMINI_MODEL to a supported model "
                "(e.g. text-bison-001) via environment variables."
            )

        return jsonify({"error": f"API Request Error: {error_text}", "hint": hint}), 502

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

    # Fixed render service URL (remove markdown-style brackets)
    RENDER_SERVICE_URL = "https://latex.yt/api/savetex"

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

        # Use JSON for the rendering service (it may accept form-data, but JSON is typical)
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
