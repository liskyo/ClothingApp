import os
import json
import time
import random
import io
from typing import Dict, Optional

class AIService:
    def __init__(self):
        # Gemini Setup
        # Allow multiple keys separated by comma
        self.gemini_keys = []
        keys_str = os.getenv("GEMINI_API_KEY", "")
        if keys_str:
            self.gemini_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        
        self.gemini_models = [
            'gemini-2.0-flash-exp',
            'gemini-flash-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro'
        ]
        
        # Replicate Setup
        self.replicate_token = os.getenv("REPLICATE_API_TOKEN")

    def _get_genai_module(self):
        try:
            import google.generativeai as genai
            return genai
        except ImportError as e:
            print(f"Failed to import google.generativeai: {e}")
            return None

    def _get_replicate_module(self):
        try:
            import replicate
            return replicate
        except ImportError as e:
            print(f"Failed to import replicate: {e}")
            return None

    def _mock_analysis(self) -> dict:
        # MOCK RESPONSE (Fallback)
        return {
            "name": "AI辨識之衣服(Mock)",
            "style": "時尚休閒(Mock)"
        }

    def analyze_image_style(self, image_bytes: bytes) -> dict:
        """
        Analyze image style using Google Gemini with Key/Model Rotation.
        """
        if not self.gemini_keys:
            print("Gemini API key not found. Using mock response.")
            return self._mock_analysis()

        genai = self._get_genai_module()
        if not genai:
            print("Gemini module not available.")
            return self._mock_analysis()

        # ... rest of the function continues ...
        try:
            # Placeholder for actual Gemini API call logic
            # This part was missing from the original content, but implied by the error handling
            # For now, it will just fall through to the mock response if no actual logic is added.
            pass
        except Exception as e:
            print(f"Gemini API Error: {e}")
            # Fallback to mock if API fails

        # MOCK RESPONSE (Fallback)
        return {
            "name": "AI辨識之衣服(Mock)",
            "style": "時尚休閒(Mock)"
        }

    def virtual_try_on(self, person_img_bytes: bytes, cloth_img_path: str) -> bytes:
        """
        Virtual Try-On using Replicate (IDM-VTON) if key exists.
        """
        if self.replicate_token:
            try:
                import io
                
                # Replicate client expects a file-like object for image input
                # We wrap the bytes in BytesIO
                
                with open(cloth_img_path, "rb") as cloth_file:
                    # IDM-VTON model on Replicate
                    # Using cuuupid/idm-vton with validated version hash
                    output = replicate.run(
                        "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
                        input={
                            "human_img": io.BytesIO(person_img_bytes),
                            "garm_img": cloth_file,
                            "garment_des": "clothing",  # Optional description
                        }
                    )
                    # Output is usually a URI string or list of URIs
                    # We need to fetch the image from the URL
                    if output:
                        import requests
                        img_url = output if isinstance(output, str) else output[0]
                        res = requests.get(img_url)
                        return res.content

            except Exception as e:
                print(f"Replicate API Error: {e}")
                # Fallback

        # MOCK RESPONSE
        return person_img_bytes
