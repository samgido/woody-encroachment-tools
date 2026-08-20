import os
from time import time
import numpy as np
import torch
import rasterio
import rasterio.enums as Enums
from pathlib import Path
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

MODEL_ID = "facebook/dinov3-vitl16-chmv2-dpt-head"

processor = None
model = None

def estimate_chm(src_fp: Path, max_spatial_res: tuple[float, float]) -> tuple[np.ndarray, tuple[float, float]]:
    global processor, model
    try:
        with rasterio.open(src_fp) as src:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            device = "cpu" # having issues with CUDA on my machine
            if processor is None: processor = AutoImageProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
            if model is None: model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID, trust_remote_code=True).to(device)

            # put model in evaluation mode
            model.eval()

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

            print(f"Loaded image of size {image.shape[1]} by {image.shape[0]} pixels, for a total size of {image.size} pixels")
            dawn=time(); print(f"Starting inference...", flush=True)
            inputs = processor(images=image, return_tensors="pt").to(model.device)

            with torch.inference_mode():
                outputs = model(**inputs)

            chm_data = processor.post_process_depth_estimation(
                outputs, target_sizes=[(image.shape[0], image.shape[1])]
            )[0]["predicted_depth"]

            chm_data = chm_data.detach().cpu().numpy()

            dusk=time(); print(f"Inference completed in {dusk-dawn} seconds.", flush=True)

            return chm_data, target_res
    except Exception as e:
        print(f"Error during CHM estimation: {e}")
        return None

if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        'imagery_fp', 
        help="Path to imagery file to run CHM estimation on.",
        type=Path,
    )
    parser.add_argument(
        ''
    )
