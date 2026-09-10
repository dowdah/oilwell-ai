from oilwell_ml.features import CORE_VARIABLES, FEATURE_NAMES, window_features


def test_window_features_are_stable_and_include_all_seven_variables() -> None:
    first = {name: float(index) for index, name in enumerate(CORE_VARIABLES)}
    second = {name: value + 2 for name, value in first.items()}
    features = window_features([first, second])
    assert len(features) == len(FEATURE_NAMES) == 63
    assert features[:9] == [1.0, 2**0.5, 0.0, 2.0, 1.0, 2.0, 2.0, 2.0, 2.0]
