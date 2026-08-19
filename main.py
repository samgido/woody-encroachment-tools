import geopandas as gpd
from pathlib import Path
import rasterio
import argparse
from argparse import ArgumentParser

from fetch_imagery import get_site_imagery
from estimate_chm import estimate_chm
from stats import save_full_stats

def parse_tuple(inp):
    try:
        cleaned = inp.replace('(', '').replace(')', '')
        return tuple(float(x) for x in cleaned.split(','))
    except:
        raise argparse.ArgumentTypeError("Tuple must be of the form (x1,x2,x3) e.g. (1.0, 2.0)")

def process_shape(aoi: gpd.GeoDataFrame, out_dir: Path, max_spatial_res: tuple[float, float]):
    imagery_file = out_dir / "imagery.tif"

    res = get_site_imagery(aoi, max_spatial_res, imagery_file, 8, 2023)
    
    if not res:
        return False

    save_full_stats(imagery_file, aoi, max_spatial_res)

def process_shape_file(aoi_fp: Path, max_spatial_res: tuple[float, float]):
    if not (aoi_fp.exists() and aoi_fp.is_file()):
        print("The provided site file does't exist or is not a file!")
        exit(1)

    try:
        aoi = gpd.read_file(aoi_fp)
    except Exception as e:
        print(f"Error opening site geometry file: {e}")
        exit(1)

    if not (out_dir := aoi_fp.parent / aoi_fp.stem).exists():
        out_dir.mkdir(exist_ok=True)

    return process_shape(aoi, out_dir, max_spatial_res)

def main():
    parser = ArgumentParser()
    parser.add_argument(
        'site', 
        type=Path, 
        help="Path to the file holding the site geometry."
    )
    parser.add_argument(
        '--spatial-res',
        type=parse_tuple,
        default=(2.0, 2.0)
    )
    args = parser.parse_args()

    aoi_fp: Path = args.site
    spatial_res: tuple[float, float] = args.spatial_res

    process_shape_file(aoi_fp, spatial_res)

if __name__ == '__main__':
    main()
