import os

base_path = 'ai_engine/datasets/raw/fingerprints/SOCOFing'

real_path = os.path.join(base_path, 'Real')
altered_path = os.path.join(base_path, 'Altered')

def count_files_in_directory(directory_path):
    if not os.path.exists(directory_path):
        return 0, f"Directory not found: {directory_path}"

    file_count = 0
    for root, dirs, files in os.walk(directory_path):
        file_count += len(files)
    return file_count, None

real_count, real_error = count_files_in_directory(real_path)
altered_count, altered_error = count_files_in_directory(altered_path)

print(f"Number of files in '{real_path}':")
if real_error:
    print(f"  Error: {real_error}")
else:
    print(f"  {real_count} files")

print(f"Number of files in '{altered_path}':")
if altered_error:
    print(f"  Error: {altered_error}")
else:
    print(f"  {altered_count} files")




from pathlib import Path

BASE = Path("ai_engine/datasets/processed/SOCOFing")

identities = [d for d in BASE.iterdir() if d.is_dir()]

print("Total identity folders:", len(identities))

all_counts = []

for identity in identities:
    num_files = len([f for f in identity.iterdir() if f.is_file()])
    all_counts.append(num_files)

print("\nMin images per identity:", min(all_counts))
print("Max images per identity:", max(all_counts))
print("Average images per identity:", sum(all_counts)/len(all_counts))
