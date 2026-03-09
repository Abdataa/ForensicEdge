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

        # Contrastive loss formula
        loss = torch.mean(
            (1 - label) * torch.pow(distance, 2) +
            label * torch.pow(torch.clamp(self.margin - distance, min=0.0), 2)
        )

        return loss
        