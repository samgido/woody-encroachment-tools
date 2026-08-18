import geopandas as gpd
from pathlib import Path
import rasterio

from fetch_imagery import get_site_imagery
from estimate_chm import estimate_chm, save_chm
from stats import save_full_stats

def process_shape(aoi: gpd.GeoDataFrame, out_dir: Path):
    imagery_file = out_dir / "imagery.tif"

    res = get_site_imagery(aoi, imagery_file, (2.0, 2.0))
    return
    if not res:
        exit(1)

    with rasterio.open(imagery_file) as src:
        save_full_stats(src, imagery_file, 1.0)

if __name__ == '__main__':
    aoi_file = Path(r"C:\Users\samue\Downloads\CedarCreek_watershed_shapefiles\USGS_07180500_basin.shp")
    aoi = gpd.read_file(aoi_file)

    if not (out_dir := aoi_file.parent / aoi_file.stem).exists():
        out_dir.mkdir(exist_ok=True)

    process_shape(aoi, out_dir)
