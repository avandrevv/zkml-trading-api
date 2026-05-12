import torch
import torch.nn as nn
import json
import numpy as np
from pathlib import Path

# Настройка путей
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_DIR = BASE_DIR / "settings"

input_dim = 10

class TradingMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 8)
        self.fc2 = nn.Linear(8, 1)

        with torch.no_grad():
            self.fc1.weight.zero_()
            self.fc1.bias.zero_()
            self.fc1.weight[0, 5] = -0.8
            self.fc1.bias[0] = 0.5
            self.fc1.weight[1, 5] = 0.8
            self.fc1.bias[1] = -0.8
            self.fc1.weight[2, 6] = 1.0
            self.fc1.weight[2, 7] = -1.0
            self.fc1.weight[3, 8] = 1.5
            self.fc1.weight[4, 4] = 0.0005
            self.fc1.bias[4] = -0.5
            self.fc1.weight[5, 3] = 1.5
            self.fc1.weight[5, 0] = -1.5
            self.fc1.weight[6, 9] = 0.5
            self.fc1.bias[6] = -0.5
            self.fc1.weight[7, 1] = 1.0
            self.fc1.weight[7, 2] = -1.0

            self.fc2.weight.zero_()
            self.fc2.bias.zero_()
            self.fc2.weight[0, 0] = 1.2
            self.fc2.weight[0, 1] = -1.2
            self.fc2.weight[0, 2] = 0.8
            self.fc2.weight[0, 3] = 0.6
            self.fc2.weight[0, 4] = 0.4
            self.fc2.weight[0, 5] = 0.7
            self.fc2.weight[0, 6] = -0.3
            self.fc2.weight[0, 7] = 0.2
            self.fc2.bias[0] = -0.3

    def forward(self, x):
        x = torch.tanh(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x


stats = {
    "mean": [300, 300, 300, 300, 300, 300, 300, 300, 300, 300],
    "std": [115, 115, 115, 115, 115, 115, 115, 115, 115, 115],
    "min": [-2400, -2300, -2400, -2350, 0, 0, -50, -50, -20, 0],
    "max": [137200, 137500, 137000, 137300, 50000, 100, 50, 50, 20, 100]
}

with open(DATA_DIR / "stats.json", "w") as f:
    json.dump(stats, f, indent=2)

model = TradingMLP()
model.eval()

dummy = torch.randn(1, 10)
torch.onnx.export(
    model,
    dummy,
    str(SETTINGS_DIR / "model.onnx"),
    input_names=["input"],
    output_names=["output"],
    opset_version=14
)

print(f"Model exported to {SETTINGS_DIR}/model.onnx")
print(f"Stats saved to {DATA_DIR}/stats.json")