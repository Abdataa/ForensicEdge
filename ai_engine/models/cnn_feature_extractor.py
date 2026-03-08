import torch
import torch.nn as nn
import torch.nn.functional as F
'''
This script defines the FingerprintCNN model, a convolutional neural network designed
to extract forensic features from fingerprint images.
The architecture consists of three convolutional layers that capture different -
levels of fingerprint details (edges, ridge flows, minutiae patterns),
followed by fully connected layers that produce a 128-dimensional embedding.
The final embedding is normalized to unit length, making it suitable
for similarity-based matching in a Siamese network setup.
This model serves as the backbone for fingerprint recognition tasks in the ForensicEdge project.
'''

class FingerprintCNN(nn.Module):
    '''
    Convolutional Neural Network for Extracting Forensic Features from Fingerprint Images.'''
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
        self.dropout = nn.Dropout(p=0.3) # Prevents memorizing specific people

        # Assuming input is 224x224.
        # After 3 pools, size is 28x28.
        self.fc1 = nn.Linear(128 * 28 * 28, 512)
        self.fc2 = nn.Linear(512, 128) # Final Forensic Embedding

    def forward(self, x):
        # Convolutional Block
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))

        # Flatten
        x = x.view(x.size(0), -1)

        # Fully Connected Block
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)

        # CRITICAL: Normalize embedding to unit length for similarity matching
        x = F.normalize(x, p=2, dim=1)

        return x