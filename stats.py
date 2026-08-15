import json
import numpy as np
from pathlib import Path
import tifffile as tf
from time import time
import geopandas as gpd
import rasterio 
from rasterio.io import DatasetReader
from rasterio.mask import mask
from pprint import pprint

from estimate_chm import estimate_chm, save_chm

def save_chm_stats_t(chm_file: Path, aoi: gpd.GeoDataFrame, model_processing_time: float, results_dir: Path):
    with rasterio.open(chm_file) as src:
        full_data = src.read()

        aoi_reproj = aoi.to_crs(src.crs)

        # using nodata=-1 should be safe, since 
        # this is operating on a CHM which
        # shouldn't have negative values
        nodata = -1
        masked_data, _ = mask(src, aoi_reproj.geometry, nodata=nodata)

    def make_stats(data):
        num_px_in_mask = data[data > nodata].size
        num_px_above_x = lambda d, x: d[d > x].size
        return {
            "min_height": float(data.min()),
            "max_height": float(data.max()),
            "percent_area_over_1m": float(num_px_above_x(data, 1) / num_px_in_mask) * 100,
            "percent_area_over_50cm": float(num_px_above_x(data, 0.5) / num_px_in_mask) * 100,
            "percent_area_over_20cm": float(num_px_above_x(data, 0.2) / num_px_in_mask) * 100,
        }

    stats = {
        "masked": make_stats(masked_data),
        "full": make_stats(full_data),
        "processing_time": float(model_processing_time)
    }
    print(stats)

    stats_file = results_dir / "stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=4)

def save_chm_stats(chm_src: DatasetReader, aoi: gpd.GeoDataFrame, model_processing_time: float, results_dir: Path):
    aoi_reproj = aoi.to_crs(chm_src.crs)

    # using nodata=-1 should be safe, since 
    # this is operating on a CHM which
    # shouldn't have negative values
    nodata = -1
    masked_data, _ = mask(chm_src, aoi_reproj.geometry, nodata=nodata)

    breakpoint()

    def make_stats(data):
        valid_data = data[data != nodata]
        percent_px_above_x = lambda x: float(data[data > x].size / valid_data.size)
        return {
            "min_height": float(valid_data.min()),
            "max_height": float(valid_data.max()),
            "percent_area_over_1m": percent_px_above_x(1) * 100,
            "percent_area_over_50cm": percent_px_above_x(0.5) * 100,
            "percent_area_over_20cm": percent_px_above_x(0.2) * 100,
        }

    stats = {
        "masked": make_stats(masked_data),
        "full": make_stats(chm_src.read()),
        "processing_time": float(model_processing_time)
    }
    pprint(stats, indent=2)

    with open(results_dir / "stats.json", 'w') as f:
        json.dump(stats, f, indent=4)

    with rasterio.open(results_dir / "chm_masked.tif", 'w', **chm_src.profile) as dst:
        masked_data[masked_data == nodata] = 0
        dst.write(masked_data)

def save_full_results(raster_file: Path, aoi: gpd.GeoDataFrame):
    print("===========================================")
    print(f"Starting analysis on {raster_file.stem}")
    print("===========================================")

    results_dir = Path(raster_file.parent) / f"{raster_file.stem}" 
    if not results_dir.exists(): results_dir.mkdir()

    with rasterio.open(raster_file) as src:
        dawn = time()
        chm_data, spatial_res = estimate_chm(src)
        dusk = time()
        print(f"File at {raster_file} took {(processing_time := dusk - dawn)}sec")

        chm_file = results_dir / "chm.tif"

        save_chm(chm_data, spatial_res, src, chm_file)
        with rasterio.open(chm_file) as chm_src:
            save_chm_stats(chm_src, aoi, processing_time, results_dir)

    print()

def process_rasters_in_dir(dir: Path):
    if not (dir.exists() and dir.is_dir()):
        print("Invalid input directory")
        exit(1)

    files = [p for p in dir.iterdir() if p.suffix == '.tif']
    for file in files:
        save_full_results(file)

if __name__ == '__main__':
    from shapely.geometry import Polygon
    site_coords = [ # Example site, just a triangle 
        [-96.628957685050764,39.096227356101906],
        [-96.607431909809492,39.100601949134813],
        [-96.609445611364322,39.088103111897944],
        [-96.628957685050764,39.096227356101906]
    ]
    aoi = gpd.GeoDataFrame(
        {'name': ['site']},
        geometry=[Polygon(site_coords)],
        crs='EPSG:4326'
    )

    save_full_results(Path(r"C:\Users\samue\Downloads\tmp_tpg6su9.tiff"), aoi)
