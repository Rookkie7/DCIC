"""
Local backend FastAPI service.
Runs on localhost:8000.
Forwards inference requests to the cloud server via SSH tunnel (localhost:8081).

Start:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from task_queue import queue
import config

app = FastAPI(title="DCIC Forgery Detection — Local Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_MODELS = {"dino_cnn", "fakeshield", "rigid", "warpad"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/submit")
async def submit(
    model: str = Form(...),
    file: UploadFile = File(...),
):
    if model not in VALID_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model '{model}'.")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG or PNG).")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(image_bytes) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")

    task_id = await queue.submit(model=model, image_bytes=image_bytes)
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/status/{task_id}")
async def status(task_id: str):
    result = queue.get_status(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
