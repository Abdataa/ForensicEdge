import os
import shutil
from collections import defaultdict
from pathlib import Path
'''
'''
BASE = Path(__file__).resolve().parent.parent
RAW_PATH = Base/"datasets/raw/fingerprints/SOCOFing/Real"
PROCESSED_PATH =Base/"datasets/processed/SOCOFing"

os.makedirs(PROCESSED_PATH, exist_ok=True)

files = os.listdir(RAW_PATH)

identity_dict = defaultdict(list)

# group files by identity
for file in files:
    identity = file.split("__")[0]
    identity_dict[identity].append(file)

print("Total identities:", len(identity_dict))

# create folders and move files
for identity, images in identity_dict.items():

    identity_folder = os.path.join(PROCESSED_PATH, identity)
    os.makedirs(identity_folder, exist_ok=True)

    for img in images:
        src = os.path.join(RAW_PATH, img)
        dst = os.path.join(identity_folder, img)

        shutil.copy(src, dst)

print("Dataset restructuring completed.")