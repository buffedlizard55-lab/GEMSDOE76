"""GEMSDOE76 pure label-free physical feature stack (H76-1, H76-2, H76-3).

Stores ``(5_167_373, 62)`` float32 features directly onto an ``np.memmap`` in
``.cache/gems76/`` so peak RSS stays comfortably below 650 MiB on 3.8 GiB RAM.
Zero label information is touched anywhere in this module.
"""
from __future__ import annotations

import csv
import gc
import io
import json
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as warp_transform
from scipy.ndimage import convolve, gaussian_filter

GRID_SHAPE = (3730, 3292)

FEATURE_GROUPS: dict[str, list[str]] = {
    "H76_1_PiedmontToe_Scarp": [
        "det_elev",
        "det_elev_slope",
        "b19_hp3",
        "b19_hp12",
        "b12_lap1_concave",
        "b12_lap3_flexure",
        "dem100_lap_concave",
        "ptcf_concave_toe_idx",
        "lid_valid",
        "lid_step",
        "lid_ex",
        "lid_down",
        "lid_up",
        "lid_cross",
        "lid_relief",
        "lid_coh",
        "lid_dipole_norm",
        "lid_concave_excess",
        "lid_tect_vs_fluv",
        "lid_piedmont_step",
        "t10_slope_p90",
        "t10_slope_max",
        "t10_steep_frac",
        "t10_curv_absmax",
        "t10_aspect_coh",
        "t10_hs_lineament",
        "t10_piedmont_step",
        "scarp_worm_600m",
        "scarp_worm_1500m",
        "scarp_worm_aniso_1500m",
    ],
    "H76_2_MagGrav_TiltWorms": [
        "mag_anom_hp15",
        "rtp_hp15",
        "tmi_hg_hp15",
        "tmi_vg_hp15",
        "iso_grav_slope_hp15",
        "iso_grav_vg_hp15",
        "iso_grav_hp15",
        "iso_grav_hg_hp15",
        "depth_base_hp15",
        "grad_depth_base",
        "tmi_shallow_res",
        "cos_tdr_mag",
        "grad_tdr_mag",
        "cos_tdr_grav",
        "mag_worm_1600m",
        "grav_worm_1600m",
    ],
    "H76_3_FluvialChi_HydroStrain": [
        "chi_step_smooth",
        "chi_ksn_smooth",
        "chi_knick_density",
        "chi_knick_worm_1400m",
        "rad_K",
        "rad_ThK_alteration",
        "rad_UTh",
        "rad_TC_hp15",
        "mag_destruct_K_alter",
        "cond_surf_hp15",
        "geod_2ndinv",
        "geod_shearrate",
        "geod_dilaterate",
        "eq_density",
        "gdr_thermal_plume_800m",
        "gdr_thermal_plume_2200m",
    ],
}

FEATURE_NAMES: list[str] = (
    FEATURE_GROUPS["H76_1_PiedmontToe_Scarp"]
    + FEATURE_GROUPS["H76_2_MagGrav_TiltWorms"]
    + FEATURE_GROUPS["H76_3_FluvialChi_HydroStrain"]
)


def _clean_band(raw: np.ndarray, fp: np.ndarray) -> tuple[np.ndarray, int]:
    """Sanitize finite float32 nodata sentinels (e.g. -3.4028235e38) inside footprint."""
    x = np.asarray(raw, dtype=np.float32)
    good = fp & np.isfinite(x) & (np.abs(x) < 1e15)
    n_bad_in_fp = int((fp & ~good).sum())
    med = np.float32(float(np.median(x[good]))) if good.any() else np.float32(0.0)
    out = np.where(good, x, np.where(fp, med, np.float32(0.0))).astype(np.float32)
    return out, n_bad_in_fp


clean_band = _clean_band


def _norm_gauss(arr: np.ndarray, valid: np.ndarray, sigma: float, v_smooth_cache: dict | None = None) -> np.ndarray:
    """Normalized Gaussian convolution preventing footprint-boundary edge bleed."""
    num = gaussian_filter(np.where(valid, arr, 0.0).astype(np.float32), sigma=sigma, mode="nearest")
    if v_smooth_cache is not None and sigma in v_smooth_cache:
        den = v_smooth_cache[sigma]
    else:
        den = np.maximum(gaussian_filter(valid.astype(np.float32), sigma=sigma, mode="nearest"), 1e-4)
        if v_smooth_cache is not None:
            v_smooth_cache[sigma] = den
    return (num / den).astype(np.float32)


