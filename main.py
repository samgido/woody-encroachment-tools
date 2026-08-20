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
    try:
        imagery_file = out_dir / "imagery.tif"

        res = get_site_imagery(aoi, max_spatial_res, imagery_file, 2023)
        if not res:
            return False

        save_full_stats(imagery_file, aoi, max_spatial_res)

        return True
    except Exception as e:
        print(f"Error processing shape: {e}")
        return False

def process_shape_file(aoi_fp: Path, max_spatial_res: tuple[float, float]):
    try:
        if not (aoi_fp.exists() and aoi_fp.is_file()):
            print("The provided site file does't exist or is not a file!")
            return False

        aoi = gpd.read_file(aoi_fp)

        # conditionally add a column, 
        # 'Site' is used to name output folders
        if 'Site' not in aoi.columns:
            aoi.insert(0, 'Site', aoi.index)

        sites = [
            aoi.iloc[[i]] for i in range(len(aoi))
        ]

        for site in sites:
            site_name = site['Site'].iloc[0]
            if not (
                out_dir := aoi_fp.parent / f"{aoi_fp.stem}_{max_spatial_res[0]}_{max_spatial_res[1]}" / f"{site_name}"
            ).exists():
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                print("Warning: output directory for this shape already exists!")

            print(f"Processing shape {site_name}")
            print("==========================================")
            res = process_shape(site, out_dir, max_spatial_res)

            if not res:
                print(f"Site {site['Site'][0]} processing failed")
            else:
                print("==========================================")
                print(f"Processing shape {site_name} COMPLETE.\n")

        return True
    except Exception as e:
        print(f"Error processing shape file: {e}")
        return False

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
