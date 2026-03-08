import os
import random
import shutil
from pathlib import Path
'''
2.Dataset Splitting (split_dataset.py)
This script takes the restructured SOCOFing dataset
and splits it into training, validation,
and test sets with a 70/15/15 ratio. The split is done at the identity level -
to ensure that all images of a given person are in the same set,
preventing data leakage.
The resulting folder structure will be:
processed/
    train/
        identity_1/
            img1.png
            img2.png
            ...
        identity_2/
            ...
    val/
        identity_3/
            ...
    test/
        identity_4/
            ...
'''

SOURCE = Path("ai_engine/datasets/processed/SOCOFing")

TRAIN_DIR = Path("ai_engine/datasets/processed/train")
VAL_DIR = Path("ai_engine/datasets/processed/val")
TEST_DIR = Path("ai_engine/datasets/processed/test")

TRAIN_DIR.mkdir(parents=True, exist_ok=True)
VAL_DIR.mkdir(parents=True, exist_ok=True)
TEST_DIR.mkdir(parents=True, exist_ok=True)

identities = [d for d in SOURCE.iterdir() if d.is_dir()]

random.shuffle(identities)

total = len(identities)

train_split = int(total * 0.7)
val_split = int(total * 0.85)

train_ids = identities[:train_split]
val_ids = identities[train_split:val_split]
test_ids = identities[val_split:]


def copy_identities(ids, dest):
    for identity in ids:
        dest_path = dest / identity.name
        shutil.copytree(identity, dest_path)


copy_identities(train_ids, TRAIN_DIR)
copy_identities(val_ids, VAL_DIR)
copy_identities(test_ids, TEST_DIR)

print("Dataset split complete")

print("Train:", len(train_ids))
print("Val:", len(val_ids))
print("Test:", len(test_ids))