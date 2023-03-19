import torch
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk


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


def resize_with_aspect_ratio_fill(image, target_size):
    img_width, img_height = image.size
    target_width, target_height = target_size

    aspect_ratio = min(target_width / img_width, target_height / img_height)
    new_width = int(img_width * aspect_ratio)
    new_height = int(img_height * aspect_ratio)

    resized_image = image.resize((new_width, new_height), Image.ANTIALIAS)

    padded_image = Image.new(image.mode, target_size, color=0 if image.mode == '1' else (255, 255, 255))
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    padded_image.paste(resized_image, (x_offset, y_offset))

    return padded_image


# def resize_with_aspect_ratio_fill(img, target_size):
#     img_width, img_height = img.size
#     target_width, target_height = target_size
#
#     # Check if one dimension of the image is already equal or larger than the corresponding dimension of the target size
#     if img_width >= target_width or img_height >= target_height:
#         aspect_ratio = max(target_width / img_width, target_height / img_height)
#         new_width = int(img_width * aspect_ratio)
#         new_height = int(img_height * aspect_ratio)
#     else:
#         # Resize the image along the maximum dimension to the corresponding dimension of the target size
#         if img_width > img_height:
#             aspect_ratio = target_width / img_width
#             new_width = target_width
#             new_height = int(img_height * aspect_ratio)
#         else:
#             aspect_ratio = target_height / img_height
#             new_width = int(img_width * aspect_ratio)
#             new_height = target_height
#
#     resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
#     result_img = Image.new(img.mode, target_size, color=0 if img.mode == '1' else (255, 255, 255))
#
#     x_offset = (target_width - new_width) // 2
#     y_offset = (target_height - new_height) // 2
#     result_img.paste(resized_img, (x_offset, y_offset))
#
#     return result_img


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


def resize_image_to_fit_canvas(img, target_size):
    img_width, img_height = img.size
    target_width, target_height = target_size

    aspect_ratio = max(target_width / img_width, target_height / img_height)
    new_width = int(img_width * aspect_ratio)
    new_height = int(img_height * aspect_ratio)

    resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
    return resized_img


def center_image_on_canvas_para(img, canvas: tk.Canvas):
    width, height = img.size
    x_offset = (canvas.winfo_width() - width) // 2
    y_offset = (canvas.winfo_height() - height) // 2
    return x_offset, y_offset


class ScrollableCanvas(tk.Canvas):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.image = None
        self.configure(scrollregion=self.bbox("all"))

        self.bind("<ButtonPress-1>", self._on_button_press)
        self.bind("<B1-Motion>", self._on_move_press)
        self.bind("<ButtonRelease-1>", self._on_button_release)
        # self.bind_all("<MouseWheel>", self._on_mousewheel)

        self._drag_data = {"x": 0, "y": 0}

    def display_image(self, img):
        x_offset, y_offset = center_image_on_canvas_para(img, self)
        canvas_image = ImageTk.PhotoImage(img)
        self.delete("all")
        self.create_image(x_offset, y_offset, anchor=tk.NW, image=canvas_image, tags="image")
        self.image = canvas_image
        self.configure(scrollregion=self.bbox("all"))

    def _on_button_press(self, event):
        self.scan_mark(event.x, event.y)

    def _on_move_press(self, event):
        self.scan_dragto(event.x, event.y, gain=1)
        self.configure(scrollregion=self.bbox("all"))

    def _on_button_release(self, event):
        pass

    # def _on_mousewheel(self, event):
    #     self.yview_scroll(int(-1 * (event.delta / 120)), "units")


class CanvasFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = ScrollableCanvas(self, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)

        self.scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=self.scrollbar_x.set)


