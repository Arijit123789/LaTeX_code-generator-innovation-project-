import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

# =========================================================
# Flask App Setup
# =========================================================
app = Flask(__name__)
CORS(app)

# =========================================================
# Gemini Configuration
# =========================================================

# Set your API key in environment variables
# Example:
# export GEMINI_API_KEY=your_api_key_here

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Free tier Gemini model
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

BASE_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GEMINI_API_URL = (
    f"{BASE_GEMINI_API_URL}/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

# =========================================================
# Health Check
# =========================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Gemini LaTeX API is running successfully"
    })


# =========================================================
# List Available Models
# =========================================================
@app.route('/api/list-models', methods=['GET'])
def list_models():

    if not GEMINI_API_KEY:
        return jsonify({
            "error": "GEMINI_API_KEY is not configured"
        }), 500

    try:
        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models?key={GEMINI_API_KEY}"
        )

        response = requests.get(url, timeout=20)

        response.raise_for_status()

        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": f"Failed to fetch models: {str(e)}"
        }), 500


# =========================================================
# Generate LaTeX Code using Gemini
# =========================================================
@app.route('/api/generate', methods=['POST'])
def generate_latex():

    try:

        data = request.json or {}

        prompt = data.get("prompt")

        if not prompt:
            return jsonify({
                "error": "Prompt is missing"
            }), 400

        if not GEMINI_API_KEY:
            return jsonify({
                "error": "GEMINI_API_KEY is not configured"
            }), 500

        # =================================================
        # System Instruction
        # =================================================
        system_instruction = """
You are an expert LaTeX assistant.

The user will describe:
- equations
- diagrams
- tables
- TikZ figures
- mathematical content

You must ONLY return valid raw LaTeX code.

DO NOT:
- explain anything
- use markdown
- use code fences
- write introductory text

Return only pure LaTeX code.
"""

        full_prompt = (
            f"{system_instruction}\n\n"
            f"USER REQUEST:\n{prompt}\n\n"
            f"LATEX CODE:"
        )

        # =================================================
        # Gemini Payload
        # =================================================
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": full_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": float(
                    data.get("temperature", 0.2)
                ),
                "maxOutputTokens": int(
                    data.get("maxOutputTokens", 4096)
                )
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        # =================================================
        # API Call
        # =================================================
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        response_data = response.json()

        # =================================================
        # Parse Response
        # =================================================
        if not response_data.get("candidates"):

            prompt_feedback = response_data.get("promptFeedback")

            if prompt_feedback:
                return jsonify({
                    "error": "Prompt blocked",
                    "details": prompt_feedback
                }), 400

            return jsonify({
                "error": "No candidates returned",
                "details": response_data
            }), 500

        candidate = response_data["candidates"][0]

        finish_reason = candidate.get("finishReason")

        if finish_reason and finish_reason != "STOP":

            return jsonify({
                "error": f"Generation stopped: {finish_reason}"
            }), 500

        raw_latex = (
            candidate["content"]["parts"][0]["text"]
        )

        if not raw_latex:
            return jsonify({
                "error": "No LaTeX generated"
            }), 500

        # =================================================
        # Cleanup Markdown if Gemini adds it
        # =================================================
        raw_latex = raw_latex.strip()

        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex.replace(
                "```latex", "", 1
            ).strip()

        if raw_latex.startswith("```"):
            raw_latex = raw_latex.replace(
                "```", "", 1
            ).strip()

        if raw_latex.endswith("```"):
            raw_latex = raw_latex[:-3].strip()

        # =================================================
        # Final Response
        # =================================================
        return jsonify({
            "latexCode": raw_latex
        })

    except requests.exceptions.RequestException as e:

        status_code = None
        error_text = str(e)

        if e.response is not None:

            status_code = e.response.status_code

            try:
                error_text = e.response.json()
            except Exception:
                error_text = e.response.text

        return jsonify({
            "error": f"Gemini API Error: {status_code}",
            "details": error_text
        }), 500

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500


# =========================================================
# Render LaTeX to SVG
# =========================================================
@app.route('/api/render', methods=['POST'])
def render_diagram():

    try:

        data = request.json or {}

        latex_code = data.get("latexCode")

        if not latex_code:
            return jsonify({
                "error": "No LaTeX code provided"
            }), 400

        # =================================================
        # External Render Service
        # =================================================
        RENDER_SERVICE_URL = "https://latex.yt/api/savetex"

        full_document = f"""
\\documentclass{{article}}
\\usepackage{{tikz}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\pagestyle{{empty}}

\\begin{{document}}

{latex_code}

\\end{{document}}
"""

        payload = {
            "tex": full_document,
            "resolution": 200,
            "dev": "svg"
        }

        response = requests.post(
            RENDER_SERVICE_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        svg_image_data = result.get("result")

        if not svg_image_data:
            return jsonify({
                "error": "SVG generation failed",
                "details": result
            }), 500

        return jsonify({
            "svgImage": svg_image_data
        })

    except requests.exceptions.RequestException as e:

        return jsonify({
            "error": f"Render service failed: {str(e)}"
        }), 500

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": f"Internal rendering error: {str(e)}"
        }), 500


# =========================================================
# Run Flask Server
# =========================================================
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        debug=True
    )
