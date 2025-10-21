import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai # <-- This is the correct import for this library

app = Flask(__name__)
CORS(app)

# --- Configure Gemini ---
# The 'google-generativeai' library uses genai.configure()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@app.route('/api/generate', methods=['POST'])
def generate_latex():
    data = request.json
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "Prompt is missing"}), 400
    
    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY is not configured on the server."}), 500

    try:
        # --- This is the correct logic for the 'google-generativeai' library ---
        
        system_instruction = "You are a LaTeX expert. Given a user's prompt, provide only the raw LaTeX code required to represent their request. Do not include any explanations, surrounding text, or markdown code fences."
        
        # 1. Initialize the model, which accepts the system_instruction
        model = genai.GenerativeModel(
            model_name='gemini-pro',
            system_instruction=system_instruction
        )
        
        # 2. Generate the content
        response = model.generate_content(prompt)
        
        # 3. Clean up the response text
        raw_latex = response.text.strip()
        if raw_latex.startswith("```latex"):
            raw_latex = raw_latex[7:]
        if raw_latex.startswith("```"):
            raw_latex = raw_latex[3:]
        if raw_latex.endswith("```"):
            raw_latex = raw_latex[:-3]
        raw_latex = raw_latex.strip()

        # --- End of logic ---

        final_response = {
            "latexCode": raw_latex,
        }
        return jsonify(final_response)

    except Exception as e:
        # This will catch errors and log them to Vercel
        print(f"Error during Gemini generation: {e}") 
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500


@app.route('/api/render', methods=['POST'])
def render_diagram():
    # --- THIS ENTIRE ROUTE IS UNCHANGED AND CORRECT ---
    
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

# This part is needed if you run locally (Vercel doesn't use it)
if __name__ == '__main__':
    app.run(debug=True)
