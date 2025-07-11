# Autophagy Puncta Counter

A Python-based graphical tool to segment, review, and annotate autophagy-related puncta in microscopy images of yeast cells.

This tool combines classical image processing, deep learning (via Cellpose), and manual inspection in a user-friendly Napari-based GUI — with a focus on 2D image slices from 3D stacks.

## Features

- **Segmentation** of cell boundaries using Cellpose  
- **Manual review** of segmented masks in Napari  
- **Blob annotation** based on intensity thresholds and manual inspection  
- Includes example images for testing (functional autophagy signal)

## Quick Start

#Clone the repository

git clone https://github.com/fsonak/autophagy_puncta_counter.git

cd autophagy_puncta_counter

#Create and activate the environment (recommended) **This environment has been tested on macOS Sonoma (ARM64, M1). For Intel or Windows/Linux, some packages may need to be reinstalled manually (e.g. ffmpeg, qt, imagecodecs).**

conda env create -f environment.yml

conda activate autophagy_gui_env

#Run the GUI

python scripts/create_blob_annotatiations_fully_gui.py



#Folder Structure:

autophagy_puncta_counter/

├── scripts/                          # Launch scripts

│   └── create_blob_annotatiations_fully_gui.py

├── pipeline/                         # Image processing pipeline

├── helper_functions/                # GUI + I/O helpers

├── assets/                          # Logo etc.

├── test_files/                      # Example images & outputs

├── environment.yml                  # Conda environment file

└── README.md


## Citation

If you use this tool in your research or publication, please consider citing it as:

Frédéric Sonak (2025). *Autophagy Puncta Counter: A Napari-based tool for image-guided segmentation and annotation of autophagosomes in yeast microscopy data*. GitHub repository: https://github.com/fsonak/autophagy_puncta_counter

BibTeX:

@misc{sonak2025autophagy,
  author       = {Frédéric Sonak},
  title        = {Autophagy Puncta Counter: A Napari-based tool for image-guided segmentation and annotation of autophagosomes in yeast microscopy data},
  year         = {2025},
  howpublished = {\url{https://github.com/fsonak/autophagy_puncta_counter}}
}
