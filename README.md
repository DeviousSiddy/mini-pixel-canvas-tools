# Mini Pixel Canvas - Utility Scripts

A collection of Python tools to help you create artwork for collaborative pixel art projects. These scripts allow you to generate color guides and convert images into a series of chat commands.

 <!-- It's a good idea to add a screenshot of your canvas here! -->

## Features

*   **Image to Commands Converter**: Launches a GUI to convert any image into a list of `!pixel x,y,##` commands, ready to be used in chat.
*   **PDF Color Key Generator**: Creates a professional, printable PDF guide from a `pallette.json` file.

## Setup and Installation

### Prerequisites

*   Python 3.8 or newer.

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/DeviousSiddy/mini-pixel-canvas-tools.git
    cd mini-pixel-canvas-tools
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Customization

You can customize the color palette by editing the `pallette.json` file. The format is a dictionary where the key is the two-digit color number (as a string) and the value contains the color's name and hex code.

**Example `pallette.json` entry:**
```json
{
    "00": {
        "name": "White",
        "hex": "#FFFFFF"
    },
    "01": {
        "name": "Light Gray",
        "hex": "#C0C0C0"
    }
}
```
After modifying `pallette.json`, remember to run the `generate_color_key.py` script again to update your PDF.

## Usage

These scripts should be run from the project's root directory.

### Convert Image to Commands

This tool launches a graphical interface that lets you select an image. It will resize the image to 32x32, match the colors to your palette, and generate a list of `!pixel` commands.

**To run:**
```bash
python py/image_to_commands.py
```

### Generate PDF Color Key

This script creates a `color_key.pdf` file based on the colors defined in `pallette.json`. This PDF is great for sharing with your community so they know which color numbers to use.

**To run:**
```bash
python py/generate_color_key.py
```
