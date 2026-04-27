# Forgery Lens — Image Forgery Detection & Localization

A web-based image forgery detection system combining four complementary models: a supervised DINOv2+CNN detector, FakeShield (ICLR 2025), and two training-free baselines (RIGID, WaRPAD). Supports pixel-level forgery localization and natural language explanation for document-scene images.

## Features

- **Four detection models** selectable at runtime
- **Pixel-level mask** output for forgery localization (DINO+CNN, FakeShield)
- **Natural language explanation** of tampered regions
- Async inference queue with live progress tracking
- Three-tier architecture: React frontend → FastAPI backend → GPU inference service

## Models

| Model | Type | Localization | Explanation |
|-------|------|--------------|-------------|
| DINO+CNN | Supervised (DINOv2-Large + CNN decoder) | Pixel-level mask | Template-based |
| FakeShield | MLLM — DTE-FDM + MFLM (ICLR 2025) | SAM pixel-level mask | Free-form text |
| RIGID | Training-free (DINOv2 CLS cosine similarity) | None | Template-based |
| WaRPAD | Training-free (wavelet patch perturbation) | None | Template-based |

## Architecture

```
frontend/     React + Vite   — upload, model selector, result panel
backend/      FastAPI        — serial task queue, proxies to inference
inference/    FastAPI        — GPU model endpoints (one per model)
```

The inference service is designed to run on a GPU host; the backend communicates with it over a configurable URL.

## Getting Started

### Prerequisites

- Node.js 18+, Python 3.10+
- GPU host with CUDA for inference (CPU fallback available for RIGID/WaRPAD)

### 1. Inference service

```bash
cd inference
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8081
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
```

Set environment variables as needed (see below).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Docker (production)

```bash
docker compose up --build -d   # http://localhost:80
```

## Configuration

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `INFERENCE_URL` | `http://localhost:8081` | Inference service base URL |
| `TASK_TIMEOUT` | `300` | Inference timeout (seconds) |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |

### Inference

| Variable | Description |
|----------|-------------|
| `DTE_PYTHON` | Python executable with `transformers==4.37.2` (FakeShield DTE-FDM stage) |
| `MFLM_PYTHON` | Python executable with `transformers==4.28.0` (FakeShield MFLM stage) |

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/submit` | Submit image + model, returns `task_id` |
| `GET` | `/api/status/{task_id}` | Poll task status and result |

## License

MIT
