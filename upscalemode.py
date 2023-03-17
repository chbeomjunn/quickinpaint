import os
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import requests
from io import BytesIO
from diffusers import StableDiffusionUpscalePipeline
import torch

from utils import get_device


def scale_image_to_closest_resolution(img):
    supported_resolutions = [256, 512, 1024, 2048]
    width, height = img.size
    target_res = min(supported_resolutions, key=lambda x: abs(x - max(width, height)))
    return img.resize((target_res, target_res), Image.ANTIALIAS)


class UpscaleMode:
    def __init__(self, tab):
        self.img = None
        self.tab = tab

        self.sidebar = tk.Frame(self.tab, width=200)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)

        self.resolution_label = tk.Label(self.sidebar, text="Target Resolution:")
        self.resolution_label.pack(padx=10, pady=5)

        self.resolution_var = tk.StringVar(self.sidebar)
        self.resolution_var.set("1024")
        self.resolution_menu = tk.OptionMenu(self.sidebar, self.resolution_var, "256", "512", "1024", "2048")
        self.resolution_menu.pack(padx=10, pady=5)

        self.upscale_button = tk.Button(self.sidebar, text="Upscale Image", command=self.upscale_image)
        self.upscale_button.pack(padx=10, pady=10)

        self.canvas = tk.Canvas(self.tab, width=800, height=800)
        self.canvas.pack()

        self.load_image_button = tk.Button(self.sidebar, text="Load Image", command=self.load_image)
        self.load_image_button.pack(padx=10, pady=5)

        self.prompt = "a white cat"

    def display_image_on_canvas(self, img):
        canvas_image = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=canvas_image)
        self.canvas.image = canvas_image

    def upscale_image(self):
        model_id = os.environ.get("STABILITYSTUDIO_UPSCALE_MODEL", "stabilityai/stable-diffusion-x4-upscaler")
        pipeline = StableDiffusionUpscalePipeline.from_pretrained(model_id, torch_dtype=torch.float16)
        pipeline = pipeline.to(get_device())

        target_res = int(self.resolution_var.get())
        if target_res not in (256, 512, 1024, 2048):
            messagebox.showerror("Error", "Invalid target resolution.")
            return

        upscaled_image = pipeline(prompt=self.prompt, image=self.img).images[0]
        upscaled_image = upscaled_image.resize((target_res, target_res), Image.ANTIALIAS)
        upscaled_image.save("upsampled_cat.png")
        messagebox.showinfo("Success", f"Upscaled image saved as 'upsampled_cat.png'.")

    def load_image(self):
        filetypes = [("Image files", ".jpg .jpeg .png .bmp")]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            try:
                self.img = scale_image_to_closest_resolution(Image.open(filepath).convert("RGB"))
                self.display_image_on_canvas(self.img)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

