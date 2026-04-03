from pathlib import Path

BASE_PATH = Path("ai_engine/datasets/processed_clean")

VALID_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}

def count_files(split_path):
    count = 0

    for file in split_path.rglob("*"):
        if file.is_file() and file.suffix.lower() in VALID_EXTS:
            count += 1

    return count


def analyze_dataset(base_path):
    total = 0

    print("\n📊 LOCAL DATASET ANALYSIS")

    for split in ["train", "val", "test"]:
        split_path = base_path / split

        if not split_path.exists():
            print(f"❌ Missing: {split}")
            continue

        count = count_files(split_path)
        total += count

        print(f"{split.upper():<5} → {count} images")

    print(f"\nTOTAL → {total} images")
    print("-" * 30)


analyze_dataset(BASE_PATH)