import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
keys_str = os.getenv("GEMINI_API_KEY", "")
keys = [k.strip() for k in keys_str.split(',') if k.strip()]

genai.configure(api_key=keys[0])

print("Listing models to find 2.5/3...")
try:
    for m in genai.list_models():
         if 'gemini' in m.name:
             print(f"Model: {m.name}")
except Exception as e:
    print(f"Error listing: {e}")
