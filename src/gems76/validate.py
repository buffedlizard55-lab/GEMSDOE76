"""Comprehensive 16-gate GeoTIFF + single-GeoTIFF ZIP preflight validator (`gems76`).
Directly guards against the DrivenData portal error `"Predicted values must be in range [0, 1]"`
as well as CRS, geotransform, shape, NaN/Inf, footprint leak, and mapped-catalogue overlap."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import numpy as np
import rasterio


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def run_strict_submission_preflight(
    tif_path: Path,
    zip_path: Path,
    sample_path: Path,
    existing_faults_path: Path,
    submission_name: str,
    submission_note: str,
) -> dict:
    with rasterio.open(sample_path) as s_ref:
        ref_crs = s_ref.crs
        ref_transform = s_ref.transform
        ref_shape = (s_ref.height, s_ref.width)
        ref_arr = s_ref.read(1)
        fp = np.isfinite(ref_arr)

    with rasterio.open(existing_faults_path) as s_cat:
        cat = (s_cat.read(1) > 0) & fp

    with rasterio.open(tif_path) as s_pred:
        pred_crs = s_pred.crs
        pred_transform = s_pred.transform
        pred_shape = (s_pred.height, s_pred.width)
        pred_count = s_pred.count
        pred_dtype = str(s_pred.dtypes[0])
        pred_nodata = s_pred.nodata
        pred_comp = str(s_pred.compression)
        arr = s_pred.read(1)

    n_total = int(arr.size)
    n_nan_total = int(np.isnan(arr).sum())
    n_nan_inside_fp = int(np.isnan(arr[fp]).sum())
    n_inf_total = int(np.isinf(arr).sum())
    finite_all = bool(np.isfinite(arr).all())
    vmin = float(np.nanmin(arr)) if n_nan_total < n_total else float("nan")
    vmax = float(np.nanmax(arr)) if n_nan_total < n_total else float("nan")
    n_lt_0 = int(np.sum(np.isfinite(arr) & (arr < 0.0)))
    n_gt_1 = int(np.sum(np.isfinite(arr) & (arr > 1.0)))
    n_pos_inside = int(np.sum((arr > 0.0) & fp))
    n_pos_outside = int(np.sum((arr > 0.0) & (~fp)))
    n_pos_on_catalogue = int(np.sum((arr > 0.0) & cat))

    tif_bytes = tif_path.read_bytes()
    tif_sha = hashlib.sha256(tif_bytes).hexdigest()
    zip_bytes = zip_path.read_bytes()
    zip_sha = hashlib.sha256(zip_bytes).hexdigest()

    with zipfile.ZipFile(zip_path) as zf:
        z_names = zf.namelist()
        zip_single_tif_ok = (len(z_names) == 1) and (z_names[0] == tif_path.name)
        zip_byte_identical_ok = zip_single_tif_ok and (zf.read(z_names[0]) == tif_bytes)

    checks = {
        "single_band_count_eq_1": pred_count == 1,
        "exact_shape_3730x3292": pred_shape == ref_shape == (3730, 3292),
        "exact_crs_epsg_32611": (pred_crs == ref_crs) and (str(pred_crs) == "EPSG:32611"),
        "exact_affine_geotransform": pred_transform == ref_transform,
        "dtype_float32": pred_dtype == "float32",
        "zero_nan_inside_footprint": n_nan_inside_fp == 0,
        "zero_nan_entire_raster_portal_safe": n_nan_total == 0,
        "zero_inf_entire_raster": n_inf_total == 0,
        "all_pixels_strictly_ge_0": finite_all and (n_lt_0 == 0) and (vmin >= 0.0),
        "all_pixels_strictly_le_1": finite_all and (n_gt_1 == 0) and (vmax <= 1.0),
        "zero_positive_outside_footprint": n_pos_outside == 0,
        "zero_positive_on_known_catalogue": n_pos_on_catalogue == 0,
        "non_trivial_positive_support": 5_000 <= n_pos_inside <= 150_000,
        "submission_name_valid": 1 <= len(submission_name.strip()) <= 140,
        "submission_note_le_140_chars": 1 <= len(submission_note.strip()) <= 140,
        "zip_single_byte_identical_geotiff": bool(zip_byte_identical_ok),
    }

    all_passed = all(checks.values())
    return {
        "all_checks_passed": all_passed,
        "portal_range_error_prevented": bool(
            checks["zero_nan_entire_raster_portal_safe"]
            and checks["all_pixels_strictly_ge_0"]
            and checks["all_pixels_strictly_le_1"]
        ),
        "tif_file": tif_path.name,
        "tif_bytes": len(tif_bytes),
        "tif_sha256": tif_sha,
        "zip_file": zip_path.name,
        "zip_bytes": len(zip_bytes),
        "zip_sha256": zip_sha,
        "crs": str(pred_crs),
        "shape": list(pred_shape),
        "geotransform": list(pred_transform)[:6],
        "dtype": pred_dtype,
        "compression": pred_comp,
        "nodata_tag": pred_nodata,
        "min_value": vmin,
        "max_value": vmax,
        "n_total_pixels": n_total,
        "n_valid_footprint_pixels": int(fp.sum()),
        "n_nan_inside_footprint": n_nan_inside_fp,
        "n_nan_entire_raster": n_nan_total,
        "n_inf_entire_raster": n_inf_total,
        "n_values_below_0": n_lt_0,
        "n_values_above_1": n_gt_1,
        "n_positive_inside_footprint": n_pos_inside,
        "n_positive_outside_footprint": n_pos_outside,
        "n_positive_on_mapped_catalogue": n_pos_on_catalogue,
        "submission_name": submission_name,
        "submission_note": submission_note,
        "submission_note_length": len(submission_note),
        "checks": checks,
    }
