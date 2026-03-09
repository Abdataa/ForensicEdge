import torch
from contrastive_loss import ContrastiveLoss

loss_fn = ContrastiveLoss()

emb1 = torch.rand(4,128)
emb2 = torch.rand(4,128)

labels = torch.tensor([0.,1.,0.,1.])

loss = loss_fn(emb1, emb2, labels)

print(loss)