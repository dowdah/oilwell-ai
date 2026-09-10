from oilwell_ml.features import CORE_VARIABLES
from oilwell_ml.tcn import TCNConfig
from oilwell_ml.tcn_data import StandardScaler


def test_scaler_keeps_the_seven_variable_order_and_transforms_channels() -> None:
    scaler = StandardScaler(tuple(float(index) for index in range(7)), tuple(2.0 for _ in range(7)))
    row = {name: float(index + 2) for index, name in enumerate(CORE_VARIABLES)}
    transformed = scaler.transform([row])
    assert len(transformed) == 7
    assert all(channel == [1.0] for channel in transformed)
    assert StandardScaler.from_dict(scaler.to_dict()) == scaler


def test_tcn_config_round_trips_without_importing_torch() -> None:
    assert TCNConfig.from_dict(TCNConfig().to_dict()) == TCNConfig()


def test_tcn_has_the_required_input_output_shape_and_small_parameter_budget() -> None:
    import torch
    from oilwell_ml.tcn import build_tcn, parameter_count, preferred_device

    model = build_tcn(TCNConfig())
    assert model(torch.zeros((2, 7, 180))).shape == (2, 4)
    assert parameter_count(model) < 1_000_000
    assert preferred_device(torch).type in {"cpu", "mps"}
