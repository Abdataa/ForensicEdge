from siamese_dataset import SiameseFingerprintDataset
'''
This script defines a SiameseFingerprintDataset class that creates pairs
of fingerprint images for training a Siamese network.
'''

dataset = SiameseFingerprintDataset(
    "ai_engine/datasets/augmented/train"
)

print("Dataset size:", len(dataset))

img1, img2, label = dataset[0]

print("Image shape:", img1.shape)
print("Label:", label)