from pathlib import Path

for split in ["train", "val", "test"]:
    path = Path(f"ai_engine/datasets/processed/{split}")
    identities = list(path.iterdir())

    print(split, "identities:", len(identities))

    if identities:
        sample = identities[0]
        print("sample images:", len(list(sample.glob("*"))))

    print()