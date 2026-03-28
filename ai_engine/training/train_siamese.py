import torch
from torch.utils.data import DataLoader
import torch.optim as optim
from pathlib import Path

from ai_engine.datasets.siamese_dataset import SiameseFingerprintDataset
from ai_engine.models.siamese_network import SiameseNetwork
from ai_engine.models.contrastive_loss import ContrastiveLoss


# ------------------------
# CONFIG
# ------------------------
DATA_DIR = "ai_engine/datasets/processed_clean/train"
VAL_DIR = "ai_engine/datasets/processed_clean/val"

BATCH_SIZE = 32
EPOCHS = 10
LR = 1e-3
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

SAVE_PATH = Path("ai_engine/models/weights")
SAVE_PATH.mkdir(parents=True, exist_ok=True)


# ------------------------
# LOAD DATA
# ------------------------
train_dataset = SiameseFingerprintDataset(DATA_DIR)
val_dataset = SiameseFingerprintDataset(VAL_DIR)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)


# ------------------------
# MODEL, LOSS, OPTIMIZER
# ------------------------
model = SiameseNetwork().to(DEVICE)

criterion = ContrastiveLoss(margin=2.0)
optimizer = optim.Adam(model.parameters(), lr=LR)


# ------------------------
# TRAIN FUNCTION
# ------------------------
def train_epoch():

    model.train()
    total_loss = 0

    for img1, img2, label in train_loader:

        img1, img2, label = img1.to(DEVICE), img2.to(DEVICE), label.to(DEVICE)

        optimizer.zero_grad()

        emb1, emb2 = model(img1, img2)

        loss = criterion(emb1, emb2, label)

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(train_loader)


# ------------------------
# VALIDATION FUNCTION
# ------------------------
def validate():

    model.eval()
    total_loss = 0

    with torch.no_grad():

        for img1, img2, label in val_loader:

            img1, img2, label = img1.to(DEVICE), img2.to(DEVICE), label.to(DEVICE)

            emb1, emb2 = model(img1, img2)

            loss = criterion(emb1, emb2, label)

            total_loss += loss.item()

    return total_loss / len(val_loader)


# ------------------------
# TRAIN LOOP
# ------------------------
best_val_loss = float("inf")

for epoch in range(EPOCHS):

    train_loss = train_epoch()
    val_loss = validate()

    print(f"Epoch [{epoch+1}/{EPOCHS}]")
    print(f"Train Loss: {train_loss:.4f}")
    print(f"Val Loss:   {val_loss:.4f}")

    # Save best model
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), SAVE_PATH / "best_model.pth")
        print("Model saved!")

print("Training completed.")