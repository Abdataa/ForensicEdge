import os
from torchvision.datasets import ImageFolder
from torchvision import transforms
from torch.utils.data import DataLoader

def get_basic_dataloader(data_dir, batch_size=8):

    transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((224, 224)),
        transforms.ToTensor()
    ])

    dataset = ImageFolder(
        root=data_dir,
        transform=transform
    )

    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True
    )

    return dataset, dataloader