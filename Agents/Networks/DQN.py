import torch
import torch.nn as nn
import torch.nn.functional as F
import math

def hidden_init(layer):
    fan_in = layer.weight.data.size()[0]
    lim = 1. / np.sqrt(fan_in)
    return (-lim, lim)

class NoisyLinear(nn.Linear):
    # Noisy Linear Layer for independent Gaussian Noise
    def __init__(self, in_features, out_features, sigma_init=0.017, bias=True):
        super(NoisyLinear, self).__init__(in_features, out_features, bias = bias)
        # make the sigmas trainable:
        self.sigma_weight = nn.Parameter(torch.full((out_features, in_features), sigma_init))
        # not trainable tensor for the nn.Module
        self.register_buffer("epsilon_weight", torch.zeros(out_features, in_features))
        # extra parameter for the bias and register buffer for the bias parameter
        if bias: 
            self.sigma_bias = nn.Parameter(torch.full((out_features,), sigma_init))
            self.register_buffer("epsilon_bias", torch.zeros(out_features))
    
        # reset parameter as initialization of the layer
        self.reset_parameter()
    
    def reset_parameter(self):
        """
        initialize the parameter of the layer and bias
        """
        std = math.sqrt(3/self.in_features)
        self.weight.data.uniform_(-std, std)
        self.bias.data.uniform_(-std, std)

    
    def forward(self, input):
        # sample random noise in sigma weight buffer and bias buffer
        self.epsilon_weight.normal_()
        bias = self.bias
        if bias is not None:
            self.epsilon_bias.normal_()
            bias = bias + self.sigma_bias * self.epsilon_bias
        return F.linear(input, self.weight + self.sigma_weight * self.epsilon_weight, bias)

class DQN(nn.Module):
    def __init__(self, state_size, action_size, seed, layer_type="ff"):
        super(DQN, self).__init__()
        self.seed = torch.manual_seed(seed)
        self.input_shape = state_size
        self.action_size = action_size
        self.cnn_1 = nn.Conv2d(4, out_channels=32, kernel_size=8, stride=4)
        self.cnn_2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=4, stride=2)
        self.cnn_3 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, stride=1)

        if layer_type == "noisy":
            self.ff_1 = NoisyLinear(self.calc_input_layer(), 512)
            self.ff_2 = NoisyLinear(512, action_size)
        else:
            self.ff_1 = nn.Linear(self.calc_input_layer(), 512)
            self.ff_2 = nn.Linear(512, action_size)
        
    def calc_input_layer(self):
        x = torch.zeros(self.input_shape).unsqueeze(0)
        x = self.cnn_1(x)
        x = self.cnn_2(x)
        x = self.cnn_3(x)
        return x.flatten().shape[0]
    
    def forward(self, input):
        """
        
        """
        x = torch.relu(self.cnn_1(input))
        x = torch.relu(self.cnn_2(x))
        x = torch.relu(self.cnn_3(x))
        x = x.view(input.size(0), -1)
        x = torch.relu(self.ff_1(x))
        out = self.ff_2(x)
        
        return out

class Dueling_QNetwork(nn.Module):
    """Actor (Policy) Model."""

    def __init__(self, state_size, action_size, seed, layer_type="ff"):
        """Initialize parameters and build model.
        Params
        ======
            state_size (int): Dimension of each state
            action_size (int): Dimension of each action
            seed (int): Random seed
            fc1_units (int): Number of nodes in first hidden layer
            fc2_units (int): Number of nodes in second hidden layer
        """
        super(Dueling_QNetwork, self).__init__()
        self.seed = torch.manual_seed(seed)
        self.input_shape = state_size
        self.action_size = action_size
        self.cnn_1 = nn.Conv2d(4, out_channels=32, kernel_size=8, stride=4)
        self.cnn_2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=4, stride=2)
        self.cnn_3 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, stride=1)

        if layer_type == "noisy":
            self.ff_1 = NoisyLinear(self.calc_input_layer(), 512)
            self.advantage = NoisyLinear(512,action_size)
            self.value = NoisyLinear(512,1)
        else:
            self.ff_1 = nn.Linear(self.calc_input_layer(), 512)
            self.advantage = nn.Linear(512,action_size)
            self.value = nn.Linear(512,1)

    def calc_input_layer(self):
        x = torch.zeros(self.input_shape).unsqueeze(0)
        x = self.cnn_1(x)
        x = self.cnn_2(x)
        x = self.cnn_3(x)
        return x.flatten().shape[0]

    def forward(self, input):
        """
        """
        x = torch.relu(self.cnn_1(input))
        x = torch.relu(self.cnn_2(x))
        x = torch.relu(self.cnn_3(x))
        x = x.view(input.size(0), -1)
        x = torch.relu(self.ff_1(x))

        value = self.value(x)
        value = value.expand(input.size(0), self.action_size)
        advantage = self.advantage(x)
        Q = value + advantage - advantage.mean()
        return Q