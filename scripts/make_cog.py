#!/usr/bin/env python
"""
make_cog.py — Convert a GeoTIFF to a Cloud Optimized GeoTIFF (COG).

Examples (Windows CMD):
  python make_cog.py ^
    --src "C:\\path\\to\\2025_GUA-2838_mos.tif" ^
    --dst "C:\\path\\to\\2025_GUA-2838_mos_cog.tif" ^
    --resampling bilinear

For single-band DEMs you can set nodata (within dtype range), e.g.:
  python make_cog.py --src dem.tif --dst dem_cog.tif --nodata -9999 --resampling bilinear
"""

import argparse
import os
import sys
import warnings

import rasterio
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles


def choose_profile(band_count: int, forced: str | None) -> dict:
    if forced:
        if forced not in {"jpeg", "lzw", "zstd"}:
            raise ValueError("--profile must be one of: jpeg|lzw|zstd")
        return cog_profiles.get(forced)
    # Auto: RGB(A) -> jpeg, everything else -> lzw
    return cog_profiles.get("jpeg" if band_count in (3, 4) else "lzw")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, help="Input GeoTIFF")
    p.add_argument("--dst", required=True, help="Output COG path")
    p.add_argument("--profile", help="Force profile: jpeg|lzw|zstd")
    p.add_argument("--nodata", type=float, default=None,
                   help="Set nodata for single-band numeric rasters (ignored for multi-band RGB)")
    p.add_argument("--resampling", default="bilinear",
                   help="Overview resampling: nearest|bilinear|cubic|lanczos|average|mode|max|min|med|q1|q3")
    p.add_argument("--web-optimized", action="store_true",
                   help="Write WebMercator-friendly layout (usually leave off)")
    return p.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.src):
        print(f"ERROR: src not found: {args.src}", file=sys.stderr)
        sys.exit(1)

    with rasterio.open(args.src) as src:
        band_count = src.count
        dtype = src.dtypes[0]  # assume all bands same dtype
        src_nodata = src.nodata  # Get source nodata value

    profile = choose_profile(band_count, args.profile)

    # Internal mask is generally what we want for RGB and is safe otherwise
    config = {"GDAL_TIFF_INTERNAL_MASK": True}

    # Decide whether nodata is valid to apply
    nodata_to_use = args.nodata if args.nodata is not None else src_nodata
    
    if nodata_to_use is not None:
        if band_count == 1:
            # Only apply if nodata is sane for the dtype (or dtype is float)
            if "float" in dtype:
                profile["nodata"] = nodata_to_use
                if args.nodata is None:
                    print(f"Auto-detected nodata: {nodata_to_use}")
            else:
                ranges = {
                    "uint8": (0, 255),
                    "uint16": (0, 65535),
                    "int16": (-32768, 32767),
                    "uint32": (0, 4294967295),
                    "int32": (-2147483648, 2147483647),
                }
                lo, hi = ranges.get(dtype, (None, None))
                if lo is not None and lo <= nodata_to_use <= hi:
                    profile["nodata"] = nodata_to_use
                    if args.nodata is None:
                        print(f"Auto-detected nodata: {nodata_to_use}")
                else:
                    warnings.warn(f"nodata {nodata_to_use} not valid for dtype {dtype}; ignoring.")
        else:
            warnings.warn("nodata ignored for multi-band imagery; using internal mask instead.")

    # IMPORTANT: rio-cogeo v5 expects the *string* name for overview_resampling
    overview_resampling = args.resampling  # e.g., "bilinear", "nearest", ...

    # Create COG with overviews
    cog_translate(
        args.src,
        args.dst,
        profile,
        in_memory=False,
        web_optimized=bool(args.web_optimized),
        config=config,
        overview_resampling=overview_resampling,  # pass string name, NOT enum/int
    )
    print(
        f"COG written: {args.dst} "
        f"(bands={band_count}, dtype={dtype}, compress={profile.get('compress','none')}, "
        f"resampling={overview_resampling})"
    )


if __name__ == "__main__":
    main()
