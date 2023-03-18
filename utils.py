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


def resize_with_aspect_ratio_fill(img, target_size):
    img_width, img_height = img.size
    target_width, target_height = target_size

    # Calculate aspect ratios
    img_aspect_ratio = img_width / img_height
    target_aspect_ratio = target_width / target_height

    if img_aspect_ratio > target_aspect_ratio:
        # Image is wider than target size, so width should match target size
        new_width = target_width
        new_height = int(target_width / img_aspect_ratio)
    else:
        # Image is taller than target size, so height should match target size
        new_width = int(target_height * img_aspect_ratio)
        new_height = target_height

    # Resize image
    resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)

    # Add letterboxing if necessary
    if img_aspect_ratio != target_aspect_ratio:
        # Calculate letterbox size
        letterbox_width = target_width - new_width
        letterbox_height = target_height - new_height

        # Calculate position of letterboxing
        letterbox_left = letterbox_width // 2
        letterbox_right = letterbox_width - letterbox_left
        letterbox_top = letterbox_height // 2
        letterbox_bottom = letterbox_height - letterbox_top

        # Create new image with letterboxing
        letterboxed_img = Image.new(img.mode, target_size, color=(0, 0, 0) if img.mode == 'RGB' else 0)
        letterboxed_img.paste(resized_img, (letterbox_left, letterbox_top))

        return letterboxed_img

    return resized_img

def remove_whitespace(image):
    image_data = image.load()
    left, right, top, bottom = 0, image.width - 1, 0, image.height - 1

    while left < image.width and all(image_data[left, y] == (255, 255, 255, 255) for y in range(image.height)):
        left += 1

    while right >= 0 and all(image_data[right, y] == (255, 255, 255, 255) for y in range(image.height)):
        right -= 1

    while top < image.height and all(image_data[x, top] == (255, 255, 255, 255) for x in range(image.width)):
        top += 1

    while bottom >= 0 and all(image_data[x, bottom] == (255, 255, 255, 255) for x in range(image.width)):
        bottom -= 1

    if left <= right and top <= bottom:
        return image.crop((left, top, right + 1, bottom + 1))
    else:
        return image

