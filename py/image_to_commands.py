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
        self.palette_data = self._load_palette()
        if not self.palette_data:
            messagebox.showerror("Error", f"Could not load or parse '{PALETTE_FILE}'.")
            self.root.destroy()
            return
        # Pre-calculate LAB values for the palette for efficiency
        self._precalculate_lab_palette()

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

    def _rgb_to_lab(self, rgb_tuple):
        """Converts an (R, G, B) tuple to a perceptually uniform CIE-L*a*b* tuple."""
        r, g, b = [x / 255.0 for x in rgb_tuple]

        # Gamma correction (sRGB to linear RGB)
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92

        # Convert to XYZ color space
        x = (r * 0.4124 + g * 0.3576 + b * 0.1805) * 100
        y = (r * 0.2126 + g * 0.7152 + b * 0.0722) * 100
        z = (r * 0.0193 + g * 0.1192 + b * 0.9505) * 100

        # Convert XYZ to Lab (using D65 illuminant reference)
        ref_x, ref_y, ref_z = 95.047, 100.0, 108.883
        x /= ref_x
        y /= ref_y
        z /= ref_z

        # Transformation
        x = x ** (1/3) if x > 0.008856 else (7.787 * x) + (16 / 116)
        y = y ** (1/3) if y > 0.008856 else (7.787 * y) + (16 / 116)
        z = z ** (1/3) if z > 0.008856 else (7.787 * z) + (16 / 116)

        l = (116 * y) - 16
        a = 500 * (x - y)
        b_lab = 200 * (y - z)

        return l, a, b_lab

    def _load_palette(self):
        """Loads the palette and stores RGB tuples."""
        try:
            with open(PALETTE_FILE, 'r') as f:
                data = json.load(f)
                # Store as { "00": {"rgb": (r,g,b)}, ... }
                return {key: {"rgb": self._hex_to_rgb(value['hex'])} for key, value in data.items()}
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def _precalculate_lab_palette(self):
        """Converts all palette RGB values to LAB and stores them."""
        for key, values in self.palette_data.items():
            values["lab"] = self._rgb_to_lab(values["rgb"])

    def _find_closest_color(self, rgb_tuple):
        """Finds the closest color in the palette using Euclidean distance in CIE-L*a*b* space."""
        min_dist_sq = float('inf')
        best_key = "00"
        # Convert the input pixel's color to LAB space for comparison
        l1, a1, b1 = self._rgb_to_lab(rgb_tuple)

        for key, palette_values in self.palette_data.items():
            l2, a2, b2 = palette_values["lab"]
            # Standard Euclidean distance, but in the perceptually uniform LAB space
            dist_sq = (l1 - l2)**2 + (a1 - a2)**2 + (b1 - b2)**2
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

            # 2. Resize in two steps for better quality: original -> 64x64 -> 32x32
            INTERMEDIATE_SIZE = 128
            
            # Step 2a: Resize to fit within the intermediate size (64x64)
            w, h = img.size
            if w > h:
                new_h = INTERMEDIATE_SIZE
                new_w = int(w * (new_h / h))
            else:
                new_w = INTERMEDIATE_SIZE
                new_h = int(h * (new_w / w))
            
            # High-quality downsample to intermediate size
            resized_img_64 = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Crop to a square 64x64
            left = (new_w - INTERMEDIATE_SIZE) / 2
            top = (new_h - INTERMEDIATE_SIZE) / 2
            right = (new_w + INTERMEDIATE_SIZE) / 2
            bottom = (new_h + INTERMEDIATE_SIZE) / 2
            cropped_img_64 = resized_img_64.crop((left, top, right, bottom))

            # Step 2b: Downsample from 64x64 to the final 32x32 canvas size
            final_img = cropped_img_64.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)

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
                    palette_rgb = self.palette_data[closest_color_key]["rgb"]
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
