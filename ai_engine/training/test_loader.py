import torch
"""
Example usage of get_basic_dataloader to load a fingerprint dataset and inspect its
contents.
This script sets a path to a raw fingerprint dataset, retrieves a dataset object
and a dataloader using :func:`get_basic_dataloader`, prints the mapping from
class names to integer indices, then fetches the first batch from the loader and
prints its shape and labels.
Intended for debugging or verifying that the dataloader is correctly
configured. Adjust ``data_path`` as needed for different datasets.
"""
from datasets.basic_dataset import get_basic_dataloader

data_path = ".../datasets/raw/fingerprints/NISTDB4_RAW/train_set"

dataset, loader = get_basic_dataloader(data_path)

print("Class to index mapping:")
print(dataset.class_to_idx)

images, labels = next(iter(loader))

print("Batch shape:", images.shape)
print("Labels:", labels)