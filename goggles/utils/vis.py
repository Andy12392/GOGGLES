import os

from matplotlib import patches as pltpatches
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image


plt.switch_backend('agg')


def get_image_from_tensor(x):
    image = x.data.cpu().numpy()

    if len(image.shape) == 4:
        image = image[0]

    image = 255. * (0.5 + (image / 2.))
    image = np.array(image, dtype=np.uint8)
    image = np.swapaxes(image, 0, 1)
    image = np.swapaxes(image, 1, 2)
    image = Image.fromarray(image)

    return image


def save_prototype_patch_visualization(model, dataset, prototype_patches, outdir):
    for prototype_idx, ((image_idx, patch_idx), nearest_patch) in prototype_patches.items():
        attribute_name = dataset.get_attribute_name_for_attribute_idx(prototype_idx)
        (i_nw, j_nw), (patch_w, patch_h) = model.get_receptive_field(patch_idx)

        image = dataset[image_idx][0]
        image = get_image_from_tensor(image)
        image = np.array(image, dtype=np.uint8)

        fig, ax = plt.subplots(1)
        ax.imshow(image)

        x_nw, y_nw = j_nw, i_nw
        ax.add_patch(
            pltpatches.Rectangle(
                (x_nw, y_nw),
                patch_w, patch_h,
                linewidth=1,
                edgecolor='r',
                facecolor='none'))

        fig.savefig(os.path.join(outdir, '%s.png' % attribute_name.replace('::', '-')))
