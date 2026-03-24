import torch
from siamese_network import SiameseNetwork

model = SiameseNetwork()

img1 = torch.randn(1,1,224,224)
img2 = torch.randn(1,1,224,224)

emb1, emb2 = model(img1, img2)

distance = model.distance(emb1, emb2)

print("Embedding1:", emb1.shape)
print("Embedding2:", emb2.shape)
print("Distance:", distance)