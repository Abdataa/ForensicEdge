from pathlib import Path

BASE_PATH = Path("ai_engine/datasets/augmented/train")

VALID_EXTS = {".bmp", ".png", ".jpg", ".jpeg"}

def count_files(base_path):
    total = 0
    identity_counts = {}

    for identity in base_path.iterdir():
        if not identity.is_dir():
            continue

        count = sum(
            1 for f in identity.iterdir()
            if f.is_file() and f.suffix.lower() in VALID_EXTS
        )

        identity_counts[identity.name] = count
        total += count

    return total, identity_counts


total, identity_counts = count_files(BASE_PATH)

print("\n📊 AUGMENTED (LOCAL)")
print(f"TOTAL → {total} images")
print(f"IDENTITIES → {len(identity_counts)}")

# Optional: show few identities
for k in list(identity_counts.keys())[:5]:
    print(f"{k}: {identity_counts[k]}")