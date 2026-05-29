"""Vector helpers."""
from __future__ import annotations
import numpy as np

def normalize_rows(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms

def normalize_vector(x: np.ndarray) -> np.ndarray:
    x = x.astype("float32")
    norm = np.linalg.norm(x)
    if norm == 0:
        return x
    return x / norm
