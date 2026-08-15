import numpy as np
from pathlib import Path
import torch
import rasterio
from rasterio.enums import Resampling

from transformers import AutoImageProcessor, AutoModelForDepthEstimation

model_id = "facebook/dinov3-vitl16-chmv2-dpt-head"
processor = AutoImageProcessor.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForDepthEstimation.from_pretrained(model_id, device_map="auto", trust_remote_code=True)

TARGET_RESOLUTION = 1

def estimate_chm(imagery_file: Path):
    with rasterio.open(imagery_file) as src:
        x_res, y_res = src.res

        target_x_res = max(TARGET_RESOLUTION, x_res)
        target_y_res = max(TARGET_RESOLUTION, y_res)

        scale_x = x_res / target_x_res
        scale_y = y_res / target_y_res

        new_width = round(src.width * scale_x)
        new_height = round(src.height * scale_y)

        image = src.read(
            out_shape=(src.count, new_height, new_width),
            resampling=Resampling.average
        )[:3, :, :]

    # (bands, height, width) -> (height, width, bands)
    image = image.transpose(1, 2, 0)

    inputs = processor(images=image, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model(**inputs)

    chm_data = processor.post_process_depth_estimation(
        outputs, target_sizes=[(image.shape[0], image.shape[1])]
    )[0]["predicted_depth"]

    chm_data = chm_data.detach().cpu().numpy()

    return chm_data

def save_chm(chm_data: np.ndarray, imagery_file: Path, dst_path: Path):
    with rasterio.open(imagery_file) as src:
        transform = src.transform

        new_transform = rasterio.Affine(
            TARGET_RESOLUTION, 0, transform.c,
            0, -1 * TARGET_RESOLUTION, transform.f
        )

        profile = src.profile.copy()
        profile.update(
            driver='GTiff',
            count=1,
            height=chm_data.shape[0],
            width=chm_data.shape[1],
            transform=new_transform,
            dtype='float32',
        )

        with rasterio.open(dst_path, 'w', **profile) as dst:
            dst.write(chm_data, 1)

if __name__ == "__main__":
    from time import time
    dawn = time()
    data = estimate_chm(r"C:\Users\samue\Downloads\tmpomsajh92.tiff")
    dusk = time()
    print(f"CHM estimation took {dusk-dawn} seconds")

    save_chm(data, r"C:\Users\samue\Downloads\tmpomsajh92.tiff", r"C:\Users\samue\Downloads\tmpomsajh92.chm.tiff")

    pass
