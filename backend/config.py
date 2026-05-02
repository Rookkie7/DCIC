"""Local backend configuration."""
import os

# Inference service URL (reachable via SSH tunnel on local machine)
INFERENCE_URL = os.environ.get("INFERENCE_URL", "http://localhost:8081")
FAKESHIELD_INFERENCE_URL = os.environ.get("FAKESHIELD_INFERENCE_URL", "http://localhost:8082")


def get_inference_url(model: str) -> str:
    if model == "fakeshield":
        return FAKESHIELD_INFERENCE_URL
    return INFERENCE_URL

# Task timeout (seconds)
TASK_TIMEOUT = int(os.environ.get("TASK_TIMEOUT", "300"))  # 5 minutes

# CORS origin allowed for the React dev server
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

HOST = "0.0.0.0"
PORT = 8000
