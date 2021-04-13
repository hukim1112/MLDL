import itertools
import math
import tensorflow as tf


def generate_default_boxes(param):
    """ Generate default boxes for all feature maps

    Args:
        config: information of feature maps
            scales: boxes' size relative to image's size
            fm_sizes: sizes of feature maps
            ratios: box ratios used in each feature maps

    Returns:
        default_boxes: tensor of shape (num_default, 4)
                       with format (cx, cy, w, h)
    """
    '''
    param examples
    "SSD300" : {"ratios": [[2], [2, 3], [2, 3], [2, 3], [2], [2]],
                           "scales": [0.1, 0.2, 0.375, 0.55, 0.725, 0.9, 1.075],
                           "fm_sizes": [38, 19, 10, 5, 3, 1],
                           "image_size": 300},
    "SSD512" : {"ratios": [[2], [2, 3], [2, 3], [2, 3], [2], [2], [2]],
                           "scales": [0.07, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.05],
                           "fm_sizes": [64, 32, 16, 8, 6, 4, 1],
                           "image_size": 512},



    '''
    default_boxes = []
    scales = param['scales']
    fm_sizes = param['fm_sizes']
    ratios = param['ratios']

    for m, fm_size in enumerate(fm_sizes):
        for i, j in itertools.product(range(fm_size), repeat=2):
            cx = (j + 0.5) / fm_size
            cy = (i + 0.5) / fm_size
            default_boxes.append([
                cx,
                cy,
                scales[m],
                scales[m]
            ])

            default_boxes.append([
                cx,
                cy,
                math.sqrt(scales[m] * scales[m + 1]),
                math.sqrt(scales[m] * scales[m + 1])
            ])

            for ratio in ratios[m]:
                r = math.sqrt(ratio)
                default_boxes.append([
                    cx,
                    cy,
                    scales[m] * r,
                    scales[m] / r
                ])

                default_boxes.append([
                    cx,
                    cy,
                    scales[m] / r,
                    scales[m] * r
                ])

    default_boxes = tf.constant(default_boxes)
    default_boxes = tf.clip_by_value(default_boxes, 0.0, 1.0)

    return default_boxes
