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

# Function to display placeholder text on the canvas
def display_placeholder_text():
    canvas.delete("all")
    text = "Drop an image or click the 'Load Image' button."
    canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2, text=text, anchor=tk.CENTER)

def match_mask_size(image, mask):
    image_width, image_height = image.size
    mask_width, mask_height = mask.size
    
    # Calculate the scaling factors
    width_factor = image_width / mask_width
    height_factor = image_height / mask_height
    
    # Calculate the new mask dimensions
    new_mask_width = int(mask_width * width_factor)
    new_mask_height = int(mask_height * height_factor)
    
    # Resize the mask
    resized_mask = mask.resize((new_mask_width, new_mask_height), Image.ANTIALIAS)
    
    return resized_mask


def resize_image_and_mask(image, mask, target_size=(512, 512)):
    resized_image = image.resize(target_size, Image.ANTIALIAS)
    resized_mask = mask.resize(target_size, Image.ANTIALIAS)
    return resized_image, resized_mask


def resize_with_aspect_ratio(image, target_size, divisor=8):
    width, height = image.size
    target_width, target_height = target_size

    # Calculate the new size while maintaining the aspect ratio
    aspect_ratio = min(target_width / width, target_height / height)
    new_width = int(width * aspect_ratio)
    new_height = int(height * aspect_ratio)

    # Round the new width and height to the nearest multiple of the divisor
    new_width = (new_width + divisor // 2) // divisor * divisor
    new_height = (new_height + divisor // 2) // divisor * divisor

    # Resize the image and return it
    return image.resize((new_width, new_height), Image.ANTIALIAS)


def load_image():
    file_path = filedialog.askopenfilename()
    if file_path:
        global original_image, mask_image, mask_draw
        original_image = Image.open(file_path).convert("RGB")
        original_image = resize_with_aspect_ratio(original_image, (canvas.winfo_width(), canvas.winfo_height()))

        mask_image = Image.new("1", original_image.size, 0)
        mask_draw = ImageDraw.Draw(mask_image)

        display_image_on_canvas(original_image)


# Drag and drop callback
def drop(event):
    if event.data:
        load_image(event.data)

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


# Function to start the inpainting process
def inpaint_image():
    inpaint_button.config(state=tk.DISABLED)
    prompt_text = prompt_entry.get()
    threading.Thread(target=perform_inpainting, args=(prompt_text,)).start()


# Function to perform inpainting and update the progress bar
def perform_inpainting(prompt_text):
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
        # revision="fp16",
        #torch_dtype=torch.float16,
    )

    # start_time = time.time()
    # duration = 15  # Approximate duration of the inpainting process in seconds
    # for i in range(1, duration + 1):
    #     update_progress_bar(i / duration)
    #     time.sleep(1)

    resized_image, resized_mask = resize_image_and_mask(original_image, mask_image)
    resized_mask = match_mask_size(resized_image, resized_mask)
    result = pipe(prompt=prompt_text, image=resized_image, mask_image=resized_mask).images[0]
    # update_progress_bar(1)

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

# Initialize the Tkinter window and canvas
root = TkinterDnD.Tk()
root.title("Image Inpainting")
canvas = tk.Canvas(root, width=800, height=600)
canvas.pack()

# Add buttons
load_button = tk.Button(root, text="Load Image", command=load_image)
load_button.pack(side=tk.LEFT)
inpaint_button = tk.Button(root, text="Inpaint Image", command=inpaint_image)
inpaint_button.pack(side=tk.RIGHT)

# Add prompt entry field
prompt_label = tk.Label(root, text="Inpainting prompt:")
prompt_label.pack(side=tk.LEFT)
prompt_entry = tk.Entry(root)
prompt_entry.pack(side=tk.LEFT)

# Initialize the original image, mask image, and mask drawing
original_image = None
mask_image = Image.new("1", (800, 600), 0)
mask_draw = ImageDraw.Draw(mask_image)
brush_size = 10

# Bind the mouse events to draw the mask
canvas.bind("<B1-Motion>", draw_mask)

# Add progress bar
progress_label = tk.Label(root, text="Progress:")
progress_label.pack(side=tk.LEFT)
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(side=tk.LEFT)

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)

root.mainloop()

