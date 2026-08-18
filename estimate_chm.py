import numpy as np
import torch
import rasterio
import rasterio.enums as Enums
from pathlib import Path
from rasterio.io import DatasetReader
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

def estimate_chm(src: DatasetReader, max_spatial_res: tuple[float, float]):
    try:
        model_id = "facebook/dinov3-vitl16-chmv2-dpt-head"
        processor = AutoImageProcessor.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForDepthEstimation.from_pretrained(model_id, device_map="auto", trust_remote_code=True)

        x_res, y_res = src.res

        # Downsample the image if it's below the target resolution
        # otherwise, just use the exisitng res
        target_res = (
            max(max_spatial_res[0], x_res),
            max(max_spatial_res[1], y_res)
        )

        scale_x = x_res / target_res[0]
        scale_y = y_res / target_res[1]

        width = round(src.width * scale_x)
        height = round(src.height * scale_y)

        image = src.read(
            out_shape=(src.count, height, width),
            resampling=Enums.Resampling.average
        )
        image = image[:3, :, :]          # extract (r, g, b) from (r, g, b, nir)
        image = image.transpose(1, 2, 0) # (bands, height, width) to (height, width, bands)

        inputs = processor(images=image, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model(**inputs)

        chm_data = processor.post_process_depth_estimation(
            outputs, target_sizes=[(image.shape[0], image.shape[1])]
        )[0]["predicted_depth"]

        chm_data = chm_data.detach().cpu().numpy()

        return chm_data, target_res
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def save_chm(chm_data: np.ndarray, spatial_res: tuple[float, float], src: DatasetReader, dst_file: Path):
    try:
        new_transform = rasterio.Affine(
            spatial_res[0], 0, src.transform.c,
            0, -1 * spatial_res[1], src.transform.f
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

        with rasterio.open(dst_file, 'w', **profile) as dst:
            dst.write(chm_data, 1)

        return dst_file
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    imagery_file = Path(r"C:\Users\samue\Downloads\tmp_tpg6su9.tiff")

    from time import time
    dawn = time()
    data, res = estimate_chm(imagery_file)
    dusk = time()
    print(f"CHM estimation took {dusk-dawn} seconds")

    out_file = imagery_file.parent / f"{imagery_file.stem}.chm.tiff"
    save_chm(data, res, imagery_file, out_file)
