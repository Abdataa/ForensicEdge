import random
from pathlib import Path
import cv2
import torch
from torch.utils.data import Dataset
'''
5. Siamese Dataset (siamese_dataset.py)
This script defines a custom PyTorch Dataset class,
SiameseFingerprintDataset, designed for training a Siamese network -
 on the augmented fingerprint dataset.
The dataset generates pairs of images along with a binary label -
 indicating whether the pair belongs to the same identity (label=1) or
 different identities (label=0).
 The __getitem__ method randomly selects pairs of images,
  ensuring a balanced mix of positive and negative pairs for effective training.
'''


class SiameseFingerprintDataset(Dataset):
    '''Custom Dataset for Siamese Network Training on Fingerprint Images.'''

    def __init__(self, root_dir):

        self.root_dir = Path(root_dir)

        # list identities
        self.identities = list(self.root_dir.iterdir())

        # map identity -> images
        self.identity_images = {}

        for identity in self.identities:

            #images = list(identity.glob("*"))
            images = [p for p in identity.glob("*") if p.suffix.lower() in [".bmp",
                                                        ".png",".jpg",
                                                        ".jpeg"]]


            if len(images) > 1:
                self.identity_images[identity.name] = images

        self.identity_names = list(self.identity_images.keys())

    def __len__(self):

        return 50000   # virtual dataset size



    def load_image(self, path):

    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)

    img = img / 255.0

    img = torch.from_numpy(img).float()

    img = img.unsqueeze(0)  # (1, H, W)-> (Channels, Height, Width)
    return img

    def __getitem__(self, idx):

        same = random.randint(0, 1)

        if same:

            identity = random.choice(self.identity_names)

            img1, img2 = random.sample(self.identity_images[identity], 2)

            label = 1

        else:

            id1, id2 = random.sample(self.identity_names, 2)

            img1 = random.choice(self.identity_images[id1])
            img2 = random.choice(self.identity_images[id2])

            label = 0

        img1 = self.load_image(img1)
        img2 = self.load_image(img2)

        return img1, img2, torch.tensor(label, dtype=torch.float32)