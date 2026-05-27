import os
import requests
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)
CORS(app)

# =========================================================
# GEMINI CONFIG
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Stable Gemini model
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-1.5-flash"
)

BASE_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)

GEMINI_API_URL = (
    f"{BASE_GEMINI_API_URL}/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "AI LaTeX Generator Backend Running"
    })

# =========================================================
# LIST MODELS ROUTE
# =========================================================

@app.route("/api/list-models", methods=["GET"])
def list_models():

    try:

        if not GEMINI_API_KEY:
            return jsonify({
                "error": "GEMINI_API_KEY not found"
            }), 500

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models?key={GEMINI_API_KEY}"
        )

        response = requests.get(url, timeout=20)

        response.raise_for_status()

        return jsonify(response.json())

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# GENERATE LATEX
# =========================================================

@app.route("/api/generate", methods=["POST"])
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
                "error": "GEMINI_API_KEY missing"
            }), 500

        # =================================================
        # SYSTEM PROMPT
        # =================================================

        system_instruction = """
You are an expert LaTeX assistant.

The user will describe:
- equations
- TikZ diagrams
- tables
- mathematical content

Return ONLY valid raw LaTeX code.

DO NOT:
- explain
- use markdown
- use code blocks
- write extra text

Only return LaTeX.
"""

        full_prompt = (
            f"{system_instruction}\n\n"
            f"USER REQUEST:\n{prompt}\n\n"
            f"LATEX CODE:"
        )

        # =================================================
        # GEMINI PAYLOAD
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
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        # =================================================
        # API CALL
        # =================================================

        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        response_data = response.json()

        print("FULL GEMINI RESPONSE:")
        print(response_data)

        # =================================================
        # VALIDATE RESPONSE
        # =================================================

        if not response_data.get("candidates"):

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
        # CLEAN MARKDOWN
        # =================================================

        raw_latex = raw_latex.strip()

        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex.replace(
                "```latex",
                "",
                1
            ).strip()

        if raw_latex.startswith("```"):
            raw_latex = raw_latex.replace(
                "```",
                "",
                1
            ).strip()

        if raw_latex.endswith("```"):
            raw_latex = raw_latex[:-3].strip()

        # =================================================
        # RETURN RESPONSE
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

        print("FULL GEMINI ERROR:")
        print(error_text)

        return jsonify({
            "error": f"Gemini API Error: {status_code}",
            "details": error_text
        }), 500

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# RENDER LATEX TO SVG
# =========================================================

@app.route("/api/render", methods=["POST"])
def render_diagram():

    try:

        data = request.json or {}

        latex_code = data.get("latexCode")

        if not latex_code:

            return jsonify({
                "error": "No LaTeX code provided"
            }), 400

        RENDER_SERVICE_URL = (
            "https://latex.yt/api/savetex"
        )

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
            timeout=30
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
            "error": str(e)
        }), 500

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        debug=True
    )
