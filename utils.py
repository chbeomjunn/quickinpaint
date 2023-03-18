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

    aspect_ratio = max(target_width / img_width, target_height / img_height)
    new_width = int(img_width * aspect_ratio)
    new_height = int(img_height * aspect_ratio)

    resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
    result_img = Image.new(img.mode, target_size, color=0 if img.mode == '1' else (255, 255, 255))

    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    result_img.paste(resized_img, (x_offset, y_offset))

    return result_img


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

