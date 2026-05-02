"""
FakeShield inference wrapper.
Runs the single-image flow from scripts/cli_demo.sh:
1. DTE-FDM writes a JSONL explanation.
2. MFLM reads that JSONL and writes a mask when DTE-FDM predicts tampering.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid

import cv2
import numpy as np

from config import (
    FAKESHIELD_DTE_TEMPERATURE,
    FAKESHIELD_MASK_CLOSE_KERNEL,
    FAKESHIELD_MASK_DILATE_ITER,
    FAKESHIELD_MASK_DILATE_KERNEL,
    FAKESHIELD_SCRIPT_DIR,
    FAKESHIELD_TMP_DIR,
    FAKESHIELD_WEIGHT_DIR,
)
from utils import mask_to_base64, overlay_to_base64
from utils.explanation import generate_explanation

os.makedirs(FAKESHIELD_TMP_DIR, exist_ok=True)

_DTE_PYTHON = os.environ.get("DTE_PYTHON", "python")
_MFLM_PYTHON = os.environ.get("MFLM_PYTHON", "python")


def _run_checked(cmd: list[str], timeout: int) -> None:
    try:
        subprocess.run(
            cmd,
            cwd=FAKESHIELD_SCRIPT_DIR,
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        raise RuntimeError(detail[-2000:]) from exc


def _run_dte_fdm(image_path: str, dte_output_path: str) -> str:
    cmd = [
        _DTE_PYTHON,
        "-m",
        "llava.serve.cli",
        "--model-path",
        f"{FAKESHIELD_WEIGHT_DIR}/DTE-FDM",
        "--DTG-path",
        f"{FAKESHIELD_WEIGHT_DIR}/DTG.pth",
        "--image-path",
        image_path,
        "--output-path",
        dte_output_path,
        "--max-new-tokens",
        "512",
        "--temperature",
        FAKESHIELD_DTE_TEMPERATURE,
    ]
    _run_checked(cmd, timeout=240)
    with open(dte_output_path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline().strip())
    return data.get("outputs") or data.get("text") or ""


def _run_mflm(dte_output_path: str, mflm_output_dir: str) -> None:
    cmd = [
        _MFLM_PYTHON,
        "./MFLM/cli_demo.py",
        "--version",
        f"{FAKESHIELD_WEIGHT_DIR}/MFLM",
        "--DTE-FDM-output",
        dte_output_path,
        "--MFLM-output",
        mflm_output_dir,
    ]
    _run_checked(cmd, timeout=240)


def _load_mflm_mask(mflm_output_dir: str, orig_h: int, orig_w: int) -> np.ndarray | None:
    for fname in os.listdir(mflm_output_dir):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(mflm_output_dir, fname)
            mask_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if mask_img is not None:
                mask = (cv2.resize(mask_img, (orig_w, orig_h)) > 127).astype(np.uint8)
                return _postprocess_mask(mask)
    return None


def _odd_kernel(size: int) -> np.ndarray | None:
    if size <= 1:
        return None
    if size % 2 == 0:
        size += 1
    return np.ones((size, size), np.uint8)


def _postprocess_mask(mask: np.ndarray) -> np.ndarray:
    close_kernel = _odd_kernel(FAKESHIELD_MASK_CLOSE_KERNEL)
    if close_kernel is not None:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)

    dilate_kernel = _odd_kernel(FAKESHIELD_MASK_DILATE_KERNEL)
    if dilate_kernel is not None and FAKESHIELD_MASK_DILATE_ITER > 0:
        mask = cv2.dilate(mask, dilate_kernel, iterations=FAKESHIELD_MASK_DILATE_ITER)

    return mask.astype(np.uint8)


def _is_fake_from_dte(text: str) -> bool:
    text_lower = text.lower()
    real_markers = (
        "has not been tampered",
        "not been tampered",
        "no tamper",
        "authentic",
        "genuine",
        "real image",
        "unaltered",
    )
    fake_markers = (
        "has been tampered",
        "tampered with",
        "fake",
        "manipulat",
        "forg",
        "alter",
        "splicing",
        "copy-move",
        "inpaint",
        "remov",
    )
    if any(marker in text_lower for marker in real_markers):
        return False
    return any(marker in text_lower for marker in fake_markers)


def infer(image_bytes: bytes) -> dict:
    run_id = str(uuid.uuid4())
    run_dir = os.path.join(FAKESHIELD_TMP_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    try:
        img_path = os.path.join(run_dir, "input.png")
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise ValueError("Could not decode image.")

        orig_h, orig_w = img_bgr.shape[:2]
        cv2.imwrite(img_path, img_bgr)

        dte_output = os.path.join(run_dir, "dte_output.jsonl")
        mflm_outdir = os.path.join(run_dir, "mflm_output")
        os.makedirs(mflm_outdir, exist_ok=True)

        dte_text = _run_dte_fdm(img_path, dte_output)
        is_fake = _is_fake_from_dte(dte_text)
        label = "fake" if is_fake else "real"

        mask_b64 = overlay_b64 = None
        mask = None
        mflm_error = None

        if is_fake:
            try:
                _run_mflm(dte_output, mflm_outdir)
                mask = _load_mflm_mask(mflm_outdir, orig_h, orig_w)
                if mask is not None and mask.sum() > 0:
                    mask_b64 = mask_to_base64(mask, orig_h, orig_w)
                    overlay_b64 = overlay_to_base64(img_bgr, mask, orig_h, orig_w)
            except Exception as exc:
                mflm_error = str(exc)

        explanation = generate_explanation(
            label=label,
            model="fakeshield",
            mask=mask,
            confidence=None,
            dte_fdm_text=dte_text if is_fake else None,
        )

        result = {
            "label": label,
            "confidence": None,
            "mask_base64": mask_b64,
            "overlay_base64": overlay_b64,
            "explanation": explanation,
            "dte_fdm_text": dte_text,
        }
        if mflm_error:
            result["mflm_error"] = mflm_error
        return result

    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
