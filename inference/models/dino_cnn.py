"""
DINO_CNN inference wrapper.
Loads DinoSegmenter once at startup and runs single-image inference.
"""
import math
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoImageProcessor, AutoModel

from config import DINO_HF_CACHE, DINO_HF_MODEL, DINO_CNN_WEIGHTS, DINO_CNN_IMG_SIZE
from utils import enhanced_adaptive_mask, gate_mask, overlay_to_base64, mask_to_base64
from utils.explanation import generate_explanation


# ── Model definition (copied from project/DINO_CNN/models.py) ────────────────

class _DinoTinyDecoder(nn.Module):
    def __init__(self, in_ch: int = 1024, out_ch: int = 1):
        super().__init__()
        self.block1 = nn.Sequential(nn.Conv2d(in_ch, 512, 3, padding=1), nn.ReLU(True), nn.Dropout2d(0.1))
        self.block2 = nn.Sequential(nn.Conv2d(512, 256, 3, padding=1), nn.ReLU(True), nn.Dropout2d(0.1))
        self.block3 = nn.Sequential(nn.Conv2d(256, 128, 3, padding=1), nn.ReLU(True))
        self.conv_out = nn.Conv2d(128, out_ch, 1)

    def forward(self, f, target_size):
        x = F.interpolate(self.block1(f), scale_factor=2, mode="bilinear", align_corners=False)
        x = F.interpolate(self.block2(x), scale_factor=2, mode="bilinear", align_corners=False)
        x = F.interpolate(self.block3(x), scale_factor=2, mode="bilinear", align_corners=False)
        x = self.conv_out(x)
        return F.interpolate(x, size=target_size, mode="bilinear", align_corners=False)


class _DinoSegmenter(nn.Module):
    def __init__(self, img_size: int = 518):
        super().__init__()
        self.img_size = img_size
        self.processor = AutoImageProcessor.from_pretrained(
            DINO_HF_MODEL,
            cache_dir=DINO_HF_CACHE,
            size={"height": img_size, "width": img_size},
        )
        self.encoder = AutoModel.from_pretrained(DINO_HF_MODEL, cache_dir=DINO_HF_CACHE)
        for p in self.encoder.parameters():
            p.requires_grad = False
        self.seg_head = _DinoTinyDecoder(in_ch=1024, out_ch=1)

    def forward_seg(self, x: torch.Tensor) -> torch.Tensor:
        imgs = (x * 255).clamp(0, 255).byte().permute(0, 2, 3, 1).cpu().numpy()
        inputs = self.processor(images=list(imgs), return_tensors="pt").to(x.device)
        outputs = self.encoder(**inputs)
        feats = outputs.last_hidden_state          # [B, 1370, 1024]
        B, N, C = feats.shape
        fmap = feats[:, 1:, :].permute(0, 2, 1)   # [B, 1024, 1369]
        s = int(math.sqrt(N - 1))
        fmap = fmap.reshape(B, C, s, s)
        return self.seg_head(fmap, (self.img_size, self.img_size))


# ── Singleton loader ──────────────────────────────────────────────────────────

_model: _DinoSegmenter | None = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> _DinoSegmenter:
    global _model
    if _model is None:
        m = _DinoSegmenter(DINO_CNN_IMG_SIZE).to(_device)
        m.load_state_dict(torch.load(DINO_CNN_WEIGHTS, map_location=_device))
        m.eval()
        _model = m
    return _model


# ── Public inference API ──────────────────────────────────────────────────────

def infer(image_bytes: bytes) -> dict:
    """
    Run DINO_CNN inference on raw image bytes.

    Returns
    -------
    dict with keys:
        label         : "real" | "fake"
        confidence    : float in [0, 1]
        mask_base64   : PNG mask as base64 string | None
        overlay_base64: overlay image as base64 JPEG | None
        explanation   : str
    """
    model = _load_model()

    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    orig_h, orig_w = img_bgr.shape[:2]

    # Resize and tensorise
    img_input = cv2.resize(img_rgb, (DINO_CNN_IMG_SIZE, DINO_CNN_IMG_SIZE))
    x = torch.from_numpy(img_input.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(_device)

    # TTA inference (original + horizontal flip)
    with torch.no_grad():
        p1 = torch.sigmoid(model.forward_seg(x))
        p2 = torch.sigmoid(model.forward_seg(torch.flip(x, dims=[3])))
        p2 = torch.flip(p2, dims=[3])
    prob_map = ((p1 + p2) / 2.0).squeeze().cpu().numpy()   # [518, 518]

    # Post-process
    mask_small, _ = enhanced_adaptive_mask(prob_map, alpha_grad=0.45)
    is_forged = gate_mask(mask_small, prob_map, area_thr=200, mean_thr=0.22)

    label = "fake" if is_forged else "real"
    # confidence: mean prob in masked region (fake) or 1-mean prob (real)
    if is_forged and mask_small.sum() > 0:
        confidence = float(prob_map[mask_small == 1].mean())
    else:
        confidence = float(1.0 - prob_map.mean())

    mask_b64 = overlay_b64 = None
    if is_forged:
        mask_b64 = mask_to_base64(mask_small, orig_h, orig_w)
        overlay_b64 = overlay_to_base64(img_bgr, mask_small, orig_h, orig_w)

    explanation = generate_explanation(
        label=label, model="dino_cnn",
        mask=mask_small if is_forged else None,
        confidence=confidence,
    )

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "mask_base64": mask_b64,
        "overlay_base64": overlay_b64,
        "explanation": explanation,
    }
