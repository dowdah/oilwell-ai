"""Training-only class and within-class well balancing."""
import numpy as np


def sample_weights(labels, groups=None):
    labels = np.asarray(labels)
    if labels.ndim != 1 or not len(labels):
        raise ValueError("labels must be a nonempty vector")
    groups = np.asarray(groups) if groups is not None else None
    if groups is not None and groups.shape != labels.shape:
        raise ValueError("one group is required for every training observation")
    weights = np.empty(len(labels), dtype=np.float32)
    for label in np.unique(labels):
        mask = labels == label
        if groups is None:
            weights[mask] = len(labels) / (len(np.unique(labels)) * mask.sum())
        else:
            wells = np.unique(groups[mask])
            for well in wells:
                within = mask & (groups == well)
                weights[within] = len(labels) / (len(np.unique(labels)) * len(wells) * within.sum())
    return weights
