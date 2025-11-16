import os

import torch
import torch.nn as nn


def input_tensor(
    previous_pump_height: list[float],
    current_fill_percent: float,
    electricity_price: list[float],
    estimated_inflow_rate: list[float],
    previous_flow_rate: list[float],
) -> torch.Tensor:
    """Create a new torch.Tensor for input data.

    This function takes input data and normalizes it into input tensor for RL-model


    Args:
        previous_pump_height (list[float]): m last 1h, 15 min bins. 4 values
        current_fill_percent (float): % filled
        electricity_price (list[float]): Price of electricity (e/kWh) for next 24h, 15 min bins. 96 values
        estimated_inflow_rate (list[float]): Estimated amount of water incoming (m3/h) 24h, 15 min bins. 96 values
        previous_flow_rate (list[float]): last 1h of flow rate (m3/h), 15 min bins. 4 values

    returns
        Tensor of shape [96, 11] where each timestep (96) contains (price, estimated_inflow, fill_percent, pump_hist_0, pump_hist_1, pump_hist_2, pump_hist3, flow_hist0, flow_hist1,flow_hist2,flow_hist3)
    """
    # Convert future sequences to [96, 1]
    assert len(electricity_price) == 96
    price = torch.tensor(electricity_price, dtype=torch.float32).unsqueeze(1)  # [96, 1]
    assert price.shape == torch.Size([96, 1])
    inflow = torch.tensor(estimated_inflow_rate, dtype=torch.float32).unsqueeze(
        1
    )  # [96, 1]
    assert inflow.shape == torch.Size([96, 1])

    # Broadcast static context
    fill_broadcast = torch.full((96, 1), current_fill_percent, dtype=torch.float32)
    pump_hist = torch.tensor(previous_pump_height, dtype=torch.float32).repeat(
        96, 1
    )  # [96, 4]
    assert pump_hist.shape == torch.Size([96, 4])
    flow_hist = torch.tensor(previous_flow_rate, dtype=torch.float32).repeat(
        96, 1
    )  # [96, 4]
    assert flow_hist.shape == torch.Size([96, 4])

    # Concatenate into feature vector
    x = torch.cat(
        [price, inflow, fill_broadcast, pump_hist, flow_hist], dim=1
    )  # [96, 11]
    assert x.shape == torch.Size([96, 11])

    return x


class TransformerFlowPolicy(nn.Module):
    def __init__(self, input_shape: list[int], nhead=4, num_layers=2, output_len=96):
        super().__init__()
        timestep_count, feature_count = input_shape
        self.input_proj = nn.Linear(feature_count, 64)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=64, nhead=nhead, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.output_head = nn.Linear(64, 1)  # predict flow per timestep
        self.output_len = output_len

        self.log_std = nn.Parameter(torch.zeros(output_len))

    def forward(self, x):
        # x shape: [timestemp_count, feature_count] -> add batch dimension
        if x.dim() == 2:
            x = x.unsqueeze(0)  # [1, seq_len, feature_dim]
        x = self.input_proj(x)
        x = self.transformer(x)
        # Take last output_len positions (corresponding to future prices)
        out = self.output_head(x[-self.output_len :, :])
        return torch.abs(out.squeeze(-1))  # shape: [output_len]

    def get_action_and_logprob(self, state):
        """
        state: [1, seq_len, feature_dim]
        returns action (sampled flow sequence), log_prob
        """
        mean = self.forward(state)  # [1,96]
        std = torch.exp(self.log_std).clamp(min=1e-3, max=1.0).unsqueeze(0)  # [1,96]
        dist = torch.distributions.Normal(mean, std)

        action = dist.rsample()  # reparameterized sample
        log_prob = dist.log_prob(action).sum(dim=-1)  # [1]
        return action, log_prob

    def load_weights(self):
        self.load_state_dict(
            torch.load(os.path.join(os.path.split(__file__)[0], "model_weights.pth"))
        )
