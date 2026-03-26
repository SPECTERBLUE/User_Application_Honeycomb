import torch
import torch.nn as nn
import torch.optim as optim

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # last timestep
        return self.fc(out)
    
def train_lstm(X, y, prediction_type):
    

    X = torch.tensor(X, dtype=torch.float32)
    y = torch.tensor(y, dtype=torch.float32)

    model = LSTMModel(
        input_size=X.shape[2],
        hidden_size=64,
        output_size=y.shape[1] if len(y.shape) > 1 else 1
    )

    criterion = nn.BCEWithLogitsLoss() if prediction_type == "fault" else nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(10):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs.squeeze(), y)
        loss.backward()
        optimizer.step()

    return model