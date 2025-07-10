import numpy as np
from skimage.feature import blob_log

def detect_blobs(image, min_sigma=1, max_sigma=3, num_sigma=6,
                 threshold_mode='percentile', threshold_value=99.5, verbose=False):
    """
    Detect 2D blobs in each Z slice of a 3D image using Laplacian of Gaussian.
    Returns an array of shape (N, 5): z, y, x, sigma, intensity
    """
    # Compute threshold for blob_log
    if threshold_mode == 'percentile':
        calculated_threshold = np.percentile(image, threshold_value)
        auto_threshold = calculated_threshold / image.max()
        if verbose:
            print(f"[detect_blobs] Threshold set to {calculated_threshold:.2f} from {threshold_value} percentile.")
    elif threshold_mode == 'absolute':
        calculated_threshold = threshold_value
        auto_threshold = calculated_threshold / image.max()
        if verbose:
            print(f"[detect_blobs] Threshold set to fixed value: {threshold_value}")
    else:
        raise ValueError("threshold_mode must be 'percentile' or 'absolute'")

    blobs_all = []
    for z in range(image.shape[0]):
        slice_ = image[z]
        blobs2d = blob_log(slice_, min_sigma=min_sigma, max_sigma=max_sigma,
                           num_sigma=num_sigma, threshold=auto_threshold)
        for blob in blobs2d:
            y, x, sigma = blob
            blobs_all.append([z, y, x, sigma])
    blob_intensities = []
    for z, y, x, sigma in blobs_all:
        z, y, x = int(z), int(y), int(x)
        y0, y1 = max(0, y - 1), min(image.shape[1], y + 2)
        x0, x1 = max(0, x - 1), min(image.shape[2], x + 2)
        patch = image[z, y0:y1, x0:x1]
        mean_intensity = patch.mean()
        blob_intensities.append(mean_intensity)
    blobs_all = np.hstack([np.array(blobs_all), np.array(blob_intensities)[:, np.newaxis]])
    if verbose:
        print(f"[detect_blobs] Total blobs detected: {len(blobs_all)}")
    return blobs_all

def suppress_close_blobs_by_intensity(blobs, radius_xy=10, z_window=2, verbose=False):
    """
    Suppress blobs that are too close in XY within a Z ± z_window range.
    Keep only the brightest blob in each local cylinder.

    blobs: numpy array of shape (N, 5): z, y, x, sigma, intensity
    """
    if len(blobs) == 0:
        return blobs

    # Sort by descending intensity
    sorted_indices = np.argsort(-blobs[:, 4])
    blobs_sorted = blobs[sorted_indices]

    keep_mask = np.ones(len(blobs_sorted), dtype=bool)

    for i, blob in enumerate(blobs_sorted):
        if not keep_mask[i]:
            continue

        z0, y0, x0 = blob[:3]

        for j in range(i + 1, len(blobs_sorted)):
            if not keep_mask[j]:
                continue
            z1, y1, x1 = blobs_sorted[j, :3]

            # Check if in Z window
            if abs(z1 - z0) <= z_window:
                dist_sq = (y1 - y0)**2 + (x1 - x0)**2
                if dist_sq <= radius_xy**2:
                    keep_mask[j] = False
    if verbose:
        print(f"[suppress_close_blobs_by_intensity] Blobs after suppression: {np.sum(keep_mask)} / {len(blobs)}")
    return blobs_sorted[keep_mask]

def detect_blob_intensities(image, blobs, verbose=False):
    """
    For each blob (z, y, x), compute the mean intensity in a 3x3 XY patch around it.
    Appends the mean intensity to the blob array.
    Returns an array of shape (N, 5): z, y, x, sigma, intensity
    """
    blob_intensities = []
    for blob in blobs:
        z, y, x = np.round(blob[:3]).astype(int)

        if (
            1 <= y < image.shape[1] - 1 and
            1 <= x < image.shape[2] - 1 and
            0 <= z < image.shape[0]
        ):
            patch = image[z, y-1:y+2, x-1:x+2]
            mean_intensity = patch.mean()
        else:
            mean_intensity = np.nan

        blob_intensities.append(mean_intensity)

    blob_intensities = np.array(blob_intensities)
    if verbose:
        print(f"[detect_blob_intensities] Blobs with intensity measured: {len(blob_intensities)}")
    return np.hstack([blobs, blob_intensities[:, np.newaxis]])

