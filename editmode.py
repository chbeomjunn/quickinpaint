import math
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw

from utils import resize_image_to_fit_canvas, remove_whitespace, resize_with_aspect_ratio_fill


class EditMode:
    def __init__(self, tab, original_image=None, inpainted_image=None):
        self.zoom_level = 1
        self.canvas_image = None
        self.original_scale_factor = None
        self.inpainted_scale_factor = None
        self.unscaled_original_image = None
        self.tab = tab
        self.original_image = original_image
        self.inpainted_image = inpainted_image

        self.sidebar = tk.Frame(self.tab, width=200)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_orig_button = tk.Button(self.sidebar, text="Load Original Image", command=self.load_original_image)
        self.load_orig_button.pack(padx=10, pady=10)

        self.load_inpainted_button = tk.Button(self.sidebar, text="Load Inpainted Image",
                                               command=self.load_inpainted_image, state=tk.DISABLED)
        self.load_inpainted_button.pack(padx=10, pady=10)

        self.canvas_frame = tk.Frame(self.tab)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, width=800, height=800)  # Adjust the size of the canvas as needed
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.vbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.canvas.config(yscrollcommand=self.vbar.set)

        self.hbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.config(xscrollcommand=self.hbar.set)

        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # self.canvas.bind("<Configure>", self.resize_canvas)
        self.canvas.bind("<MouseWheel>", self.zoom)

        if self.inpainted_image:
            self.overlay_image = Image.new("RGBA", self.inpainted_image.size, (0, 0, 0, 0))
            self.overlay_draw = ImageDraw.Draw(self.overlay_image)
            self.display_image_on_canvas(self.inpainted_image)
        else:
            self.display_placeholder_text()

        self.canvas.bind("<B1-Motion>", self.draw_original_on_inpainted)
        self.canvas.bind("<ButtonRelease-1>",
                         lambda event: (setattr(event.widget, "last_x", None), setattr(event.widget, "last_y", None)))

    # Add other methods here

    def zoom(self, event):
        if not self.original_image:
            return

        steps = -1 * (event.delta // 120)
        self.zoom_level = max(1, self.zoom_level + steps * 0.1)

        zoomed_image = self.original_image.resize((int(self.original_image.width * self.zoom_level),
                                                   int(self.original_image.height * self.zoom_level)), Image.ANTIALIAS)
        self.display_image_on_canvas(zoomed_image)

        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    # Add other methods here
    def resize_canvas(self, event):
        total_width, total_height = event.width, event.height
        sidebar_width = self.sidebar.winfo_width()
        # bottom_height = bottom_frame.winfo_height()

        width = total_width - sidebar_width
        height = total_height

        # update the size of the canvas
        self.canvas.config(width=width, height=height)

        if self.original_image:
            # update the size of the displayed image based on the new canvas size
            resized_image = resize_image_to_fit_canvas(self.original_image, (width, height))
            self.display_image_on_canvas(resized_image)
        else:
            self.display_placeholder_text()

    def update_images(self, original_image, inpainted_image):
        self.original_image = original_image
        self.inpainted_image = inpainted_image

        if self.inpainted_image:
            self.overlay_image = Image.new("RGBA", self.inpainted_image.size, (0, 0, 0, 0))
            self.overlay_draw = ImageDraw.Draw(self.overlay_image)
            self.display_image_on_canvas(self.inpainted_image)
        else:
            self.display_placeholder_text()

    def display_image_on_canvas(self, img):
        canvas_image = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=canvas_image, tags="image")
        self.canvas.image = canvas_image

    def display_placeholder_text(self):
        self.canvas.create_text(400, 300, text="No Image Loaded", font=("Arial", 20, "bold"))

    def draw_original_on_inpainted(self, event):
        if not self.original_image or not self.inpainted_image:
            return

        x, y = event.x, event.y
        brush_size = 10

        x_offset, y_offset = self.center_image_on_canvas(self.inpainted_image)
        x_rel = x - x_offset
        y_rel = y - y_offset

        if 0 <= x_rel < self.inpainted_image.width and 0 <= y_rel < self.inpainted_image.height:
            x1, y1, x2, y2 = x_rel - brush_size, y_rel - brush_size, x_rel + brush_size, y_rel + brush_size
            original_patch = self.original_image.crop((x1, y1, x2, y2))
            original_patch_rgba = original_patch.copy().convert("RGBA")
            original_patch_no_alpha = original_patch_rgba.convert("RGBA")
            self.overlay_image.paste(original_patch_no_alpha, (x1, y1), original_patch_rgba.split()[3])
            temp_img = self.inpainted_image.copy()
            temp_img.alpha_composite(self.overlay_image)
            self.display_image_on_canvas(temp_img)

    def center_image_on_canvas(self, img):
        width, height = img.size
        x_offset = (self.canvas.winfo_width() - width) // 2
        y_offset = (self.canvas.winfo_height() - height) // 2
        return x_offset, y_offset

    def load_original_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", ".jpg .jpeg .png .bmp")])
        if file_path:
            self.original_image = Image.open(file_path).convert("RGBA")
        self.load_inpainted_button.config(state=tk.NORMAL)

    def load_inpainted_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", ".jpg .jpeg .png .bmp")])
        if file_path:
            inpainted_image = Image.open(file_path).convert("RGBA")
            self.inpainted_image = remove_whitespace(inpainted_image)
            self.inpainted_image = resize_image_to_fit_canvas(self.inpainted_image,
                                                              (self.canvas.winfo_width(), self.canvas.winfo_height()))
            self.original_image = resize_with_aspect_ratio_fill(self.original_image,
                                                                (self.inpainted_image.width,
                                                                 self.inpainted_image.height))
            self.overlay_image = Image.new("RGBA", self.inpainted_image.size, (0, 0, 0, 0))
            self.overlay_draw = ImageDraw.Draw(self.overlay_image)
            self.display_image_on_canvas(self.inpainted_image)
            self.canvas.delete("all")
        else:
            self.display_placeholder_text()
