from cellpose import models
from cellpose.models import SizeModel
from skimage.io import imread, imsave
import numpy as np
import os
import time


def segment_2d_image_with_cellpose(input_brightfield_path, output_dir=None, model_type='cyto', diameter=65,
                                   channels=[0, 0], save_mask=True, verbose=True, z_handling='middle'):
    """
    Run 2D segmentation on an image using Cellpose.
    If 3D input, collapsed to 2D using mean projection.

    Parameters:
    ------------
    input_path : str
        Path to the input image

    output_path : str or None, optional
        If provided, the segmented mask will be saved to this path.
        If None, a default filename will be generated from the input path.

    model_type : str
        The Cellpose model type to use. Common choices: 'cyto', 'nuclei'.

    diameter : float or None, optional
        Estimated diameter of objects in the image. If None, Cellpose will auto-estimate.

    channels : list of int
        Specifies the image channels (e.g., [0, 0] for grayscale).

    save_mask : bool
        If True, the mask is saved to disk as a TIFF file.

    verbose : bool
        If True, prints progress messages and timing.

    Returns:
    --------
    masks : np.ndarray
        The segmentation mask returned by Cellpose (2D label image).
    output_path : str or None
        Full path where the mask was saved, or None if saving was disabled.
    """
    if verbose:
        print(f"Loading image from: {input_brightfield_path}")
    img = imread(input_brightfield_path)

    if img.ndim == 2:
        img_input = img
    elif img.ndim == 3:
        if z_handling == 'collapse':
            if verbose:
                print("3D image detected. Collapsing into 2D using mean projection.")
            img_input = img.mean(axis=0)
        elif z_handling == 'middle':
            if verbose:
                print("3D image detected. Using middle slice for segmentation.")
            img_input = img[img.shape[0] // 2]
        else:
            raise ValueError("Unsupported z_handling option. Use 'collapse' or 'middle'.")
    else:
        raise ValueError("Unsupported image shape for 2D segmentation.")

    model = models.Cellpose(model_type=model_type)

    if diameter is None:
        if verbose:
            print("No diameter provided. Estimating using SizeModel...")
        size_model = SizeModel(cp_model=model.cp, pretrained_size=model.pretrained_size)
        diameter = size_model.eval(img_input, channels=channels)[0]
        if verbose:
            print(f"Estimated diameter: {diameter:.2f}")

    if verbose:
        print("Running Cellpose segmentation...")
        start_time = time.time()
    masks, flows, styles, diams = model.eval(img_input, diameter=diameter, channels=channels)

    if output_dir is not None and os.path.isdir(output_dir):
        # Use base filename from input and save into output directory
        base_filename = os.path.splitext(os.path.basename(input_brightfield_path))[0]
        output_dir = os.path.join(output_dir, f"{base_filename}_mask.tif")
    elif output_dir is None and save_mask:
        base, _ = os.path.splitext(input_brightfield_path)
        output_dir = base + "_mask.tif"

    if save_mask:
        imsave(output_dir, masks.astype(np.uint16))
        if verbose:
            print(f"Segmentation mask saved to: {output_dir}")

    if verbose:
        elapsed = time.time() - start_time
        print(f"Segmentation completed in {elapsed:.2f} seconds.")

    return masks, output_dir
