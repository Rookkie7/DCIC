"""
RIGID inference wrapper (training-free).
Calibrated threshold for DCIC data: similarity >= 0.8747 → FAKE
(direction inverted from original paper; see cc-output/02_model_analysis.md).
"""
from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import timm
from PIL import Image
from torchvision import transforms

from config import RIGID_NOISE_LEVEL, RIGID_THRESHOLD, RIGID_FAKE_IF_HIGH, TIMM_DINOV2_WEIGHTS
from utils.explanation import generate_explanation

_MEAN = (0.485, 0.456, 0.406)
_STD  = (0.229, 0.224, 0.225)

_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])

_model: torch.nn.Module | None = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> torch.nn.Module:
    global _model
    if _model is None:
        if not TIMM_DINOV2_WEIGHTS:
            raise RuntimeError(
                "TIMM_DINOV2_WEIGHTS is not set. Point it to the local "
                "vit_large_patch14_dinov2.lvd142m checkpoint file."
            )
        m = timm.create_model(
            "vit_large_patch14_dinov2.lvd142m",
            pretrained=True,
            pretrained_cfg_overlay={"file": TIMM_DINOV2_WEIGHTS},
            img_size=224,
        )
        m.eval().to(_device)
        _model = m
    return _model


@torch.no_grad()
def _rigid_score(model: torch.nn.Module, tensor: torch.Tensor, noise_level: float) -> float:
    feat = model.forward_features(tensor)[:, 0, :]
    if hasattr(model, "norm"):
        feat = model.norm(feat)
    noise = torch.randn_like(tensor) * noise_level
    feat_n = model.forward_features(tensor + noise)[:, 0, :]
    if hasattr(model, "norm"):
        feat_n = model.norm(feat_n)
    return float(F.cosine_similarity(feat, feat_n, dim=-1).item())


def infer(image_bytes: bytes) -> dict:
    model = _load_model()

    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    tensor = _transform(img_pil).unsqueeze(0).to(_device)
    score = _rigid_score(model, tensor, RIGID_NOISE_LEVEL)

    # On DCIC data: high sim → fake (calibrated direction)
    is_fake = (score >= RIGID_THRESHOLD) if RIGID_FAKE_IF_HIGH else (score < RIGID_THRESHOLD)
    label = "fake" if is_fake else "real"

    # Normalise similarity to [0,1] confidence in the predicted direction
    if RIGID_FAKE_IF_HIGH:
        confidence = score if is_fake else (1.0 - score)
    else:
        confidence = (1.0 - score) if is_fake else score
    confidence = float(np.clip(confidence, 0, 1))

    explanation = generate_explanation(
        label=label, model="rigid", confidence=confidence
    )
    return {
        "label": label,
        "confidence": round(confidence, 4),
        "mask_base64": None,
        "overlay_base64": None,
        "explanation": explanation,
        "raw_score": round(score, 6),
    }
