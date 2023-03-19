import os
import time
import sv_ttk
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import torch
from diffusers import StableDiffusionInpaintPipeline
import threading
from tkinterdnd2 import DND_FILES, TkinterDnD
from editmode import EditMode
from settingstab import SettingsTab
from upscalemode import UpscaleMode
from utils import get_device, match_mask_size, resize_with_aspect_ratio_fill

last_x, last_y = None, None


# class ProgressCapture:
#     def __init__(self, progress_callback):
#         self.progress_callback = progress_callback
#
#     def write(self, text):
#         if text.startswith(" "):
#             progress = text.strip().split("|")[0].rstrip("%")
#             try:
#                 progress = float(progress)
#                 self.progress_callback(progress)
#             except ValueError:
#                 pass
#
#     def flush(self):
#         pass


def center_image_on_canvas(img):
    width, height = img.size
    x_offset = (canvas.winfo_width() - width) // 2
    y_offset = (canvas.winfo_height() - height) // 2
    return x_offset, y_offset


def display_image_on_canvas(img, zoom=1):
    img = img.resize((int(img.width * zoom), int(img.height * zoom)), Image.ANTIALIAS)
    x_offset, y_offset = center_image_on_canvas(img)
    canvas_image = ImageTk.PhotoImage(img)
    canvas.display_image(img)

    # keep a reference to the canvas_image object
    canvas.canvas_image = canvas_image

    canvas.delete("image")
    canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=canvas_image, tags="image")


def display_placeholder_text():
    canvas.delete("all")
    text = "Drop an image or click the 'Load Image' button."
    canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2, text=text, anchor=tk.CENTER)


def resize_image_and_mask(image, mask, target_size=(512, 512)):
    resized_image = resize_with_aspect_ratio_fill(image, target_size)
    resized_mask = resize_with_aspect_ratio_fill(mask, target_size)
    return resized_image, resized_mask


def resize_image_to_target_resolution(image, target_resolution=None):
    if target_resolution is None:
        target_resolution = (resolution_var.get(), resolution_var.get())
    img_width, img_height = image.size
    aspect_ratio = min(target_resolution / img_width, target_resolution / img_height)
    new_width = int(img_width * aspect_ratio)
    new_height = int(img_height * aspect_ratio)
    resized_image = image.resize((new_width, new_height), Image.ANTIALIAS)
    return resized_image


def load_image(file_path=None):
    if not file_path:
        filetypes = [("Image files", ".jpg .jpeg .png .bmp")]
        file_path = filedialog.askopenfilename(filetypes=filetypes)
    if file_path:
        global original_image, mask_image, mask_draw
        original_image = Image.open(file_path).convert("RGB")

        target_resolution = resolution_var.get()
        resized_image = resize_image_to_target_resolution(original_image, target_resolution)

        original_image, mask_image = resize_image_and_mask(resized_image, mask_image, (canvas.winfo_width(), canvas.winfo_height()))
        mask_draw = ImageDraw.Draw(mask_image)
        display_image_on_canvas(original_image)


# Drag and drop callback
def drop(event):
    if event.data:
        load_image(event.data[0])


def smooth_mask_path(points, brush_size):
    if brush_mode.get():
        x1, y1, x2, y2 = points
        mask_draw.ellipse(
            (x1 - brush_size, y1 - brush_size, x1 + brush_size, y1 + brush_size),
            fill="white",
        )
        mask_draw.ellipse(
            (x2 - brush_size, y2 - brush_size, x2 + brush_size, y2 + brush_size),
            fill="white",
        )
    else:
        mask_draw.line(points, fill="white", width=brush_size, joint='curve')


# Modify the draw_mask function as follows:
def draw_mask(event):
    global last_x, last_y

    x, y = event.x, event.y
    x_offset, y_offset = center_image_on_canvas(original_image)
    x_rel = x - x_offset
    y_rel = y - y_offset

    if 0 <= x_rel < original_image.width and 0 <= y_rel < original_image.height:
        if last_x is not None and last_y is not None:
            smooth_mask_path([last_x, last_y, x_rel, y_rel], brush_size.get())
        else:
            mask_draw.ellipse(
                (x_rel - brush_size.get(),
                 y_rel - brush_size.get(),
                 x_rel + brush_size.get(),
                 y_rel + brush_size.get()),
                fill="white",
            )
        temp_img = original_image.copy()
        temp_img.paste(mask_image, (0, 0), mask_image)
        display_image_on_canvas(temp_img)

        last_x, last_y = x_rel, y_rel


def clear_mask():
    global mask_image, mask_draw, last_x, last_y
    mask_image = Image.new("1", (canvas.winfo_width(), canvas.winfo_height()), 0)
    mask_draw = ImageDraw.Draw(mask_image)
    last_x, last_y = None, None
    if original_image:
        display_image_on_canvas(original_image)


def progress_callback(progress):
    # progress_var.set(progress)
    root.update_idletasks()


def perform_inpainting():
    inpaint_button.config(state=tk.DISABLED)
    prompt_text = prompt_entry.get()
    threading.Thread(target=perform_inpainting_thread, args=(prompt_text,)).start()


