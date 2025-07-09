"""
This script reads all .dv microscopy files from a specified input folder, extracts each channel,
saves them as individual TIFF files, and exports associated metadata to text files. The TIFF and
metadata files are saved in an 'output' directory parallel to the input folder.
"""
from aicsimageio import AICSImage
import tifffile
import os
from tqdm import tqdm


"""
Extracts each channel from a .dv file, saves it as a TIFF stack, and writes associated metadata to a .txt file.

Parameters:
    dv_path (str): Full path to the .dv file.
    output_dir (str): Directory where the TIFFs and metadata will be saved.
    verbose (bool): Whether to print progress messages.
"""
def extract_and_save_channels(dv_path, output_dir, verbose=True):
    # Load the image
    img = AICSImage(dv_path)

    # Shape is (T, C, Z, Y, X); drop time axis if it's 1
    data = img.get_image_data("CZYX", T=0)  # shape: (C, Z, Y, X)

    # Prepare output folder
    os.makedirs(output_dir, exist_ok=True)

    for channel_idx in range(data.shape[0]):
        channel_data = data[channel_idx]  # shape: (Z, Y, X)
        input_basename = os.path.splitext(os.path.basename(dv_path))[0]
        out_name = f"{input_basename}_channel_{channel_idx}.tif"
        out_path = os.path.join(output_dir, out_name)

        # Save as TIFF stack
        if verbose:
            print(f"Creating TIFF for {input_basename}")
        tifffile.imwrite(out_path, channel_data, imagej=True)
        if verbose:
            print(f"Saved channel {channel_idx} to {out_path}")

    metadata_txt_path = os.path.join(output_dir, f"{input_basename}_metadata.txt")
    with open(metadata_txt_path, 'w') as f:
        f.write(f"File: {dv_path}\n")
        f.write(f"Shape: {img.dims}\n")
        f.write(f"Physical pixel size (Z, Y, X): {img.physical_pixel_sizes}\n")
        f.write(f"Number of channels: {data.shape[0]}\n")
        try:
            channel_names = img.channel_names
            f.write(f"Channel names: {channel_names}\n")
        except AttributeError:
            pass
        f.write("\n" + "*" * 40 + "\nRaw metadata:\n")
        f.write(str(img.reader.metadata))
    if verbose:
        print(f"Saved metadata to {metadata_txt_path}")


"""
Iterates over all .dv files in the specified input folder, and processes them using extract_and_save_channels.

Parameters:
    path_to_input_folder (str): Folder containing .dv files.
    verbose (bool): Whether to print progress messages.
"""
def create_tiffs_from_dv(path_to_input_folder, verbose=True):
    if not os.path.isdir(path_to_input_folder):
        raise NotADirectoryError(f"Expected a directory path ending with '/input/', but got: {path_to_input_folder}")

    base_dir = os.path.dirname(path_to_input_folder)
    output_folder = os.path.join(base_dir, "output")
    os.makedirs(output_folder, exist_ok=True)

    # Process all .dv files in the input folder with progress bar
    for filename in tqdm(os.listdir(path_to_input_folder), desc="Processing .dv files"):
        if filename.endswith(".dv"):
            dv_path = os.path.join(path_to_input_folder, filename)
            extract_and_save_channels(dv_path, output_folder, verbose=verbose)


# Example usage
path_to_input_dvs = '/Users/frederic/Desktop/test_segmentation_cargo/input/'
create_tiffs_from_dv(path_to_input_dvs)
