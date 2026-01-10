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

        # Prompt for Gemini
        prompt = """
        請分析這張衣服圖片。
        請回傳一個 JSON 物件，包含以下兩個欄位：
        1. "name": 給這件衣服一個簡短但有吸引力的名稱 (例如：日系碎花長裙、經典丹寧外套)。
        2. "style": 這件衣服的風格 (例如：休閒、正式、街頭、復古、波西米亞)。
        
        請直接回傳 JSON，不要 markdown 格式。
        """

        # Prepare image part
        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        # Rotation Logic
        errors = []
        start_key_idx = random.randint(0, len(self.gemini_keys) - 1)
        rotated_keys = self.gemini_keys[start_key_idx:] + self.gemini_keys[:start_key_idx]
        
        for key in rotated_keys:
            genai.configure(api_key=key)
            
            for model_name in self.gemini_models:
                try:
                    print(f"Trying Gemini with Key ending in ...{key[-4:]} and Model {model_name}")
                    model = genai.GenerativeModel(model_name)
                    
                    response = model.generate_content([prompt, image_part])
                    
                    text = response.text
                    # clean json
                    text = text.replace("```json", "").replace("```", "").strip()
                    
                    result = json.loads(text)
                    return result

                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"Key(...{key[-4:]})/{model_name}: {error_msg}")
                    
                    # Rate Limit handling
                    if "429" in error_msg or "Quota" in error_msg:
                        print(f"  -> Quota exceeded. Switching key...")
                        break # Break model loop to try next key
                        
                    # Model Not Found handling
                    if "404" in error_msg or "not found" in error_msg:
                        print(f"  -> Model not found. Switching model...")
                        continue # Next model
                    
                    print(f"  -> Error: {error_msg}")
                    
        print("All Gemini attempts failed.")
        print("\n".join(errors))
        return self._mock_analysis()

    def virtual_try_on(self, person_img_bytes: bytes, cloth_img_path: str) -> bytes:
        """
        Virtual Try-On using Replicate (IDM-VTON) if key exists.
        """
        if not self.replicate_token:
             return person_img_bytes

        replicate = self._get_replicate_module()
        if not replicate:
            print("Replicate module not available.")
            return person_img_bytes

        try:
            # Replicate client expects a file-like object for image input
            with open(cloth_img_path, "rb") as cloth_file:
                # IDM-VTON model on Replicate
                output = replicate.run(
                    "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
                    input={
                        "human_img": io.BytesIO(person_img_bytes),
                        "garm_img": cloth_file,
                        "garment_des": "clothing",
                    }
                )
                
                if output:
                    import requests
                    img_url = output if isinstance(output, str) else output[0]
                    res = requests.get(img_url)
                    return res.content

        except Exception as e:
            print(f"Replicate API Error: {e}")
            
        # Fallback
        return person_img_bytes
