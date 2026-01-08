def render_comp(im_group1, im_group2):
    """
    Compare two groups of images and return the mean differance metrics.
    Args:
        im_group1: List of first group of images as NumPy arrays.
        im_group2: List of second group of images as NumPy arrays.
    Returns:
        mean_diff: The mean differance metrics between the two groups of images.
    """
    import numpy as np

    if len(im_group1) != len(im_group2):
        raise ValueError("Image groups must have the same number of images.")

    total_diff = []
    num_images = len(im_group1)

    for im1, im2 in zip(im_group1, im_group2):
        diff = comp_2_img(im1, im2)
        total_diff.append(diff)

    return mean_diff(total_diff)


def comp_2_img(im1, im2):
    """
    Compare two images and return a difference image.
    Args:
        im1: First input image as a NumPy array.
        im2: Second input image as a NumPy array.
    Returns:
        diff: The differances between the two images as a dictionary of metrics.
    """
    import numpy as np

    # Ensure the images have the same shape
    if im1.shape != im2.shape:
        raise ValueError("Input images must have the same dimensions.")
    
    diff = dict()

    # Compute Normalize Mean Absolute Error (NMAE)
    nmae = np.mean(np.abs(im1.astype("float") - im2.astype("float"))) / 255.0
    diff['NMAE'] = nmae

    # Compute the Normalize Mean Squared Error (MSE)
    nmse = np.mean((im1.astype("float") - im2.astype("float")) ** 2) / (255.0 ** 2)
    diff['NMSE'] = nmse
    
    # Compute Zero-mean Normalized Cross-Correlation (ZNCC)
    im1_mean = im1.astype("float") - np.mean(im1.astype("float"))
    im2_mean = im2.astype("float") - np.mean(im2.astype("float"))
    numerator = np.sum(im1_mean * im2_mean)
    denominator = np.sqrt(np.sum(im1_mean ** 2) * np.sum(im2_mean ** 2))
    zncc = numerator / denominator if denominator != 0 else 0
    diff['ZNCC'] = zncc

    return diff


def mean_diff(diff_list):
    """
    Compute the mean of a list of difference metrics.
    Args:
        diff_list: List of dictionaries containing difference metrics.
    Returns:
        mean_diff: Dictionary containing the mean of each metric.
    """
    mean_diff = dict()
    num_diffs = len(diff_list)

    if num_diffs == 0:
        return mean_diff

    # Initialize sums
    for key in diff_list[0].keys():
        mean_diff[key] = 0.0

    # Sum up all metrics
    for diff in diff_list:
        for key, value in diff.items():
            mean_diff[key] += value

    # Compute means
    for key in mean_diff.keys():
        mean_diff[key] /= num_diffs

    return mean_diff


def print_comp(diff):
    """
    Print the difference metrics in a formatted way.
    Args:
        diff: Dictionary containing difference metrics.
    """
    print("Difference Metrics:")
    for key, value in diff.items():
        print(f"{key}: {value:.3f}")