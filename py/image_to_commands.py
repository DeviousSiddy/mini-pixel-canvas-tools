import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from PIL import Image, ImageTk, ImageFilter
import os

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PALETTE_FILE = os.path.join(PROJECT_ROOT, "pallette.json")
CANVAS_SIZE = 32
PREVIEW_PIXEL_SIZE = 10
SUPER_SAMPLE_FACTOR = 10 # Process at 10x resolution (320x320) then scale down

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
        # Prepare the palette for dithering
        self._prepare_dithering_palette()

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
        """Loads the palette and stores RGB tuples."""
        try:
            with open(PALETTE_FILE, 'r') as f:
                data = json.load(f)
                # Store as { "00": {"rgb": (r,g,b)}, ... }
                return {key: {"rgb": self._hex_to_rgb(value['hex'])} for key, value in data.items()}
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def _prepare_dithering_palette(self):
        """Prepares the palette for use with Pillow's quantize method."""
        # Sort keys numerically to ensure index from quantize matches our key order
        self.sorted_palette_keys = sorted(self.palette_data.keys(), key=int)

        # Create a flat palette list [r,g,b, r,g,b, ...] for Pillow
        flat_palette = []
        for key in self.sorted_palette_keys:
            flat_palette.extend(self.palette_data[key]["rgb"])

        # The palette must be 768 values (256 colors * 3 channels).
        # Pad with black if our palette is smaller.
        if len(flat_palette) < 256 * 3:
            flat_palette.extend([0, 0, 0] * (256 - len(self.sorted_palette_keys)))

        # Create a 1x1 palette image that Pillow can use for quantization
        self.dither_palette_img = Image.new("P", (1, 1))
        self.dither_palette_img.putpalette(flat_palette)

        # Find the darkest and lightest colors in the palette for line art preservation
        self.darkest_color_key = "00"
        self.lightest_color_key = "00"
        min_lum = 256
        max_lum = -1
        for key, value in self.palette_data.items():
            r, g, b = value["rgb"]
            # Using a simple luminance calculation
            luminance = 0.299*r + 0.587*g + 0.114*b
            if luminance < min_lum:
                min_lum = luminance
                self.darkest_color_key = key

    def _find_closest_color(self, rgb_tuple):
        """Finds the closest color in the palette using Euclidean distance in RGB space."""
        min_dist_sq = float('inf')
        best_key = "00"
        r1, g1, b1 = rgb_tuple

        for key, palette_values in self.palette_data.items():
            r2, g2, b2 = palette_values["rgb"]
            # Standard Euclidean distance in RGB space. Much faster than LAB.
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

            # 1. Open image
            img = Image.open(file_path)

            # 2. Crop image to a 1:1 aspect ratio from the center, preserving the shortest side.
            width, height = img.size
            if width != height:
                short_side = min(width, height)
                left = (width - short_side) / 2
                top = (height - short_side) / 2
                right = (width + short_side) / 2
                bottom = (height + short_side) / 2
                img = img.crop((left, top, right, bottom))

            # 3. Supersample: Resize to a much larger canvas for high-resolution processing.
            # We use LANCZOS for a high-quality upscale.
            super_sample_size = CANVAS_SIZE * SUPER_SAMPLE_FACTOR
            high_res_img = img.resize((super_sample_size, super_sample_size), Image.Resampling.LANCZOS).convert("RGBA")

            # 4. Separate the alpha channel to use as a definitive silhouette mask later
            high_res_alpha_mask = high_res_img.getchannel('A')

            # --- 5. Create the "Color Fill" Layer at high resolution ---
            high_res_color_fill_paletted = high_res_img.convert("RGB").quantize(
                palette=self.dither_palette_img,
                dither=Image.Dither.FLOYDSTEINBERG
            )
            high_res_color_fill_rgb = high_res_color_fill_paletted.convert("RGB").filter(ImageFilter.MedianFilter(size=11))

            # --- 6. Create the "Line Art" Layer at high resolution ---
            # Use CONTOUR filter on a grayscale version to find edges
            high_res_line_art_mask = high_res_img.convert('L').filter(ImageFilter.CONTOUR)
            # Invert the mask: lines are black (0), so we want to use them as the mask.
            high_res_line_art_mask = high_res_line_art_mask.point(lambda p: 255 if p < 128 else 0)

            # --- 7. Combine Layers at high resolution ---
            # Create a solid layer of the darkest palette color for the lines
            darkest_color_rgb = self.palette_data[self.darkest_color_key]["rgb"]
            line_art_color_layer = Image.new("RGB", high_res_img.size, darkest_color_rgb)
            # Paste the line art over the color fill
            high_res_color_fill_rgb.paste(line_art_color_layer, mask=high_res_line_art_mask)

            # --- 8. Final Assembly at high resolution ---
            high_res_final_img = high_res_color_fill_rgb.convert("RGBA")
            high_res_final_img.putalpha(high_res_alpha_mask)

            # --- 9. Denoise the supersampled image ---
            # Apply a Median Filter to the final high-resolution image before downscaling.
            # This is effective at removing small artifacts from dithering and line art
            # without causing the "blobby" effect of filtering the final 32x32 image.
            high_res_final_img = high_res_final_img.filter(ImageFilter.RankFilter(size=5, rank=20))

            # --- 10. Scale the high-res processed image down to the final canvas size ---
            # This is the final step of supersampling, averaging the results.
            final_img = high_res_final_img.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.NEAREST)
            
            # --- 11. Generate Commands and Draw Preview from the final 32x32 image ---
            self.preview_canvas.delete("all")
            self.commands_text.delete("1.0", tk.END)
            
            commands = []
            final_pixels = final_img.load()

            for y in range(CANVAS_SIZE):
                for x in range(CANVAS_SIZE):
                    r, g, b, a = final_pixels[x, y]
                    if a < 128: # Check the final, masked alpha value
                        continue

                    # Find the closest color key for the final pixel's RGB value
                    closest_color_key = self._find_closest_color((r, g, b))
                    commands.append(f"!pixel {x},{y},{closest_color_key}")

                    # Draw preview pixel
                    palette_rgb = self.palette_data[closest_color_key]["rgb"]
                    color_hex = f"#{palette_rgb[0]:02x}{palette_rgb[1]:02x}{palette_rgb[2]:02x}"
                    self.preview_canvas.create_rectangle(
                        x * PREVIEW_PIXEL_SIZE, y * PREVIEW_PIXEL_SIZE,
                        (x + 1) * PREVIEW_PIXEL_SIZE, (y + 1) * PREVIEW_PIXEL_SIZE,
                        fill=color_hex, outline=""
                    )

            # 12. Display commands
            self.commands_text.insert("1.0", "\n".join(commands))
            self.status_label.config(text=f"Done! {len(commands)} commands generated.")

        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred while processing the image:\n{e}")
            self.status_label.config(text="Error. Please try another image.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToCommandsApp(root)
    root.mainloop()
