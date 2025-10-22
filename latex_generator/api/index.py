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
            # Optional tuning params
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

        # --- NEW ROBUST PARSING LOGIC ---
        raw_latex = None
        try:
            # Check if candidates list exists and is not empty
            if not response_data.get("candidates"):
                # If no candidates, it might be a prompt-level block
                prompt_feedback = response_data.get("promptFeedback")
                if prompt_feedback:
                    block_reason = prompt_feedback.get("blockReason", "Unknown")
                    safety_ratings = prompt_feedback.get("safetyRatings", "N/A")
                    return jsonify({
                        "error": f"Prompt was blocked by API.",
                        "details": f"Reason: {block_reason}. Safety Ratings: {safety_ratings}"
                    }), 400
                
                # Otherwise, it's an unknown empty response
                return jsonify({"error": "API returned an empty response with no candidates.", "details": response_data}), 500

            # Get the first candidate
            candidate = response_data["candidates"][0]

            # Check if generation finished normally
            finish_reason = candidate.get("finishReason")
            if finish_reason and finish_reason != "STOP":
                safety_ratings = candidate.get("safetyRatings", "N/A")
                return jsonify({
                    "error": f"Generation stopped for reason: {finish_reason}",
                    "details": f"Safety Ratings: {safety_ratings}"
                }), 500

            # Safely try to access the text
            if (
                candidate.get("content") and
                candidate["content"].get("parts") and
                len(candidate["content"]["parts"]) > 0 and
                candidate["content"]["parts"][0].get("text")
            ):
                raw_latex = candidate["content"]["parts"][0]["text"]
            else:
                # If the structure is valid but text is missing
                return jsonify({
                    "error": "API response format unexpected: 'text' part is missing.",
                    "details": candidate
                }), 500

        except (KeyError, IndexError, TypeError, AttributeError) as e:
            # This is a fallback for a truly unexpected structure
            error_details = response_data.get("error", response_data)
            return jsonify({
                "error": f"API response parsing failed unexpectedly: {e}",
                "details": error_details
            }), 500
        # --- END OF NEW PARSING LOGIC ---


        if not raw_latex:
            # This should not be reachable if the logic above is correct, but as a safeguard
            return jsonify({"error": "API returned no text output.", "details": response_data}), 500

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
             hint = "The request payload (JSON) is likely malformed or the prompt was blocked."
        elif status_code == 429:
             hint = "You have exceeded your API quota. Check your Google AI Studio."
        elif status_code == 503:
             hint = "The service is temporarily overloaded. Please try again in a moment."

        return jsonify({"error": f"API Request Error: {status_code} - {error_text}", "hint": hint}), 502

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500
