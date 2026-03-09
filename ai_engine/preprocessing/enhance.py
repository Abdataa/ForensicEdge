import cv2
from pathlib import Path

INPUT_DIR = Path("ai_engine/datasets/processed")
OUTPUT_DIR = Path("ai_engine/datasets/processed_clean")

TARGET_SIZE = (224, 224)

# CLAHE initialization
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def preprocess_image(img_path):

    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

    if img is None:
        return None

    # 1. Resize
    img = cv2.resize(img, TARGET_SIZE)

    # 2. Denoise while preserving ridges
    img = cv2.bilateralFilter(img, d=5, sigmaColor=75, sigmaSpace=75)

    # 3. Local contrast enhancement
    img = clahe.apply(img)

    return img


def process_split(split):

    input_path = INPUT_DIR / split
    output_path = OUTPUT_DIR / split

    if not input_path.exists():
        print(f"Skipping {split}: folder not found")
        return

    for img_file in input_path.rglob("*"):

        if img_file.suffix.lower() not in [".bmp", ".png", ".jpg", ".jpeg"]:
            continue

        # preserve folder structure
        relative_path = img_file.relative_to(input_path)
        save_path = output_path / relative_path

        save_path.parent.mkdir(parents=True, exist_ok=True)

        processed_img = preprocess_image(img_file)

        if processed_img is not None:
            cv2.imwrite(str(save_path), processed_img)

    print(f"Finished preprocessing {split}")


if __name__ == "__main__":

    for split in ["train", "val", "test"]:
        process_split(split)

    print("All forensic preprocessing finished")