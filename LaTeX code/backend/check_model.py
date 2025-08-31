import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load the .env file to get the key
load_dotenv()
print("Attempting to configure API key...")

try:
    # Configure the API key
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    print("API key configured successfully.")

    print("\n--- Available Models ---")
    # List all models and check which ones support the 'generateContent' method
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(model.name)
    print("------------------------")

except Exception as e:
    print(f"\nAn error occurred: {e}")