import cv2
import albumentations as A
from pathlib import Path
import random
'''
4. Data Augmentation (augment.py)
This script performs data(train data) augmentation on the training set of the processed_clean SOCOFing dataset.
It applies a series of transformations suitable for fingerprint images, such as :
    - Small rotation (-10° to +10°)
    - Gaussian noise
    - Brightness variation
    - Elastic deformation (simulates skin pressure)
For each original image, it generates 3 augmented versions, resulting in a 4x increase in the number of training samples.
so each identity had 10 original images, after augmentation it will have 40 images (10 original + 30 augmented).

This augmentation step is crucial for improving the model's robustness and generalization, especially given the limited size of the original dataset.

'''

INPUT_DIR = Path("ai_engine/datasets/processed_clean/train")
OUTPUT_DIR = Path("ai_engine/datasets/augmented/train")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Augmentation pipeline (for fingerprints)
transform = A.Compose([
    A.Rotate(limit=10, p=0.7),
    A.GaussNoise(var_limit=(5.0, 20.0), p=0.5),
    A.RandomBrightnessContrast(p=0.5),
    A.ElasticTransform(alpha=1, sigma=50, p=0.3),
])


def augment_image(img):

    augmented = transform(image=img)

    return augmented["image"]


def augment_identity(identity_path):
'''
For a given identity (folder), this function reads all images,
applies augmentation, and saves both original
and augmented images to the output directory.'''
    identity_name = identity_path.name
    out_identity = OUTPUT_DIR / identity_name
    out_identity.mkdir(parents=True, exist_ok=True)

    images = list(identity_path.glob("*"))

    for img_path in images:

        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

        # Save original
        cv2.imwrite(str(out_identity / img_path.name), img)

        # Generate 3 augmented versions
        for i in range(3):

            aug_img = augment_image(img)

            new_name = f"{img_path.stem}_aug{i}.png"

            cv2.imwrite(str(out_identity / new_name), aug_img)


def run_augmentation():

    identities = list(INPUT_DIR.iterdir())

    for identity in identities:

        augment_identity(identity)

    print("Augmentation finished")


if __name__ == "__main__":
    run_augmentation()
    