def _steerable_worm(field_2d: np.ndarray, valid: np.ndarray, half_len_px: int, n_angles: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Memory-lean 8-azimuth 1D line integral max along strike and orthogonal anisotropy."""
    arr = np.where(valid, field_2d, 0.0).astype(np.float32)
    size = 2 * half_len_px + 1
    c = half_len_px
    half_n = n_angles // 2
    along_max = np.full(arr.shape, -1e30, dtype=np.float32)
    aniso = np.zeros(arr.shape, dtype=np.float32)

    for k_idx in range(half_n):
        k1 = np.zeros((size, size), dtype=np.float32)
        k2 = np.zeros((size, size), dtype=np.float32)
        t1 = k_idx * np.pi / n_angles
        t2 = (k_idx + half_n) * np.pi / n_angles
        for s in np.linspace(-half_len_px, half_len_px, 2 * half_len_px + 1):
            r1 = int(round(c + s * np.sin(t1)))
            c1 = int(round(c + s * np.cos(t1)))
            if 0 <= r1 < size and 0 <= c1 < size:
                k1[r1, c1] += 1.0
            r2 = int(round(c + s * np.sin(t2)))
            c2 = int(round(c + s * np.cos(t2)))
            if 0 <= r2 < size and 0 <= c2 < size:
                k2[r2, c2] += 1.0
        k1 /= k1.sum()
        k2 /= k2.sum()
        r_a = convolve(arr, k1, mode="nearest")
        r_b = convolve(arr, k2, mode="nearest")
        m_a = r_a > along_max
        if m_a.any():
            along_max[m_a] = r_a[m_a]
            aniso[m_a] = r_a[m_a] - r_b[m_a]
        m_b = r_b > along_max
        if m_b.any():
            along_max[m_b] = r_b[m_b]
            aniso[m_b] = r_b[m_b] - r_a[m_b]
        del r_a, r_b, m_a, m_b
    return along_max, aniso


def _read_dbf_shp_points(zf: zipfile.ZipFile, shp_member: str, dbf_member: str):
    """Minimal pure-stdlib shapefile point + DBF attribute reader."""
    shp_bytes = zf.read(shp_member)
    dbf_bytes = zf.read(dbf_member)

    num_rec, header_len, rec_len = struct.unpack("<IHH", dbf_bytes[4:12])
    fields = []
    pos = 32
    while pos < header_len - 1 and dbf_bytes[pos] != 0x0D:
        fname = dbf_bytes[pos:pos + 11].split(b"\x00", 1)[0].decode("latin1").strip()
        ftype = chr(dbf_bytes[pos + 11])
        flen = dbf_bytes[pos + 16]
        fields.append((fname, ftype, flen))
        pos += 32

    records = []
    rpos = header_len
    for _ in range(num_rec):
        if rpos + rec_len > len(dbf_bytes):
            break
        row = {}
        cpos = rpos + 1
        for fname, _ft, flen in fields:
            row[fname] = dbf_bytes[cpos:cpos + flen].decode("latin1", errors="ignore").strip()
            cpos += flen
        records.append(row)
        rpos += rec_len

    pts = []
    spos = 100
    while spos + 12 <= len(shp_bytes):
        _rec_no, content_words = struct.unpack(">II", shp_bytes[spos:spos + 8])
        clen = content_words * 2
        body = shp_bytes[spos + 8:spos + 8 + clen]
        if len(body) >= 20 and struct.unpack("<I", body[:4])[0] in (1, 11, 21):
            x, y = struct.unpack("<dd", body[4:20])
            pts.append((x, y))
        else:
            pts.append((np.nan, np.nan))
        spos += 8 + clen
    return pts, records


def _build_gdr_thermal_rasters(ext_dir: Path, fp: np.ndarray, vcache: dict) -> tuple[np.ndarray, np.ndarray]:
    """Build label-free multi-scale thermal/geochemical upflow rasters from DOE GDR #1391."""
    H, W = fp.shape
    imp = np.zeros((H, W), dtype=np.float32)

    ws_path = ext_dir / "gdr_wellspring_in_footprint.csv"
    if ws_path.is_file():
        with ws_path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    r = int(float(row["row"]))
                    c = int(float(row["col"]))
                except (KeyError, ValueError):
                    continue
                if not (0 <= r < H and 0 <= c < W and fp[r, c]):
                    continue
                w = 0.0
                for col_k, thresh, scale in (
                    ("temp_c", 25.0, 45.0),
                    ("geothermquartz_c", 70.0, 90.0),
                    ("geothermchalc_c", 60.0, 80.0),
                    ("geothermcat_c", 80.0, 100.0),
                ):
                    try:
                        val = float(row.get(col_k, "") or "nan")
                        if np.isfinite(val) and val >= thresh:
                            w = max(w, min(2.0, 0.5 + (val - thresh) / scale))
                    except ValueError:
                        pass
                tc_str = (row.get("thermalclass") or "").lower()
                if any(k in tc_str for k in ("hot", "warm", "therm")):
                    w = max(w, 0.8)
                if w > 0.0:
                    imp[r, c] += np.float32(w)

    pr_zip = ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    if pr_zip.is_file():
        with zipfile.ZipFile(pr_zip) as zf:
            shp_m = [m for m in zf.namelist() if m.endswith(".shp")][0]
            dbf_m = [m for m in zf.namelist() if m.endswith(".dbf")][0]
            pts, recs = _read_dbf_shp_points(zf, shp_m, dbf_m)
            xs, ys, ws = [], [], []
            for (lon, lat), rec in zip(pts, recs):
                if not (np.isfinite(lon) and np.isfinite(lat)):
                    continue
                try:
                    anom = float(rec.get("F2mDAB", "") or "nan")
                except ValueError:
                    anom = np.nan
                if np.isfinite(anom) and anom >= 1.5:
                    xs.append(lon)
                    ys.append(lat)
                    ws.append(min(2.0, 0.6 + (anom - 1.5) / 3.0))
            if xs:
                ux, uy = warp_transform("EPSG:4269", "EPSG:32611", xs, ys)
                for x_m, y_m, w in zip(ux, uy, ws):
                    rr = int((4508550.0 - y_m) // 100.0)
                    cc = int((x_m - 243350.0) // 100.0)
                    if 0 <= rr < H and 0 <= cc < W and fp[rr, cc]:
                        imp[rr, cc] += np.float32(w)

    pa_zip = ext_dir / "paleo_geothermal_regional.zip"
    if pa_zip.is_file():
        with zipfile.ZipFile(pa_zip) as zf:
            csv_m = [m for m in zf.namelist() if m.endswith(".csv")]
            if csv_m:
                txt = zf.read(csv_m[0]).decode("utf-8", errors="ignore")
                xs, ys = [], []
                for row in csv.DictReader(io.StringIO(txt)):
                    for xk, yk in (("Longitude", "Latitude"), ("lon", "lat"), ("X", "Y"), ("x", "y")):
                        if xk in row and yk in row:
                            try:
                                xv, yv = float(row[xk]), float(row[yk])
                                if np.isfinite(xv) and np.isfinite(yv):
                                    xs.append(xv)
                                    ys.append(yv)
                            except ValueError:
                                pass
                            break
                if xs:
                    ux, uy = warp_transform("EPSG:4269", "EPSG:32611", xs, ys)
                    for x_m, y_m in zip(ux, uy):
                        rr = int((4508550.0 - y_m) // 100.0)
                        cc = int((x_m - 243350.0) // 100.0)
                        if 0 <= rr < H and 0 <= cc < W and fp[rr, cc]:
                            imp[rr, cc] += np.float32(1.0)

    imp = np.log1p(imp)
    return _norm_gauss(imp, fp, sigma=8.0, v_smooth_cache=vcache), _norm_gauss(imp, fp, sigma=22.0, v_smooth_cache=vcache)


def build_or_load_feature_memmap(
    work_dir: Path | str = "/home/user/GEMSDOE76/.cache/gems76",
    gems_data_dir: Path | str = "/tmp/gems_data",
    ext_root: Path | str = "/tmp/ref/60GEMSDOE/data",
    force: bool = False,
) -> tuple[np.memmap, list[str], np.ndarray]:
    """Compute or reload cached float32 memmap ``(N_fp, 62)`` for all active footprint cells."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    gdir = Path(gems_data_dir)
    eroot = Path(ext_root)
    ext_dir = eroot / "external"

    with rasterio.open(gdir / "sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
    fp_idx = np.flatnonzero(fp.ravel())
    n_fp = int(fp_idx.size)
    n_feats = len(FEATURE_NAMES)

    mm_path = work / "stage1_features_v1.f32"
    meta_path = work / "stage1_features_v1.json"
    if not force and mm_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if meta.get("feature_names") == FEATURE_NAMES and meta.get("n_fp") == n_fp:
            mm = np.memmap(mm_path, mode="r", dtype=np.float32, shape=(n_fp, n_feats))
            return mm, list(FEATURE_NAMES), fp

    mm = np.memmap(mm_path, mode="w+", dtype=np.float32, shape=(n_fp, n_feats))
    col_map = {name: idx for idx, name in enumerate(FEATURE_NAMES)}
    sentinel_audit: dict[str, int] = {}
    vcache: dict[float, np.ndarray] = {}

    def _put(name: str, arr2d: np.ndarray) -> None:
        vals = np.asarray(arr2d, dtype=np.float32).ravel()[fp_idx]
        vals = np.where(np.isfinite(vals), vals, 0.0).astype(np.float32)
        mm[:, col_map[name]] = vals

    b_src = np.memmap(gdir / "bands19.f32", mode="r", dtype=np.float32, shape=(19, *GRID_SHAPE))

    # --- Domain 1: H76-1 Piedmont-Toe Concave Flexure & Tectonic Scarp Persistence ---
    b12, bad12 = _clean_band(b_src[11], fp)
    b19, bad19 = _clean_band(b_src[18], fp)
    sentinel_audit["b12_det_elev"] = bad12
    sentinel_audit["b19_det_elev_slope"] = bad19

    b19_g3 = _norm_gauss(b19, fp, 3.0, vcache)
    b19_g12 = _norm_gauss(b19, fp, 12.0, vcache)
    b19_hp3 = b19 - b19_g3
    b19_hp12 = b19 - b19_g12

    b12_lap1 = _norm_gauss(b12, fp, 4.0, vcache) - _norm_gauss(b12, fp, 1.0, vcache)
    b12_lap3 = _norm_gauss(b12, fp, 10.0, vcache) - _norm_gauss(b12, fp, 3.0, vcache)

    with rasterio.open(eroot / "geodawn_dem_a2_100m.tif") as dsrc:
        dem100, bad_dem = _clean_band(dsrc.read(1), fp)
    sentinel_audit["geodawn_dem_a2_100m"] = bad_dem
    dem100_lap = _norm_gauss(dem100, fp, 8.0, vcache) - _norm_gauss(dem100, fp, 2.0, vcache)

    slope_env = np.exp(-0.5 * np.clip(((b19_g3 - 5.8) / 4.2) ** 2, 0.0, 50.0)).astype(np.float32)
    ptcf = np.maximum(b12_lap1, 0.0) * np.maximum(-b19_hp3 + 0.5, 0.0) * slope_env

    _put("det_elev", b12)
    _put("det_elev_slope", b19)
    _put("b19_hp3", b19_hp3)
    _put("b19_hp12", b19_hp12)
    _put("b12_lap1_concave", b12_lap1)
    _put("b12_lap3_flexure", b12_lap3)
    _put("dem100_lap_concave", dem100_lap)
    _put("ptcf_concave_toe_idx", ptcf)
    del b12, b19, b19_g3, b19_g12, b19_hp3, b19_hp12, b12_lap1, b12_lap3, dem100, dem100_lap, slope_env, ptcf
    gc.collect()

    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as lsrc:
        lid = lsrc.read().astype(np.float32) / np.float32(255.0)
    lid_valid = (lid[11] > 0.5) & fp
    lid_tvf = (np.maximum(lid[5], 1.35 * lid[6]) * (0.30 + lid[9]) / (lid[7] + 0.08)).astype(np.float32)
    lid_pstep = (lid[2] / np.sqrt(lid[8] + 0.04)).astype(np.float32)
    lid_dip = ((lid[4] + lid[3]) / (lid[8] + 0.05)).astype(np.float32)
    lid_conc = (lid[4] - lid[3]).astype(np.float32)

    _put("lid_valid", lid_valid.astype(np.float32))
    _put("lid_step", np.where(lid_valid, lid[2], 0.0))
    _put("lid_ex", np.where(lid_valid, lid[0], 0.0))
    _put("lid_down", np.where(lid_valid, lid[5], 0.0))
    _put("lid_up", np.where(lid_valid, lid[6], 0.0))
    _put("lid_cross", np.where(lid_valid, lid[7], 0.0))
    _put("lid_relief", np.where(lid_valid, lid[8], 0.0))
    _put("lid_coh", np.where(lid_valid, lid[9], 0.0))
    _put("lid_dipole_norm", np.where(lid_valid, lid_dip, 0.0))
    _put("lid_concave_excess", np.where(lid_valid, lid_conc, 0.0))
    _put("lid_tect_vs_fluv", np.where(lid_valid, lid_tvf, 0.0))
    _put("lid_piedmont_step", np.where(lid_valid, lid_pstep, 0.0))
    lid_combo = (0.50 * lid_tvf + 0.30 * lid_pstep + 0.20 * lid_dip).astype(np.float32)
    del lid, lid_tvf, lid_pstep, lid_dip, lid_conc
    gc.collect()

    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as tsrc:
        t10 = tsrc.read().astype(np.float32) / np.float32(255.0)
    t10_pstep = (t10[1] / np.sqrt(t10[4] + 0.05)).astype(np.float32)
    _put("t10_slope_p90", t10[0])
    _put("t10_slope_max", t10[1])
    _put("t10_steep_frac", t10[2])
    _put("t10_curv_absmax", t10[5])
    _put("t10_aspect_coh", t10[6])
    _put("t10_hs_lineament", t10[7])
    _put("t10_piedmont_step", t10_pstep)

    t10_combo = (0.45 * t10_pstep + 0.30 * t10[7] + 0.25 * t10[5] * t10[6]).astype(np.float32)
    del t10, t10_pstep
    qg = np.linspace(0.0, 1.0, 501)
    seamless_scarp = np.where(
        lid_valid,
        lid_combo,
        np.interp(
            t10_combo,
            np.quantile(t10_combo[lid_valid], qg),
            np.quantile(lid_combo[lid_valid], qg),
        ).astype(np.float32),
    )
    del lid_combo, t10_combo, lid_valid
    gc.collect()

    sw600, _ = _steerable_worm(seamless_scarp, fp, half_len_px=3, n_angles=8)
    _put("scarp_worm_600m", sw600)
    del sw600
    sw1500, sw1500_aniso = _steerable_worm(seamless_scarp, fp, half_len_px=7, n_angles=8)
    _put("scarp_worm_1500m", sw1500)
    _put("scarp_worm_aniso_1500m", sw1500_aniso)
    del sw1500, sw1500_aniso, seamless_scarp
    gc.collect()

    # --- Domain 2: H76-2 True Miller-Singh Magnetic & Gravity Tilt Worms ---
    for band_idx, fname in (
        (0, "mag_anom_hp15"),
        (1, "rtp_hp15"),
        (2, "tmi_hg_hp15"),
        (8, "tmi_vg_hp15"),
        (4, "iso_grav_slope_hp15"),
        (10, "iso_grav_vg_hp15"),
        (12, "iso_grav_hp15"),
        (17, "iso_grav_hg_hp15"),
        (14, "depth_base_hp15"),
        (5, "rad_TC_hp15"),
        (16, "cond_surf_hp15"),
    ):
        arr, nbad = _clean_band(b_src[band_idx], fp)
        sentinel_audit[f"band_{band_idx+1}_{fname}"] = nbad
        _put(fname, arr - _norm_gauss(arr, fp, 15.0, vcache))
        del arr

    b2_rtp, _ = _clean_band(b_src[1], fp)
    rtp_hp15 = b2_rtp - _norm_gauss(b2_rtp, fp, 15.0, vcache)
    del b2_rtp

    b3_hg_f, _ = _clean_band(b_src[2], fp)
    b9_vg_f, _ = _clean_band(b_src[8], fp)
    b14_tmi, _ = _clean_band(b_src[13], fp)
    b15_db, _ = _clean_band(b_src[14], fp)
    b11_gvg, _ = _clean_band(b_src[10], fp)
    b18_ghg, _ = _clean_band(b_src[17], fp)

    b3_abs = np.abs(b3_hg_f)
    b18_abs = np.abs(b18_ghg)
    tdr_mag = np.arctan2(b9_vg_f, b3_abs + np.float32(1e-6)).astype(np.float32)
    cos_tdr_mag = np.cos(tdr_mag).astype(np.float32)
    gy_tdr, gx_tdr = np.gradient(_norm_gauss(tdr_mag, fp, 1.0, vcache))
    grad_tdr_mag = np.hypot(gy_tdr, gx_tdr).astype(np.float32)
    del gy_tdr, gx_tdr, tdr_mag, b3_hg_f, b9_vg_f

    cos_tdr_grav = (b18_abs / np.hypot(b18_abs, b11_gvg + np.float32(1e-6))).astype(np.float32)
    gy_db, gx_db = np.gradient(_norm_gauss(b15_db, fp, 1.5, vcache))
    grad_db = np.hypot(gy_db, gx_db).astype(np.float32)
    del gy_db, gx_db, b15_db, b11_gvg, b18_ghg

    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as esrc:
        ext = esrc.read().astype(np.float32) / np.float32(255.0)
    tmi_norm = (b14_tmi - _norm_gauss(b14_tmi, fp, 8.0, vcache)).astype(np.float32)
    ext_up_hp = ext[3] - _norm_gauss(ext[3], fp, 8.0, vcache)
    del b14_tmi

    _put("grad_depth_base", grad_db)
    _put("tmi_shallow_res", tmi_norm - np.float32(50.0) * ext_up_hp)
    _put("cos_tdr_mag", cos_tdr_mag)
    _put("grad_tdr_mag", grad_tdr_mag)
    _put("cos_tdr_grav", cos_tdr_grav)
    del grad_db, tmi_norm, ext_up_hp, cos_tdr_grav

    mag_edge = (cos_tdr_mag * np.log1p(b3_abs)).astype(np.float32)
    del cos_tdr_mag, b3_abs
    mw1600, _ = _steerable_worm(mag_edge, fp, half_len_px=8, n_angles=8)
    _put("mag_worm_1600m", mw1600)
    del mag_edge, mw1600
    gw1600, _ = _steerable_worm(np.log1p(b18_abs), fp, half_len_px=8, n_angles=8)
    _put("grav_worm_1600m", gw1600)
    del b18_abs, gw1600
    gc.collect()

    # --- Domain 3: H76-3 Fluvial Chi Knickpoints & Hydrothermal Alteration ---
    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as c16, rasterio.open(ext_dir / "dem10_chi_100m_u8.tif") as cu8:
        chi16 = c16.read().astype(np.float32)
        chiu8 = cu8.read().astype(np.float32)
    chi_valid = (chiu8[3] > 0) & fp
    chi_step_s = _norm_gauss(np.where(chi_valid, np.maximum(chi16[0], 0.0), 0.0), fp, 2.5, vcache)
    chi_ksn_s = _norm_gauss(np.where(chi_valid, np.maximum(chi16[2], 0.0), 0.0), fp, 2.5, vcache)
    chi_knick_d = _norm_gauss(np.where(fp, chiu8[1] + chiu8[2], 0.0), fp, 3.5, vcache)
    del chi16, chiu8, chi_valid
    ck_worm, _ = _steerable_worm(chi_knick_d * np.log1p(chi_step_s), fp, half_len_px=7, n_angles=8)

    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as rsrc:
        rad = rsrc.read().astype(np.float32) / np.float32(255.0)

    _put("chi_step_smooth", chi_step_s)
    _put("chi_ksn_smooth", chi_ksn_s)
    _put("chi_knick_density", chi_knick_d)
    _put("chi_knick_worm_1400m", ck_worm)
    _put("rad_K", rad[0])
    _put("rad_ThK_alteration", rad[0] - rad[1])
    _put("rad_UTh", ext[2])
    _put("mag_destruct_K_alter", np.maximum(-rtp_hp15, 0.0) * rad[0])
    del chi_step_s, chi_ksn_s, chi_knick_d, ck_worm, rad, ext, rtp_hp15

    for bidx, fn in ((3, "geod_2ndinv"), (6, "geod_shearrate"), (7, "geod_dilaterate"), (15, "eq_density")):
        arr_s, nbad = _clean_band(b_src[bidx], fp)
        sentinel_audit[f"band_{bidx+1}_{fn}"] = nbad
        _put(fn, arr_s)
        del arr_s

    th_800, th_2200 = _build_gdr_thermal_rasters(ext_dir, fp, vcache)
    _put("gdr_thermal_plume_800m", th_800)
    _put("gdr_thermal_plume_2200m", th_2200)
    del th_800, th_2200, vcache
    mm.flush()
    del mm
    gc.collect()

    meta_path.write_text(json.dumps({
        "n_fp": n_fp,
        "n_feats": n_feats,
        "feature_names": FEATURE_NAMES,
        "feature_groups": FEATURE_GROUPS,
        "sentinel_cells_sanitized_in_footprint": sentinel_audit,
    }, indent=2) + "\n")
    return np.memmap(mm_path, mode="r", dtype=np.float32, shape=(n_fp, n_feats)), list(FEATURE_NAMES), fp
