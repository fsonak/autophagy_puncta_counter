import time
start = time.time()


import sys
import os

# Determine base path depending on whether we're in a PyInstaller bundle
if getattr(sys, 'frozen', False):
    # PyInstaller sets this when running as a bundled app
    base_path = sys._MEIPASS
else:
    # Running from source
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Ensure bundled folders like 'pipeline' and 'helper_functions' are discoverable
if base_path not in sys.path:
    sys.path.insert(0, base_path)

# Now safe to import your own modules
# PyQt5
from PyQt5.QtWidgets import QApplication

# Your modules
from pipeline.c_image_segmentation import segment_2d_image_with_cellpose
# takes 80s
from pipeline.d_review_cells_manually_with_gui import review_cells_with_napari
# takes 80s
from helper_functions.gui_helper_functions import pick_file_paths, SplashScreen, resource_path
# takes 80s
from pipeline.e_manual_blob_annotation_gui_tool import manual_blob_annotation_gui
#takes 80s
app = QApplication(sys.argv)

print(f'done importing all')


LOGO_PATH = resource_path("assets/software_logo.png")
print(LOGO_PATH)

# Show splash screen modally before file picker
splash = SplashScreen(LOGO_PATH, duration=3000)
splash.exec_()

# Pick files via GUI
bf, sig, out = pick_file_paths()

# Run pipeline
mask, mask_path = segment_2d_image_with_cellpose(bf, out, save_mask=True)
excluded = review_cells_with_napari(sig, mask_path, bf, out)
manual_blob_annotation_gui(sig, bf, out)


#TODO the imports all take quite long. do they maybe import the same thing over and over? make it faster!