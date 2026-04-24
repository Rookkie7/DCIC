# DCIC Image Forgery Detection System

ISY5004 Capstone Project — NUS 2025  
Web demo for image forgery detection using four complementary models.

## Architecture

```
Local machine
├── frontend/   React + Vite  (port 5173 / 80)
├── backend/    FastAPI       (port 8000)  ← task queue + SSH tunnel proxy
│
SSH tunnel ──── ssh -N -L 8081:localhost:8081 -p 43780 root@connect.westd.seetacloud.com
│
Cloud server (AutoDL)
└── inference/  FastAPI       (port 8081)  ← four model endpoints
```

## Quick Start (Development)

### 1. Start SSH tunnel
```bash
ssh -N -L 8081:localhost:8081 -p 43780 root@connect.westd.seetacloud.com
```

### 2. Start inference service (on cloud server)
```bash
cd /root/autodl-tmp/DCIC/inference
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8081
```

### 3. Start local backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
```

### 4. Start frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Docker (Production)
```bash
ssh -fN -L 8081:localhost:8081 -p 43780 root@connect.westd.seetacloud.com
docker compose up --build -d   # http://localhost:80
```

## Models

| Model | Type | Localization | Explanation |
|-------|------|--------------|-------------|
| DINO+CNN | Supervised | Pixel-level mask | Rule template |
| FakeShield | MLLM (ICLR 2025) | Pixel-level mask | DTE-FDM output |
| RIGID | Training-free | None | Rule template |
| WaRPAD | Training-free | None | Rule template |

## Environment Variables — backend

| Variable | Default | Description |
|----------|---------|-------------|
| `INFERENCE_URL` | `http://localhost:8081` | Inference service (via SSH tunnel) |
| `TASK_TIMEOUT` | `300` | Max wait seconds |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |

## Environment Variables — inference

| Variable | Description |
|----------|-------------|
| `DTE_PYTHON` | Python with transformers==4.37.2 (for FakeShield DTE-FDM) |
| `MFLM_PYTHON` | Python with transformers==4.28.0 (for FakeShield MFLM) |