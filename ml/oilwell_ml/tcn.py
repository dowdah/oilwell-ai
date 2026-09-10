"""Small residual temporal convolutional network used by the shadow model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TCNConfig:
    input_channels: int = 7
    channels: tuple[int, int, int] = (32, 64, 64)
    dilations: tuple[int, int, int] = (1, 2, 4)
    kernel_size: int = 3
    classes: int = 4

    def to_dict(self) -> dict:
        result = asdict(self)
        result["channels"] = list(self.channels)
        result["dilations"] = list(self.dilations)
        return result

    @classmethod
    def from_dict(cls, value: dict) -> "TCNConfig":
        return cls(
            input_channels=int(value["input_channels"]),
            channels=tuple(int(item) for item in value["channels"]),
            dilations=tuple(int(item) for item in value["dilations"]),
            kernel_size=int(value["kernel_size"]),
            classes=int(value["classes"]),
        )


def preferred_device(torch_module):
    """Prefer Apple MPS when available, while keeping CPU training reproducible."""
    return torch_module.device("mps" if torch_module.backends.mps.is_available() else "cpu")


def build_tcn(config: TCNConfig):
    """Construct the model lazily so API startup without a TCN artifact needs no torch."""
    import torch
    from torch import nn

    class ResidualBlock(nn.Module):
        def __init__(self, inputs: int, outputs: int, dilation: int) -> None:
            super().__init__()
            padding = dilation * (config.kernel_size - 1)
            self.layers = nn.Sequential(
                nn.Conv1d(inputs, outputs, config.kernel_size, padding=padding, dilation=dilation),
                nn.ReLU(),
                nn.Conv1d(outputs, outputs, config.kernel_size, padding=padding, dilation=dilation),
                nn.ReLU(),
            )
            self.shortcut = nn.Identity() if inputs == outputs else nn.Conv1d(inputs, outputs, 1)

        def forward(self, value):
            result = self.layers(value)[..., : value.shape[-1]]
            return torch.relu(result + self.shortcut(value))

    blocks = []
    inputs = config.input_channels
    for outputs, dilation in zip(config.channels, config.dilations, strict=True):
        blocks.append(ResidualBlock(inputs, outputs, dilation))
        inputs = outputs
    return nn.Sequential(*blocks, nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Linear(inputs, config.classes))


def parameter_count(model) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
