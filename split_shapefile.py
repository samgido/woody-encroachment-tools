"""
Helper script

Splits the features of a Shapefile into GeoJSON file

Use: launch script with -i flag, call save() from there
"""

from pathlib import Path
import geopandas as gpd

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument("shp")
args = parser.parse_args()

sf_path = Path(args.shp)

df = gpd.read_file(sf_path)

def save():
    if not (splitdir := Path("./split_output")).exists():
        splitdir.mkdir()

    for _, row in df.iterrows():
        site_name = row['Site']

        single_feat = gpd.GeoDataFrame([row], columns=df.columns, crs=df.crs)

        out_file = splitdir / f"{site_name}.geojson"

        single_feat.to_file(out_file, driver='GeoJSON')
