import pystac_client as pystac
import planetary_computer as pc
import geopandas as gpd
import rasterio
import rasterio.io as IO
import rasterio.merge as Merge
import rasterio.windows as Windows
import rasterio.transform as Transform
import rasterio.enums as Enums
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from time import time
from pprint import pprint
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import ExitStack
from shapely.geometry import Polygon
from tempfile import NamedTemporaryFile

@dataclass
class RemoteRasterInfo:
    id: str
    image_href: str

def download_windowed_tile(
    aoi: gpd.GeoDataFrame, 
    remote_raster: RemoteRasterInfo, 
    max_spatial_res: tuple[float, float], 
    out_dir: Path
):
    try:
        id = remote_raster.id
        url = remote_raster.image_href

        with rasterio.open(url) as src:
            src: IO.DatasetReader = src

            window = Windows.from_bounds(
                *aoi.to_crs(src.crs).total_bounds,
                transform=src.transform
            )
            x_res, y_res = src.res

            # take the larger pixels size 
            # between the raster and the given 
            # max spatial resolution
            #
            # A higher spatial resolution means a smaller
            # pixel size, which is confusing 
            # so the maximum resolution parameter
            # is the smallest the pixels are allowed 
            # to be in the resulting raster 
            target_res = (
                max(x_res, max_spatial_res[0]),
                max(y_res, max_spatial_res[1])
            )

            # contain window to be within this raster
            window_intersect = Windows.intersection(
                window, 
                Windows.Window(0, 0, src.width, src.height)
            )

            # size in meters of the image
            image_width_m = window_intersect.width * x_res
            image_height_m = window_intersect.height * y_res

            # size in pixels of the image
            image_width_px = round(image_width_m / target_res[0])
            image_height_px = round(image_height_m / target_res[1])

            data = src.read(
                window=window_intersect,
                out_shape=(4, image_height_px, image_width_px),
                resampling=Enums.Resampling.average
            )

            # Get the bounds of the window, and get a new 
            # transform based on the new resolution
            window_intersect_bounds = Windows.bounds(
                window_intersect,
                src.transform
            )
            new_transform = Transform.from_bounds(
                *window_intersect_bounds,
                width=image_width_px,
                height=image_height_px
            )

            new_profile = src.profile.copy()
            new_profile.update(
                driver='GTiff',
                height=data.shape[1],
                width=data.shape[2],
                transform=new_transform,
                count=4
            )

            dst_fp = out_dir / f'{id}.tif'
            with rasterio.open(dst_fp, 'w', **new_profile) as dst:
                dst.write(data)

        return dst_fp
    except Exception as e:
        print(f"\nException caught while downloading windowed tile {id}: {e}")
        return None

def fetch_remote_rasters(aoi: gpd.GeoDataFrame, year: int):
    try:
        catalog = pystac.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1/",
            modifier=pc.sign_inplace,
        )

        aoi_bounds = aoi.to_crs(epsg=4326).total_bounds
        search_res = catalog.search(
            collections=['naip'],
            bbox=aoi_bounds,
        )

        try:
            remote_rasters_info = [
                RemoteRasterInfo(si.id, si.assets['image'].href)
                for si in search_res.item_collection()
                if si.properties['naip:year'] == str(year)
            ]
        except KeyError as ke:
            print(f"Couldn't find image link in search items: {ke}\nSearch item keys example: ")
            pprint(remote_rasters_info[0], indent=2, sort_dicts=False)
            return None
        except Exception as e:
            print(f"Error occurred while reading from search items: {e}")
            return None

        print(f"Found {(found_count := len(remote_rasters_info))} valid tiles that intersect the site from {year}. ", end='')
        if found_count < 1:
            print("\n\tNo tiles found!")
            return None
        print(f"Using these NAIP entities:")
        print('\n'.join([f'\t{rri.id}' for rri in remote_rasters_info]))

        return remote_rasters_info
    except Exception as e:
        print(f"Error fetching remote rasters: {e}")
        return None

def get_site_imagery(
    aoi: gpd.GeoDataFrame, 
    max_spatial_res: tuple[float, float], 
    dst_path: Path, 
    max_workers: int,
    year: int,
) -> bool:
    """
    Downloads the NAIP imagery raster containing the site to dst_path

    Returns True on success, False on failure
    """
    try:
        remote_rasters_info = fetch_remote_rasters(aoi, year)
        if not remote_rasters_info:
            return False

        remote_raster_count = len(remote_rasters_info)

        with TemporaryDirectory(delete=False) as temp_dir: 
            temp_dir = Path(temp_dir)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                window_raster_paths = []

                print(f"Adding images into download queue with {max_workers} workers"); dawn=time()
                futures = [
                    executor.submit(download_windowed_tile, aoi, rri, max_spatial_res, temp_dir)
                    for rri in remote_rasters_info
                ]

                for future in as_completed(futures):
                    try:
                        res = future.result()
                        if res:
                            print(f"\tDownload success: {res}")
                            window_raster_paths.append(res)
                        else:
                            print(f"\tDownload failed.")
                    except Exception as e:
                        print(f"Exception: {e}")
            downloaded_count = len(window_raster_paths)
            dusk=time(); print(f"Downloading {downloaded_count}/{remote_raster_count} windowed tiles took {dusk-dawn} seconds.")

            if downloaded_count < remote_raster_count:
                print(f"Error: Not all remote raster windows downloaded")
                return False

            # Open each window raster for merging, 
            # use an exit stack to make sure all files 
            # are closed, so they can be cleaned up later
            with ExitStack() as stack:
                window_rasters: list[IO.DatasetReader] = [
                    stack.enter_context(rasterio.open(wrp))
                    for wrp in window_raster_paths
                ]

                mosaic, transform = Merge.merge(window_rasters)

                with rasterio.open(remote_rasters_info[0].image_href) as src:
                    mosaic_profile = src.profile.copy()
                mosaic_profile.update(
                    driver="GTiff",
                    height=mosaic.shape[1],
                    width=mosaic.shape[2],
                    transform=transform,
                    count=4 # keep 4 here, incase its wanted elsewhere
                )

                with rasterio.open(dst_path, 'w', **mosaic_profile) as dst:
                    dst.write(mosaic)
    except Exception as e:
        print(f"Error downloading site imagery: {e}")
        return False
    finally:
        print("Site imagery downloaded and ready.")
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
    if (t := Path(Path.home() / 'Downloads')).is_dir(): dir = t
    else: dir = Path.home()

    imagery_tf = NamedTemporaryFile(delete=False, dir=dir, suffix='.tiff')
    imagery_tf.close()


    print(f'Downloading example image to {imagery_tf.name}')
    res = get_site_imagery(aoi, (2.0, 2.0), Path(imagery_tf.name))

    if res: print("\tDownload success")
    else:   print("\tDownload failed")

    aoi_tf = NamedTemporaryFile(delete=False, dir=dir, suffix='.geojson')
    aoi_tf.close()

    aoi.to_file(aoi_tf.name, driver='GeoJson')
    print(f'Saved example AOI to {aoi_tf.name}')
