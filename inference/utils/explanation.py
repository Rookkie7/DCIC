"""
Rule-based explanation template generator (English output).
Used by DINO_CNN, RIGID, and WaRPAD (FakeShield uses DTE-FDM output directly).
"""
from __future__ import annotations

import numpy as np
from .postprocess import mask_centroid_label


def generate_explanation(
    label: str,
    model: str,
    mask: np.ndarray | None = None,
    confidence: float | None = None,
    dte_fdm_text: str | None = None,
) -> str:
    """
    Returns an English explanation string.

    Parameters
    ----------
    label         : "real" or "fake"
    model         : one of "dino_cnn", "fakeshield", "rigid", "warpad"
    mask          : binary mask (H×W uint8) or None
    confidence    : model confidence in [0, 1]
    dte_fdm_text  : raw DTE-FDM output (used when model == "fakeshield")
    """
    if label == "real":
        return "No forgery detected. The image appears to be authentic."

    # FakeShield — use raw model output
    if model == "fakeshield" and dte_fdm_text:
        return dte_fdm_text.strip()

    # RIGID / WaRPAD — no spatial mask
    if model in ("rigid", "warpad"):
        note = (
            "Note: this model was designed for AI-generated image detection "
            "and has limited accuracy on traditional manipulation datasets."
        )
        return (
            f"The image shows statistical signatures consistent with manipulation "
            f"or AI generation (confidence: {confidence:.0%}). {note}"
        )

    # DINO_CNN — mask-based explanation
    if mask is not None and mask.sum() > 0:
        area_ratio = mask.sum() / mask.size
        position = mask_centroid_label(mask)

        if area_ratio < 0.05:
            size_desc = "a small tampered region"
        elif area_ratio < 0.30:
            size_desc = "a moderately-sized forged region"
        else:
            size_desc = "a large manipulated region"

        return (
            f"Forgery detected. {size_desc.capitalize()} was identified in the "
            f"{position} of the image (covering {area_ratio:.1%} of the image area). "
            f"The highlighted region likely involves splicing, copy-move, or inpainting manipulation."
        )

    return "Forgery detected. The model flagged this image as tampered, but could not isolate a specific region."
