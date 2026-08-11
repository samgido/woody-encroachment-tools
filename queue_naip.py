"""
Uses the USGS M2M API to add all images under a given spatial extent to the account described in .env
"""
import os
import sys
from time import time
from pathlib import Path
import dotenv
from shapely import Polygon
import geopandas as gpd
from usgs_m2m.usgsMethods import API as M2M_base
from usgs_m2m.usgsDataTypes import (
    GeoJson,
    SpatialFilterGeoJson,
    SceneFilter,
)

from util import mkdir_if_not_exists

# Verify dot env variables
M2M_USERNAME_ENVNAME = "M2M_USERNAME"
M2M_TOKEN_ENVNAME = "M2M_TOKEN"
dotenv.load_dotenv()
if (user := os.getenv(M2M_USERNAME_ENVNAME)) is None or (token := os.getenv(M2M_TOKEN_ENVNAME)) is None:
    print("One or both M2M credentials not found\n")
    print(f"Define both {M2M_USERNAME_ENVNAME} and {M2M_TOKEN_ENVNAME} in a file named '.env' in this directory.")
    exit(1)

class M2M(M2M_base):
    """
    A small wrapper class around the M2M api from https://github.com/MrChebur/usgs-machine-to-machine-API/blob/master/usgs_m2m/usgsMethods.py
    """
    def __init__(self):
        super()
        self.loud_mode = True

    def login(self):
        self.loginToken(user, token)

    def sceneSearchForPolygon(self, shape: Polygon, name: str, datasetName='naip'): 
        if self.loud_mode: print(f"Starting scene search for site {name}")

        # The following lines adapted from 
        #   https://github.com/MrChebur/usgs-machine-to-machine-API/blob/master/usgs_m2m/usgsMethods.py
        ROI = [[list(c) for c in list(shape.boundary.coords)]]
        geoJson = GeoJson(type='Polygon', coordinates=ROI).dict
        spatialFilter = SpatialFilterGeoJson(filterType='geojson', geoJson=geoJson).dict
        sceneFilter = SceneFilter(spatialFilter=spatialFilter).dict

        dawn = time()
        sceneSearchResult = self.sceneSearch(datasetName=datasetName, sceneFilter=sceneFilter)
        dusk = time()
        if self.loud_mode: print(f"\tScene search took {dusk-dawn} seconds")

        return sceneSearchResult

def get_ids(name: str, geom: gpd.GeoSeries):
    result = api.sceneSearchForPolygon(geom, name)
    ids = [res['entityId'] for res in result['data']['results']]

    return ids

def run(api: M2M, gdf: gpd.GeoDataFrame):
    # process each shape in the input 
    for _, r in gdf.iterrows():
        # queue up images under each site shape
        name = r.Site
        geom = r.geometry

        print(f"Creating scene list {name}")
        ids = get_ids(name, geom)
        print(f'\tAdding {len(ids)} entities to the list')

        # idk if this works, seems to
        time.sleep(0.5)
        api.sceneListAdd(name, 'naip', entityIds=ids)

        # add the individual site shape to the output folder
        outdir = mkdir_if_not_exists(f'./out/{name}')
        df = gpd.GeoDataFrame(
            data=[r], 
            columns=gdf.columns, 
            crs=gdf.crs
        )
        df.to_file(outdir / "site.geojson", driver='GeoJSON')

        # create the folder to put the raw naip files into
        mkdir_if_not_exists(f'./out/{name}/raw')

if __name__ == '__main__':
    # process cli input
    from argparse import ArgumentParser
    (parser := ArgumentParser()).add_argument('shapefile')
    args = parser.parse_args()

    if not (inputPath := Path(args.shapefile)).exists() or not inputPath.is_file():
        print("input file not a file")
        exit(1)

    # login to USGS M2M service
    api = M2M()
    print(f"Logging in as {user}"); api.loginToken(user, token)

    # read input
    gdf = gpd.read_file(inputPath)

    if not sys.flags.interactive:
        run(api, gdf)
    else:
        r = list(gdf.iterrows())[0][1]
