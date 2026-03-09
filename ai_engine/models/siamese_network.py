import torch
import torch.nn as nn
import torch.nn.functional as F
from cnn_feature_extractor import FingerprintCNN


class SiameseNetwork(nn.Module):

    def __init__(self):
        super(SiameseNetwork, self).__init__()

        # Shared CNN
        self.cnn = FingerprintCNN()

    def forward_once(self, x):
        return self.cnn(x)

    def forward(self, input1, input2):

        output1 = self.forward_once(input1)
        output2 = self.forward_once(input2)

        return output1, output2


    def distance(self, emb1, emb2):
        return F.pairwise_distance(emb1, emb2)
    def 