def filter_blobs_by_local_intensity(image, blobs, region_size=10, ratio_threshold=2.0, verbose=False):
    """
    Filters blobs by comparing their intensity to the local mean intensity in a square XY region.
    Only keeps blobs where intensity > ratio_threshold * local_mean.

    Parameters:
    - image: 3D array
    - blobs: array of shape (N, 5): z, y, x, sigma, intensity
    - region_half_size: half-width of the square region in XY
    - ratio_threshold: threshold multiplier for filtering

    Returns:
    - filtered array of blobs
    """
    filtered_blobs = []
    for blob in blobs:
        z, y, x = np.round(blob[:3]).astype(int)
        intensity = blob[4]

        if (
            region_size <= y < image.shape[1] - region_size and
            region_size <= x < image.shape[2] - region_size and
            0 <= z < image.shape[0]
        ):
            region = image[z, y - region_size:y + region_size + 1,
                              x - region_size:x + region_size + 1]
            local_mean = region.mean()
            if intensity > ratio_threshold * local_mean:
                filtered_blobs.append(blob)
    if verbose:
        print(f"[filter_blobs_by_local_intensity] Blobs after local intensity filter: {len(filtered_blobs)} / {len(blobs)}")
    return np.array(filtered_blobs)

def filter_blobs_outside_eroded_mask(blobs, original_mask, erosion_iterations=10, verbose=False):
    """
    Removes blobs that are located in the ring between the original and eroded mask.
    Returns only those blobs that are inside the eroded mask.

    Parameters:
    - blobs: array of shape (N, 5): z, y, x, sigma, intensity
    - original_mask: 3D binary array
    - erosion_iterations: number of iterations for erosion

    Returns:
    - filtered blobs inside the eroded region
    - eroded mask
    """
    from scipy.ndimage import binary_erosion

    eroded_mask = binary_erosion(original_mask, iterations=erosion_iterations)
    mask_difference = (original_mask.astype(bool)) & (~eroded_mask.astype(bool))
    filtered = []
    for blob in blobs:
        z, y, x = np.round(blob[:3]).astype(int)
        if (
            0 <= z < eroded_mask.shape[0] and
            0 <= y < eroded_mask.shape[1] and
            0 <= x < eroded_mask.shape[2]
        ) and not mask_difference[z, y, x]:
            filtered.append(blob)
    if verbose:
        print(f"[filter_blobs_outside_eroded_mask] Blobs inside eroded mask: {len(filtered)} / {len(blobs)}")
    return np.array(filtered), eroded_mask


def filter_blobs_by_sharpness(blobs, image, drop_factor=1.4, verbose=False):
    """
    Reject blobs that are not sharply peaked: center voxel should be significantly brighter than mean of its neighborhood.
    """
    kept = []
    for blob in blobs:
        z, y, x = np.round(blob[:3]).astype(int)
        if not (0 < z < image.shape[0]-1 and 0 < y < image.shape[1]-1 and 0 < x < image.shape[2]-1):
            continue
        center_intensity = image[z, y, x]
        local_cube = image[z-1:z+2, y-1:y+2, x-1:x+2]
        local_mean = local_cube.mean()
        if center_intensity > drop_factor * local_mean:
            kept.append(blob)
    if verbose:
        print(f"[filter_blobs_by_sharpness] Blobs after sharpness filter: {len(kept)} / {len(blobs)}")
    return np.array(kept)

from skimage.draw import line_nd

def suppress_blobs_by_bridge_intensity(blobs, image, radius_xy=20, z_window=4, dip_threshold=0.5, verbose=False):
    """
    Remove one of two nearby blobs if the intensity along the line between them doesn't dip significantly.

    Example:
      Blob A                           Blob B
        ●                                ●
         \                              /
          \                            /
           \__________________________/
                 Intensity Profile
    """
    if len(blobs) == 0:
        return blobs

    # Sort by intensity (descending)
    sorted_indices = np.argsort(-blobs[:, 4])
    blobs_sorted = blobs[sorted_indices]
    keep_mask = np.ones(len(blobs_sorted), dtype=bool)

    for i, blob1 in enumerate(blobs_sorted):
        if not keep_mask[i]:
            continue
        z1, y1, x1, _, intensity1 = blob1

        for j in range(i + 1, len(blobs_sorted)):
            if not keep_mask[j]:
                continue
            z2, y2, x2, _, intensity2 = blobs_sorted[j]

            if abs(z2 - z1) > z_window:
                continue
            dist_sq = (y2 - y1)**2 + (x2 - x1)**2
            if dist_sq > radius_xy**2:
                continue

            # Sample intensity along line
            coords = line_nd((int(z1), int(y1), int(x1)), (int(z2), int(y2), int(x2)))
            values = image[tuple(coords)]

            min_val = np.min(values)
            avg_peak = (intensity1 + intensity2) / 2
            dip_ratio = min_val / avg_peak

            if dip_ratio > dip_threshold:
                # No real dip, likely same structure → remove weaker blob
                if intensity1 > intensity2:
                    keep_mask[j] = False
                else:
                    keep_mask[i] = False
                    break

    filtered = blobs_sorted[keep_mask]
    if verbose:
        print(f"[suppress_blobs_by_bridge_intensity] {np.sum(keep_mask)} / {len(blobs)} blobs kept after bridge check")
        print(f"[suppress_blobs_by_bridge_intensity] Blob pairs tested: {sum(1 for i in range(len(blobs_sorted)) for j in range(i + 1, len(blobs_sorted)) if keep_mask[i] and keep_mask[j])}")
    return filtered
