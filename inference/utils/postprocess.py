"""
Shared post-processing utilities for mask generation.
Adapted from project/DINO_CNN/eval.py.
"""
import cv2
import numpy as np
import base64


# ── Mask post-processing ─────────────────────────────────────────────────────

def enhanced_adaptive_mask(prob: np.ndarray, alpha_grad: float = 0.45) -> tuple[np.ndarray, float]:
    """
    Sobel-gradient enhanced adaptive thresholding.
    Returns (binary_mask uint8, threshold_value).
    """
    gx = cv2.Sobel(prob, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(prob, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(gx ** 2 + gy ** 2)
    grad_norm = grad_mag / (grad_mag.max() + 1e-6)

    enhanced = (1 - alpha_grad) * prob + alpha_grad * grad_norm
    enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)

    thr = np.mean(enhanced) + 0.3 * np.std(enhanced)
    mask = (enhanced > thr).astype(np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return mask, thr


def gate_mask(mask: np.ndarray, prob: np.ndarray,
              area_thr: int = 200, mean_thr: float = 0.22) -> bool:
    """Returns True if the mask passes the forgery gate (area + mean-prob)."""
    area = int(mask.sum())
    if area < area_thr:
        return False
    mean_in = prob[mask == 1].mean() if area > 0 else 0.0
    return mean_in >= mean_thr


# ── Mask encoding ─────────────────────────────────────────────────────────────

def mask_to_base64(mask: np.ndarray, orig_h: int, orig_w: int) -> str:
    """Resize mask to original image size and encode as PNG base64."""
    resized = cv2.resize(mask.astype(np.uint8) * 255,
                         (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
    _, buf = cv2.imencode(".png", resized)
    return base64.b64encode(buf).decode("utf-8")


def overlay_to_base64(image_bgr: np.ndarray, mask: np.ndarray,
                      orig_h: int, orig_w: int,
                      color: tuple = (0, 0, 220), alpha: float = 0.45) -> str:
    """
    Overlay red-ish mask on original image and return as JPEG base64.
    Useful for direct frontend display.
    """
    img = cv2.resize(image_bgr, (orig_w, orig_h))
    mask_full = cv2.resize(mask.astype(np.uint8),
                           (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
    overlay = img.copy()
    overlay[mask_full == 1] = color
    blended = cv2.addWeighted(img, 1 - alpha, overlay, alpha, 0)
    _, buf = cv2.imencode(".jpg", blended, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode("utf-8")


# ── Mask region description ───────────────────────────────────────────────────

def mask_centroid_label(mask: np.ndarray) -> str:
    """Map mask centroid to a human-readable position label."""
    h, w = mask.shape
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return "unknown region"
    cy, cx = ys.mean() / h, xs.mean() / w

    v = "upper" if cy < 0.4 else ("lower" if cy > 0.6 else "middle")
    h_label = "left" if cx < 0.4 else ("right" if cx > 0.6 else "center")

    if v == "middle" and h_label == "center":
        return "central area"
    if v == "middle":
        return f"{h_label} side"
    return f"{v}-{h_label}"
