import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
keys_str = os.getenv("GEMINI_API_KEY", "")
keys = [k.strip() for k in keys_str.split(',') if k.strip()]

print(f"Found {len(keys)} keys.")

valid_key_found = False

for i, key in enumerate(keys):
    print(f"Testing Key [{i}] (Starts with {key[:4]})...")
    genai.configure(api_key=key)
    try:
        # Try listing models
        count = 0
        for m in genai.list_models():
            count += 1
            if count > 0: break
        print(f"  -> SUCCESS! Key [{i}] works.")
        valid_key_found = True
        
        # Now try to find a valid model for this key
        print("  -> Available Models:")
        for m in genai.list_models():
             if 'generateContent' in m.supported_generation_methods:
                 print(f"     - {m.name}")
        break # Found a working key, stop.
    except Exception as e:
        print(f"  -> FAILED: {e}")

if not valid_key_found:
    print("ALL KEYS FAILED.")
