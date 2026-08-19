import json
import geopandas as gpd
import rasterio 
import rasterio.mask as Mask
import rasterio.io as IO
import numpy as np
import numpy.ma as ma
from pathlib import Path
from time import time
from pprint import pprint

from estimate_chm import estimate_chm

def save_chm_stats(
    chm_src_fp: Path, 
    model_processing_time: float, 
    results_dir: Path
):
    with rasterio.open(chm_src_fp) as chm_src:
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

def get_clipped_raster_data(
    chm_src_fp: Path,
    aoi: gpd.GeoDataFrame,
    nodata: float,
):
    try:
        with rasterio.open(chm_src_fp) as chm_src:
            aoi_reproj = aoi.to_crs(chm_src.crs)

            # using nodata=-1 should be safe, since 
            # this is operating on a CHM which
            # shouldn't have negative values
            masked_chm_data, _ = Mask.mask(chm_src, aoi_reproj.geometry, nodata=nodata, filled=False)
            breakpoint()

            return masked_chm_data
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

def save_chm(chm_data: np.ndarray, spatial_res: tuple[float, float], src_fp: Path, dst_fp: Path):
    try:
        new_transform = rasterio.Affine(
            spatial_res[0], 0, src.transform.c,
            0, -1 * spatial_res[1], src.transform.f
        )

        with rasterio.open(src_fp) as src:
            profile = src.profile.copy()
        profile.update(
            driver='GTiff',
            count=1,
            height=chm_data.shape[0],
            width=chm_data.shape[1],
            transform=new_transform,
            dtype='float32',
        )

        with rasterio.open(dst_fp, 'w', **profile) as dst:
            dst.write(chm_data, 1)

        return dst_fp
    except Exception as e:
        print(f"Error: {e}")
        return None

def save_auxiliary_products(
    src_fp: Path,
    spatial_res: tuple[float, float], 
    dst_dir: Path
):
    with rasterio.open(src_fp) as src:
        src: IO.DatasetReader
        pass

def save_full_stats(src_fp: Path, aoi: gpd.GeoDataFrame, max_spatial_res: tuple[float, float]):
    results_dir = Path(src_fp.parent) / "stats"
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"Beginning CHM estimation..."); dawn = time()

    res = estimate_chm(src_fp, max_spatial_res)
    if not res:
        return False
    chm_data, spatial_res = res

    dusk = time(); print(f"File at {src_fp} took {dusk-dawn}sec")

    chm_src_fp = save_chm(chm_data, spatial_res, src_fp, results_dir / "chm.tif")
    if not chm_src_fp:
        return False

    return True

    res = get_clipped_raster_data(chm_src_fp, aoi, results_dir)
    if not res:
        return False
    masked_chm_data, clipped_chm_fp = res

    print("Statistics calculated and saved.")
    return True

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
