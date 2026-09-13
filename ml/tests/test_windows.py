from datetime import datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from oilwell_ml.features import CORE_VARIABLES
from oilwell_ml.windows import labelled_windows


def write_rows(tmp_path, offsets, labels=None, bad_at=None):
    rows = {name: [float(i) for i in range(len(offsets))] for name in CORE_VARIABLES}
    if bad_at is not None: rows['QGL'][bad_at] = float('nan')
    rows['timestamp'] = [datetime(2026, 1, 1) + timedelta(seconds=i) for i in offsets]
    rows['class'] = labels if labels is not None else [3] * len(offsets)
    path = tmp_path / 'sample.parquet'
    pq.write_table(pa.table(rows), path)
    return path


def test_windows_have_exact_length_and_stride(tmp_path):
    windows = list(labelled_windows(write_rows(tmp_path, range(200)), ['3']))
    assert len(windows) == 3
    assert [w[-1]['QGL'] for w in windows] == [179, 189, 199]
    assert all(len(w) == 180 for w in windows)


@pytest.mark.parametrize('reason', ['gap', 'backwards', 'label', 'nonfinite'])
def test_invalid_boundaries_cannot_be_joined_into_a_window(tmp_path, reason):
    offsets = list(range(200))
    labels = [3] * 200
    if reason == 'gap': offsets[100:] = range(101, 201)
    if reason == 'backwards': offsets[100:] = range(50, 150)
    if reason == 'label': labels[100] = 0
    path = write_rows(tmp_path, offsets, labels, 100 if reason == 'nonfinite' else None)
    assert list(labelled_windows(path, ['3'])) == []


def test_formally_allowed_transient_label_and_missing_timestamp(tmp_path):
    path = write_rows(tmp_path, range(180), [109] * 180)
    assert len(list(labelled_windows(path, ['9', '109']))) == 1
    assert not list(labelled_windows(path, ['9']))
    pq.write_table(pq.read_table(path).drop(['timestamp']), path)
    with pytest.raises(ValueError, match='timestamps'):
        list(labelled_windows(path, ['9', '109']))


def test_inspector_reports_nonfinite_and_sampling_gaps(tmp_path):
    from oilwell_ml.manifest import inspect_parquet
    path = write_rows(tmp_path, [0, 1, 3, 4], bad_at=2)
    report = inspect_parquet(path, tmp_path)
    assert report['eligible'] is False
    assert report['nonfinite_counts']['QGL'] == 1
    assert report['sampling_intervals_seconds']['2.0'] == 1
    assert report['descriptive_statistics']['QGL']['count'] == 3
    assert 'missing_or_nonfinite_values' in report['exclusion_reasons']


def test_dynamics_keep_the_original_statistics_and_are_affine_invariant():
    import numpy as np
    from oilwell_ml.features import window_features as baseline
    from oilwell_ml.features_v2 import window_features as dynamics, FEATURE_NAMES
    rows = [{name: float(10 + np.sin(i / 5)) for name in CORE_VARIABLES} for i in range(180)]
    actual = dynamics(rows)
    assert len(actual) == len(FEATURE_NAMES) == 119
    assert actual[:63] == baseline(rows)
    changed = [{name: value * 2 + 30 for name, value in row.items()} for row in rows]
    np.testing.assert_allclose(actual[63:], dynamics(changed)[63:], atol=1e-10)
    assert np.isfinite(actual).all()


def test_demo_window_uses_the_same_gap_boundaries_and_source_identity(tmp_path):
    import importlib.util
    from pathlib import Path
    script = Path(__file__).parents[1] / 'scripts' / 'prepare_demo_windows.py'
    spec = importlib.util.spec_from_file_location('prepare_demo_windows', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = write_rows(tmp_path, list(range(100)) + list(range(200, 380)))
    item = {'source_path': path.name, 'label': '3', 'label_name': 'Severe Slugging',
            'well_id': 'WELL-00001', 'instance_id': 'sample', 'sha256': 'test'}
    result = module.first_window(item, tmp_path, 180)
    assert result['well_id'] == item['well_id']
    assert result['window_start'] == '2026-01-01T00:03:20+00:00'
    assert result['window_end'] == '2026-01-01T00:06:19+00:00'
    from oilwell_ml.features import FEATURE_NAMES, window_features
    expected = next(labelled_windows(path, ['3']))
    assert result['features'] == dict(zip(FEATURE_NAMES, window_features(expected)))


def test_shape_statistics_remove_independent_channel_offsets_and_scales():
    import numpy as np
    from oilwell_ml.features_v2 import window_features
    from oilwell_ml.preprocessing import transform_features
    original = [{name: float(np.sin(i / 9) + i / 180) for name in CORE_VARIABLES} for i in range(180)]
    shifted = [{name: value * (channel + 1) + channel * 2 for channel, (name, value) in enumerate(row.items())} for row in original]
    left = transform_features(np.array([window_features(original)]), 'window-shape-v1')
    right = transform_features(np.array([window_features(shifted)]), 'window-shape-v1')
    np.testing.assert_allclose(left, right, atol=2e-6)
