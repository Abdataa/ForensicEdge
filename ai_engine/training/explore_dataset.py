from collections import defaultdict
import os
from PIL import Image
import matplotlib.pyplot as plt
import random

data_path = "../datasets/raw/fingerprints/SOCOFing/Real"

files = os.listdir(data_path)

#print("Total fingerprint images:", len(files))

# show sample files
#for f in files[:10]:
   # print(f)

identity_count = defaultdict(int)

for file in files:
    person_id = file.split("__")[0]
    identity_count[person_id] += 1

print("Total identities:", len(identity_count))

print("\nSample identity counts:")
for k in list(identity_count.keys())[:5]:
   print(k, identity_count[k])



#  visualize the image

sample = random.choice(files)

img_path = os.path.join(data_path, sample)

img = Image.open(img_path)

plt.imshow(img, cmap="gray")
plt.title(sample)
plt.axis("off")
plt.show()