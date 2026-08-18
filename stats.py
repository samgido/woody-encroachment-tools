import json
import geopandas as gpd
import rasterio 
import rasterio.io as IO
import rasterio.mask as Mask
from pathlib import Path
from time import time
from pprint import pprint

from estimate_chm import estimate_chm, save_chm

def save_chm_stats_t(
    chm_file: Path, 
    aoi: gpd.GeoDataFrame, 
    model_processing_time: float, 
    results_dir: Path
):
    with rasterio.open(chm_file) as src:
        full_data = src.read()

        aoi_reproj = aoi.to_crs(src.crs)

        # using nodata=-1 should be safe, since 
        # this is operating on a CHM which
        # shouldn't have negative values
        nodata = -1
        masked_data, _ = Mask.mask(src, aoi_reproj.geometry, nodata=nodata)

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

def save_chm_stats(
    chm_src: IO.DatasetReader, 
    model_processing_time: float, 
    results_dir: Path
):
    stats = {
        "masked": make_stats(masked_data),
        "full": make_stats(chm_src.read()),
        "processing_time": float(model_processing_time)
    }
    pprint(stats, indent=2)

    with open(results_dir / "stats.json", 'w') as f:
        json.dump(stats, f, indent=4)

def make_stats(data, nodata: float):
    valid_data = data[data != nodata]
    percent_px_above_x = lambda x: float(data[data > x].size / valid_data.size)
    return {
        "min_height": float(valid_data.min()),
        "max_height": float(valid_data.max()),
        "percent_area_over_1m": percent_px_above_x(1) * 100,
        "percent_area_over_50cm": percent_px_above_x(0.5) * 100,
        "percent_area_over_20cm": percent_px_above_x(0.2) * 100,
    }

def save_clipped_raster(
    chm_src: IO.DatasetReader,
    aoi: gpd.GeoDataFrame,
    results_dir: Path,
):
    try:
        aoi_reproj = aoi.to_crs(chm_src.crs)

        # using nodata=-1 should be safe, since 
        # this is operating on a CHM which
        # shouldn't have negative values
        nodata = -1
        masked_chm_data, _ = Mask.mask(chm_src, aoi_reproj.geometry, nodata=nodata)

        dst_fp = results_dir / "chm_masked.tif"
        with rasterio.open(dst_fp, 'w', **chm_src.profile) as dst:
            saved_data = masked_chm_data.copy()
            saved_data[saved_data == nodata] = 0
            dst.write(saved_data)

        return masked_chm_data, dst_fp
    except Exception as e:
        print(f"Error saving clipped raster: {e}")
        return None

def save_binary_mask(data, threshold: float, profile, dst_fp: Path):
    try:
        binary_data = data.copy()

        binary_data[binary_data > threshold] = 1
        binary_data[binary_data <= threshold] = 0

        with rasterio.open(dst_fp, 'w', **profile) as dst:
            dst.write(binary_data)

        return True
    except Exception as e:
        print(f"Error saving binary mask: {e}")
        return False

def save_full_stats(src_fp: Path, aoi: gpd.GeoDataFrame, max_spatial_res: tuple[float, float]):
    with rasterio.open(src_fp) as src:
        results_dir = Path(src_fp.parent) / f"{src_fp.stem}" 
        if not results_dir.exists(): results_dir.mkdir()

        print(f"Beginning CHM estimation..."); dawn = time()

        chm_data, spatial_res = estimate_chm(src, max_spatial_res)
        if not (chm_data and spatial_res):
            return False

        dusk = time()
        print(f"File at {src_fp} took {(processing_time := dusk - dawn)}sec")

        chm_file = save_chm(chm_data, spatial_res, src, results_dir / "chm.tif")
        if not chm_file:
            return False

        with rasterio.open(chm_file) as chm_src:
            res = save_clipped_raster(chm_src, aoi, results_dir)
            if not res:
                return False
            masked_chm_data, clipped_chm_fp = res

        print()

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

    save_full_stats(Path(r"C:\Users\samue\Downloads\tmp_tpg6su9.tiff"), aoi, (2.0, 2.0))
