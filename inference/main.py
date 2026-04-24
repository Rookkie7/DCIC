"""
Inference FastAPI service — runs on the AutoDL cloud server.
Listens on 0.0.0.0:8081.

Start:
    uvicorn main:app --host 0.0.0.0 --port 8081

Access from local machine via SSH tunnel:
    ssh -N -L 8081:localhost:8081 -p 43780 root@connect.westd.seetacloud.com
"""
import time
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import REGISTRY
import config

app = FastAPI(title="DCIC Forgery Detection — Inference Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_MODELS = set(REGISTRY.keys())


@app.get("/health")
def health():
    return {"status": "ok", "models": list(VALID_MODELS)}


@app.post("/infer/{model_name}")
async def infer(
    model_name: str,
    file: UploadFile = File(...),
):
    if model_name not in VALID_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown model '{model_name}'. "
                            f"Available: {sorted(VALID_MODELS)}")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    t0 = time.perf_counter()
    try:
        result = REGISTRY[model_name](image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    result["model"]      = model_name
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
