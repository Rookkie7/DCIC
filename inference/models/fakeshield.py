"""
FakeShield inference wrapper.
Runs DTE-FDM (transformers 4.37.2) then MFLM (transformers 4.28.0)
as subprocesses, since the two modules require conflicting library versions.

Expected environment on cloud server:
  - /root/envs/dte/   : conda env with transformers==4.37.2
  - /root/envs/mflm/  : conda env with transformers==4.28.0
  (or use the pip-install-on-the-fly approach from cli_demo.sh as fallback)
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import uuid
import cv2
import numpy as np

from config import FAKESHIELD_WEIGHT_DIR, FAKESHIELD_SCRIPT_DIR, FAKESHIELD_TMP_DIR
from utils import mask_to_base64, overlay_to_base64
from utils.explanation import generate_explanation

os.makedirs(FAKESHIELD_TMP_DIR, exist_ok=True)

# Paths to Python executables for each sub-environment.
# Adjust these to match the actual conda env paths on the server.
_DTE_PYTHON  = os.environ.get("DTE_PYTHON",  "python")   # env with transformers 4.37.2
_MFLM_PYTHON = os.environ.get("MFLM_PYTHON", "python")   # env with transformers 4.28.0


def _run_dte_fdm(image_path: str, dte_output_path: str) -> str:
    """Run DTE-FDM and return the raw text output."""
    cmd = [
        _DTE_PYTHON, "-m", "llava.serve.cli",
        "--model-path", f"{FAKESHIELD_WEIGHT_DIR}/DTE-FDM",
        "--DTG-path",   f"{FAKESHIELD_WEIGHT_DIR}/DTG.pth",
        "--image-path", image_path,
        "--output-path", dte_output_path,
    ]
    subprocess.run(
        cmd,
        cwd=FAKESHIELD_SCRIPT_DIR,
        check=True,
        timeout=240,
        capture_output=True,
    )
    with open(dte_output_path, "r") as f:
        data = json.loads(f.readline().strip())
    return data.get("text", "")


def _run_mflm(image_path: str, dte_output_path: str, mflm_output_dir: str):
    """Run MFLM segmentation and save mask to mflm_output_dir."""
    cmd = [
        _MFLM_PYTHON, "./MFLM/cli_demo.py",
        "--version",        f"{FAKESHIELD_WEIGHT_DIR}/MFLM",
        "--DTE-FDM-output", dte_output_path,
        "--MFLM-output",    mflm_output_dir,
    ]
    subprocess.run(
        cmd,
        cwd=FAKESHIELD_SCRIPT_DIR,
        check=True,
        timeout=240,
        capture_output=True,
    )


def _load_mflm_mask(mflm_output_dir: str, orig_h: int, orig_w: int) -> np.ndarray | None:
    """Find the first mask PNG output by MFLM and return it."""
    for fname in os.listdir(mflm_output_dir):
        if fname.lower().endswith((".png", ".jpg")):
            path = os.path.join(mflm_output_dir, fname)
            mask_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if mask_img is not None:
                return (cv2.resize(mask_img, (orig_w, orig_h)) > 127).astype(np.uint8)
    return None


def infer(image_bytes: bytes) -> dict:
    run_id = str(uuid.uuid4())
    run_dir = os.path.join(FAKESHIELD_TMP_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    try:
        # Save uploaded image to temp file
        img_path = os.path.join(run_dir, "input.png")
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        orig_h, orig_w = img_bgr.shape[:2]
        cv2.imwrite(img_path, img_bgr)

        dte_output  = os.path.join(run_dir, "dte_output.jsonl")
        mflm_outdir = os.path.join(run_dir, "mflm_output")
        os.makedirs(mflm_outdir, exist_ok=True)

        # Stage 1: DTE-FDM
        dte_text = _run_dte_fdm(img_path, dte_output)

        # Determine label from DTE-FDM text
        text_lower = dte_text.lower()
        is_fake = any(kw in text_lower for kw in (
            "tamper", "fake", "manipulat", "forg", "alter", "splicing",
            "copy-move", "inpaint", "remov",
        ))
        # Fallback: if text mentions "authentic" / "real" / "no tamper" → real
        if any(kw in text_lower for kw in ("authentic", "no tamper", "genuine", "real image")):
            is_fake = False

        label = "fake" if is_fake else "real"

        mask_b64 = overlay_b64 = None
        mask = None

        if is_fake:
            # Stage 2: MFLM segmentation
            try:
                _run_mflm(img_path, dte_output, mflm_outdir)
                mask = _load_mflm_mask(mflm_outdir, orig_h, orig_w)
                if mask is not None and mask.sum() > 0:
                    mask_b64    = mask_to_base64(mask, orig_h, orig_w)
                    overlay_b64 = overlay_to_base64(img_bgr, mask, orig_h, orig_w)
            except Exception:
                pass  # MFLM failure is non-fatal; still return DTE-FDM result

        explanation = generate_explanation(
            label=label, model="fakeshield",
            mask=mask, confidence=None,
            dte_fdm_text=dte_text if is_fake else None,
        )

        return {
            "label": label,
            "confidence": None,          # FakeShield doesn't output a scalar confidence
            "mask_base64": mask_b64,
            "overlay_base64": overlay_b64,
            "explanation": explanation,
        }

    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
