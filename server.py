import os
import sys
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import uvicorn

# Set current directory in path to resolve imports correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from module.ocr_onnx import OCR

app = FastAPI(title="Vietnamese OCR API")

# Initialize OCR Model globally
print("Initializing ONNX OCR Model...")
ocr_model = OCR()
print("Model initialized successfully!")

@app.post("/api/ocr")
async def run_ocr(file: UploadFile = File(...)):
    try:
        # Read file contents
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file or format")

        # Run OCR
        # Returns list(zip([a.tolist() for a in filter_boxes], filter_rec_res))
        results = ocr_model(img)
        return JSONResponse(content=results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for UI (index.html, style.css, app.js)
ui_dir = os.path.join(current_dir, "ui")
if os.path.exists(ui_dir):
    app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")
else:
    print(f"Warning: UI directory not found at {ui_dir}")

if __name__ == "__main__":
    print("Starting Vietnamese OCR Demo Server at http://127.0.0.1:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
