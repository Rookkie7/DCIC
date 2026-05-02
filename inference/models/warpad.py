"""
WaRPAD inference wrapper (training-free, wavelet-patch based).
Calibrated threshold for DCIC data: mean_sim < 0.9424 → FAKE.
Note: AUC ≈ 0.50 on DCIC data — limited detection capability.
"""
from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import timm
from PIL import Image
from torchvision import transforms
from pytorch_wavelets import DWTForward, DWTInverse

from config import (
    TIMM_DINOV2_WEIGHTS,
    WARPAD_PREP_SIZE, WARPAD_PATCH_SIZE, WARPAD_NOISE_LEVEL, WARPAD_THRESHOLD,
)
from utils.explanation import generate_explanation

_MEAN = (0.485, 0.456, 0.406)
_STD  = (0.229, 0.224, 0.225)

_transform = transforms.Compose([
    transforms.Resize((WARPAD_PREP_SIZE, WARPAD_PREP_SIZE), interpolation=Image.BICUBIC),
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])

_model: torch.nn.Module | None = None
_dwt: DWTForward | None = None
_idwt: DWTInverse | None = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model():
    global _model, _dwt, _idwt
    if _model is None:
        if not TIMM_DINOV2_WEIGHTS:
            raise RuntimeError(
                "TIMM_DINOV2_WEIGHTS is not set. Point it to the local "
                "vit_large_patch14_dinov2.lvd142m checkpoint file."
            )
        _model = timm.create_model(
            "vit_large_patch14_dinov2.lvd142m",
            pretrained=True,
            pretrained_cfg_overlay={"file": TIMM_DINOV2_WEIGHTS},
            img_size=WARPAD_PATCH_SIZE,
        ).eval().to(_device)
        _dwt  = DWTForward(J=2, wave="haar").to(_device)
        _idwt = DWTInverse(wave="haar").to(_device)


@torch.no_grad()
def _warpad_score(tensor: torch.Tensor) -> float:
    """Returns mean patch similarity score for the image tensor [1,3,H,W]."""
    b, c, h, w = tensor.shape
    ps = WARPAD_PATCH_SIZE

    # Unfold into patches [b, c, nph, npw, ps, ps] → [-1, c, ps, ps]
    patches = tensor.unfold(2, ps, ps).unfold(3, ps, ps)
    n_h, n_w = patches.shape[2], patches.shape[3]
    patches = patches.reshape(b, c, -1, ps, ps).transpose(1, 2)
    patches = patches.reshape(-1, c, ps, ps)   # [N_patches, c, ps, ps]

    yl, yh = _dwt(patches)
    pert = _idwt((torch.zeros_like(yl), yh))
    perturbed = patches - WARPAD_NOISE_LEVEL * pert

    out   = _model.forward_features(patches)[:, 0, :]
    out_p = _model.forward_features(perturbed)[:, 0, :]
    if hasattr(_model, "norm"):
        out   = _model.norm(out)
        out_p = _model.norm(out_p)

    sims = F.cosine_similarity(out, out_p, dim=-1)   # [N_patches]
    return float(sims.mean().item())


def infer(image_bytes: bytes) -> dict:
    _load_model()

    nparr  = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))

    tensor = _transform(img_pil).unsqueeze(0).to(_device)
    score  = _warpad_score(tensor)

    # Higher sim → more real (standard direction)
    is_fake = score < WARPAD_THRESHOLD
    label   = "fake" if is_fake else "real"

    confidence = float(np.clip(abs(score - WARPAD_THRESHOLD) / WARPAD_THRESHOLD, 0, 1))

    explanation = generate_explanation(
        label=label, model="warpad", confidence=confidence
    )
    return {
        "label": label,
        "confidence": round(confidence, 4),
        "mask_base64": None,
        "overlay_base64": None,
        "explanation": explanation,
        "raw_score": round(score, 6),
    }
