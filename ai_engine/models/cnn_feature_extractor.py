import torch
import torch.nn as nn
import torch.nn.functional as F
from cnn_feature_extractor import FingerprintCNN


class SiameseNetwork(nn.Module):

    def __init__(self):
        super(SiameseNetwork, self).__init__()

        # Shared CNN Feature Extractor
        self.cnn = FingerprintCNN()

    # Pass one image through CNN
    def forward_once(self, x):
        embedding = self.cnn(x)
        embedding = F.normalize(embedding, p=2, dim=1)  # normalize embeddings
        return embedding

    # Forward pass
    def forward(self, input1, input2):

        emb1 = self.forward_once(input1)
        emb2 = self.forward_once(input2)

        return emb1, emb2

    # Euclidean Distance (internal metric)
    def euclidean_distance(self, emb1, emb2):
        return F.pairwise_distance(emb1, emb2)

    # Cosine Similarity
    def cosine_similarity(self, emb1, emb2):
        return F.cosine_similarity(emb1, emb2)

    # Convert similarity to percentage
    def similarity_percentage(self, emb1, emb2):

        cos_sim = self.cosine_similarity(emb1, emb2)

        # Convert [-1,1] → [0,100]
        similarity = ((cos_sim + 1) / 2) * 100

        return similarity

    # Match classification for investigators
    def match_status(self, similarity):

        if similarity >= 85:
            return "MATCH"

        elif similarity >= 60:
            return "POSSIBLE MATCH"

        else:
            return "NO MATCH"

    # Full forensic analysis output
    def analyze(self, input1, input2):

        emb1, emb2 = self.forward(input1, input2)

        euclidean = self.euclidean_distance(emb1, emb2)
        cosine = self.cosine_similarity(emb1, emb2)
        similarity = self.similarity_percentage(emb1, emb2)

        status = self.match_status(similarity.item())

        result = {
            "similarity_percentage": similarity.item(),
            "cosine_similarity": cosine.item(),
            "euclidean_distance": euclidean.item(),
            "match_status": status
        }

        return result