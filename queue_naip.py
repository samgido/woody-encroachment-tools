"""
Uses the USGS M2M API to add all images under a given spatial extent to the account described in .env
"""

import dotenv
import os

M2M_USERNAME_ENVNAME = "M2M_USERNAME"
M2M_TOKEN_ENVNAME = "M2M_TOKEN"
dotenv.load_dotenv()
if (user := os.getenv(M2M_USERNAME_ENVNAME)) is None or (token := os.getenv(M2M_TOKEN_ENVNAME)) is None:
    print("One or both M2M credentials not found\n")
    print(f"Define both {M2M_USERNAME_ENVNAME} and {M2M_TOKEN_ENVNAME} in a file named '.env' in this directory.")
    exit(1)

import json 
from pathlib import Path
from usgs_m2m.usgsMethods import API as M2M
from usgs_m2m.otherMethods import otherMethods
from usgs_m2m.usgsDataTypes import (
    GeoJson,
    SpatialFilterGeoJson,
    AcquisitionFilter,
    SceneFilter,
)
import geopandas as gpd

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument('shapefile')
args = parser.parse_args()

input_path = Path(args.shapefile)
gdf = gpd.read_file(input_path)

datasetName = 'naip'
api = M2M()
api.loginToken(user, token)

row = list(gdf.iterrows())[0][1]

def process_row(row):
    geoJson = row.geometry.__geo_interface__
    spatialFilter = SpatialFilterGeoJson(filterType='geojson', geoJson=geoJson).dict
    sceneFilter = SceneFilter(spatialFilter=spatialFilter).dict

    sceneSearchResult = api.sceneSearch(datasetName=datasetName, sceneFilter=sceneFilter)

    entityIds = [res['entityId'] for res in sceneSearchResult['data']['results']]

process_row(row)

def run():
    for _, row in gdf.iterrows():
        process_row(row)

