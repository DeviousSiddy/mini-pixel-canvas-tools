import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from PIL import Image, ImageTk
import os

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PALETTE_FILE = os.path.join(PROJECT_ROOT, "pallette.json")
CANVAS_SIZE = 32
PREVIEW_PIXEL_SIZE = 10

class ImageToCommandsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to Pixel Commands Converter")
        self.root.resizable(False, False)

        # --- Load Data ---
        self.palette_rgb = self._load_palette()
        if not self.palette_rgb:
            messagebox.showerror("Error", f"Could not load or parse '{PALETTE_FILE}'.")
            self.root.destroy()
            return

        # --- UI Setup ---
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # Left side: Controls and Preview
        left_frame = ttk.Frame(self.main_frame, padding="5")
        left_frame.grid(row=0, column=0, sticky="ns")

        self.select_button = ttk.Button(left_frame, text="Select Image", command=self._select_and_process_image)
        self.select_button.pack(pady=10, fill='x')

        preview_label = ttk.Label(left_frame, text="32x32 Preview:")
        preview_label.pack(pady=(10, 2))

        self.preview_canvas = tk.Canvas(
            left_frame,
            width=CANVAS_SIZE * PREVIEW_PIXEL_SIZE,
            height=CANVAS_SIZE * PREVIEW_PIXEL_SIZE,
            bg="#333"
        )
        self.preview_canvas.pack()

        # Right side: Commands Output
        right_frame = ttk.Frame(self.main_frame, padding="5")
        right_frame.grid(row=0, column=1, sticky="nsew")

        commands_label = ttk.Label(right_frame, text="Generated Commands:")
        commands_label.pack(anchor='w')

        self.commands_text = tk.Text(right_frame, width=40, height=25, wrap=tk.WORD)
        self.commands_text.pack(fill='both', expand=True)

        self.status_label = ttk.Label(self.main_frame, text="Ready. Select an image to begin.")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _hex_to_rgb(self, hex_color):
        """Converts a hex color string like #RRGGBB to an (R, G, B) tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _load_palette(self):
        """Loads the palette and converts hex colors to RGB tuples for distance calculation."""
        try:
            with open(PALETTE_FILE, 'r') as f:
                data = json.load(f)
                # Store as { "00": (r, g, b), ... }
                return {key: self._hex_to_rgb(value['hex']) for key, value in data.items()}
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def _find_closest_color(self, rgb_tuple):
        """Finds the closest color in the palette using Euclidean distance in RGB space."""
        min_dist_sq = float('inf')
        best_key = "00"
        r1, g1, b1 = rgb_tuple

        for key, palette_rgb in self.palette_rgb.items():
            r2, g2, b2 = palette_rgb
            dist_sq = (r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_key = key
        return best_key

    def _select_and_process_image(self):
        """Opens a file dialog and triggers the image processing."""
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            self.status_label.config(text=f"Processing '{os.path.basename(file_path)}'...")
            self.root.update_idletasks()

            # 1. Open and convert to RGB
            img = Image.open(file_path).convert("RGB")

            # 2. Resize while maintaining aspect ratio, then crop to a square
            w, h = img.size
            if w > h:
                new_h = CANVAS_SIZE
                new_w = int(w * (new_h / h))
            else:
                new_w = CANVAS_SIZE
                new_h = int(h * (new_w / w))
            
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            left = (new_w - CANVAS_SIZE) / 2
            top = (new_h - CANVAS_SIZE) / 2
            right = (new_w + CANVAS_SIZE) / 2
            bottom = (new_h + CANVAS_SIZE) / 2

            final_img = resized_img.crop((left, top, right, bottom))

            # 3. Generate commands and draw preview
            self.preview_canvas.delete("all")
            self.commands_text.delete("1.0", tk.END)
            
            commands = []
            pixels = final_img.load()
            for y in range(CANVAS_SIZE):
                for x in range(CANVAS_SIZE):
                    pixel_rgb = pixels[x, y]
                    closest_color_key = self._find_closest_color(pixel_rgb)
                    
                    # Add command to list
                    commands.append(f"!pixel {x},{y},{closest_color_key}")

                    # Draw preview pixel
                    palette_rgb = self.palette_rgb[closest_color_key]
                    color_hex = f"#{palette_rgb[0]:02x}{palette_rgb[1]:02x}{palette_rgb[2]:02x}"
                    self.preview_canvas.create_rectangle(
                        x * PREVIEW_PIXEL_SIZE, y * PREVIEW_PIXEL_SIZE,
                        (x + 1) * PREVIEW_PIXEL_SIZE, (y + 1) * PREVIEW_PIXEL_SIZE,
                        fill=color_hex, outline=""
                    )

            # 4. Display commands
            self.commands_text.insert("1.0", "\n".join(commands))
            self.status_label.config(text=f"Done! {len(commands)} commands generated.")

        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred while processing the image:\n{e}")
            self.status_label.config(text="Error. Please try another image.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToCommandsApp(root)
    root.mainloop()
