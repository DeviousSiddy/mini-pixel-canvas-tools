# Mini Pixel Canvas - Utility Scripts

A collection of Python tools to help you create artwork for collaborative pixel art projects. These scripts allow you to generate color guides and convert images into a series of chat commands.

## Canvas Usage

You can use the command '!pixel x,y,##' in any of the following:
*Discord: https://discord.gg/gXKxKvHEAA (any channel (where appropriate) but feedback in #mini-pixel-canvas channel)
*Youtube: https://www.youtube.com/@DeviousSiddy (when live, in livechat)
*Twitch: https://www.twitch.tv/devioussiddy (in chat)

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

## Usage

These scripts should be run from the project's root directory.

### Convert Image to Commands

This tool launches a graphical interface that lets you select an image. It will resize the image to 32x32, match the colors to your palette, and generate a list of `!pixel` commands.

**To run:**
```bash
python py/image_to_commands.py
```


