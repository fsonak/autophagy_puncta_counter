import napari
from magicgui import magicgui
from magicgui.widgets import CheckBox
import pandas as pd
import os
from qtpy.QtWidgets import QMessageBox
from helper_functions.image_utils import load_image
from blob_detection_functions import detect_blobs, suppress_close_blobs_by_intensity, suppress_blobs_by_bridge_intensity
import numpy as np
import atexit
from helper_functions.file_handling_helpers import resolve_output_path_with_user_prompt



def manual_blob_annotation_gui(path_to_signal, path_to_brightfield, output_directory,
                               min_sigma=1, max_sigma=5, num_sigma=6,
                               threshold_mode='percentile', threshold_value=99.5,
                               show_all_detected_blobs=True, verbose=True):
    '''
    Launches an interactive Napari-based GUI for manual correction and annotation of automatically detected blobs in 3D microscopy images.

    **Features:**
    - Loads signal and brightfield images.
    - Detects blobs using Laplacian of Gaussian and filters them by proximity and intensity bridges.
    - Displays raw image, brightfield, and detected blobs in a Napari viewer.
    - Provides toggleable blob coordinate labels.
    - Displays contrast limits in the image corner.
    - Allows manual correction (add/remove blobs) and annotation via comments.
    - Exports corrected results as a CSV with origin, status, and optional comment.
    - Automatically saves results on exit.
    '''

    # --- Load images ---
    image = load_image(path_to_signal)
    brightfield = load_image(path_to_brightfield)

    # --- Detect and Filter Blobs ---
    # detect blobs using a percentile based threshold for the LoG
    all_detected_blobs = detect_blobs(image, min_sigma=min_sigma, max_sigma=max_sigma, num_sigma=num_sigma,
                                      threshold_mode=threshold_mode, threshold_value=threshold_value, verbose=verbose)

    # remove close blobs
    blobs_after_removing_close_ones = suppress_close_blobs_by_intensity(all_detected_blobs, verbose=verbose)

    # remove blobs where intensity between them doesn't drop significantly
    blobs_after_supressing_bridge = suppress_blobs_by_bridge_intensity(blobs_after_removing_close_ones, image, verbose=verbose)

    original_detected_blobs = blobs_after_supressing_bridge[:, :3].copy()

    # --- Setup Napari Viewer and Display Layers ---
    viewer = napari.Viewer()
    image_layer = viewer.add_image(image, name='Raw Image', colormap='green')
    brightfield_layer = viewer.add_image(brightfield, name='Brightfield', colormap='gray', blending='additive')

    viewer.add_points(blobs_after_supressing_bridge[:, :3], name='Filtered Blobs', size=20, face_color='red',
                      symbol='ring', border_width=2, border_width_is_relative=False)
    # Add per-blob coordinate labels to the Filtered Blobs layer
    layer = viewer.layers['Filtered Blobs']
    layer.text = {
        'text': [f"{tuple(np.round(pt).astype(int))}" for pt in blobs_after_supressing_bridge[:, :3]],
        'anchor': 'upper_left',
        'translation': [0, 0, 0],
        'size': 12,
        'color': 'white',
        'visible': True,
    }

    # Function to update blob labels dynamically
    def update_blob_labels(event=None):
        if 'Filtered Blobs' in viewer.layers:
            layer = viewer.layers['Filtered Blobs']
            layer.text = {
                'text': [f"{tuple(np.round(pt).astype(int))}" for pt in layer.data],
                'anchor': 'upper_left',
                'translation': [0, 0, 0],
                'size': 12,
                'color': 'white',
                'visible': label_toggle_checkbox.value,
            }

    # Connect to data event of Filtered Blobs layer
    viewer.layers['Filtered Blobs'].events.data.connect(update_blob_labels)

    # Create checkbox widget manually
    label_toggle_checkbox = CheckBox(value=False, text="Show Blob Locations (z, x, y)")

    # Add logic: update label visibility on checkbox change
    def on_checkbox_change(value):
        layer = viewer.layers['Filtered Blobs'] if 'Filtered Blobs' in viewer.layers else None
        if layer:
            layer.text.visible = value
        update_blob_labels()

    label_toggle_checkbox.changed.connect(on_checkbox_change)

    # Add to GUI
    viewer.window.add_dock_widget(label_toggle_checkbox, name="Show Blob ID", area="right")

    if show_all_detected_blobs:
        viewer.add_points(all_detected_blobs[:, :3], name='All Detected Blobs', size=20, face_color='pink',
                          symbol='ring', border_width=2, border_width_is_relative=False)

    # show signal contrast limits inside of image
    def update_contrast_overlay():
        viewer.text_overlay.visible = True
        signal_limits = tuple(int(x) for x in image_layer.contrast_limits)
        brightfield_limits = tuple(int(x) for x in brightfield_layer.contrast_limits)
        viewer.text_overlay.color = 'white'
        viewer.text_overlay.text = (
            f"Signal contrast: {signal_limits}\n"
            f"Brightfield contrast: {brightfield_limits}"
        )

    # write contrast levels into right lower corner of image and update when changed
    def on_image_contrast_change(event): update_contrast_overlay()
    def on_brightfield_contrast_change(event): update_contrast_overlay()

    image_layer.events.contrast_limits.connect(on_image_contrast_change)
    brightfield_layer.events.contrast_limits.connect(on_brightfield_contrast_change)
    update_contrast_overlay()

    # --- Export corrected annotations as ground truth CSV ---
    @magicgui(call_button="Export Ground Truth CSV")
    def export_ground_truth():
        layer_name = 'Filtered Blobs' if 'Filtered Blobs' in viewer.layers else (
            'Puncta' if 'Puncta' in viewer.layers else None
        )
        if layer_name is None:
            print("No layer named 'Filtered Blobs' or 'Puncta' found for export.")
            QMessageBox.warning(None, "Export Failed", "No blob layer found to export.")
            return

        points_layer = viewer.layers[layer_name]
        current_data = points_layer.data  # shape (N, 3)
        original_data = original_detected_blobs  # from outer scope

        used = np.zeros(len(current_data), dtype=bool)
        labels = []
        origins = []
        statuses = []

        # Tolerance for considering two points the same
        atol = 1.0

        # Match original detected blobs to current layer
        for orig in original_data:
            match_found = False
            for i, curr in enumerate(current_data):
                if not used[i] and np.allclose(orig, curr, atol=atol):
                    used[i] = True
                    match_found = True
                    labels.append("true_positive")
                    origins.append("detected")
                    statuses.append("kept")
                    break
            if not match_found:
                labels.append("false_positive")
                origins.append("detected")
                statuses.append("removed")

        # Remaining unmatched current points are manual additions
        for i, curr in enumerate(current_data):
            if not used[i]:
                labels.append("false_negative")
                origins.append("manual")
                statuses.append("added")

        # Collect coordinates: start with matched original blobs (even removed)
        coords = list(original_data) + [curr for i, curr in enumerate(current_data) if not used[i]]

        # Build dataframe
        df = pd.DataFrame(coords, columns=["z", "y", "x"])
        df["origin"] = origins
        df["status"] = statuses
        df["label_for_ml"] = labels

        # Fill in comments by matching coordinates
        comments_full = []
        comment_dict = points_layer.metadata.get('comments', {})
        for coord in coords:
            rounded_coord = tuple(np.round(coord, 2))
            comments_full.append(comment_dict.get(rounded_coord, ""))

        df["comment"] = comments_full

        # Build unique output filename based on signal image name
        signal_filename = os.path.splitext(os.path.basename(path_to_signal))[0]
        output_filename = f"{signal_filename}_manually_checked_blob_annotations.csv"
        output_path = os.path.join(output_directory, output_filename)

        output_path = resolve_output_path_with_user_prompt(output_path, output_filename)
        if output_path is None:
            return

        df.to_csv(output_path, index=False)
        print(f"Exported {len(df)} blobs to {output_path}")
        QMessageBox.information(None, "Export Successful", f"Exported {len(df)} blobs to:\n{output_path}")

    # for adding comments to each detected punctum
    @magicgui(call_button="Update Comment")
    def update_comment(comment: str = ""):
        points_layer = viewer.layers['Filtered Blobs'] if 'Filtered Blobs' in viewer.layers else (
            viewer.layers['Puncta'] if 'Puncta' in viewer.layers else None
        )
        if points_layer is None:
            print("No suitable blob layer found for adding comment.")
            QMessageBox.warning(None, "Update Failed", "No layer found to update comment.")
            return
        selected = list(points_layer.selected_data)
        if not selected:
            print("No point selected.")
            return
        index = selected[0]
        coord = tuple(np.round(points_layer.data[index], 2))  # Round to 2 decimals to ensure consistency
        if 'comments' not in points_layer.metadata or not isinstance(points_layer.metadata['comments'], dict):
            points_layer.metadata['comments'] = {}
        points_layer.metadata['comments'][coord] = comment
        print(f"Updated comment for point {coord}: {comment}")
        QMessageBox.information(None, "Comment Updated", f"Updated comment for point {coord}.")

    # --- Add GUI widgets ---
    viewer.window.add_dock_widget(export_ground_truth, area="right")
    viewer.window.add_dock_widget(update_comment, area="right")

    # export ground truth automatically BEFORE closing the viewer (Idiotensicher :-)  )
    atexit.register(lambda: export_ground_truth())

    napari.run()

    return viewer


# test above function


# manual_blob_annotation_gui(
#         path_to_signal='/Users/frederic/Desktop/test_segmentation_cargo/input/output/240215_GAC8_02_R3D_D3D_channel_0_membrane.tif',
#         path_to_brightfield='/Users/frederic/Desktop/test_segmentation_cargo/input/output/240215_GAC8_02_R3D_D3D_channel_2_brightfield.tif',
#         output_directory="/Users/frederic/Desktop/Files_for_ground_truth_blob_count/output", show_all_detected_blobs=False,
#     )
