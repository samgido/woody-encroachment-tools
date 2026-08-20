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
) -> np.ndarray | None:
    try:
        with rasterio.open(chm_src_fp) as chm_src:
            aoi_reproj = aoi.to_crs(chm_src.crs)

            # using nodata=-1 should be safe, since 
            # this is operating on a CHM which
            # shouldn't have negative values
            masked_chm_data, _ = Mask.mask(chm_src, aoi_reproj.geometry, nodata=nodata, filled=False)

            # kill the band dimension, the other functions don't expect it
            masked_chm_data = masked_chm_data[0]

            return masked_chm_data
    except Exception as e:
        print(f"Error saving clipped raster: {e}")
        return None

def save_chm(chm_data: np.ndarray, spatial_res: tuple[float, float], nodata: float, src_fp: Path, dst_fp: Path):
    try:
        with rasterio.open(src_fp) as src:
            profile = src.profile.copy()

            new_transform = rasterio.Affine(
                spatial_res[0], 0, src.transform.c,
                0, -1 * spatial_res[1], src.transform.f
            )

        profile.update(
            driver='GTiff',
            count=1,
            height=chm_data.shape[0],
            width=chm_data.shape[1],
            transform=new_transform,
            dtype='float32',
            nodata=nodata,
        )

        with rasterio.open(dst_fp, 'w', **profile) as dst:
            dst.write(chm_data, 1)

        return dst_fp
    except Exception as e:
        print(f"Error saving CHM: {e}")
        return None

def save_auxiliary_products(src_fp: Path) -> bool:
    """
    Calculates and saves the other statistics and products used for a CHM. 
    Implemented to use the nodata value of the source raster, for a clipped CHM. 

    Products
    - Binary mask
    - Min height
    - Max height
    - % area > [1m, 0.5m, 0.2m]
    """
    try:
        with rasterio.open(src_fp) as src:
            data = src.read()
            nodata = src.nodata

            stats = make_stats(data, nodata)

            with open(src_fp.parent / f"{src_fp.stem}_stats.geojson", 'w') as f:
                json.dump(stats, f, indent=4)

        return True
    except Exception as e:
        print(f"Error saving auxiliary products: {e}")
        return False

def save_full_stats(src_fp: Path, aoi: gpd.GeoDataFrame, max_spatial_res: tuple[float, float]):
    nodata = -1

    results_dir = Path(src_fp.parent)

    print(f"Beginning CHM estimation..."); dawn = time()
    res = estimate_chm(src_fp, max_spatial_res)
    if res is None: return False
    chm_data, spatial_res = res
    dusk = time(); print(f"CHM estimation complete! Took {(dusk-dawn):.2f} seconds.")

    chm_src_fp = save_chm(chm_data, spatial_res, nodata, src_fp, results_dir / "chm.tif")
    if chm_src_fp is None: return False

    res = save_auxiliary_products(chm_src_fp)
    if not res: return False

    masked_chm_data = get_clipped_raster_data(chm_src_fp, aoi, results_dir)
    if masked_chm_data is None: return False

    chm_masked_src_fp = save_chm(masked_chm_data, spatial_res, nodata, src_fp, results_dir / "masked_chm.tif")
    if chm_masked_src_fp is None: return False

    res = save_auxiliary_products(chm_masked_src_fp)
    if not res: return False

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
