"""
DINO-CNN v3 inference wrapper.
Uses the FPN decoder from Dino-CNN/v3/models.py and the v3 TTA/post-processing.
"""
from __future__ import annotations

import math
import os
import shutil
import tempfile

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from scipy.ndimage import binary_fill_holes
from transformers import AutoImageProcessor, AutoModel

from config import (
    DINO_HF_CACHE,
    DINO_HF_MODEL,
    DINO_CNN_WEIGHTS,
    DINO_CNN_IMG_SIZE,
    DINO_REPORT_TMP_DIR,
    QWEN_VL_MODEL_DIR,
)
from utils import mask_to_base64, overlay_to_base64
from utils.explanation import generate_explanation


class _FeatureFusionBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor | None = None) -> torch.Tensor:
        if skip is not None:
            x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class _DinoFPNDecoder(nn.Module):
    def __init__(self, embed_dim: int = 1024, out_ch: int = 1):
        super().__init__()
        self.layer4 = _FeatureFusionBlock(embed_dim, 512)
        self.layer3 = _FeatureFusionBlock(512 + embed_dim, 256)
        self.layer2 = _FeatureFusionBlock(256 + embed_dim, 128)
        self.layer1 = _FeatureFusionBlock(128 + embed_dim, 64)
        self.conv_out = nn.Conv2d(64, out_ch, kernel_size=1)

    def forward(self, features: list[torch.Tensor], target_size: tuple[int, int]) -> torch.Tensor:
        f6, f12, f18, f24 = features

        x = self.layer4(f24)
        x = self.layer3(x, f18)
        x = self.layer2(x, f12)
        x = self.layer1(x, f6)

        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = self.conv_out(x)
        return F.interpolate(x, size=target_size, mode="bilinear", align_corners=False)


class _DinoSegmenter(nn.Module):
    def __init__(self, img_size: int = 518):
        super().__init__()
        self.img_size = img_size
        self.processor = AutoImageProcessor.from_pretrained(
            DINO_HF_MODEL,
            cache_dir=DINO_HF_CACHE,
            local_files_only=True,
            size=img_size,
        )
        self.encoder = AutoModel.from_pretrained(
            DINO_HF_MODEL,
            cache_dir=DINO_HF_CACHE,
            local_files_only=True,
            output_hidden_states=True,
        )
        for p in self.encoder.parameters():
            p.requires_grad = False
        self.seg_head = _DinoFPNDecoder(embed_dim=1024, out_ch=1)

    def forward_seg(self, x: torch.Tensor) -> torch.Tensor:
        imgs = (x * 255).clamp(0, 255).byte().permute(0, 2, 3, 1).cpu().numpy()
        inputs = self.processor(images=list(imgs), return_tensors="pt").to(x.device)
        outputs = self.encoder(**inputs)
        selected_features = []

        for idx in (6, 12, 18, 24):
            feat = outputs.hidden_states[idx]
            b, n, c = feat.shape
            fmap = feat[:, 1:, :].permute(0, 2, 1)
            s = int(math.sqrt(n - 1))
            selected_features.append(fmap.reshape(b, c, s, s))

        return self.seg_head(selected_features, (self.img_size, self.img_size))


_model: _DinoSegmenter | None = None
_report_model = None
_report_processor = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_model() -> _DinoSegmenter:
    global _model
    if _model is None:
        model = _DinoSegmenter(DINO_CNN_IMG_SIZE).to(_device)
        checkpoint = torch.load(DINO_CNN_WEIGHTS, map_location=_device)
        if isinstance(checkpoint, dict):
            checkpoint = checkpoint.get("state_dict", checkpoint.get("model", checkpoint))
        model.load_state_dict(checkpoint)
        model.eval()
        _model = model
    return _model


def _post_process_v3(prob: np.ndarray) -> tuple[bool, np.ndarray]:
    prob = cv2.GaussianBlur(prob, (5, 5), 0)
    mask = (prob > 0.5).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    final_mask = np.zeros_like(mask)
    is_forged = False

    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= 300:
            final_mask[labels == i] = 1
            is_forged = True

    if is_forged:
        final_mask = binary_fill_holes(final_mask).astype(np.uint8)

    return is_forged, final_mask


def _load_reporter():
    global _report_model, _report_processor
    if _report_model is None or _report_processor is None:
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        _report_model = Qwen2VLForConditionalGeneration.from_pretrained(
            QWEN_VL_MODEL_DIR,
            torch_dtype=dtype,
            device_map="auto",
            local_files_only=True,
        )
        _report_processor = AutoProcessor.from_pretrained(
            QWEN_VL_MODEL_DIR,
            local_files_only=True,
            use_fast=True,
        )
    return _report_model, _report_processor


