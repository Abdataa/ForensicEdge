import torch
import torch.nn as nn
import torch.nn.functional as F

class ContrastiveLoss(nn.Module):
    def __init__(self, margin=2.0):
        super(ContrastiveLoss, self).__init__()
        self.margin = margin

    def forward(self, emb1, emb2, label):
        # Euclidean distance between embeddings
        distance = F.pairwise_distance(emb1, emb2)

        # UPDATED FORMULA TO DATASET (1=SAME, 0=DIFFERENT)
        # If label is 1 (Same): We want distance to be 0 -> (label) * dist^2
        # If label is 0 (Diff): We want distance to be > margin -> (1-label) * max(0, M-dist)^2
        loss = torch.mean(
            label * torch.pow(distance, 2) +
            (1 - label) * torch.pow(torch.clamp(self.margin - distance, min=0.0), 2)
        )

        return loss