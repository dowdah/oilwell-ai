"""Versioned per-window transforms; no cross-window statistics are fitted."""
import numpy as np


def transform_features(values, mode='identity'):
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.shape[-1] not in (63, 119) or not np.isfinite(matrix).all():
        raise ValueError('expected 63 or 119 finite features')
    if mode == 'identity': return matrix
    grouped = matrix[..., :63].reshape(*matrix.shape[:-1], 7, 9)
    if mode == 'window-shape-v1':
        centered = grouped.copy()
        for index in (0, 2, 3, 4, 7):
            centered[..., index] -= grouped[..., 0]
        scale = np.maximum(grouped[..., 1], 1e-6)
        normalized = (centered / scale[..., None]).reshape(*matrix.shape[:-1], 63)
        return np.concatenate([normalized, matrix[..., 63:]], axis=-1)
    if mode != 'window-relative-v1': raise ValueError('unknown feature preprocessing')
    scale = np.maximum(np.maximum(np.abs(grouped[..., 0]), grouped[..., 5]), 1e-6)
    relative = (grouped / scale[..., None]).reshape(*matrix.shape[:-1], 63)
    return np.concatenate([relative, matrix[..., 63:]], axis=-1)


def augment_training(values, labels, copies=4, seed=20260910):
    """Affine-transform consistent statistics using training baselines only."""
    matrix = transform_features(values, 'identity')
    grouped = matrix.reshape(-1, 7, 9)
    rng = np.random.default_rng(seed)
    outputs = [matrix]
    for _ in range(copies):
        scale = np.exp(rng.uniform(-np.log(2), np.log(2), size=grouped.shape[:2])).astype(np.float32)
        baseline = np.stack([rng.choice(grouped[:, channel, 0], size=len(grouped)) for channel in range(7)], axis=1)
        altered = grouped * scale[..., None]
        shift = baseline - grouped[..., 0] * scale
        for index in (0, 2, 3, 4, 7): altered[..., index] += shift
        outputs.append(altered.reshape(matrix.shape))
    return np.concatenate(outputs), np.tile(labels, copies + 1)