def perform_inpainting_thread(prompt_text):

    from diffusers.pipelines.stable_diffusion import safety_checker

    def sc(self, clip_input, images) :
        return images, [False for i in images]

    # edit StableDiffusionSafetyChecker class so that, when called, it just returns the images and an array of True values
    safety_checker.StableDiffusionSafetyChecker.forward = sc

    model_id = os.environ.get("STABILITYSTUDIO_GENERATE_MODEL", "ImNoOne/f222-inpainting-diffusers")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(model_id)
    pipe = pipe.to(get_device())

    resized_image, resized_mask = resize_image_and_mask(original_image, mask_image)
    resized_mask = match_mask_size(resized_image, resized_mask)
    result = pipe(prompt=prompt_text, image=resized_image, mask_image=resized_mask).images[0]

    os.makedirs("out", exist_ok=True)
    unique_filename = f"result_{int(time.time())}.png"
    result_path = os.path.join("out", unique_filename)
    result.save(result_path)

    display_image_on_canvas(result)
    inpaint_button.config(state=tk.NORMAL)

    # Unlock the edit  tab and initialize its contents
    notebook.tab(tab2, state="normal")
    editmode.update_images(original_image, result)


def reset_application():
    global original_image, mask_image, mask_draw
    original_image = None
    mask_image = Image.new("1", (canvas.winfo_width(), canvas.winfo_height()), 0)
    mask_draw = ImageDraw.Draw(mask_image)
    display_placeholder_text()
    last_x, last_y = None, None


def resize_image_to_fit_canvas(img, target_size):
    img_width, img_height = img.size
    target_width, target_height = target_size

    aspect_ratio = max(target_width / img_width, target_height / img_height)
    new_width = int(img_width * aspect_ratio)
    new_height = int(img_height * aspect_ratio)

    resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
    return resized_img


def resize_canvas(event):
    global original_image
    total_width, total_height = event.width, event.height
    sidebar_width = sidebar_frame.winfo_width()
    bottom_height = bottom_frame.winfo_height()

    width = total_width - sidebar_width
    height = total_height - bottom_height

    # update the size of the canvas
    canvas.config(width=width, height=height)

    if original_image:
        # update the size of the displayed image based on the new canvas size
        resized_image = resize_image_to_fit_canvas(original_image, (width, height))
        display_image_on_canvas(resized_image)
    else:
        display_placeholder_text()


# Initialize the Tkinter window and canvas
root = TkinterDnD.Tk()
root.title("Stability Studio")
notebook = ttk.Notebook(root)
tab1 = tk.Frame(notebook, width=1024, height=1024)
tab2 = tk.Frame(notebook)
tab3 = tk.Frame(notebook)
tab4 = tk.Frame(notebook)

notebook.add(tab1, text="Generate")
notebook.add(tab2, text="Edit")
notebook.add(tab3, text="Upscale")
notebook.add(tab4, text="Settings")
notebook.pack(fill=tk.BOTH, expand=True)

editmode = EditMode(tab2, None, None)
upscaletab = UpscaleMode(tab3)
settingstab = SettingsTab(tab4)

sidebar_frame = tk.Frame(tab1)
sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, anchor=tk.N)

# buttons
button_frame = tk.Frame(sidebar_frame)
button_frame.pack(side=tk.TOP)

reset_button = tk.Button(button_frame, text="Reset", command=reset_application)
reset_button.pack(pady=10)
clear_mask_button = tk.Button(button_frame, text="Clear Mask", command=clear_mask)
clear_mask_button.pack(pady=10)

bottom_frame = tk.Frame(tab1)
bottom_frame.pack(side=tk.BOTTOM, anchor=tk.W)

# Add bottom fields

load_button = tk.Button(bottom_frame, text="Load Image", command=load_image)
load_button.pack(side=tk.LEFT)

inpaint_button = tk.Button(bottom_frame, text="Inpaint Image", command=perform_inpainting)
inpaint_button.pack(side=tk.RIGHT)

prompt_label = tk.Label(bottom_frame, text="Inpainting prompt:")
prompt_label.pack(side=tk.LEFT)
prompt_entry = tk.Entry(bottom_frame, width=60)
prompt_entry.pack(side=tk.BOTTOM)

# Initialize the original image, mask image, and mask drawing
original_image = None
mask_image = Image.new("1", (800, 600), 0)
mask_draw = ImageDraw.Draw(mask_image)

brush_size_label = tk.Label(button_frame, text="Brush size:")
brush_size_label.pack(pady=5)
brush_size = tk.IntVar(value=10)
brush_size_slider = tk.Scale(button_frame, from_=1, to=50, orient=tk.HORIZONTAL, variable=brush_size)
brush_size_slider.pack(pady=5)

brush_mode = tk.BooleanVar(value=True)
brush_mode_checkbutton = tk.Checkbutton(
    button_frame, text="Use round brush", variable=brush_mode
)
brush_mode_checkbutton.pack(pady=10)

resolution_frame = tk.Frame(sidebar_frame)
resolution_frame.pack(side=tk.TOP, pady=10)

resolution_label = tk.Label(resolution_frame, text="Image resolution:")
resolution_label.pack(side=tk.TOP, pady=5)

resolution_var = tk.IntVar(value=512)
available_resolutions = [64, 128, 256, 512, 1024, 2048]
for res in available_resolutions:
    resolution_radio = tk.Radiobutton(
        resolution_frame, text=str(res), variable=resolution_var, value=res
    )
    resolution_radio.pack(side=tk.TOP)

canvas = tk.Canvas(tab1, width=1024, height=1024)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

canvas.bind("<B1-Motion>", draw_mask)
canvas.bind("<ButtonRelease-1>", lambda event: (setattr(event.widget, "last_x", None),
                                                setattr(event.widget, "last_y", None)))

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)
canvas.bind("<Configure>", resize_canvas)

sv_ttk.set_theme("light")

root.mainloop()

