import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Gemini Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# We define the V1 API endpoint directly with the CORRECT hostname
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}" # Corrected URL path


@app.route('/api/generate', methods=['POST'])
def generate_latex():
    data = request.json
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "Prompt is missing"}), 400

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    try:
        # --- Direct API call logic ---

        system_instruction_text = "You are a LaTeX expert. Given a user's prompt, provide only the raw LaTeX code required to represent their request. Do not include any explanations, surrounding text, or markdown code fences."

        # Create the payload
        payload = {
            # Use camelCase 'systemInstruction' as expected by the API
            "systemInstruction": {
                "parts": [{"text": system_instruction_text}]
            },
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        # Define the headers
        headers = {
            "Content-Type": "application/json"
        }

        # Make the web request to the v1 API
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

        # Check for HTTP errors
        response.raise_for_status()

        # Extract the text
        response_data = response.json()

        # Handle potential variations in response structure
        try:
            raw_latex = response_data['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError, TypeError) as e:
             print(f"Error parsing response structure: {e}. Response data: {response_data}")
             return jsonify({"error": f"Failed to parse API response. Structure might have changed."}), 500


        # Clean up the response
        raw_latex = raw_latex.strip()
        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex[7:]
        if raw_latex.startswith("```"):
            raw_latex = raw_latex[3:]
        if raw_latex.endswith("```"):
            raw_latex = raw_latex[:-3]
        raw_latex = raw_latex.strip()

        final_response = {
            "latexCode": raw_latex,
        }
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        error_message = f'HTTP Error {e.response.status_code}'
        try:
            # Try to return the specific error message from Google
            error_details = e.response.json().get('error', {})
            error_message = error_details.get('message', error_message)
            print(f"Google API Error Details: {error_details}")
        except:
            # Fallback if parsing the error fails
             pass # Use the basic HTTP error message
        return jsonify({"error": f"API Error: {error_message}"}), 502

    except Exception as e:
        print(f"An internal server error occurred: {e}")
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500


@app.route('/api/render', methods=['POST'])
def render_diagram():
    # --- This route is unchanged ---

    data = request.json
    latex_code = data.get('latexCode')

    if not latex_code:
        return jsonify({"error": "No LaTeX code provided"}), 400

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

        response = requests.post(RENDER_SERVICE_URL, data=payload)
        response.raise_for_status()

        svg_image_data = response.json().get('result')

        if not svg_image_data:
            return jsonify({"error": "Rendering service failed to return an image."}), 500

        return jsonify({"svgImage": svg_image_data})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to rendering service: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"An internal rendering error occurred: {e}"}), 500
