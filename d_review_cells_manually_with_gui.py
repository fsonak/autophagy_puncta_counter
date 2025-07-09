from helper_functions.image_utils import load_image
import os
import numpy as np
import napari
import subprocess
from skimage.segmentation import find_boundaries
from scipy.ndimage import binary_dilation
from datetime import datetime


def review_cells_with_napari(path_to_signal, path_to_mask, path_to_brightfield, output_dir=None, verbose=False,
                             exclude_border_cells=False):
    """
    Loads a signal image, a corresponding mask, and a brightfield image,
    displays them in Napari and allows the user to manually mark each cell as included or excluded by clicking on it. Exclusions are saved to a text file.

    Args:
        path_to_signal (str): File path to the signal image (e.g., fluorescence).
        path_to_mask (str): File path to the labeled mask image.
        path_to_brightfield (str): File path to the brightfield image.
        output_dir (str): Directory where the exclusion file will be saved.
        verbose (bool): If True, print debug and status information.
        exclude_border_cells (bool): If True, cells touching the image border are initially marked as excluded.

    Returns:
        str: Path to the exclusion text file saved on disk.
    """



    # loading signal, mask, and brightfield as nd.array
    signal = load_image(path_to_signal, verbose=True)
    mask = load_image(path_to_mask, verbose=True)
    brightfield = load_image(path_to_brightfield, verbose=True)

    # creating cell_review_exclusion txt file
    base_filename = os.path.splitext(os.path.basename(path_to_signal))[0]
    if output_dir is None:
        raise ValueError("No output_dir provided. Please specify a directory to save the exclusion file.")
    excluded_txt_path = os.path.join(output_dir, f"{base_filename}_cell_review_exclusion.txt")

    # Get number of cells
    n_cells = mask.max()

    exclusion_mask = np.zeros_like(mask, dtype=np.uint8)  # 2D mask
    boundary_overlay = np.zeros_like(mask, dtype=np.float32) # for boundary visualisation of excluded cells in napari

    if verbose:
        print(f' number of cells in mask: {n_cells} ')
        print(f"Started manual review GUI for {n_cells} cells...")

    # Check if exclusion file exists
    if os.path.exists(excluded_txt_path):
        with open(excluded_txt_path, 'r') as f:
            excluded = [line.strip().lower().endswith('true') for line in f if not line.startswith('#')]
        if verbose:
            print(f"Review file found and loaded from {excluded_txt_path}")
    else:
        excluded = [False] * n_cells
        if verbose:
            print(f"Review file not found; creating new exclusion file at {excluded_txt_path}")

    # Update exclusion list to add border cells if requested
    if exclude_border_cells:
        image_height, image_width = mask.shape
        for cell_id in range(1, n_cells + 1):
            cell_mask = (mask == cell_id)
            if np.any(cell_mask[0, :]) or np.any(cell_mask[-1, :]) or np.any(cell_mask[:, 0]) or np.any(cell_mask[:, -1]):
                excluded[cell_id - 1] = True

    # Create exclusion mask and overlay based on updated list
    for index, is_excluded in enumerate(excluded):
        if is_excluded:
            cell_id = index + 1
            cell_mask = (mask == cell_id)
            exclusion_mask[cell_mask] = 1
    excluded_boundary = find_boundaries(exclusion_mask > 0, mode='outer')
    thick_boundary = binary_dilation(excluded_boundary, iterations=3)
    boundary_overlay[...] = 0.0
    boundary_overlay[thick_boundary] = 1.0

    # Save current exclusion list to disk (either new or updated)
    with open(excluded_txt_path, 'w') as f:
        f.write(f"# Exclusion file for: {base_filename}\n")
        f.write(f"# Saved to: {excluded_txt_path}\n")
        f.write(f"# Created on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total cells: {n_cells}\n")
        f.write(f"# Format: cell_index, excluded\n")
        for idx, val in enumerate(excluded):
            f.write(f"{idx}, {val}\n")

    # Extend 2D mask into 3D to match signal
    if mask.ndim == 2 and signal.ndim == 3:
        if verbose:
            print(f"Input mask shape: {mask.shape} -> extend into 3D (make cylinder)")
        mask_3d = np.repeat(mask[np.newaxis, :, :], signal.shape[0], axis=0)
    else:
        mask_3d = mask
        if verbose:
            print(f'Input mask shape: {mask.shape}')


    current_index = 0

    # Start Napari viewer
    viewer = napari.Viewer()
    brightfield_layer = viewer.add_image(brightfield, name='Brightfield')
    signal_layer = viewer.add_image(signal, name='Signal')
    signal_layer.visible = False
    mask_layer = viewer.add_labels(mask_3d, name='Mask')
    mask_layer.visible = False
    exclusion_boundary_layer = viewer.add_image(boundary_overlay, name="Excluded Boundaries", colormap='red', opacity=1.0, blending='additive')

    def update_cell(index):
        nonlocal current_index
        current_index = index
        cell_id = index + 1
        cell_mask = (mask == cell_id)
        exclusion_mask[cell_mask] = 1 if excluded[index] else 0

        excluded_boundary = find_boundaries(exclusion_mask > 0, mode='outer')
        thick_boundary = binary_dilation(excluded_boundary, iterations=3)
        boundary_overlay[...] = 0.0
        boundary_overlay[thick_boundary] = 1.0
        exclusion_boundary_layer.data = boundary_overlay

    def on_mouse_click(viewer, event):
        if event.type == 'mouse_press' and event.button == 1:  # Left-click
            pos = np.round(viewer.cursor.position).astype(int)
            y, x = pos[-2], pos[-1]  # handles both 2D and 3D

            # Bounds check to not get error if clicked outside of image
            if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]:
                clicked_cell_id = mask[y, x]
                if clicked_cell_id > 0:
                    idx = clicked_cell_id - 1
                    # Toggle exclusion status for the clicked cell
                    excluded[idx] = not excluded[idx]
                    update_cell(idx)

    viewer.mouse_drag_callbacks.append(on_mouse_click)

    # Initialize the viewer with the first cell
    update_cell(0)
    signal_layer.contrast_limits = (0, np.max(signal) / 80)  # force the contrast limits on the brightfield image

    napari.run()

    # Save updated exclusion list after manual review
    with open(excluded_txt_path, 'w') as f:
        f.write(f"# Exclusion file for: {base_filename}\n")
        f.write(f"# Saved to: {excluded_txt_path}\n")
        f.write(f"# Created on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total cells: {n_cells}\n")
        f.write(f"# Format: cell_index, excluded\n")
        for idx, val in enumerate(excluded):
            f.write(f"{idx}, {val}\n")
    if verbose:
        print(f"Final exclusion list saved to {excluded_txt_path}")
        # opens the excluded txt file in standard txt editor for visualisation/ checking
        subprocess.run(['open', excluded_txt_path])

    return excluded_txt_path



####################

# #test running above functions
#
#
# path_to_signal = '/Users/frederic/Desktop/test/gui/signal_1_small.tif'
# path_to_mask = '/Users/frederic/Desktop/test/gui/widefield_1_small copy_cp_masks.png'
# path_to_brightfield = '/Users/frederic/Desktop/test/gui/widefield_1_small copy.tif'
# output_dir = '/Users/frederic/Desktop/test/gui/'
#
#
# review_cells_with_napari(path_to_signal = path_to_signal, path_to_mask=path_to_mask, path_to_brightfield=path_to_brightfield,
#                          output_dir=output_dir,verbose=True, exclude_border_cells=True)
