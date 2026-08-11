import pystac_client as pystac
import planetary_computer as pc
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.windows import from_bounds
from pprint import pprint
from shapely import box

def main():
    project_crs = 3857 

    aoi = gpd.read_file('./aoi.geojson').to_crs(project_crs)
    aoi_geom = aoi.union_all().__geo_interface__

    year = 2023

    catalog = pystac.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1/",
        modifier=pc.sign_inplace
    )

    search_res = catalog.search(
        collections=['naip'],
        intersects=aoi_geom,
    )

    search_items = [item.to_dict() for item in search_res.items()]
    search_items = [item for item in search_items if int(item['properties']['naip:year']) == year]

    print(f"Found {(found_count := len(search_items))} tiles that intersect the site. ", end='')
    if found_count < 1:
        print("No tiles found")
        exit(1)
    print(f"Using these naip entities:")
    for si in search_items: print(f"\t{si['id']}")

    try:
        print("Creating virtual raster objects")
        source_rasters = [rasterio.open(si['assets']['image']['href']) for si in search_items]
    except KeyError as ke:
        print(f"Couldn't find image link in search items: {ke}\nSearch item keys example: ")
        pprint(search_items[0], indent=2, sort_dicts=False)
        exit(1)

    aoi_reproj = aoi.to_crs(source_rasters[0].crs)

    breakpoint()

    print("Merging virtual rasters")
    mosaic, transform = merge(
        source_rasters, 
        bounds=tuple(aoi_reproj.total_bounds), 
        masked=True,
        # mem_limit=1000, # use 1gb of memory
    )

    final_profile = source_rasters[1].profile.copy()
    final_profile.update({
        'height': mosaic.shape[1],
        'width': mosaic.shape[2],
        'transform': transform,
    })

    breakpoint()

    with rasterio.open('./mosaic.tif', 'w', **final_profile) as dst:
        dst.write(mosaic)

    breakpoint()

    return

    with MemoryFile() as memfile:
        with memfile.open(**final_profile) as tmp:
            print(f"Writing mosaic to file")
            tmp.write(mosaic)

            window = from_bounds(
                *aoi_reproj.total_bounds, 
                transform=transform
            )

            window.round_offsets(ops='floor').round_lengths(ops='ceil')

            print("Cropping mosaic to aoi")
            cropped, cropped_transform = mask(
                tmp, 
                [box(*aoi_reproj.total_bounds)],
                filled=False,
                crop=False,
            )

            final_profile.update({
                'height': cropped.shape[1],
                'width': cropped.shape[2],
                'transform': cropped_transform,
            })

    output = './naip_aoi.tif'
    with rasterio.open(output, 'w', **final_profile) as dst:
        dst.write(cropped)

    for sr in source_rasters:
        sr.close()

    print(f"Saved clipped raster to {output}")

    breakpoint()

if __name__ == '__main__':
    main()
