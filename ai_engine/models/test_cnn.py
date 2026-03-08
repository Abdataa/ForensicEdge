import torch
from cnn_feature_extractor import FingerprintCNN
'''
This script tests the FingerprintCNN model,,,
by creating an instance of the model,
generating a dummy input tensor of the appropriate shape (1, 1, 224, 224),
and passing it through the model to verify that the output embedding has the expected shape (1, 128).'''

model = FingerprintCNN()

dummy = torch.randn(1, 1, 224, 224)

output = model(dummy)

print("Embedding shape:", output.shape)