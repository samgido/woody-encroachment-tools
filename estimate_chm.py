import os
from time import time
import numpy as np
import torch
import rasterio
import rasterio.enums as Enums
from pathlib import Path
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

def estimate_chm(src_fp: Path, max_spatial_res: tuple[float, float]):
    try:
        with rasterio.open(src_fp) as src:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            device = "cpu"

            model_id = "facebook/dinov3-vitl16-chmv2-dpt-head"
            processor = AutoImageProcessor.from_pretrained(model_id, trust_remote_code=True)
            model = AutoModelForDepthEstimation.from_pretrained(model_id, trust_remote_code=True).to(device)

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
        print(f"Error: {e}")
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
