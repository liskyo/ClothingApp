from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from typing import Optional, List
import shutil
import os
# import uuid # Removed uuid

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
    return {"status": "ok", "backend": "active", "managers": {"clothes": manager_status, "ai": ai_status}}

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
            filtered = [c for c in filtered if gender in c['gender']]
        if height:
            # Simple string match for now. 
            # Ideally, we should parse "150-165cm" into ranges and check overlap.
            # For prototype, we check if the search term is in the range string.
            filtered = [c for c in filtered if height in c['height_range']]
            
        # Add image URL to response
        for c in filtered:
            # If item has 'image_url', use it (Cloudinary or predefined local)
            # If not, fallback to legacy ID-based local path
            if 'image_url' not in c or not c['image_url']:
                c['image_url'] = f"/images/{c['id']}.jpg"
            
            # If it's a local path but not absolute (starts with /), ensure it's correct context?
            # Our frontend expects /images/... which is relative to root domain.
            # Cloudinary URL starts with http.

        return filtered
    except Exception as e:
        print(f"Error in get_clothes: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_clothing(
    file: UploadFile = File(...),
    height_range: str = Form(...),
    gender: str = Form(...)
):
    """
    Upload a clothing image.
    1. Analyze with AI (Mock or Real).
    2. Upload to Cloudinary (if configured) or Save Locally.
    3. Save to DB (MongoDB or JSON).
    """
    try:
        # Read file content
        content = await file.read()
        
        # Use AI to analyze
        analysis = ai_service.analyze_image_style(content)
        name = analysis.get("name", "未命名")
        style = analysis.get("style", "一般")
        
        image_url = ""
        filename = ""
        
        # Check for Cloudinary
        cloudinary_url = os.getenv("CLOUDINARY_URL")
        uploaded_to_cloud = False
        
        if cloudinary_url:
            try:
                import cloudinary
                import cloudinary.uploader
                import io
                
                # Cloudinary auto-configures from CLOUDINARY_URL env var
                # Upload directly from bytes, needs BytesIO
                print("Uploading to Cloudinary...")
                # Wrap bytes in BytesIO and naming it helps Cloudinary detect type
                file_obj = io.BytesIO(content)
                file_obj.name = "upload.jpg" 
                
                response = cloudinary.uploader.upload(file_obj, folder="clothing_app")
                image_url = response.get("secure_url")
                print(f"Cloudinary Upload Success: {image_url}")
                uploaded_to_cloud = True
            except Exception as e:
                print(f"Cloudinary Upload Failed: {e}. Fallback to local.")
                # Important: If Cloudinary fails, we set flag to False so we try local
                uploaded_to_cloud = False
        
        if not cloudinary_url:
            print("Warning: CLOUDINARY_URL not set. Attempting local save.")
            # Fallback to local storage (Volatile on Vercel)
            # Use tempfile or standard path, but handle Read-Only errors
            try:
                import time
                temp_id = f"temp_{int(time.time())}"
                filename = f"{temp_id}.jpg"
                
                # Check write permissions implicitly
                file_path = os.path.join(MODEL_DIR, filename)
                
                with open(file_path, "wb") as f:
                    f.write(content)
                
                image_url = f"/images/{filename}"
            except OSError as e:
                print(f"Local Save Failed (Read-Only FS?): {e}")
                # If we cannot save locally and not on Cloudinary, we must fail or warn
                if not uploaded_to_cloud:
                   raise HTTPException(status_code=500, detail="Storage Error: Cannot save file (Cloudinary not configured & Local FS read-only).")


        # Add to database
        # Note: If local, we might want to update the filename with real ID later, 
        # but for simplicity, let's just keep the temp name or handle it.
        # Actually, if we use MongoDB, ID is generated there.
        # If we use local JSON, ID is generated there.
        
        new_id = clothes_manager.add_clothing_item(name, height_range, gender, style, image_url=image_url)
        
        # If local and we want strict {id}.jpg, we would need to rename.
        # But our new system stores `image_url`, so we don't STRICTLY need {id}.jpg anymore.
        # The frontend uses `image_url` property.
        
        return {
            "id": new_id,
            "name": name,
            "style": style,
            "image_url": image_url
        }
        
    except Exception as e:
        print(f"Error processing upload: {e}")
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
        # Verify clothes exist
        json_path = os.path.join(MODEL_DIR, f"{clothes_id}.jpg")
        if not os.path.exists(json_path):
             raise HTTPException(status_code=404, detail="Clothes not found")

        user_image = await file.read()
        
        # Get clothes info
        cloth_info = clothes_manager.get_cloth_by_id(clothes_id)
        cloth_name = cloth_info['name'] if cloth_info else "Upper-body"
        category = cloth_info.get('category', 'Upper-body') if cloth_info else "Upper-body"
        try_on_method = cloth_info.get('try_on_method', 'auto') if cloth_info else 'auto'
        height_ratio = cloth_info.get('height_ratio', None) if cloth_info else None
        
        # Call AI VTON Service
        result_image = ai_service.virtual_try_on(
            user_image, 
            json_path, 
            cloth_name=cloth_name, 
            category=category,
            method=try_on_method,
            height_ratio=height_ratio
        )
        
        return Response(content=result_image, media_type="image/jpeg")

        return Response(content=result_image, media_type="image/jpeg")

    except Exception as e:
        print(f"Try-on error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
