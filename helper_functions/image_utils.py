"""
image_utils.py

Helper functions for microscopy image processing, including loading,
downsampling, basic metadata extraction, and Napari visualization.
"""

import os

# Image handling
from skimage import io
from PIL import Image

# Visualization
import napari




def load_image(image_path, verbose=False):
    """
    Load an image from a file path.

    Args:
        image_path (str): Path to image file.
        verbose (bool): If True, print image info.

    Returns:
        np.ndarray: Loaded image as array.
    """
    image = io.imread(image_path)
    if verbose:
        print(f'loading image from path {image_path}')
        print(f"Image shape: {image.shape}")
    return image



def view_with_napari(path_to_image, label, verbose = False):
    """
    Display an image in Napari viewer.

    Args:
        path_to_image (str): Path to image file.
        label (str): Name of the image layer.
        verbose (bool): If True, print path info.
    """
    if verbose:
        print(f'Viewing {path_to_image} with napari')
    image = io.imread(path_to_image)

    viewer = napari.Viewer()
    viewer.add_image(image, name=label, colormap='gray', blending='additive', visible=False)
    napari.run()



def get_basic_image_metadata(path_to_image):
    """
    Get basic metadata of an image file.

    Args:
        path_to_image (str): File path to image.

    Returns:
        dict: Contains filename, size, dimensions, and format.
    """
    info = {}

    if not os.path.isfile(path_to_image):
        raise FileNotFoundError(f"No such file: {path_to_image}")

    info['file_path'] = path_to_image
    info['file_name'] = os.path.basename(path_to_image)
    info['file_format'] = os.path.splitext(path_to_image)[-1].lower()
    info['file_size_kb'] = round(os.path.getsize(path_to_image) / 1024, 2)

    try:
        with Image.open(path_to_image) as img:
            info['width'], info['height'] = img.size
            info['channels'] = len(img.getbands())
            info['mode'] = img.mode
    except Exception as e:
        info['error'] = f"Could not open as image: {e}"

    return info




def generate_small_version_of_image(path_to_image, shrinking_factor=4, three_dimensions=False, save=False, verbose=False):
    """
    Downsample and optionally save a cropped image.

    Args:
        path_to_image (str): Path to image.
        shrinking_factor (int): Factor by which to reduce dimensions.
        three_dimensions (bool): Keep full 3D if True.
        save (bool): Whether to save the downsampled image.
        verbose (bool): Verbose output and Napari display.

    Returns:
        np.ndarray: Cropped and downsampled image.
    """
    if verbose:
        print(f'Generating small version of {path_to_image}')
        print(f'Shrinking image by {shrinking_factor}, 3D = {three_dimensions}')

    # Load image
    image = io.imread(path_to_image)

    # If the image is 3D and `three_dimensions` is False, convert to 2D by selecting the middle slice
    if not three_dimensions and len(image.shape) == 3:
        image = image[len(image) // 2]  # Take the middle slice

    # Compute new cropped dimensions
    height, width = image.shape[-2:]  # Take last two dimensions for cropping
    new_h, new_w = height // shrinking_factor, width // shrinking_factor

    # Crop the top-right corner
    cropped_image = image[..., :new_h, -new_w:]  # Keep all slices if 3D, else crop 2D

    if verbose:
        print(f'Original shape: {image.shape}, Cropped shape: {cropped_image.shape}')

    if save:
        # Extract directory and generate new filename with "_small" suffix
        directory = os.path.dirname(path_to_image)
        filename, ext = os.path.splitext(os.path.basename(path_to_image))
        new_filename = f"{filename}_small{ext}"
        new_path = os.path.join(directory, new_filename)

        # Save the cropped image
        io.imsave(new_path, cropped_image)
        if verbose:
            print(f'Saved small version at {new_path}')

    if verbose:
        viewer = napari.Viewer()
        viewer.add_image(image, name="Original Image", colormap='gray', blending='additive')
        viewer.add_image(cropped_image, name="Cropped Image", colormap='gray', blending='additive')
        napari.run()

    return cropped_image  # Return the processed image

