import torch
import torchvision.transforms as transforms

def get_base_transform():
    return transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])


def get_train_transform():
    return transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((224, 224)),

        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),

        transforms.ToTensor(),
        transforms.Lambda(lambda x: x + 0.01 * torch.randn_like(x)),

        transforms.Normalize((0.5,), (0.5,))
    ])
    