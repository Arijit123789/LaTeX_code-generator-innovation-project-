import os
import traceback
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

# =========================================================
# Load Environment Variables
# =========================================================

load_dotenv()

# =========================================================
# Flask App Setup
# =========================================================

app = Flask(__name__)
CORS(app)

# =========================================================
# OpenAI Configuration
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing.")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================================================
# Health Check Route
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "model": OPENAI_MODEL
    })

# =========================================================
# List Models Route
# =========================================================

@app.route("/api/list-models", methods=["GET"])
def list_models():
    try:
        models = client.models.list()

        model_names = []

        for model in models.data:
            model_names.append(model.id)

        return jsonify({
            "models": model_names
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# Generate LaTeX Route
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

        temperature = float(data.get("temperature", 0.2))
        max_output_tokens = int(data.get("maxOutputTokens", 4000))

        # =====================================================
        # System Prompt
        # =====================================================

        system_prompt = """
You are an expert LaTeX assistant.

The user will provide a description of:
- diagrams
- equations
- tables
- tikz images
- mathematical expressions

You must respond with ONLY valid raw LaTeX code.

Rules:
- No markdown
- No explanations
- No code fences
- No extra text
- Output ONLY LaTeX
"""

        # =====================================================
        # OpenAI API Call
        # =====================================================

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=temperature,
            max_tokens=max_output_tokens,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # =====================================================
        # Extract Output
        # =====================================================

        raw_latex = response.choices[0].message.content.strip()

        # =====================================================
        # Cleanup
        # =====================================================

        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex.replace("```latex", "").strip()

        if raw_latex.startswith("```"):
            raw_latex = raw_latex.replace("```", "").strip()

        if raw_latex.endswith("```"):
            raw_latex = raw_latex[:-3].strip()

        # =====================================================
        # Return Response
        # =====================================================

        return jsonify({
            "latexCode": raw_latex
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# Render Route
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

        # =====================================================
        # External Rendering Service
        # =====================================================

        RENDER_SERVICE_URL = "https://latex.yt/api/savetex"

        full_document = (
            "\\documentclass{article}\n"
            "\\usepackage{tikz}\n"
            "\\usepackage{amsmath}\n"
            "\\usepackage{amssymb}\n"
            "\\usepackage{pgfplots}\n"
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

        response = requests.post(
            RENDER_SERVICE_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        response_json = response.json()

        svg_image_data = response_json.get("result")

        if not svg_image_data:
            return jsonify({
                "error": "Rendering service failed.",
                "details": response_json
            }), 500

        return jsonify({
            "svgImage": svg_image_data
        })

    except requests.exceptions.RequestException as e:

        return jsonify({
            "error": f"Rendering service error: {str(e)}"
        }), 502

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# Main Entry
# =========================================================

if __name__ == "__main__":

    port = int(os.getenv("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
