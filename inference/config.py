"""
Cloud-server path configuration.
All paths are absolute paths on the AutoDL server.
"""
import os

# ── DINOv2 shared backbone ──────────────────────────────────────────────────
DINO_HF_CACHE   = "/root/autodl-tmp/hf_models"
DINO_HF_MODEL   = "facebook/dinov2-large"
TIMM_DINOV2_WEIGHTS = "/root/autodl-tmp/hf_models/models--timm--vit_large_patch14_dinov2.lvd142m/snapshots/47b73eefe95e8d44ec3623f8890bd894b6ea2d6c/model.safetensors"

# ── DINO_CNN ─────────────────────────────────────────────────────────────────
DINO_CNN_WEIGHTS = "/root/autodl-tmp/DINO_CNN/model_seg_final.pt"
DINO_CNN_IMG_SIZE = 518

# ── RIGID ────────────────────────────────────────────────────────────────────
# noise_level tuned on DCIC data (default paper value was 0.05)
RIGID_NOISE_LEVEL = 0.5
# On DCIC data the direction inverts (fake has slightly higher sim).
# Threshold & direction were calibrated from saved score files.
RIGID_THRESHOLD   = 0.8747   # similarity >= threshold → FAKE
RIGID_FAKE_IF_HIGH = True     # True = high similarity means fake (inverted)

# ── WaRPAD ───────────────────────────────────────────────────────────────────
WARPAD_PREP_SIZE   = 896
WARPAD_PATCH_SIZE  = 56
WARPAD_NOISE_LEVEL = 0.2
# AUC ≈ 0.50 on DCIC data; threshold set at midpoint of both distributions
WARPAD_THRESHOLD   = 0.9424   # mean similarity >= threshold → REAL

# ── FakeShield ───────────────────────────────────────────────────────────────
FAKESHIELD_WEIGHT_DIR  = "/root/autodl-tmp/FakeShield/weight/fakeshield-v1-22b"
FAKESHIELD_SCRIPT_DIR  = "/root/autodl-tmp/FakeShield"
FAKESHIELD_TMP_DIR     = "/tmp/fakeshield_inference"

# ── Service ───────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 8081
