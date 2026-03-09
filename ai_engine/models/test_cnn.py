import torch
from cnn_feature_extractor import FingerprintCNN

model = FingerprintCNN()

dummy = torch.randn(1, 1, 224, 224)

output = model(dummy)

print("Embedding shape:", output.shape)