import torch
import torch.nn as nn
import torch.nn.functional as F

class ICM(nn.Module):
    """
    Intrinsic Curiosity Module (ICM)
    Implementation based on the paper: "Curiosity-driven Exploration by Self-supervised Prediction"
    (https://arxiv.org/abs/1705.05363)
    """
    def __init__(self, observation_dim, action_dim, hidden_dim=64, encoding_dim=32):
        super(ICM, self).__init__()

        # 1. Feature Encoder: Encodes observations (state) into a more abstract feature space.
        # This network is shared by both the forward and inverse models.
        self.encoder = nn.Sequential(
            nn.Linear(observation_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, encoding_dim)
        )

        # 2. Inverse Model: Predicts the action taken between two consecutive states.
        # Input: Concatenation of encoded state (phi_t) and encoded next state (phi_t+1)
        # Output: Predicted action (a_hat_t)
        self.inverse_model = nn.Sequential(
            nn.Linear(encoding_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )

        # 3. Forward Model: Predicts the encoded next state based on the current state and action.
        # Input: Concatenation of encoded state (phi_t) and the actual action (a_t)
        # Output: Predicted encoded next state (phi_hat_t+1)
        self.forward_model = nn.Sequential(
            nn.Linear(encoding_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, encoding_dim)
        )

        # Initialize weights for better stability
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                nn.init.zeros_(m.bias)

    def forward(self, state, next_state, action):
        """
        Calculates the losses for the ICM module.
        
        Args:
            state (torch.Tensor): The current state observation.
            next_state (torch.Tensor): The next state observation.
            action (torch.Tensor): The action taken to transition from state to next_state.

        Returns:
            forward_loss (torch.Tensor): The prediction error of the forward model (this is the curiosity reward).
            inverse_loss (torch.Tensor): The prediction error of the inverse model (used for training the encoder).
        """
        # Encode the current and next states into the feature space
        encoded_state = self.encoder(state)
        encoded_next_state = self.encoder(next_state)

        # --- Forward Model Loss ---
        # Predict the next encoded state
        predicted_encoded_next_state = self.forward_model(torch.cat((encoded_state, action), dim=1))
        # The forward loss is the mean squared error between the predicted and actual next encoded state.
        # This loss is our intrinsic reward signal.
        forward_loss = F.mse_loss(predicted_encoded_next_state, encoded_next_state, reduction='none').mean(dim=1)

        # --- Inverse Model Loss ---
        # Predict the action that was taken
        predicted_action = self.inverse_model(torch.cat((encoded_state, encoded_next_state), dim=1))
        # The inverse loss is the mean squared error between the predicted and actual action.
        # This loss is used to train the feature encoder.
        inverse_loss = F.mse_loss(predicted_action, action)

        return forward_loss, inverse_loss

    def get_intrinsic_reward(self, state, next_state, action):
        """
        Calculates the intrinsic reward (curiosity) for a given transition.
        This is done by calculating the forward model's prediction error.
        We detach the result from the computation graph as it's used as a reward, not for gradient descent here.
        """
        with torch.no_grad():
            encoded_state = self.encoder(state)
            encoded_next_state = self.encoder(next_state)
            
            predicted_encoded_next_state = self.forward_model(torch.cat((encoded_state, action), dim=1))
            
            # The intrinsic reward is the MSE, representing the "surprise"
            intrinsic_reward = F.mse_loss(predicted_encoded_next_state, encoded_next_state, reduction='none').mean(dim=1)
            
        return intrinsic_reward
