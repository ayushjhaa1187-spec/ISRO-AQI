import torch
import torch.nn as nn

class ConvLSTMCell(nn.Module):
    def __init__(self, input_dim, hidden_dim, kernel_size, bias):
        """
        Initialize ConvLSTM cell.
        """
        super(ConvLSTMCell, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.kernel_size = kernel_size
        self.padding = kernel_size[0] // 2, kernel_size[1] // 2
        self.bias = bias
        
        self.conv = nn.Conv2d(in_channels=self.input_dim + self.hidden_dim,
                              out_channels=4 * self.hidden_dim,
                              kernel_size=self.kernel_size,
                              padding=self.padding,
                              bias=self.bias)

    def forward(self, input_tensor, cur_state):
        h_cur, c_cur = cur_state
        
        combined = torch.cat([input_tensor, h_cur], dim=1)  # concatenate along channel axis
        
        combined_conv = self.conv(combined)
        cc_i, cc_f, cc_o, cc_g = torch.split(combined_conv, self.hidden_dim, dim=1)
        
        i = torch.sigmoid(cc_i)
        f = torch.sigmoid(cc_f)
        o = torch.sigmoid(cc_o)
        g = torch.tanh(cc_g)
        
        c_next = f * c_cur + i * g
        h_next = o * torch.tanh(c_next)
        
        return h_next, c_next

    def init_hidden(self, batch_size, image_size):
        height, width = image_size
        return (torch.zeros(batch_size, self.hidden_dim, height, width, device=self.conv.weight.device),
                torch.zeros(batch_size, self.hidden_dim, height, width, device=self.conv.weight.device))


class SpatioTemporalAQIModel(nn.Module):
    def __init__(self, in_channels, hidden_dim=64):
        super(SpatioTemporalAQIModel, self).__init__()
        
        # Spatial Encoder
        # Extract spatial features from the raw 0.05° grid variables
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU()
        )
        
        # Temporal Dynamics
        self.convlstm = ConvLSTMCell(
            input_dim=hidden_dim,
            hidden_dim=hidden_dim,
            kernel_size=(3, 3),
            bias=True
        )
        
        # Spatial Decoder
        # Project back to a 1-channel PM2.5 / AQI grid
        self.decoder = nn.Sequential(
            nn.Conv2d(hidden_dim, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 1, kernel_size=1)
        )
        
    def forward(self, x):
        """
        x shape: (batch_size, seq_len, channels, height, width)
        returns: (batch_size, 1, height, width)
        """
        b, seq_len, c, h, w = x.size()
        
        # Initialize hidden states
        h_t, c_t = self.convlstm.init_hidden(b, (h, w))
        
        for t in range(seq_len):
            x_t = x[:, t, :, :, :]
            
            # Encode spatial features
            e_t = self.encoder(x_t)
            
            # Update temporal state
            h_t, c_t = self.convlstm(e_t, (h_t, c_t))
            
        # Decode the final hidden state into a 2D map
        out = self.decoder(h_t)
        
        # Squeeze out the channel dim so it matches (batch_size, height, width)
        return out.squeeze(1)

def masked_mse_loss(preds, targets, mask):
    """
    Computes MSE only at grid cells where mask == 1 (i.e. where CPCB data exists).
    preds: (batch, H, W)
    targets: (batch, H, W)
    mask: (batch, H, W)
    """
    diff = (preds - targets) ** 2
    masked_diff = diff * mask
    
    # Avoid division by zero if there are no valid sensors in the batch
    valid_count = mask.sum()
    if valid_count == 0:
        return torch.tensor(0.0, device=preds.device, requires_grad=True)
        
    return masked_diff.sum() / valid_count
