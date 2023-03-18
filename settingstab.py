import tkinter as tk
import os


class SettingsTab:
    def __init__(self, tab):
        self.tab = tab

        self.frame = tk.Frame(self.tab)
        self.frame.pack(padx=20, pady=20)

        self.generate_label = tk.Label(self.frame, text="Diffuser Model for Generate Tab:")
        self.generate_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 10))

        self.generate_entry = tk.Entry(self.frame)
        self.generate_entry.set(os.environ.get("STABILITYSTUDIO_GENERATE_MODEL", ""))
        self.generate_entry.grid(row=0, column=1, pady=(0, 10))

        self.upscale_label = tk.Label(self.frame, text="Diffuser Model for Upscale Tab:")
        self.upscale_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 10))

        self.upscale_entry = tk.Entry(self.frame)
        self.upscale_entry.set(os.environ.get("STABILITYSTUDIO_UPSCALE_MODEL", ""))
        self.upscale_entry.grid(row=1, column=1)

        self.save_button = tk.Button(self.frame, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=2, column=0, columnspan=2, pady=(20, 0))

        # Load saved settings
        self.generate_entry.insert(0, os.environ.get("STABILITYSTUDIO_GENERATE_MODEL", ""))
        self.upscale_entry.insert(0, os.environ.get("STABILITYSTUDIO_UPSCALE_MODEL", ""))

    def save_settings(self):
        generate_model = self.generate_entry.get()
        upscale_model = self.upscale_entry.get()

        os.environ["STABILITYSTUDIO_GENERATE_MODEL"] = generate_model
        os.environ["STABILITYSTUDIO_UPSCALE_MODEL"] = upscale_model
