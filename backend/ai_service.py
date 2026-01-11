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

    def _ensure_aspect_ratio(self, img_bytes, target_ratio=0.75): # 3:4 = 0.75
        """
        Resize/Pad image to match target aspect ratio (3:4) to prevent distortion.
        Returns bytes of new image.
        """
        try:
            from PIL import Image, ImageOps
            img = Image.open(io.BytesIO(img_bytes))
            
            # Auto-orient (fix EXIF rotation) to ensure correct dimensions
            img = ImageOps.exif_transpose(img)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            w, h = img.size
            current_ratio = w / h
            
            # Tolerance
            if abs(current_ratio - target_ratio) < 0.01:
                return img_bytes
                
            # Need to pad
            if current_ratio < target_ratio:
                # Too tall (skinny) -> Add padding to sides to make it wider
                new_w = int(h * target_ratio)
                new_h = h
                pad_color = (255, 255, 255) # Assuming white background
                
                new_img = Image.new("RGB", (new_w, new_h), pad_color)
                offset_x = (new_w - w) // 2
                new_img.paste(img, (offset_x, 0))
                
            else:
                # Too wide -> Add padding to top/bottom
                new_w = w
                new_h = int(w / target_ratio)
                pad_color = (255, 255, 255)
                
                new_img = Image.new("RGB", (new_w, new_h), pad_color)
                offset_y = (new_h - h) // 2
                new_img.paste(img, (0, offset_y))
            
            out_buf = io.BytesIO()
            new_img.save(out_buf, format='JPEG', quality=95)
            return out_buf.getvalue()
            
        except Exception as e:
            print(f"Resize failed: {e}")
            return img_bytes

    def _try_on_gradio(self, person_bytes, cloth_path, cloth_name="Upper-body", category=None, height_ratio=None):
        """
        Try using free OOTDiffusion via Gradio Client.
        """
        try:
            from gradio_client import Client, handle_file
            
            # PRE-PROCESS: Ensure 3:4 Aspect Ratio to prevent distortion
            person_bytes = self._ensure_aspect_ratio(person_bytes)
            
            # PRE-PROCESS Garment: OOTD handles garment resizing internally.
            
            # Determine category: Use explicit first, else guess
            if not category:
                if "裙" in cloth_name or "洋裝" in cloth_name:
                    category = "Dress"
                elif "褲" in cloth_name:
                    category = "Lower-body"
                else:
                    category = "Upper-body"

            # Map our internal categories to OOTDiffusion's exact strings
            # OOTD expects: 'Upper-body', 'Lower-body', 'Dress'
            ootd_category = "Upper-body"
            if category.lower() in ["lower-body", "lower_body", "bottom"]:
                ootd_category = "Lower-body"
            elif category.lower() in ["dress", "dresses", "whole-body", "whole_body"]:
                ootd_category = "Dress"
            
            # Garment Normalization & Resizing Logic
            # Goal: Enforce "Standard/Full" size by default, or "Specific" size if height_ratio is set.
            # 1. Trim Whitespace (to get true garment size)
            # 2. Scale to target (Default or Custom)
            # 3. Paste on 3:4 Canvas
            
            from PIL import Image, ImageChops
            
            def trim(im):
                bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
                diff = ImageChops.difference(im, bg)
                diff = ImageChops.add(diff, diff, 2.0, -100)
                bbox = diff.getbbox()
                if bbox:
                    return im.crop(bbox)
                return im

            with open(cloth_path, "rb") as f:
                raw_c_img = Image.open(f).convert("RGB")
            
            # 1. Trim (Remove borders)
            c_img_trimmed = trim(raw_c_img)
            w, h = c_img_trimmed.size
            
            # 2. Determine Target Scale (relative to 3:4 Canvas)
            # We will construct a canvas of width = w_canvas (fixed arbitrary or relative)
            # Let's use a high resolution canvas, e.g., width=768 (standard OOTD width)
            canvas_w = 768
            canvas_h = 1024 # 3:4 aspect
            
            # Determine how much of the canvas height the garment should cover
            target_coverage_h = 0.0
            
            if height_ratio:
                 print(f"Custom Height Ratio: {height_ratio}")
                 # User specified ratio (e.g. 0.5 of body)
                 # Map this to canvas height.
                 # Body is approx 90% of canvas height normally? 
                 # Let's simplify: 
                 # Dress/Whole-body: 0.5 ratio -> 0.5 of canvas (approx)
                 # Upper-body: 0.5 ratio -> is that half shirt?
                 # Let's map directly to canvas height % for simplicity, or relative to 'Standard'
                 
                 # Refined mapping:
                 if ootd_category == "Dress":
                     # Standard Dress ~ 0.85
                     target_coverage_h = height_ratio
                 elif ootd_category == "Lower-body":
                     # Standard Skirt ~ 0.6
                     target_coverage_h = height_ratio
                 else:
                     # Upper body default
                     target_coverage_h = height_ratio
            else:
                 # DEFAULT: FULL COVERAGE (User Request)
                 print(f"Default Full Coverage for {ootd_category}")
                 if ootd_category == "Dress":
                     target_coverage_h = 0.85 # Long dress
                 elif ootd_category == "Lower-body":
                     target_coverage_h = 0.65 # Long pants/skirt
                 else:
                     # Upper-body: Enforce "Full Coverage" (Long Shirt) by default
                     # Previously 0.0 (Width Mode) allowed crop-tops to stay short.
                     # Now setting to 0.6 (approx 60% canvas height) covers torso fully.
                     target_coverage_h = 0.6 
            
            # Calculate resize dimensions
            final_w, final_h = w, h
            
            if target_coverage_h > 0:
                # Resize based on Height
                # Goal height = canvas_h * target_coverage_h
                goal_h = int(canvas_h * target_coverage_h)
                
                # Aspect ratio
                aspect = w / h
                goal_w = int(goal_h * aspect)
                
                # Constraint: Don't exceed canvas width
                if goal_w > canvas_w * 0.9:
                    goal_w = int(canvas_w * 0.9)
                    goal_h = int(goal_w / aspect)
                
                final_w, final_h = goal_w, goal_h
            else:
                # Fallback (Should be rare now as all categories have defaults)
                # Resize based on Width 
                goal_w = int(canvas_w * 0.9)
                aspect = h / w 
                goal_h = int(goal_w * aspect)
                final_w, final_h = goal_w, goal_h

            print(f"Resizing garment to {final_w}x{final_h} (Canvas: {canvas_w}x{canvas_h})")
            
            # Resize
            resized_img = c_img_trimmed.resize((final_w, final_h), Image.Resampling.LANCZOS)
            
            # 3. Create Canvas and Paste
            canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
            
            # Paste Position: Top Center (with slight margin top)
            paste_x = (canvas_w - final_w) // 2
            paste_y = 0
            
            # For Upper-body, usually top align is fine.
            # For Lower-body, OOTD usually expects them Centered or slightly lower? 
            # Actually OOTD pre-processor handles 'Lower-body' input by looking for the object. 
            # But standardizing to Top-Center on a White Canvas is the safest "Clean Input".
            if ootd_category == "Lower-body":
                 # Maybe center vertically? No, standard OOTD inputs are usually full images.
                 # Let's stick to Top-Center but add clear margin if needed. 
                 # Actually, top-aligning pants might make them look like high-waist.
                 # Let's center vertically for Lower-body?
                 # No, consistent top-align is safer for now.
                 pass
            
            canvas.paste(resized_img, (paste_x, paste_y))
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                canvas.save(tf, format="JPEG")
                proc_cloth_path = tf.name

            print(f"Connecting to Gradio Space (OOTDiffusion) for {ootd_category} (orig: {category})...")
            client = Client("levihsu/OOTDiffusion")
            
            # Save person bytes to temp file because gradio client needs path usually or handle_file
            # Actually handle_file can wrap a path. We need to save bytes to disk first.
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(person_bytes)
                person_path = f.name
            
            result = client.predict(
                vton_img=handle_file(person_path),
                garm_img=handle_file(proc_cloth_path), # Use processed path
                category=ootd_category,
                n_samples=1,
                n_steps=20, 
                image_scale=2.0, 
                seed=-1,
                api_name="/process_dc"
            )
            
            # Result is a list of dicts or paths depending on return type.
            # inspection says: [Gallery] output: List[Dict(image: filepath, caption: str | None)]
            if result and len(result) > 0:
                first_img = result[0]['image']
                
                # Check if it's a path or url
                import shutil
                with open(first_img, "rb") as r:
                    return r.read()
                    
            return None
            
        except Exception as e:
            print(f"Gradio VTON Failed: {e}")
            return None

    def validate_and_crop_user_photo(self, img_bytes: bytes) -> Dict:
        """
        Validate and Auto-Crop User Photo.
        Returns:
            {
                "valid": bool,
                "reason": str,
                "processed_image": bytes (optional)
            }
        """
        if not self.gemini_keys:
             print("CRITICAL: No Gemini API Key found. Validation cannot proceed.")
             # Fallback to REJECT to prevent bypassing checks.
             return {"valid": False, "reason": "系統設定錯誤：未檢測到 AI 金鑰 (GEMINI_API_KEY)，無法進行驗證。", "processed_image": None}

        genai = self._get_genai_module()
        if not genai:
            return {"valid": False, "reason": "系統環境錯誤：缺少 Google GenAI 模組。", "processed_image": None}
            
        # 1. Gemini Analysis
        prompt = """
        請仔細分析這張照片是否適合做虛擬試穿 (Virtual Try-On)。
        試穿系統需要一張包含「頭部到膝蓋以下」的全身照，且人物清晰。
        
        標準檢查：
        1. "is_single": 是否只有一個主體人物？(True/False)
        2. "is_front": 是否為正面或微側面朝前？(不能是背影或純側面) (True/False)
        3. "is_full_body": 重點檢查！人物是否完整包含頭部、軀幹、手臂以及「大部分腿部(至少過膝蓋)」？僅上半身、半身照、切到大腿的都不行。(True/False)
        4. "is_clear": 影像是否清晰主體明確？(True/False)
        5. "box_2d": 人物的 Bounding Box [ymin, xmin, ymax, xmax] (0-1000 範圍整數)。
        
        若不符合上述任何一點，請將 valid 設為 false。
        回傳 JSON: {"valid": bool, "reason": str, "box_2d": [ymin, xmin, ymax, xmax], "is_single": bool, "is_front": bool, "is_full_body": bool}
        """
        
        image_part = {"mime_type": "image/jpeg", "data": img_bytes}
        
        # Simple Rotation for single call
        key = self.gemini_keys[0] # Just use first key for this helper
        genai.configure(api_key=key)
        # updated model name to try and fix 404
        model = genai.GenerativeModel('gemini-1.5-flash-latest') 
        
        processed_bytes = img_bytes
        
        try:
            response = model.generate_content([prompt, image_part])
            text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            
            if not data.get("valid", False):
                # Construct strict failure reason
                reasons = []
                if not data.get("is_single"): reasons.append("偵測到多人或無人")
                if not data.get("is_front"): reasons.append("非正面拍攝")
                if not data.get("is_full_body"): reasons.append("非全身照(需含膝蓋以上)")
                
                full_reason = "、".join(reasons)
                if not full_reason: full_reason = data.get("reason", "照片不符規格")
                
                return {"valid": False, "reason": full_reason, "processed_image": None}
            
            # 2. Auto-Crop Logic
            box = data.get("box_2d", [100, 100, 900, 900]) # ymin, xmin, ymax, xmax (0-1000)
            
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            w, h = img.size
            
            # Normalize box to pixels
            ymin = int(box[0] / 1000 * h)
            xmin = int(box[1] / 1000 * w)
            ymax = int(box[2] / 1000 * h)
            xmax = int(box[3] / 1000 * w)
            
            # Person Dimensions
            p_h = ymax - ymin
            p_w = xmax - xmin
            
            # Target: Person Height = 75% of Canvas Height
            # Target Canvas Height = p_h / 0.75
            target_canvas_h = int(p_h / 0.75)
            
            # Target Aspect Ratio 3:4 (0.75)
            # Target Canvas Width = target_canvas_h * 0.75 = p_h
            target_canvas_w = int(target_canvas_h * 0.75)
            
            # Ensure canvas is wide enough for person
            if target_canvas_w < p_w * 1.1: # Add 10% minimal side padding margin
                target_canvas_w = int(p_w * 1.1)
                target_canvas_h = int(target_canvas_w / 0.75) # Re-adjust height to match ratio
            
            # Create Canvas
            canvas = Image.new("RGB", (target_canvas_w, target_canvas_h), (255, 255, 255))
            
            # Crop Person
            person_crop = img.crop((xmin, ymin, xmax, ymax))
            
            # Paste Position: Bottom Center? Or Vertically Centered?
            # User said: "Display frame 3/4 Size" -> usually implies centered with margins.
            # Let's Center Vertically.
            paste_x = (target_canvas_w - p_w) // 2
            paste_y = (target_canvas_h - p_h) // 2
            
            canvas.paste(person_crop, (paste_x, paste_y))
            
            buf = io.BytesIO()
            canvas.save(buf, format="JPEG", quality=95)
            processed_bytes = buf.getvalue()
            
            return {"valid": True, "reason": "OK", "processed_image": processed_bytes}

        except Exception as e:
            print(f"Validation Error: {e}")
            # Strict Failure: Do not allow bypass on error
            return {"valid": False, "reason": f"AI 驗證連線失敗: {str(e)}", "processed_image": None}

    def _add_watermark(self, img_bytes: bytes, text: str = "僅供穿搭參考，並非真實穿著效果") -> bytes:
        """
        Add a disclaimer watermark to the bottom of the image.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            draw = ImageDraw.Draw(img)
            w, h = img.size
            
            # Font Setup
            # Try loading standard Chinese font on Windows
            font_path = "C:/Windows/Fonts/msjh.ttc" 
            if not os.path.exists(font_path):
                 # Fallback to standard arial if Chinese font missing (unlikely on TW Windows)
                 font_path = "arial.ttf"
            
            # Dynamic font size (approx 2.5% of image height)
            font_size = int(h * 0.025)
            font_size = max(16, font_size) # Min size
            
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            # Calculate Text Size
            # getting text bbox: left, top, right, bottom
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            # Position: Bottom Center with padding
            x = (w - text_w) // 2
            y = h - text_h - 20 # 20px padding from bottom
            
            # Draw Outline (Shadow) for visibility
            outline_color = (0, 0, 0)
            text_color = (255, 255, 255)
            
            # Draw outline by drawing text at offsets
            draw.text((x-1, y-1), text, font=font, fill=outline_color)
            draw.text((x+1, y-1), text, font=font, fill=outline_color)
            draw.text((x-1, y+1), text, font=font, fill=outline_color)
            draw.text((x+1, y+1), text, font=font, fill=outline_color)
            
            # Draw Main Text
            draw.text((x, y), text, font=font, fill=text_color)
            
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            return output.getvalue()
            
        except Exception as e:
            print(f"Watermark failed: {e}")
            return img_bytes

    def virtual_try_on(self, person_img_bytes: bytes, cloth_img_path: str, cloth_name: str = "Upper-body", category: str = "Upper-body", method: str = "auto", height_ratio: float = None) -> bytes:
        """
        Virtual Try-On Pipeline:
        1. Replicate (Paid, Best) - Skipped if no token.
        2. Gradio OOTDiffusion (Free, Slow, GenAI) - Skipped if method='overlay'
        3. Gemini Overlay (Free, Fast, 2D) - Fallback or Explicit.
        """
        
        final_result_bytes = None
        
        # 1. Replicate (Paid)
        if self.replicate_token and method != 'overlay':
             # Just a placeholder for Replicate logic presence
             pass 
             
        # 2. Gradio (Free GenAI)
        if method != 'overlay' and not final_result_bytes:
            print(f"Attempting OOTDiffusion (Free GenAI) for {cloth_name} ({category})...")
            gen_img = self._try_on_gradio(person_img_bytes, cloth_img_path, cloth_name, category, height_ratio)
            if gen_img:
                final_result_bytes = gen_img
        elif method == 'overlay':
            print(f"Skipping GenAI due to explicit method='{method}'")
            
        # 3. Fallback / Free Mode: Gemini Guided Overlay
        if not final_result_bytes:
            print("Using Free Mode: Gemini Guided Overlay")
            try:
                from PIL import Image, ImageOps
                
                # ... (Overlay Logic) ...
                person_img = Image.open(io.BytesIO(person_img_bytes)).convert("RGBA")
                cloth_img = Image.open(cloth_img_path)
                
                # Key Step: Remove Background from Cloth
                cloth_img = self._remove_background_simple(cloth_img)

                try:
                    analysis = self.analyze_image_style(person_img_bytes)
                except:
                    analysis = {}
                
                center_x = analysis.get("torso_center_x", 0.5)
                center_y = analysis.get("torso_center_y", 0.4)
                width_ratio = analysis.get("shoulders", 0.5)
                
                p_width, p_height = person_img.size
                
                # Adjust scaling and position based on type
                # Use explicit category if available
                is_lower = category in ["Lower-body", "lower-body"] or "褲" in cloth_name or "裙" in cloth_name
                is_dress = category in ["Dress", "Whole-body", "whole-body", "One-piece"] or "洋裝" in cloth_name
                
                if is_lower and not is_dress:
                    # Pants/Skirt: Center lower
                    target_width = int(p_width * width_ratio * 1.3)
                else:
                    # Shirt/Dress
                    target_width = int(p_width * width_ratio * 1.5) 
                
                # Maintain aspect ratio of cloth
                c_width, c_height = cloth_img.size
                
                # Explicit proportion override (User requested JSON control)
                if height_ratio and height_ratio > 0:
                    print(f"Using explicit height ratio from JSON: {height_ratio}")
                    target_height = int(p_height * height_ratio)
                    if c_height > 0:
                         # Recalculate width to maintain aspect
                         aspect = c_width / c_height
                         target_width = int(target_height * aspect)
                elif c_width > 0:
                    aspect = c_height / c_width
                    target_height = int(target_width * aspect)
                else:
                    target_height = target_width # Fallback
                
                resized_cloth = cloth_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Calculate Position
                pos_x = int((center_x * p_width) - (target_width / 2))
                
                if is_lower and not is_dress:
                    # Place at "waist" approx
                    pos_y = int((center_y * p_height) + (p_height * 0.05))
                else:
                    # Place at "shoulders" approx
                    pos_y = int((center_y * p_height) - (target_height / 3))
                
                result = Image.new("RGBA", person_img.size, (0,0,0,0))
                result.paste(person_img, (0,0))
                result.paste(resized_cloth, (pos_x, pos_y), resized_cloth) 
                
                output = io.BytesIO()
                result.convert("RGB").save(output, format="JPEG", quality=90)
                final_result_bytes = output.getvalue()
                
            except Exception as e:
                print(f"Free VTON Error: {e}")
                raise e
        
        # 4. Post-Process: Add Watermark (Prompt)
        if final_result_bytes:
            print("Adding Disclaimer Watermark...")
            final_result_bytes = self._add_watermark(final_result_bytes)
            
        return final_result_bytes
