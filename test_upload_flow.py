import requests
import os

from PIL import Image
import io

# Create a valid dummy image (Cloudinary validates headers)
dummy_filename = "test_upload.jpg"
img = Image.new('RGB', (100, 100), color = 'red')
img.save(dummy_filename)

url = "http://localhost:8000/api/upload"

files = {
    'file': (dummy_filename, open(dummy_filename, 'rb'), 'image/jpeg')
}
data = {
    'height_range': '160-170',
    'gender': '女性'
}

print("Testing Upload Endpoint...")
try:
    # Need backend running. This script assumes backend is running on port 8000.
    # Since I cannot run the backend server in background easily and wait for it in this environment effectively 
    # (relying on user to run it usually), I will write a script that imports the app and uses TestClient.
    
    from fastapi.testclient import TestClient
    from backend.main import app
    
    client = TestClient(app)
    
    response = client.post("/api/upload", files=files, data=data)
    
    if response.status_code == 200:
        res_json = response.json()
        print("✅ Upload Success!")
        print(f"ID: {res_json.get('id')}")
        print(f"Name: {res_json.get('name')}")
        print(f"Style: {res_json.get('style')}")
        print(f"Image URL: {res_json.get('image_url')}")
        
        if "cloudinary" in res_json.get('image_url', ''):
             print("☁️  Cloudinary detected in URL")
        else:
             print("📂 Local URL detected (Fallback/Mock)")
             
    else:
        print(f"❌ Upload Failed: {response.status_code}")
        print(response.text)

except ImportError as e:
    print(f"❌ Dependencies missing or path issue: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

# Cleanup
try:
    os.remove(dummy_filename)
except:
    pass
