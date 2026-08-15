import pystac_client as pystac
import planetary_computer as pc
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds
from pprint import pprint
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import ExitStack
from shapely.geometry import Polygon
from tempfile import NamedTemporaryFile

def get_site_imagery(aoi: gpd.GeoDataFrame, dst_path: Path, year: int=2023) -> bool:
    aoi_geom = aoi.union_all().__geo_interface__

    catalog = pystac.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1/",
        modifier=pc.sign_inplace,
    )

    search_res = catalog.search(
        collections=['naip'],
        intersects=aoi_geom,
    )

    try:
        search_items = [
            item for item 
            in [item.to_dict() for item in search_res.items()]
            if int(item['properties']['naip:year']) == year
        ]

        search_item_ids = [si['id'] for si in search_items]
        search_item_hrefs = [si['assets']['image']['href'] for si in search_items]
    except KeyError as ke:
        print(f"Couldn't find image link in search items: {ke}\nSearch item keys example: ")
        pprint(search_items[0], indent=2, sort_dicts=False)
        return False
    except:
        print("Error occurred")
        return False

    print(f"Found {(found_count := len(search_items))} valid tiles that intersect the site from. {year}", end='')
    if found_count < 1:
        print("\n\tNo tiles found! Stopping execution.")
        return False
    print(f"Using these NAIP entities:")
    for id in search_item_ids: print(f"\t{id}")

    print('Downloading window images')
    # Window raster files are kept here, and deleted when the context is finished
    with TemporaryDirectory() as tmpdir: 
        tmpdir = Path(tmpdir)

        window_raster_paths = []
        for id, href in zip(search_item_ids, search_item_hrefs):
            # Open remote source raster
            source_raster = rasterio.open(href)

            window = from_bounds(
                *aoi.to_crs(source_raster.crs).total_bounds,
                transform = source_raster.transform
            )

            print(f'\tDownloading window data for entity {id}', end='', flush=True)
            data = source_raster.read(window=window)
            print(' -- Complete')

            transform = source_raster.window_transform(window)
            profile = source_raster.profile.copy()
            profile.update(
                driver="GTiff",
                height=data.shape[1],
                width=data.shape[2],
                transform=transform,
                count=4
            )

            raster_path = tmpdir / f'{id}.tif'
            print(f'\t\tWriting to {raster_path.name}', end='', flush=True)
            with rasterio.open(raster_path, 'w', **profile) as dst:
                dst.write(data)
            print(' -- Complete')

            window_raster_paths.append(raster_path)

        # Open each window raster for merging, 
        # use an exit stack to make sure all files 
        # are closed, so they can be cleaned up later
        with ExitStack() as stack:
            window_rasters = [
                stack.enter_context(
                    rasterio.open(wrp)
                )
                for wrp in window_raster_paths
            ]
            mosaic, transform = merge(window_rasters)
            mosaic_profile = source_raster.profile.copy()
            mosaic_profile.update(
                driver="GTiff",
                height=mosaic.shape[1],
                width=mosaic.shape[2],
                transform=transform,
                count=4 # keep 4 here, incase its wanted elsewhere
            )

            breakpoint()

            with rasterio.open(dst_path, 'w', **mosaic_profile) as dst:
                dst.write(mosaic)

    return True
    
if __name__ == '__main__':
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

    dir = None
    if (t := Path(Path.home() / 'Downloads')).is_dir():
        dir = t
    else: 
        dir = Path.home()

    tf = NamedTemporaryFile(delete=False, dir=dir, suffix='.tiff')
    tf.close()

    print(f'Downloading example image to {tf.name}')
    get_site_imagery(aoi, Path(tf.name))
