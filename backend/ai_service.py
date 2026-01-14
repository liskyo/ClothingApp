import os
import json
import time
import random
import io
from typing import Dict, Optional
import traceback

class AIService:
    def __init__(self):
        # Gemini Setup
        # Allow multiple keys separated by comma
        self.gemini_keys = []
        
        # Load from BOTH variables to ensure we catch whatever the user set
        keys_1 = (os.getenv("GEMINI_API_KEY", "")).split(',')
        keys_2 = (os.getenv("GOOGLE_API_KEY", "")).split(',')
        
        # Combine and deduplicate
        all_keys = [k.strip() for k in keys_1 + keys_2 if k.strip()]
        self.gemini_keys = list(set(all_keys))
        
        self.gemini_models = [
            'gemini-3-flash',          # High performance (2026 verified)
            'gemini-2.5-flash',        # (2026 verified)
            'gemini-2.5-flash-lite',   # (2026 verified)
            'gemini-1.5-flash',        # Legacy fallback
            'gemini-1.5-pro',          # Legacy fallback
        ]
        
        # Replicate Setup
        self.replicate_token = os.getenv("REPLICATE_API_TOKEN")

        # Debug Logging
        if self.gemini_keys:
            print(f"✅ Gemini Service Initialized with {len(self.gemini_keys)} keys.")
            # Print hint of keys for server logs
            for i, k in enumerate(self.gemini_keys):
                print(f"  Key {i+1}: ...{k[-4:]}")
        else:
            print("⚠️ Gemini Service: No API Keys found (Env: GEMINI_API_KEY or GOOGLE_API_KEY)")
            
        if not self.replicate_token:
            print("⚠️ Replicate Service: No Token found")

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

    def _mock_analysis(self, reason: str = "") -> dict:
        # MOCK RESPONSE (Fallback)
        # Debug: Include reason in name so user can see it in UI
        suffix = f" - {reason}" if reason else "(Mock)"
        return {
            "name": f"AI辨識之衣服{suffix}",
            "style": f"時尚休閒{suffix}"
        }

    def analyze_image_style(self, image_bytes: bytes) -> dict:
        """
        Analyze image style using Google Gemini with Key/Model Rotation.
        Also tries to detect the body position for overlay mapping.
        """
        if not self.gemini_keys:
            print("Gemini API key not found. Using mock response.")
            return self._mock_analysis("無 API Key")

        genai = self._get_genai_module()
        if not genai:
            print("Gemini module not available.")
            return self._mock_analysis("無法載入 Google 模組")

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
                    # FIX: Use loop variable model_name instead of hardcoded value
                    print(f"Trying Gemini Model: {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    
                    response = model.generate_content([prompt, image_part])
                    text = response.text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(text)
                    return result

                except Exception as e:
                    error_msg = str(e)
                    # Include Key hint in error log
                    key_hint = f"...{key[-4:]}"
                    errors.append(f"Key({key_hint})/{model_name}: {error_msg}")
                    # Basic rotation logic same as before...
                    if "404" in error_msg:
                        continue
        
        # If all failed, use the last error as reason
        last_error = errors[-1] if errors else "Unknown Error"
        print(f"All Gemini attempts failed. Errors: {errors}")
        
        # Return a shortened error for UI with KEY HINT
        try:
            parts = last_error.split(':')
            key_info = parts[0]
            err_code = parts[1].strip()[:20]
            if "Key" in key_info:
                # Example: 404 Not Found (Key...1234)
                short_error = f"{err_code} ({key_info})"
            else:
                short_error = err_code
        except:
             short_error = last_error[:30]

        # Show Key Count to verify loading
        key_count = len(self.gemini_keys)
        return self._mock_analysis(f"Err({key_count} keys): {short_error}")

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
            try:
                from gradio_client import Client, handle_file
            except ImportError as ie:
                print(f"CRITICAL: gradio_client import failed. {ie}")
                raise Exception("Server Error: Missing gradio_client library.")
            
            # PRE-PROCESS: Ensure 3:4 Aspect Ratio to prevent distortion (Skipped if we trust input)
            # Default input logic handles person image.
            
            # Determine category
            if not category:
                if "裙" in cloth_name or "洋裝" in cloth_name:
                    category = "Dress"
                elif "褲" in cloth_name:
                    category = "Lower-body"
                else:
                    category = "Upper-body"

            # Map to OOTD strings
            ootd_category = "Upper-body"
            if category.lower() in ["lower-body", "lower_body", "bottom"]:
                ootd_category = "Lower-body"
            elif category.lower() in ["dress", "dresses", "whole-body", "whole_body"]:
                ootd_category = "Dress"
            
            from PIL import Image, ImageChops
            import io
            import time
            import os
            import tempfile
            
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
            
            # 2. Standardize for VTON (768x1024 Canvas)
            # This ensures OOTD receives a high-quality, centered input regardless of original crop.
            canvas_w, canvas_h = 768, 1024
            
            # Fit garment into canvas
            # Adjust coverage based on category
            target_coverage_w = 0.9
            target_coverage_h = 0.9
            
            c_w, c_h = c_img_trimmed.size
            
            if ootd_category == "Lower-body":
                 # PANTS FIX (Texture Preservation):
                 # Problem: Stretching distorted the texture (e.g. Plaid), creating weird artifacts.
                 # Problem: Wide inputs became shorts.
                 # Solution: CROP the sides of the input garment to force a "Tall" aspect ratio WITHOUT stretching.
                 
                 # 1. Check Aspect Ratio
                 c_aspect = c_w / c_h
                 target_aspect = 0.55 # Target: Slim Tall Pants
                 
                 if c_aspect > target_aspect:
                     # Too Wide!
                     # Calculate new width to match target aspect ratio based on height
                     new_source_w = int(c_h * target_aspect)
                     
                     # Center Crop
                     left = (c_w - new_source_w) // 2
                     right = left + new_source_w
                     print(f"Pants too wide ({c_aspect:.2f}). Cropping width from {c_w} to {new_source_w} to force Long Pants...")
                     
                     c_img_trimmed = c_img_trimmed.crop((left, 0, right, c_h))
                     c_w, c_h = c_img_trimmed.size # Update dimensions
                 
                 # 2. Scale to Canvas
                 # Now proper aspect ratio is guaranteed. Scale to Height.
                 target_h = int(canvas_h * 0.92) # 92% Height (Ankle)
                 
                 scale = target_h / c_h
                 new_w = int(c_w * scale)
                 new_h = target_h
                 
                 # Cap width if it exceeds canvas (unlikely after crop, but good for safety)
                 if new_w > int(canvas_w * 0.9):
                      scale = (canvas_w * 0.9) / c_w
                      new_w = int(c_w * scale)
                      new_h = int(c_h * scale)

                 c_img_resized = c_img_trimmed.resize((new_w, new_h), Image.Resampling.LANCZOS)
                 
                 # 3. Position (Centered-ish)
                 # Shift slightly down to ensure waist isn't too high
                 paste_x = (canvas_w - new_w) // 2
                 paste_y = canvas_h - new_h # Flush Bottom
                 
            else:
                 # Standard logic for Check/Upper/Dress (Centered)
                 scale = min((canvas_w * target_coverage_w) / c_w, (canvas_h * target_coverage_h) / c_h)
                 new_w = int(c_w * scale)
                 new_h = int(c_h * scale)
                 c_img_resized = c_img_trimmed.resize((new_w, new_h), Image.Resampling.LANCZOS)
                 
                 paste_x = (canvas_w - new_w) // 2
                 paste_y = (canvas_h - new_h) // 2
            
            # Paste on White Canvas
            final_cloth = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
            final_cloth.paste(c_img_resized, (paste_x, paste_y))
            
            if ootd_category == "Lower-body":
                 print(f"Pants Layout: SIDE-CROP - Size {c_img_resized.size}")
            
            # Save processed cloth
            proc_cloth_path = os.path.join(tempfile.gettempdir(), f"proc_cloth_{int(time.time())}.jpg")
            final_cloth.save(proc_cloth_path, format="JPEG", quality=95)
            
            print(f"Processed Garment (Standardized) saved to {proc_cloth_path}")
            
            # PRE-PROCESS: Smart Padding to 3:4
            # OOTD works best at 3:4 (0.75). Inputting other ratios causes hidden cropping/zooming.
            # We must PAD the input to 3:4, run VTON, then CROP back to original.
            
            from PIL import Image, ImageOps
            import io
            
            # Restore missing logic: Save person_bytes to file first
            person_path = os.path.join(tempfile.gettempdir(), f"person_{int(time.time())}.jpg")
            with open(person_path, "wb") as f:
                f.write(person_bytes)
            
            with open(person_path, "rb") as f:
                orig_pil = Image.open(f).convert("RGB")
                
            orig_w, orig_h = orig_pil.size
            target_ratio = 0.75 # 3:4
            current_ratio = orig_w / orig_h
            
            pad_w, pad_h = 0, 0
            
            if current_ratio < target_ratio:
                # Too tall (e.g. 9:16 = 0.56). Need Width Padding.
                target_w = int(orig_h * target_ratio)
                pad_total = target_w - orig_w
                pad_l = pad_total // 2
                pad_r = pad_total - pad_l
                
                padded_pil = Image.new("RGB", (target_w, orig_h), (255, 255, 255))
                padded_pil.paste(orig_pil, (pad_l, 0))
                
                # Update pad info for post-crop
                pad_w = pad_l # We only care about left offset and original width
                
            elif current_ratio > target_ratio:
                # Too wide. Need Height Padding.
                target_h = int(orig_w / target_ratio)
                pad_total = target_h - orig_h
                pad_t = pad_total // 2
                pad_b = pad_total - pad_t
                
                padded_pil = Image.new("RGB", (orig_w, target_h), (255, 255, 255))
                padded_pil.paste(orig_pil, (0, pad_t))
                
                # Update pad info
                pad_h = pad_t
            else:
                padded_pil = orig_pil
            
            # Save Padded Person for OOTD
            padded_person_path = os.path.join(tempfile.gettempdir(), f"person_padded_{int(time.time())}.jpg")
            padded_pil.save(padded_person_path, format="JPEG", quality=95)
            
            print(f"Padded Person saved to {padded_person_path} (Ratio: {current_ratio:.2f} -> {target_ratio})")

            try:
                print(f"Connecting to Gradio Space (OOTDiffusion) for {ootd_category}...")
                client = Client("levihsu/OOTDiffusion")
                
                # Call Gradio Client
                # Using 'levihsu/OOTDiffusion'
                print(f"Calling client.predict with standard params...")
                try:
                    # OOTDiffusion API often changes. Trying most standard one.
                    result = client.predict(
                        vton_img=handle_file(padded_person_path), 
                        garm_img=handle_file(proc_cloth_path), 
                        category=ootd_category, 
                        n_samples=1,
                        n_steps=20, # Reduced steps for speed (Timeout fix?)
                        image_scale=2, 
                        seed=-1,
                        api_name="/process_dc"
                    )
                except Exception as api_err:
                     print(f"First API attempt failed: {api_err}. Trying fallback API name...")
                     # Fallback to /process_hd just in case
                     result = client.predict(
                        vton_img=handle_file(padded_person_path), 
                        garm_img=handle_file(proc_cloth_path), 
                        category=ootd_category, 
                        n_samples=1,
                        n_steps=20,
                        image_scale=2, 
                        seed=-1,
                        api_name="/process_hd"
                     )
            
                # Handle Result (can be list or tuple)
                out_path = None
                if result:
                    if isinstance(result, list) and len(result) > 0:
                         # Usually list of dict or list of paths
                         item = result[0]
                         out_path = item.get('image') if isinstance(item, dict) else item
                    elif isinstance(result, tuple) and len(result) > 0:
                         out_path = result[0]
                    else:
                         out_path = result
                else:
                    print("GenAI returned empty result.")
                     
                print(f"GenAI Result Path: {out_path}")
                
                if out_path and os.path.exists(out_path):
                     # POST-PROCESS: Un-Pad (Crop back to original relative area)
                     with Image.open(out_path) as res_pil:
                         # Res is likely 768x1024 (3:4) or similar.
                         # We need to map the padding relative to the RESULT dimensions.
                         rw, rh = res_pil.size
                         
                         # Since we padded the INPUT to exactly 3:4, and OOTD outputs 3:4...
                         # The relative padding % should be identical.
                         
                         if pad_w > 0: # We added width padding
                             # Calculate Pad Percentage of Input Padded Image
                             # pad_l / target_w
                             # But wait, we have orig_w and target_w (from logic above).
                             target_w_in = int(orig_h * target_ratio)
                             pad_l_in = (target_w_in - orig_w) // 2
                             
                             ratio_l = pad_l_in / target_w_in
                             ratio_w = orig_w / target_w_in
                             
                             # Crop Result
                             crop_x = int(rw * ratio_l)
                             crop_w = int(rw * ratio_w)
                             res_cropped = res_pil.crop((crop_x, 0, crop_x + crop_w, rh))
                             
                         elif pad_h > 0: # We added height padding
                             target_h_in = int(orig_w / target_ratio)
                             pad_t_in = (target_h_in - orig_h) // 2
                             
                             ratio_t = pad_t_in / target_h_in
                             ratio_h = orig_h / target_h_in
                             
                             crop_y = int(rh * ratio_t)
                             crop_h = int(rh * ratio_h)
                             res_cropped = res_pil.crop((0, crop_y, rw, crop_y + crop_h))
                         else:
                             res_cropped = res_pil
                             
                         # Convert to bytes
                         buf = io.BytesIO()
                         res_cropped.save(buf, format="JPEG", quality=95)
                         return buf.getvalue()
                         
                else:
                     print("GenAI returned invalid path.")
                     return None

            except Exception as e:
                print(f"GenAI Call Error: {e}")
                raise e # Re-raise to ensure main handler catches it

        except Exception as e:
            print(f"Gradio VTON Setup/Run Failed: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"VTON Error: {str(e)[:100]}")

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
        # updated model name to stable version
        # gemini-1.5-flash gave 404. Using gemini-flash-latest which is confirmed available.
        model = genai.GenerativeModel('gemini-flash-latest') 
        
        try:
            response = model.generate_content([prompt, image_part])
            
            # Robust Parsing
            try:
                text = response.text.replace("```json", "").replace("```", "").strip()
                # Find first { and last }
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end != 0:
                    text = text[start:end]
                    
                data = json.loads(text)
            except Exception as parse_err:
                print(f"JSON Parse Error: {parse_err}. Raw Text: {response.text}")
                # FAIL OPEN: If AI messes up formatting, assume valid to avoid blocking user.
                print("Defaulting to VALID (Fail Open).")
                return {"valid": True, "reason": "AI 輸出格式錯誤 (自動通過)", "processed_image": img_bytes}
            
            if not data.get("valid", False):
                # Construct strict failure reason
                reasons = []
                if not data.get("is_single"): reasons.append("偵測到多人或無人")
                if not data.get("is_front"): reasons.append("非正面拍攝")
                if not data.get("is_full_body"): reasons.append("非全身照(需含膝蓋以上)")
                
                full_reason = "、".join(reasons)
                if not full_reason: full_reason = data.get("reason", "照片不符規格")
                
                return {"valid": False, "reason": full_reason, "processed_image": None}
            
            # User Request: "If valid, do not move/resize photo". 
            # We skip all auto-crop logic and return original bytes.
            print("Validation Passed. Keeping original image as requested.")
            return {"valid": True, "reason": "OK (Original Kept)", "processed_image": img_bytes}

        except Exception as e:
            print(f"Validation Error: {e}")
            # Strict Failure: Do not allow bypass on error
            return {"valid": False, "reason": f"AI 驗證連線失敗: {str(e)}", "processed_image": None}

    def _add_watermark(self, img_bytes: bytes, text: str = "此為試穿效果，並非真實穿著樣貌") -> bytes:
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
        
        # 1. Replicate (Paid, Best)
        if self.replicate_token and method != 'overlay':
            try:
                print(f"🚀 Starting Replicate processing...")
                # 確保傳入的是二進位數據，而不是路徑
                with open(cloth_img_path, "rb") as f:
                    cloth_bytes = f.read()

                # Use Hardcoded Version Hash to avoid "NoneType" error during lookup
                import replicate
                client = replicate.Client(api_token=self.replicate_token)
                
                # This is the "cuuupid/idm-vton" model: c871bb9b046607e580c22118d08d6800dd7edc9b11e73719000c0293d5bd7308
                model_id = "cuuupid/idm-vton:c871bb9b046607e580c22118d08d6800dd7edc9b11e73719000c0293d5bd7308"
                print(f"Using Replicate Model: {model_id}")
                
                # Prepare Inputs with explicit filenames (Fix for 'Concatenate NoneType' error)
                human_file = io.BytesIO(person_img_bytes)
                human_file.name = "human.jpg"
                
                cloth_file = io.BytesIO(cloth_bytes)
                cloth_file.name = "cloth.jpg"

                print(f"Human File: Size={human_file.getbuffer().nbytes} Name={human_file.name}")
                print(f"Cloth File: Size={cloth_file.getbuffer().nbytes} Name={cloth_file.name}")

                output = client.run(
                    model_id,
                    input={
                        "human_img": human_file, 
                        "garm_img": cloth_file,
                        "category": category.lower() if category.lower() in ["upper_body", "lower_body", "dresses"] else "upper_body",
                        "crop": False, 
                        "steps": 20 # Reduced from 30 to speed up and avoid Vercel 60s timeout
                    }
                )
                print(f"Replicate Result URL: {output}")
                if output:
                    # Replicate returns a URL
                    import requests
                    res = requests.get(output)
                    if res.status_code == 200:
                        final_result_bytes = res.content
                        print("Replicate success. Image downloaded.")
                    else:
                        print(f"Replicate URL download failed: {res.status_code}")
                        
            except Exception as e:
                print(f"Replicate Error Traceback: {traceback.format_exc()}")
                # Debugging: Stop fallback to see WHY Replicate is failing
                print("⚠️ Replicate failed. FORCING ERROR for debugging...")
                raise Exception(f"Replicate Error: {str(e)}") # Force UI to show error
                
                # print("⚠️ Replicate failed. Falling back to Free Model...")
                # pass # Fallback disabled for debug
                
        else:
             print(f"Skipping Replicate. Token: {bool(self.replicate_token)}, Method: {method}")
 
             
        # 2. Gradio (Free GenAI)
        if method != 'overlay' and not final_result_bytes:
            print(f"Attempting OOTDiffusion (Free GenAI) for {cloth_name} ({category})...")
            gen_img = self._try_on_gradio(person_img_bytes, cloth_img_path, cloth_name, category, height_ratio)
            if gen_img:
                final_result_bytes = gen_img
        elif method == 'overlay':
            print(f"Skipping GenAI due to explicit method='{method}'")
            
        # 3. Fallback: Removed.
        # User requested NO overlay/paste results.
        if not final_result_bytes:
             print("GenAI failed and Fallback is disabled.")
             raise Exception("生成失敗：AI 模型無回應，請稍後再試。")
        
        # 4. Post-Process: Resize back to Original Dimensions (User Request)
        if final_result_bytes:
            try:
                from PIL import Image # Fix: Import Image locally to avoid NameError
                # Get original size
                with Image.open(io.BytesIO(person_img_bytes)) as orig_img:
                    orig_w, orig_h = orig_img.size
                    
                with Image.open(io.BytesIO(final_result_bytes)) as res_img:
                    # Only resize if different
                    if res_img.size != (orig_w, orig_h):
                        print(f"Resizing result from {res_img.size} to original {orig_w}x{orig_h}...")
                        res_img = res_img.resize((orig_w, orig_h), Image.Resampling.LANCZOS)
                        
                        # Save back to bytes
                        out = io.BytesIO()
                        res_img.save(out, format="JPEG", quality=95)
                        final_result_bytes = out.getvalue()
            except Exception as e:
                print(f"Resize Error: {e}")

        # 5. Post-Process: Add Watermark (Prompt)
        if final_result_bytes:
            print("Adding Disclaimer Watermark...")
            final_result_bytes = self._add_watermark(final_result_bytes)
            
        return final_result_bytes
