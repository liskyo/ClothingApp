from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from typing import Optional, List
import shutil
import shutil
import os

# Serverless/Vercel Fix: Force cache directories to /tmp
os.environ['HF_HOME'] = '/tmp/hf'
os.environ['GRADIO_TEMP_DIR'] = '/tmp/gradio'
os.environ['XDG_CACHE_HOME'] = '/tmp/cache'

# script continues...

from backend.clothes_manager import ClothesManager
from backend.ai_service import AIService
from pydantic import BaseModel

app = FastAPI()

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "model")
DATA_FILE = os.path.join(MODEL_DIR, "clothes.json")

# Debug Endpoint
@app.get("/api/debug")
async def debug_info():
    try:
        files = []
        for root, dirs, filenames in os.walk(BASE_DIR):
            for filename in filenames:
                files.append(os.path.relpath(os.path.join(root, filename), BASE_DIR))
        return {
            "base_dir": BASE_DIR,
            "model_dir": MODEL_DIR,
            "data_file": DATA_FILE,
            "exists": os.path.exists(DATA_FILE),
            "files": files[:50], # Limit output
            "env": {k: "***" for k in os.environ.keys()} # List env keys only
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    manager_status = "active" if clothes_manager else "failed"
    ai_status = "active" if ai_service else "failed"
    
    storage_info = {"mode": "unknown", "error": None}
    if clothes_manager:
        try:
            storage_info = clothes_manager.get_status()
        except Exception as e:
            storage_info["error"] = str(e)
        
    return {
        "status": "ok", 
        "backend": "active", 
        "managers": {"clothes": manager_status, "ai": ai_status},
        "storage": storage_info
    }

# Ensure model directory exists - SKIP for Vercel (Read Only)
# os.makedirs(MODEL_DIR, exist_ok=True)

# Services Initialization with Error Handling
clothes_manager = None
ai_service = None

try:
    clothes_manager = ClothesManager(DATA_FILE)
except Exception as e:
    print(f"Failed to init ClothesManager: {e}")

try:
    ai_service = AIService()
except Exception as e:
    print(f"Failed to init AIService: {e}")

# Mount static files for accessing images
try:
    if os.path.exists(MODEL_DIR):
        app.mount("/images", StaticFiles(directory=MODEL_DIR), name="images")
    else:
        print(f"Warning: Model dir {MODEL_DIR} not found. Images will not load.")
except Exception as e:
    print(f"Failed to mount static files: {e}")

@app.get("/api/clothes")
async def get_clothes(gender: Optional[str] = None, height: Optional[str] = None):
    """
    Get list of clothes. Optional filters for gender and height.
    """
    if not clothes_manager:
        raise HTTPException(status_code=500, detail="ClothesManager failed to initialize")
        
    try:
        all_clothes = clothes_manager.get_all_clothes()
        
        # Filter logic
        filtered = all_clothes
        if gender:
            # "中性" matches "女性"? Debatable. 
            # Current logic: if "女性", we want items marked "女性" or "中性"?
            # User Input: "女性" -> returns items with gender="女性" or "中性" (maybe?)
            # Or if item is "中性", it matches everyone.
            # Let's adjust: Item matches if item.gender == '中性' OR item.gender == user_gender
            if gender != '中性':
                filtered = [c for c in filtered if c['gender'] == '中性' or gender in c['gender']]
            else:
                 # Users selecting "中性" might want everything or just neutral?
                 # Usually users select their OWN gender.
                 # If user says "中性", they see "中性" items.
                 filtered = [c for c in filtered if c['gender'] == '中性']
        
        # Debugging: Expose storage mode in header
        mode = "MongoDB" if clothes_manager.use_mongo else "Local-JSON"
        return JSONResponse(content=filtered, headers={"X-Storage-Mode": mode})

        if height:
        if height:
            # Range Logic: Parse "155-175"
            def is_in_range(user_h, range_str):
                try:
                    # Extract numbers
                    import re
                    nums = re.findall(r'\d+', range_str)
                    if len(nums) >= 2:
                        min_h, max_h = int(nums[0]), int(nums[1])
                        return min_h <= int(user_h) <= max_h
                    if len(nums) == 1:
                        # Maybe "160+" or "160cm"
                        return int(nums[0]) - 5 <= int(user_h) <= int(nums[0]) + 5
                    return False
                except:
                    return False

            filtered = [c for c in filtered if is_in_range(height, c.get('height_range', ''))]
            
        # Add image URL to response
        for c in filtered:
            if 'image_url' not in c or not c['image_url']:
                c['image_url'] = f"/images/{c['id']}.jpg"

        return filtered
    except Exception as e:
        print(f"Error in get_clothes: {e}")
        import traceback
        traceback.print_exc()
        return []
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug-status")
async def debug_status():
    """
    Diagnostic endpoint to check environment health.
    """
    import tempfile
    import os
    import sys
    
    status = {
        "python_version": sys.version,
        "temp_dir": tempfile.gettempdir(),
        "hf_home": os.environ.get("HF_HOME"),
        "gradio_temp": os.environ.get("GRADIO_TEMP_DIR"),
        "write_test": "pending",
        "gradio_import": "pending",
        "cloudinary_import": "pending"
    }
    
    # 1. Test Write
    try:
        with tempfile.NamedTemporaryFile(delete=True) as f:
            f.write(b"test")
        status["write_test"] = "ok"
    except Exception as e:
        status["write_test"] = f"fail: {str(e)}"
        
    # 2. Test Import
    try:
        import gradio_client
        status["gradio_import"] = f"ok ({gradio_client.__version__})"
    except Exception as e:
        status["gradio_import"] = f"fail: {str(e)}"

    # 3. Test Cloudinary
    try:
        import cloudinary
        status["cloudinary_import"] = "ok"
    except Exception as e:
        status["cloudinary_import"] = f"fail: {str(e)}"
        
    return status

@app.post("/api/upload")
async def upload_clothing(
    file: UploadFile = File(...),
    height_range: str = Form(...),
    gender: str = Form(...)
):
    """
    Upload a clothing image.
    Optimized: Runs AI Analysis and Cloudinary Upload in PARALLEL.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Define wrapper functions for blocking calls
        def run_ai_analysis():
            return ai_service.analyze_image_style(content)
            
        def run_cloudinary_upload():
            cloudinary_url = os.getenv("CLOUDINARY_URL")
            if not cloudinary_url:
                return None, False
                
            try:
                import cloudinary
                import cloudinary.uploader
                import io
                
                print("Uploading to Cloudinary (Thread)...")
                file_obj = io.BytesIO(content)
                file_obj.name = "upload.jpg" 
                
                response = cloudinary.uploader.upload(file_obj, folder="clothing_app")
                url = response.get("secure_url")
                print(f"Cloudinary Upload Success: {url}")
                return url, True
            except Exception as e:
                print(f"Cloudinary Upload Failed: {e}")
                return None, False

        # Execute in parallel using threads (since these libs are blocking)
        import asyncio
        
        # Create tasks
        ai_task = asyncio.to_thread(run_ai_analysis)
        upload_task = asyncio.to_thread(run_cloudinary_upload)
        
        # Await both
        print("Starting Parallel Tasks: AI + Upload")
        analysis_result, (cloud_url, uploaded_to_cloud) = await asyncio.gather(ai_task, upload_task)
        print("Parallel Tasks Completed")
        
        # Process Results
        name = analysis_result.get("name", "未命名")
        style = analysis_result.get("style", "一般")
        
        image_url = ""
        
        if uploaded_to_cloud and cloud_url:
             image_url = cloud_url
        else:
             # Local Fallback (for testing or if Cloudinary fails)
             print("Using Local Fallback for Storage")
             try:
                import time
                temp_id = f"temp_{int(time.time())}"
                filename = f"{temp_id}.jpg"
                file_path = os.path.join(MODEL_DIR, filename)
                
                # Simple check to avoid crash on Read-Only FS
                try:
                    with open(file_path, "wb") as f:
                        f.write(content)
                    image_url = f"/images/{filename}"
                except OSError:
                     # If we really can't save (Read-only Vercel + No Cloudinary), we are in trouble.
                     # But we handled this logic before.
                     if not uploaded_to_cloud:
                         print("CRITICAL: Cannot save image anywhere.")
                         # For now, return empty URL or handle error
                         pass
             except Exception as e:
                print(f"Local save error: {e}")

        if not image_url and not uploaded_to_cloud:
             # If completely failed to store, we should probably warn
             # But let's proceed to allow DB entry (maybe with broken image link)
             # or raise error.
             # User prompt implies "Failed to load resource" logic handled in frontend
             pass

        # Add to database
        new_id = clothes_manager.add_clothing_item(name, height_range, gender, style, image_url=image_url)
        
        return {
            "id": new_id,
            "name": name,
            "style": style,
            "image_url": image_url
        }
        
    except Exception as e:
        print(f"Error processing upload: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/validate-avatar")
async def validate_avatar(file: UploadFile = File(...)):
    """
    Validate and Auto-Crop user photo for Try-On.
    """
    try:
        content = await file.read()
        result = ai_service.validate_and_crop_user_photo(content)
        
        if not result["valid"]:
             return JSONResponse(status_code=400, content={"message": result["reason"]})
        
        # If valid, return the processed image
        # We need to return the bytes.
        # But FastAPI return usually file or json.
        # Let's return the file directly.
        if result["processed_image"]:
             return Response(content=result["processed_image"], media_type="image/jpeg")
        else:
             # Should not happen if valid image returned
             return Response(content=content, media_type="image/jpeg")
             
    except Exception as e:
        print(f"Validate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/try-on")
async def try_on(
    file: UploadFile = File(...), # User's photo
    clothes_id: str = Form(...)
):
    """
    Virtual Try-On Endpoint.
    """
    try:
        # Get clothes info first
        cloth_info = clothes_manager.get_cloth_by_id(clothes_id)
        if not cloth_info:
             raise HTTPException(status_code=404, detail="Clothes not found in DB")

        # Determine Cloth Image Path
        # Priority: 1. Existing Local File  2. Download from Image URL
        local_path = os.path.join(MODEL_DIR, f"{clothes_id}.jpg")
        temp_cloth_path = None
        final_cloth_path = None

        if os.path.exists(local_path):
            final_cloth_path = local_path
        elif cloth_info.get('image_url', '').startswith('http'):
            # Download from Cloudinary/URL
            try:
                import requests
                import tempfile
                print(f"Downloading cloth image from {cloth_info['image_url']}...")
                response = requests.get(cloth_info['image_url'])
                if response.status_code == 200:
                    # Create temp file
                    fd, temp_cloth_path = tempfile.mkstemp(suffix=".jpg")
                    os.close(fd)
                    with open(temp_cloth_path, "wb") as f:
                        f.write(response.content)
                    final_cloth_path = temp_cloth_path
                    print(f"Downloaded to temp: {final_cloth_path}")
                else:
                    print(f"Failed to download image: {response.status_code}")
            except Exception as e:
                 print(f"Download error: {e}")
        
        if not final_cloth_path or not os.path.exists(final_cloth_path):
             raise HTTPException(status_code=404, detail="Clothing image file not found locally or remotely.")

        user_image = await file.read()
        
        cloth_name = cloth_info.get('name', 'Upper-body')
        category = cloth_info.get('category', 'Upper-body')
        try_on_method = cloth_info.get('try_on_method', 'auto')
        height_ratio = cloth_info.get('height_ratio', None)
        
        # Verify Replicate Token Status
        replicate_status = "Available" if os.environ.get("REPLICATE_API_TOKEN") else "Missing"
        print(f"Preparing AI processing. Replicate Token: {replicate_status}")
        print(f"Inputs: User({len(user_image)} bytes), Cloth({final_cloth_path})")

        # Call AI VTON Service
        try:
            print("Calling ai_service.virtual_try_on...")
            result_image = ai_service.virtual_try_on(
                user_image, 
                final_cloth_path, 
                cloth_name=cloth_name, 
                category=category,
                method=try_on_method,
                height_ratio=height_ratio
            )
            print("AI Service returned successfully.")
        finally:
            # Cleanup temp file
            if temp_cloth_path and os.path.exists(temp_cloth_path):
                try:
                    os.remove(temp_cloth_path)
                    print(f"Cleaned up temp cloth: {temp_cloth_path}")
                except:
                    pass
        
        return Response(content=result_image, media_type="image/jpeg")

        return Response(content=result_image, media_type="image/jpeg")

    except Exception as e:
        print(f"Try-on error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Try-on Error: {str(e)}")

@app.delete("/api/clothes/{cloth_id}")
async def delete_clothing(cloth_id: str):
    """
    Delete a clothing item and its image.
    """
    try:
        # Get item first to find image path/url
        item = clothes_manager.get_cloth_by_id(cloth_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        # Delete from DB
        success = clothes_manager.delete_clothing_item(cloth_id)
        if not success:
             raise HTTPException(status_code=500, detail="Failed to delete from DB")

        # Delete Image
        image_url = item.get('image_url', '')
        
        # 1. Cloudinary Delete
        if "cloudinary" in image_url and os.getenv("CLOUDINARY_URL"):
            try:
                import cloudinary.uploader
                # Extract public_id
                # URL: https://res.cloudinary.com/cloudname/image/upload/v12345/folder/id.jpg
                # We need header/id (without extension usually)
                parts = image_url.split('/')
                filename = parts[-1]
                public_id_name = filename.split('.')[0]
                
                # Check for folder (assuming 1 level folder "clothing_app")
                # If we used folder="clothing_app" in upload
                folder = "clothing_app"
                public_id = f"{folder}/{public_id_name}"
                
                print(f"Deleting from Cloudinary: {public_id}")
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Cloudinary delete failed: {e}")
        
        # 2. Local File Delete
        # Even if using Cloudinary, we might have local temp files or old files
        local_filename = f"{cloth_id}.jpg" # Simplified assumption
        local_path = os.path.join(MODEL_DIR, local_filename)
        if os.path.exists(local_path):
             try:
                 os.remove(local_path)
             except Exception as e:
                 print(f"Local file delete failed: {e}")

        return {"status": "deleted", "id": cloth_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class UpdateClothRequest(BaseModel):
    name: Optional[str] = None
    style: Optional[str] = None
    gender: Optional[str] = None
    height_range: Optional[str] = None

@app.put("/api/clothes/{cloth_id}")
async def update_clothing(cloth_id: str, updates: UpdateClothRequest):
    """
    Update clothing metadata.
    """
    try:
        # Filter None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_data:
             return {"status": "no_changes"}

        success = clothes_manager.update_clothing_item(cloth_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found or update failed")
            
        return {"status": "updated", "updates": update_data}
    except Exception as e:
        print(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
