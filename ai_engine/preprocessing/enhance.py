import cv2
from pathlib import Path

'''
This script preprocesses the images in the processed dataset
by resizing them to 224x224, enhancing contrast using histogram equalization,
and normalizing pixel values to the range [0, 1].
The preprocessed images are saved in a new directory structure under "processed_clean".
'''
INPUT_DIR = Path("ai_engine/datasets/processed")
OUTPUT_DIR = Path("ai_engine/datasets/processed_clean")

TARGET_SIZE = (224, 224)


def preprocess_image(img_path):
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

    # Resize
    img = cv2.resize(img, TARGET_SIZE)

    # Enhance contrast
    img = cv2.equalizeHist(img)

    # Normalize
    img = img / 255.0

    return img


def process_split(split):

    input_path = INPUT_DIR / split
    output_path = OUTPUT_DIR / split

    for identity in input_path.iterdir():

        identity_out = output_path / identity.name
        identity_out.mkdir(parents=True, exist_ok=True)

        for img_file in identity.glob("*"):

            img = preprocess_image(img_file)

            save_path = identity_out / img_file.name

            cv2.imwrite(str(save_path), (img * 255).astype("uint8"))

    print(f"{split} preprocessing done")


if __name__ == "__main__":

    for split in ["train", "val", "test"]:
        process_split(split)

    print("All preprocessing finished")