def _report_prompt(is_forged: bool) -> str:
    if is_forged:
        return (
            "你是一名图像篡改鉴定专家。输入包含两张图：第一张是原图，第二张是检测模型生成的可疑区域掩膜，"
            "白色区域代表疑似篡改位置。请结合原图和掩膜，用中文给出专业报告：先说明图像是否疑似篡改，"
            "再描述可疑区域的大致位置、视觉异常现象、可能的篡改方式，以及为什么这些区域在纹理、边缘、"
            "光照、文字排版或语义逻辑上不自然。不要虚构看不见的具体文字或坐标。"
        )
    return (
        "你是一名图像篡改鉴定专家。该图像经检测模型判断为真实。请用中文给出简洁专业报告，"
        "从光照一致性、边缘/纹理连续性、文字或物体排布合理性、整体语义一致性等角度说明为什么暂未发现明显篡改迹象。"
    )


def _generate_llm_report(image_bgr: np.ndarray, is_forged: bool, mask: np.ndarray) -> str:
    from qwen_vl_utils import process_vision_info

    os.makedirs(DINO_REPORT_TMP_DIR, exist_ok=True)
    run_dir = tempfile.mkdtemp(prefix="report_", dir=DINO_REPORT_TMP_DIR)
    try:
        image_path = os.path.join(run_dir, "image.png")
        cv2.imwrite(image_path, image_bgr)

        content = [{"type": "image", "image": image_path}]
        if is_forged:
            mask_path = os.path.join(run_dir, "mask.png")
            Image.fromarray((mask.astype(np.uint8) * 255)).convert("RGB").save(mask_path)
            content.append({"type": "image", "image": mask_path})

        content.append({"type": "text", "text": _report_prompt(is_forged)})
        messages = [{"role": "user", "content": content}]

        model, processor = _load_reporter()
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        processor_kwargs = {
            "text": [text],
            "images": image_inputs,
            "padding": True,
            "return_tensors": "pt",
            "min_pixels": 256 * 28 * 28,
            "max_pixels": 1024 * 28 * 28,
        }
        if video_inputs is not None:
            processor_kwargs["videos"] = video_inputs

        inputs = processor(
            **processor_kwargs,
        ).to(next(model.parameters()).device)

        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=512)
        output_ids = generated_ids[:, inputs.input_ids.shape[1]:]
        return processor.batch_decode(output_ids, skip_special_tokens=True)[0].strip()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def infer(image_bytes: bytes, explain_mode: str = "template") -> dict:
    model = _load_model()

    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image.")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    orig_h, orig_w = img_bgr.shape[:2]

    img_input = cv2.resize(
        img_rgb,
        (DINO_CNN_IMG_SIZE, DINO_CNN_IMG_SIZE),
        interpolation=cv2.INTER_LANCZOS4,
    )
    img_flip = np.flip(img_input, axis=1).copy()
    batch = np.stack([img_input, img_flip])
    x = torch.from_numpy(batch.astype(np.float32) / 255.0).permute(0, 3, 1, 2).to(_device)

    with torch.no_grad():
        probs = torch.sigmoid(model.forward_seg(x)).cpu().numpy()

    prob_small = (probs[0, 0] + np.flip(probs[1, 0], axis=1)) / 2.0
    prob_map = cv2.resize(prob_small, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    is_forged, mask = _post_process_v3(prob_map)

    label = "fake" if is_forged else "real"
    if is_forged and mask.sum() > 0:
        confidence = float(prob_map[mask == 1].mean())
    else:
        confidence = float(1.0 - prob_map.mean())

    mask_b64 = overlay_b64 = None
    if is_forged:
        mask_b64 = mask_to_base64(mask, orig_h, orig_w)
        overlay_b64 = overlay_to_base64(img_bgr, mask, orig_h, orig_w)

    explanation_source = "template"
    if explain_mode == "llm":
        explanation = _generate_llm_report(img_bgr, is_forged, mask)
        explanation_source = "qwen2_vl"
    else:
        explanation = generate_explanation(
            label=label,
            model="dino_cnn",
            mask=mask if is_forged else None,
            confidence=confidence,
        )

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "mask_base64": mask_b64,
        "overlay_base64": overlay_b64,
        "explanation": explanation,
        "explanation_source": explanation_source,
    }
