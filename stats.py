import json
import numpy as np
from pathlib import Path
import tifffile as tf
import rasterstats
from time import time

from estimate_chm import estimate_chm

def save_chms(data: np.ndarray, results_dir: Path):
    # CHM
    chm_file = results_dir / "chm.tif"
    if tf.imwrite(chm_file, data) is not None:
        print(f"Writing CHM to {chm_file}")

    # Binary CHM 
    mask_height = 1 # meter
    data_masked = data.copy()
    data_masked[data_masked > mask_height] = 1
    data_masked[data_masked < mask_height] = 0
    chm_masked_file = results_dir / "chm_1m_masked.tif"
    if tf.imwrite(chm_masked_file, data_masked) is not None:
        print(f"Writing CHM masked to {chm_masked_file}")

def save_chm_stats(data: np.ndarray, processing_time, results_dir: Path):
    stats = {
        "min_height": float(data.min()),
        "max_height": float(data.max()),
        "percent_area_over_1m": float(data[data > 1].size / data.size) * 100,
        "percent_area_over_50cm": float(data[data > 0.5].size / data.size) * 100,
        "percent_area_over_20cm": float(data[data > 0.2].size / data.size) * 100,
        "processing_time": float(processing_time)
    }
    print(stats)

    stats_file = results_dir / "stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=4)

def save_full_results(raster_file: Path):
    print("===========================================")
    print(f"Starting analysis on {raster_file.stem}")
    print("===========================================")

    results_dir = Path(raster_file.parent) / f"{raster_file.stem}" 
    results_dir.mkdir()

    dawn = time()
    chm_data = estimate_chm(raster_file)
    dusk = time()
    print(f"File at {raster_file} took {(processing_time := dusk - dawn)}sec")

    save_chms(chm_data, results_dir)
    save_chm_stats(chm_data, processing_time, results_dir)

    print()

def process_rasters_in_dir(dir: Path):
    if not (dir.exists() and dir.is_dir()):
        print("Invalid input directory")
        exit(1)

    files = [p for p in dir.iterdir() if p.suffix == '.tif']
    for file in files:
        save_full_results(file)