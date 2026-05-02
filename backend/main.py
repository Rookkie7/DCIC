"""Local backend FastAPI service."""
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from batch_queue import batch_queue
from task_queue import queue
import config


app = FastAPI(title="DCIC Forgery Detection Local Backend", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_MODELS = {"dino_cnn", "fakeshield", "rigid", "warpad"}


def validate_model_options(model: str, explain_mode: str) -> None:
    if model not in VALID_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid model '{model}'.")
    if explain_mode not in {"template", "llm"}:
        raise HTTPException(status_code=400, detail="explain_mode must be 'template' or 'llm'.")
    if explain_mode == "llm" and model != "dino_cnn":
        raise HTTPException(status_code=400, detail="LLM reports are currently supported only for DINO + CNN.")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/submit")
async def submit(
    model: str = Form(...),
    explain_mode: str = Form("template"),
    file: UploadFile = File(...),
):
    validate_model_options(model, explain_mode)

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG or PNG).")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB).")

    task_id = await queue.submit(model=model, image_bytes=image_bytes, explain_mode=explain_mode)
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/status/{task_id}")
async def status(task_id: str):
    result = queue.get_status(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return result


@app.post("/api/batch/submit")
async def submit_batch(
    model: str = Form(...),
    folder_path: str = Form(...),
    save_dir: str = Form(""),
    explain_mode: str = Form("template"),
    recursive: bool = Form(False),
):
    validate_model_options(model, explain_mode)
    if not folder_path.strip():
        raise HTTPException(status_code=400, detail="folder_path is required.")

    try:
        batch_id, total = await batch_queue.submit(
            model=model,
            folder_path=folder_path.strip(),
            save_dir=save_dir.strip() or None,
            explain_mode=explain_mode,
            recursive=recursive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"batch_id": batch_id, "status": "queued", "total": total, "save_dir": save_dir.strip() or None}


@app.get("/api/batch/status/{batch_id}")
async def batch_status(batch_id: str):
    result = batch_queue.get_status(batch_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Batch task not found.")
    return result


@app.get("/api/batch/image/{batch_id}/{index}")
async def batch_image(batch_id: str, index: int):
    image_path = batch_queue.get_image_path(batch_id, index)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Batch image not found.")
    return FileResponse(image_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
