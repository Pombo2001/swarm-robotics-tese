import torch
import torch.nn as nn
import yaml
import os

class GNNAgent3D(nn.Module):
    def __init__(self, agent_id, action_space, config_path=None):
        super(GNNAgent3D, self).__init__()
        self.agent_id = agent_id

        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../../configs/foraging.yaml')

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        agent_config = config.get('gnn_agent', {})
        self.hidden_dim = agent_config.get('hidden_dim', 64)

        # 4 (Ninho) + 8 (Sensores Obstáculos) + 4 (Porta) + 8 (Sensores Feromonas) = 24
        self.env_feats_dim = 24
        self.neighbor_dim = 5

        self.encoder = nn.Sequential(
            nn.Linear(self.env_feats_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        self.msg_net = nn.Sequential(
            nn.Linear(self.neighbor_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        self.actor = nn.Sequential(
            nn.Linear(self.hidden_dim * 2, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, 3),
            nn.Tanh()
        )

    def forward(self, obs):
        batch_size = obs.shape[0] if len(obs.shape) > 1 else 1

        if len(obs.shape) == 1:
            obs = obs.unsqueeze(0)

        env_data = obs[:, :self.env_feats_dim]
        neighbor_data = obs[:, self.env_feats_dim:]

        num_neighbors = neighbor_data.shape[1] // self.neighbor_dim

        h_env = self.encoder(env_data)

        if num_neighbors > 0:
            neighbors = neighbor_data.view(batch_size, num_neighbors, self.neighbor_dim)
            msg = self.msg_net(neighbors)
            msg_pool = msg.mean(dim=1)
        else:
            msg_pool = torch.zeros((batch_size, self.hidden_dim), device=obs.device)

        combined = torch.cat([h_env, msg_pool], dim=1)
        action = self.actor(combined)

        if batch_size == 1:
            return action.squeeze(0)

        return action