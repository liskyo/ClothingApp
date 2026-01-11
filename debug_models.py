import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Try splitting if multiple
    pass

if "," in api_key:
    api_key = api_key.split(",")[0].strip()

print(f"Using Key: {api_key[:5]}...")
genai.configure(api_key=api_key)

print("Listing Models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
