import os
import time
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import torch
from diffusers import StableDiffusionInpaintPipeline
import threading
import subprocess
from tkinterdnd2 import DND_FILES, TkinterDnD
from tqdm import tqdm
import sys


def get_device():
    if torch.cuda.is_available():
        print("cuda")
        return torch.device("cuda")
    try:
        print("a pole silicon")
        _ = torch.ones(1, device="mps")
        return torch.device("mps")
    except RuntimeError:
        print("falling back cpu")
        return torch.device("cpu")


device = get_device()


class ProgressCapture:
    def __init__(self, progress_callback):
        self.progress_callback = progress_callback

    def write(self, text):
        if text.startswith(" "):
            progress = text.strip().split("|")[0].rstrip("%")
            try:
                progress = float(progress)
                self.progress_callback(progress)
            except ValueError:
                pass

    def flush(self):
        pass


# Function to center the image on the canvas
def center_image_on_canvas(img):
    width, height = img.size
    x_offset = (canvas.winfo_width() - width) // 2
    y_offset = (canvas.winfo_height() - height) // 2
    return x_offset, y_offset


# Function to display the image on the canvas
def display_image_on_canvas(img):
    x_offset, y_offset = center_image_on_canvas(img)
    canvas_image = ImageTk.PhotoImage(img)
    canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=canvas_image)
    canvas.image = canvas_image


def display_placeholder_text():
    canvas.delete("all")
    text = "Drop an image or click the 'Load Image' button."
    canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2, text=text, anchor=tk.CENTER)

def match_mask_size(image, mask):
    image_width, image_height = image.size
    mask_width, mask_height = mask.size
    
    width_factor = image_width / mask_width
    height_factor = image_height / mask_height
    
    new_mask_width = int(mask_width * width_factor)
    new_mask_height = int(mask_height * height_factor)
    
    resized_mask = mask.resize((new_mask_width, new_mask_height), Image.ANTIALIAS)
    
    return resized_mask


def resize_image_and_mask(image, mask, target_size=(512, 512)):
    def resize_with_aspect_ratio_fill(img, target_size):
        img_width, img_height = img.size
        target_width, target_height = target_size

        aspect_ratio = min(target_width / img_width, target_height / img_height)
        new_width = int(img_width * aspect_ratio)
        new_height = int(img_height * aspect_ratio)

        resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
        result_img = Image.new(img.mode, target_size, color=0 if img.mode == '1' else (255, 255, 255))

        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        result_img.paste(resized_img, (x_offset, y_offset))

        return result_img

    resized_image = resize_with_aspect_ratio_fill(image, target_size)
    resized_mask = resize_with_aspect_ratio_fill(mask, target_size)
    return resized_image, resized_mask


def load_image(file_path=None):
    if not file_path:
        file_path = filedialog.askopenfilename()
    if file_path:
        global original_image, mask_image, mask_draw
        original_image = Image.open(file_path).convert("RGB")
        original_image, mask_image = resize_image_and_mask(original_image, mask_image, (canvas.winfo_width(), canvas.winfo_height()))

        mask_draw = ImageDraw.Draw(mask_image)

        display_image_on_canvas(original_image)



# Drag and drop callback
def drop(event):
    if event.data:
        load_image(event.data[0])


def draw_mask(event):
    x, y = event.x, event.y
    x_offset, y_offset = center_image_on_canvas(original_image)
    x_rel = x - x_offset
    y_rel = y - y_offset

    if 0 <= x_rel < original_image.width and 0 <= y_rel < original_image.height:
        mask_draw.ellipse((x_rel - brush_size, y_rel - brush_size, x_rel + brush_size, y_rel + brush_size), fill="white")
        temp_img = original_image.copy()
        temp_img.paste(mask_image, (0, 0), mask_image)
        display_image_on_canvas(temp_img)

def progress_callback(progress):
    progress_var.set(progress)
    root.update_idletasks()
    
def inpaint_image():
    inpaint_button.config(state=tk.DISABLED)
    prompt_text = prompt_entry.get()
    threading.Thread(target=perform_inpainting, args=(prompt_text,)).start()


def perform_inpainting():
    inpaint_button.config(state=tk.DISABLED)
    prompt_text = prompt_entry.get()
    threading.Thread(target=perform_inpainting_thread, args=(prompt_text,)).start()

def perform_inpainting_thread(prompt_text):
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
    )

    # Set up the custom stdout to capture progress
    original_stdout = sys.stdout
    sys.stdout = ProgressCapture(progress_callback)

    resized_image, resized_mask = resize_image_and_mask(original_image, mask_image)
    resized_mask = match_mask_size(resized_image, resized_mask)
    result = pipe(prompt=prompt_text, image=resized_image, mask_image=resized_mask).images[0]

    # Restore the original stdout
    sys.stdout = original_stdout

    os.makedirs("out", exist_ok=True)
    unique_filename = f"result_{int(time.time())}.png"
    result_path = os.path.join("out", unique_filename)
    result.save(result_path)

    display_image_on_canvas(result)
    inpaint_button.config(state=tk.NORMAL)

    # Open the image with the default image viewer
    if os.name == 'posix':
        subprocess.call(('xdg-open', result_path))
    elif os.name == 'nt':
        os.startfile(result_path)
    else:
        subprocess.call(('open', result_path))


def reset_application():
    global original_image, mask_image, mask_draw
    original_image = None
    mask_image = Image.new("1", (canvas.winfo_width(), canvas.winfo_height()), 0)
    mask_draw = ImageDraw.Draw(mask_image)
    display_placeholder_text()


def clear_mask():
    global mask_image, mask_draw
    mask_image = Image.new("1", (canvas.winfo_width(), canvas.winfo_height()), 0)
    mask_draw = ImageDraw.Draw(mask_image)
    if original_image:
        display_image_on_canvas(original_image)



# Initialize the Tkinter window and canvas
root = TkinterDnD.Tk()
root.title("Image Inpainting")
canvas = tk.Canvas(root, width=800, height=600)
canvas.pack()

progress_frame = tk.Frame(root)
progress_frame.pack(side=tk.TOP, fill=tk.X)

progress_label = tk.Label(progress_frame, text="Progress:")
progress_label.pack(side=tk.LEFT)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)

# Add buttons
button_frame = tk.Frame(root)
button_frame.pack(side=tk.RIGHT, fill=tk.Y)

load_button = tk.Button(root, text="Load Image", command=load_image)
load_button.pack(side=tk.LEFT)

reset_button = tk.Button(button_frame, text="Reset", command=reset_application)
reset_button.grid(row=0, column=0, sticky=tk.N)
clear_mask_button = tk.Button(button_frame, text="Clear Mask", command=clear_mask)
clear_mask_button.grid(row=1, column=0, sticky=tk.N)

inpaint_button = tk.Button(root, text="Inpaint Image", command=perform_inpainting)
inpaint_button.pack(side=tk.RIGHT)

# Add prompt entry field
prompt_label = tk.Label(root, text="Inpainting prompt:")
prompt_label.pack(side=tk.LEFT)
prompt_entry = tk.Entry(root, width=50)
prompt_entry.pack(side=tk.LEFT)

# Initialize the original image, mask image, and mask drawing
original_image = None
mask_image = Image.new("1", (800, 600), 0)
mask_draw = ImageDraw.Draw(mask_image)
brush_size = 10

# Bind the mouse events to draw the mask
canvas.bind("<B1-Motion>", draw_mask)


root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)

root.mainloop()

