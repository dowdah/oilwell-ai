"""Candidate dynamics features; original 63 statistics are retained unchanged."""
import numpy as np
from .features import CORE_VARIABLES, FEATURE_NAMES as BASE_NAMES, window_features as base_features

DYNAMIC_STATS = ('autocorr_1', 'autocorr_10', 'autocorr_30', 'autocorr_60', 'diff_rms_ratio', 'skewness', 'spectral_entropy', 'low_frequency_share')
FEATURE_NAMES = BASE_NAMES + tuple(f'{name}__{stat}' for name in CORE_VARIABLES for stat in DYNAMIC_STATS)


def window_features(rows):
    values = base_features(rows)
    for name in CORE_VARIABLES:
        data = np.asarray([row[name] for row in rows], dtype=np.float64)
        centered = data - data.mean()
        rms = np.sqrt(np.mean(centered ** 2))
        if rms < 1e-12:
            values.extend([0.0] * len(DYNAMIC_STATS)); continue
        normalized = centered / rms
        for lag in (1, 10, 30, 60):
            if len(data) <= lag:
                raise ValueError('dynamics features require a complete 180-row window')
            values.append(float(np.mean(normalized[:-lag] * normalized[lag:])))
        values.append(float(np.sqrt(np.mean(np.diff(normalized) ** 2))))
        values.append(float(np.mean(normalized ** 3)))
        power = np.abs(np.fft.rfft(normalized)) ** 2
        power[0] = 0
        probabilities = power / max(power.sum(), 1e-12)
        nonzero = probabilities[probabilities > 0]
        values.append(float(-(nonzero * np.log(nonzero)).sum() / np.log(len(power) - 1)))
        values.append(float(probabilities[1:10].sum()))
    return values
