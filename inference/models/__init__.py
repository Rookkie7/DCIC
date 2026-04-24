from . import dino_cnn, rigid, warpad, fakeshield

REGISTRY = {
    "dino_cnn":   dino_cnn.infer,
    "rigid":      rigid.infer,
    "warpad":     warpad.infer,
    "fakeshield": fakeshield.infer,
}
