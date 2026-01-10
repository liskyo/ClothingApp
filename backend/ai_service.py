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
        Also tries to detect the body position for overlay mapping.
        """
        if not self.gemini_keys:
            print("Gemini API key not found. Using mock response.")
            return self._mock_analysis()

        genai = self._get_genai_module()
        if not genai:
            print("Gemini module not available.")
            return self._mock_analysis()

        # Complex Prompt: asking for Style + Bounding Box
        prompt = """
        請分析這張全身照或半身照。
        請回傳一個 JSON 物件，包含以下欄位：
        1. "name": 適合這張圖片中衣著的簡短名稱。
        2. "style": 風格 (例如：休閒、正式)。
        3. "shoulders": 肩膀寬度 (估計值，相對於圖片寬度的比例，例如 0.4)。
        4. "torso_center_x": 軀幹中心點 X 座標 (0.0-1.0)。
        5. "torso_center_y": 軀幹中心點 Y 座標 (0.0-1.0)。
        6. "torso_height": 軀幹高度 (估計值，0.0-1.0)。
        
        如果無法辨識人物，請回傳預設值。
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
                    # model = genai.GenerativeModel(model_name)
                    # Use flash for speed
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    response = model.generate_content([prompt, image_part])
                    text = response.text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(text)
                    return result

                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"Key(...{key[-4:]})/{model_name}: {error_msg}")
                    # Basic rotation logic same as before...
                    if "429" in error_msg or "Quota" in error_msg:
                        break
                    if "404" in error_msg:
                        continue
        
        return self._mock_analysis()

    def _remove_background_simple(self, img):
        """
        Simple color-keying to remove white/light background.
        Converts white/light-gray pixels to transparent.
        """
        try:
            from PIL import Image
            img = img.convert("RGBA")
            datas = img.getdata()
            
            new_data = []
            for item in datas:
                # RGB values + Alpha
                # Check if pixel is close to white (e.g. > 200 in all channels)
                if item[0] > 200 and item[1] > 200 and item[2] > 200:
                    new_data.append((255, 255, 255, 0)) # Make transparent
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            return img
        except Exception as e:
            print(f"BG Removal failed: {e}")
            return img

    def virtual_try_on(self, person_img_bytes: bytes, cloth_img_path: str) -> bytes:
        """
        Free "Virtual Try-On" using Gemini-guided 2D Overlay with BG Removal.
        """
        # If Replicate Token exists, try that first
        if self.replicate_token:
             # Just a placeholder for Replicate logic presence
             pass 

        # --- Fallback / Free Mode: Gemini Guided Overlay ---
        print("Using Free Mode: Gemini Guided Overlay")
        
        try:
            from PIL import Image, ImageOps
            
            # 1. Load Images
            person_img = Image.open(io.BytesIO(person_img_bytes)).convert("RGBA")
            cloth_img = Image.open(cloth_img_path)
            
            # 2. Key Step: Remove Background from Cloth
            cloth_img = self._remove_background_simple(cloth_img)

            # 3. Get Body Coordinates from Gemini
            try:
                analysis = self.analyze_image_style(person_img_bytes)
            except:
                analysis = {}
            
            # Defaults if AI fails
            center_x = analysis.get("torso_center_x", 0.5)
            center_y = analysis.get("torso_center_y", 0.4)
            width_ratio = analysis.get("shoulders", 0.5)
            
            # 4. Calculate Geometry
            p_width, p_height = person_img.size
            target_width = int(p_width * width_ratio * 1.5) 
            
            # Maintain aspect ratio of cloth
            c_width, c_height = cloth_img.size
            if c_width > 0:
                aspect = c_height / c_width
                target_height = int(target_width * aspect)
            else:
                target_height = target_width # Fallback
            
            # Resize Cloth
            resized_cloth = cloth_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # 5. Composite
            # Calculate Position (Center the cloth on the torso center)
            pos_x = int((center_x * p_width) - (target_width / 2))
            pos_y = int((center_y * p_height) - (target_height / 3))
            
            # Paste
            result = Image.new("RGBA", person_img.size, (0,0,0,0))
            result.paste(person_img, (0,0))
            # Paste with alpha mask
            result.paste(resized_cloth, (pos_x, pos_y), resized_cloth) 
            
            # 6. Convert to JPG bytes
            output = io.BytesIO()
            result.convert("RGB").save(output, format="JPEG", quality=90)
            return output.getvalue()
            
        except Exception as e:
            print(f"Free VTON Error: {e}")
            return person_img_bytes
