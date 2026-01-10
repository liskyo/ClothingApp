from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response
from typing import Optional, List
import shutil
import os
import uuid

from .clothes_manager import ClothesManager
from .ai_service import AIService

app = FastAPI()

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "model")
DATA_FILE = os.path.join(MODEL_DIR, "clothes.json")

# Ensure model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)

# Services
clothes_manager = ClothesManager(DATA_FILE)
ai_service = AIService()

# Mount static files for accessing images
app.mount("/images", StaticFiles(directory=MODEL_DIR), name="images")

@app.get("/api/clothes")
async def get_clothes(gender: Optional[str] = None, height: Optional[str] = None):
    """
    Get list of clothes. Optional filters for gender and height.
    """
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
            # Assume existing files have .jpg extension if not specified in ID?
            # The ID generation adds extension-less ID.
            # But we need to map ID to filename.
            # Implementation Detail: When uploading, we should probably save as {id}.jpg
            # and checking if parsing legacy IDs (which might be 001.jpg or just 001).
            
            # Let's assume files are named {id}.jpg for simplicity in this new system.
            c['image_url'] = f"/images/{c['id']}.jpg"

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
    1. Save temporarily.
    2. Analyze with AI (Mock).
    3. Save permanently with generated ID.
    4. Update database.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Use AI to analyze
        analysis = ai_service.analyze_image_style(content)
        name = analysis.get("name", "未命名")
        style = analysis.get("style", "一般")
        
        # Add to database to get ID
        new_id = clothes_manager.add_clothing_item(name, height_range, gender, style)
        
        # Save file to model directory with ID
        # Preserve original extension or enforce jpg? Enforcing jpg is easier.
        filename = f"{new_id}.jpg"
        file_path = os.path.join(MODEL_DIR, filename)
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        return {
            "id": new_id,
            "name": name,
            "style": style,
            "filename": filename
        }
        
    except Exception as e:
        print(f"Error processing upload: {e}")
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
        
        # Call AI VTON Service
        result_image = ai_service.virtual_try_on(user_image, json_path)
        
        return Response(content=result_image, media_type="image/jpeg")

    except Exception as e:
        print(f"Try-on error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
