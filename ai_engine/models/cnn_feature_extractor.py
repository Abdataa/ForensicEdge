import torch
import torch.nn as nn
import torch.nn.functional as F

class FingerprintCNN(nn.Module):
    def __init__(self):
        super(FingerprintCNN, self).__init__()

        # Layer 1: Captures basic edges
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)

        # Layer 2: Captures ridge flows
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)

        # Layer 3: Captures minutiae patterns (Bifurcations, Endings)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)

        self.pool = nn.MaxPool2d(2, 2)

        # NEW: Global Average Pooling replaces the massive flattened layer
        self.gap = nn.AdaptiveAvgPool2d((1, 1))

        self.dropout = nn.Dropout(p=0.3)

        # UPDATED: fc1 now receives 128 features (the channel count from conv3)
        # instead of 100,352 features.
        self.fc1 = nn.Linear(128, 512)
        self.fc2 = nn.Linear(512, 128) # Final Forensic Embedding

    def forward(self, x):
        # Convolutional Block
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))

        # Global Average Pooling
        x = self.gap(x)

        # Flatten to (Batch Size, 128)
        x = x.view(x.size(0), -1)

        # Fully Connected Block
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)

        # Normalize embedding to unit length for similarity matching
        x = F.normalize(x, p=2, dim=1)

        return x