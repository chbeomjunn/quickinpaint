import torch
from PIL import Image


def get_device():
    if torch.cuda.is_available():
        print("cuda")
        return torch.device("cuda")
    try:
        _ = torch.ones(1, device="mps")
        print("a pole silicon")
        return torch.device("mps")
    except RuntimeError:
        print("falling back cpu")
        return torch.device("cpu")


def match_mask_size(image, mask):
    image_width, image_height = image.size
    mask_width, mask_height = mask.size

    width_factor = image_width / mask_width
    height_factor = image_height / mask_height

    new_mask_width = int(mask_width * width_factor)
    new_mask_height = int(mask_height * height_factor)

    resized_mask = mask.resize((new_mask_width, new_mask_height), Image.ANTIALIAS)

    return resized_mask
