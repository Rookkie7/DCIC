from importlib import import_module


def _lazy_infer(module_name: str):
    def infer(image_bytes: bytes) -> dict:
        module = import_module(f".{module_name}", __name__)
        return module.infer(image_bytes)

    return infer

REGISTRY = {
    "dino_cnn":   _lazy_infer("dino_cnn"),
    "rigid":      _lazy_infer("rigid"),
    "warpad":     _lazy_infer("warpad"),
    "fakeshield": _lazy_infer("fakeshield"),
}
