"""
Reconvert the bathymetric DEM with proper nodata handling
"""
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import rasterio
import numpy as np

src_path = 'data/2025_GUA-2838_dem.tif'
dst_path = 'data/2025_GUA-2838_dem_cog.tif'

print("="*60)
print("Bathymetric DEM COG Conversion")
print("="*60)

# Use LZW profile for bathymetric DEM (lossless)
profile = cog_profiles.get("lzw")
profile["nodata"] = -32767.0  # KEEP original nodata value!

print(f"\nSource: {src_path}")
print(f"Destination: {dst_path}")
print(f"NoData: {profile['nodata']}")
print(f"Compression: {profile.get('compress', 'none')}")
print(f"Resampling: bilinear")

config = {"GDAL_TIFF_INTERNAL_MASK": True}

print("\nConverting...")
cog_translate(
    src_path,
    dst_path,
    profile,
    in_memory=False,
    web_optimized=False,
    config=config,
    overview_resampling="bilinear"
)

print("✅ COG conversion complete!")

# Verify the conversion
print("\n" + "="*60)
print("Verification")
print("="*60)

with rasterio.open(dst_path) as src:
    print(f"\nCOG Properties:")
    print(f"  NoData: {src.nodata}")
    print(f"  Overviews: {src.overviews(1)}")
    print(f"  Tiled: {src.profile.get('tiled', False)}")
    print(f"  Compression: {src.profile.get('compress', 'none')}")
    
    data = src.read(1)
    valid_data = data[data != src.nodata]
    
    print(f"\nData Statistics:")
    print(f"  Valid pixels: {len(valid_data):,} / {data.size:,} ({len(valid_data)/data.size*100:.1f}%)")
    print(f"  Depth range: {valid_data.min():.2f}m to {valid_data.max():.2f}m")
    print(f"  Mean depth: {valid_data.mean():.2f}m")

print("\n" + "="*60)
print("✅ Ready to view in the orthomosaic viewer!")
print("="*60)
