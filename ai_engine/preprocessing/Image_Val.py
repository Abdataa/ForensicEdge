import cv2
import numpy as np
import random
from pathlib import Path

# Assumes your logic is in enhance.py
from enhance import preprocess_image

def add_label(img, text):
    """Adds a forensic label to the top-left of the image."""
    # Create a small black background for the text for better readability
    cv2.putText(img, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return img

def visualize_enhancement(input_dir, output_folder="ai_engine/previews", num_samples=5):
    input_path = Path(input_dir)
    preview_path = Path(output_folder)

    # Create output directory
    preview_path.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Searching in: {input_path.absolute()}")

    # Gather images with case-insensitive check
    all_images = []
    extensions = ["*.bmp", "*.BMP", "*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg", "*.JPEG"]
    for ext in extensions:
        all_images.extend(list(input_path.rglob(ext)))

    if not all_images:
        print(f"❌ No images found in {input_dir}!")
        return

    print(f"🖼️ Found {len(all_images)} images. Generating {num_samples} comparisons...")

    samples = random.sample(all_images, min(num_samples, len(all_images)))

    for i, img_path in enumerate(samples):
        # 1. Load Original
        original = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if original is None: continue
        original = cv2.resize(original, (224, 224))

        # 2. Run Forensic Enhancement
        enhanced = preprocess_image(img_path)
        if enhanced is None: continue

        # 3. Apply Text Labels for clarity
        original_labeled = add_label(original.copy(), "ORIGINAL")
        enhanced_labeled = add_label(enhanced.copy(), "ENHANCED")

        # 4. Create Side-by-Side with Divider
        divider = np.ones((224, 5), dtype=np.uint8) * 255 # White divider
        comparison = np.hstack((original_labeled, divider, enhanced_labeled))

        # 5. Save to the new previews folder
        # Naming includes the Subject ID (parent folder name)
        subject_id = img_path.parent.name
        save_filename = f"comparison_Subject_{subject_id}_{i}.png"
        save_full_path = preview_path / save_filename

        cv2.imwrite(str(save_full_path), comparison)
        print(f"✅ Saved: {save_filename}")

if __name__ == "__main__":
    # Point this to your RAW subject-nested folders
    visualize_enhancement(
        input_dir="../datasets/processed/train",
        output_folder="previews",
        num_samples=5
    )