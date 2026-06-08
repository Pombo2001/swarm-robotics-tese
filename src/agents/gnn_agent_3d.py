import torch
import torch.nn as nn
import torch.nn.functional as F
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

        # Ego-features = 16: bússola ninho (4) + LiDAR (8) + bússola porta (4) [B1].
        self.env_feats_dim = 16
        self.neighbor_dim = 5

        self.encoder = nn.Sequential(
            nn.Linear(self.env_feats_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        self.neighbor_embed = nn.Sequential(
            nn.Linear(self.neighbor_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim)
        )

        self.query_proj = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.key_proj = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.value_proj = nn.Linear(self.hidden_dim, self.hidden_dim)

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
            h_neighbors = self.neighbor_embed(neighbors)
            
            # Combine ego node and neighbor nodes to allow self-attention
            h_env_expanded = h_env.unsqueeze(1)
            h_all = torch.cat([h_env_expanded, h_neighbors], dim=1)
            
            # QKV Projections
            Q = self.query_proj(h_env_expanded)
            K = self.key_proj(h_all)
            V = self.value_proj(h_all)
            
            # Scaled Dot Product Attention
            scores = torch.bmm(Q, K.transpose(1, 2)) / (self.hidden_dim ** 0.5)
            alpha = F.softmax(scores, dim=-1)
            
            msg_pool = torch.bmm(alpha, V).squeeze(1)
        else:
            Q = self.query_proj(h_env.unsqueeze(1))
            K = self.key_proj(h_env.unsqueeze(1))
            V = self.value_proj(h_env.unsqueeze(1))
            scores = torch.bmm(Q, K.transpose(1, 2)) / (self.hidden_dim ** 0.5)
            alpha = F.softmax(scores, dim=-1)
            msg_pool = torch.bmm(alpha, V).squeeze(1)

        combined = torch.cat([h_env, msg_pool], dim=1)
        action = self.actor(combined)

        if batch_size == 1:
            return action.squeeze(0)

        return action