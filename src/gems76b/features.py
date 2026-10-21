"""Lane G76B: multi-physics patch-context corroboration features.

Catalogue-free feature construction over the pinned stack.  All full-grid
temporaries are built one at a time and immediately reduced into a compact
``(N_valid, F)`` float32 matrix to fit the 3 GB sandbox.

Feature families (see docs/preregistration-g76b.md):
  LiDAR      step, dipole, polarity, coherence, relief, strike persistence,
             ex_mean, has_lidar, non-LiDAR fallback response
  magnetic   |grad rtp| (smoothed), cross-scale agreement with |grad TMI_up150|,
             tmi_hg, tc
  gravity    de-regionalized |grad iso_grav|, iso_grav_hg
  radiometric K/(Th+10) local anomaly, its edge magnitude
  strain     21 px regional means of geod_2ndinv / shearrate ranks, |dilaterate| rank
  topo       detrended-elevation high-pass, slope, |grad depth_to_basement|
  context    for each of 4 responses (scarp, mag-agree, grav-edge, rad-edge):
             directional persistence (max over 8 azimuths, 5-tap line kernel)
             and 5x5 local support density of the response rank
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from gems76.features import QUANT, _line_kernels, rank01  # noqa: E402  (this repo's own G76 helpers)

SENTINEL = -1e30
LINE_KERNELS = _line_kernels(half=2, n_az=8)


def _decode_u8(q: np.ndarray, name: str) -> np.ndarray:
    xmax, kind = QUANT[name]
    u = (q.astype(np.float32) - 1.0) / 254.0
    x = xmax * (u * u) if kind == "sqrt" else xmax * u
    return np.where(q > 0, x, np.nan).astype(np.float32)


def _grad_mag(a: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(np.nan_to_num(a, nan=0.0).astype(np.float32))
    return np.hypot(gy, gx).astype(np.float32)


def directional_persistence(response: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """Max over 8 azimuths of the 5-tap line-kernel mean of ``response``."""
    r = np.where(domain, np.nan_to_num(response, nan=0.0), 0.0).astype(np.float32)
    best = np.full(r.shape, -np.inf, np.float32)
    for k in LINE_KERNELS:
        conv = ndi.convolve(r, k, mode="nearest")
        np.maximum(best, conv, out=best)
    best[~domain] = 0.0
    return np.maximum(best, 0.0).astype(np.float32)


def support_density(response_rank: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """5x5 local mean of the response rank (fraction of strong neighbours)."""
    s = ndi.uniform_filter(np.where(domain, response_rank, 0.0).astype(np.float32), size=5)
    return np.where(domain, s, 0.0).astype(np.float32)


def build_feature_matrix(valid: np.ndarray, data_dir: Path
                         ) -> tuple[np.ndarray, list[str], dict]:
    """Return (X, names, aux) with X of shape (n_valid, n_features).

    ``aux`` carries small full-grid arrays needed downstream (has_lidar,
    decoded LiDAR relief and basement depth for the C76-piedmont truth).
    """
    n_valid = int(valid.sum())
    feats: list[tuple[str, np.ndarray]] = []

    def push(name: str, grid_arr: np.ndarray) -> None:
        feats.append((name, grid_arr[valid].astype(np.float32)))

    # ---------- LiDAR family (sequential band reads; ~50 MB each) ----------
    lidar_path = data_dir / "external" / "lidar_scarp_features_u8.tif"
    band_ix = {"ex_max": 1, "ex_mean": 2, "step_max": 3, "lapneg_max": 4, "lappos_max": 5,
               "downface_max": 6, "upface_max": 7, "cross_max": 8, "relief": 9, "coh100": 10,
               "strike": 11, "valid": 12}
    with rasterio.open(lidar_path) as src:
        def read_dec(name: str) -> np.ndarray:
            return _decode_u8(src.read(band_ix[name]), name)

        v = read_dec("valid")
        has_lidar = np.isfinite(v) & (v > 0)
        del v

        step = np.nan_to_num(read_dec("step_max"))
        lapn = np.maximum(np.nan_to_num(read_dec("lapneg_max")), 0.0)
        lapp = np.maximum(np.nan_to_num(read_dec("lappos_max")), 0.0)
        dipole = np.where(has_lidar, step * np.sqrt(lapn * lapp), 0.0).astype(np.float32)
        del lapn, lapp
        upf = np.nan_to_num(read_dec("upface_max"))
        dnf = np.nan_to_num(read_dec("downface_max"))
        cross = np.nan_to_num(read_dec("cross_max"))
        face = np.maximum(upf, dnf)
        polarity = (face / (face + cross + 1e-6)).astype(np.float32)
        del upf, dnf, cross, face
        coh = np.nan_to_num(read_dec("coh100"))
        exm = np.nan_to_num(read_dec("ex_mean"))
        relief = read_dec("relief")
        strike = read_dec("strike")

        # strike-guided persistence of the dipole response (G76 semantics)
        az = np.where(np.isfinite(strike), strike, 0.0)
        bin_id = np.floor(np.mod(az, 180.0) / 22.5).astype(np.int32)
        have = has_lidar & np.isfinite(strike)
        iso_mean = ndi.uniform_filter(dipole, size=3)
        persist = iso_mean.copy()
        for b, k in enumerate(LINE_KERNELS):
            conv = ndi.convolve(dipole, k, mode="nearest")
            sel = have & (bin_id == b)
            persist[sel] = conv[sel]
        persist = np.where(has_lidar, persist, 0.0).astype(np.float32)
        del strike, az, bin_id, have, iso_mean

        push("lid_step", np.where(has_lidar, step, 0.0))
        push("lid_dipole", dipole)
        push("lid_polarity", np.where(has_lidar, polarity, 0.0))
        push("lid_coh", np.where(has_lidar, coh, 0.0))
        push("lid_exmean", np.where(has_lidar, exm, 0.0))
        push("lid_relief", np.where(has_lidar, np.nan_to_num(relief), 0.0))
        push("lid_persist", persist)
        push("has_lidar", has_lidar.astype(np.float32))
        del step, polarity, coh, exm

    # ---------- topo + non-LiDAR fallback response ----------
    with rasterio.open(data_dir / "training_features.tif") as src:
        det_elev = src.read(12).astype(np.float32)
        det_elev[(det_elev <= SENTINEL) | ~np.isfinite(det_elev)] = np.nan
        det_slope = src.read(19).astype(np.float32)
        det_slope[(det_slope <= SENTINEL) | ~np.isfinite(det_slope)] = np.nan

        fallback_dom = valid & ~has_lidar & np.isfinite(det_elev)
        hp = (det_elev - ndi.uniform_filter(np.nan_to_num(det_elev), size=9)).astype(np.float32)
        g1 = _grad_mag(hp)
        g2 = _grad_mag(g1)
        fb = np.where(fallback_dom, g1 * (g2 / (g2.max() + 1e-6)), 0.0).astype(np.float32)
        fb = np.where(fallback_dom, ndi.uniform_filter(fb, size=3), 0.0).astype(np.float32)
        push("fallback_resp", fb)
        push("elev_hp", np.where(valid, hp, 0.0))
        push("elev_slope", np.where(valid, np.nan_to_num(det_slope), 0.0))
        del hp, g1, g2, fallback_dom

    # combined scarp response: LiDAR dipole where available, fallback elsewhere
    scarp_resp = (dipole + fb).astype(np.float32)
    del dipole, fb

    # ---------- magnetic family ----------
    with rasterio.open(data_dir / "training_features.tif") as src:
        rtp = src.read(2).astype(np.float32)
        rtp[(rtp <= SENTINEL) | ~np.isfinite(rtp)] = np.nan
        tmi_hg = src.read(3).astype(np.float32)
        tmi_hg[(tmi_hg <= SENTINEL) | ~np.isfinite(tmi_hg)] = np.nan
        tc = src.read(6).astype(np.float32)
        tc[(tc <= SENTINEL) | ~np.isfinite(tc)] = np.nan
    mag_edge = ndi.uniform_filter(_grad_mag(rtp), size=3)
    del rtp
    with rasterio.open(data_dir / "external" / "geodawn_extensions_u8.tif") as src:
        up150 = src.read(4).astype(np.float32)  # 0-255 upward-continued TMI
    up_edge = ndi.uniform_filter(_grad_mag(up150), size=3)
    del up150
    r_mag = rank01(mag_edge, valid)
    r_up = rank01(up_edge, valid)
    xedge_agree = np.minimum(r_mag, r_up).astype(np.float32)
    del up_edge, r_up, mag_edge
    push("mag_edge", r_mag)
    push("xedge_agree", xedge_agree)
    push("tmi_hg", np.where(valid, np.nan_to_num(tmi_hg), 0.0))
    push("tc", np.where(valid, np.nan_to_num(tc), 0.0))
    del tmi_hg, tc

    # ---------- gravity family ----------
    with rasterio.open(data_dir / "training_features.tif") as src:
        iso = src.read(13).astype(np.float32)
        iso[(iso <= SENTINEL) | ~np.isfinite(iso)] = np.nan
        iso_hg = src.read(18).astype(np.float32)
        iso_hg[(iso_hg <= SENTINEL) | ~np.isfinite(iso_hg)] = np.nan
    iso_hp = iso - ndi.uniform_filter(np.nan_to_num(iso), size=15)
    del iso
    r_grav = rank01(_grad_mag(iso_hp), valid)
    del iso_hp
    push("grav_edge", r_grav)
    push("iso_hg", np.where(valid, np.nan_to_num(iso_hg), 0.0))
    del iso_hg

    # ---------- radiometric family ----------
    with rasterio.open(data_dir / "external" / "geodawn_rad_u8.tif") as src:
        k = src.read(1).astype(np.float32)
        th = src.read(2).astype(np.float32)
    ratio = (k + 1.0) / (th + 10.0)
    del k, th
    ratio_anom = ratio - ndi.uniform_filter(ratio, size=21)
    del ratio
    r_rad = rank01(ndi.uniform_filter(_grad_mag(ratio_anom), size=3), valid)
    push("rad_anom", rank01(ratio_anom, valid))
    push("rad_edge", r_rad)
    del ratio_anom

    # ---------- strain-belt regional context ----------
    with rasterio.open(data_dir / "training_features.tif") as src:
        g2 = src.read(4).astype(np.float32)
        g2[(g2 <= SENTINEL) | ~np.isfinite(g2)] = np.nan
        gsh = src.read(7).astype(np.float32)
        gsh[(gsh <= SENTINEL) | ~np.isfinite(gsh)] = np.nan
        gdi = src.read(8).astype(np.float32)
        gdi[(gdi <= SENTINEL) | ~np.isfinite(gdi)] = np.nan
    strain_mean = 0.5 * (rank01(g2, valid) + rank01(gsh, valid))
    del g2, gsh
    push("strain_belt", ndi.uniform_filter(strain_mean, size=21))
    del strain_mean
    push("strain_dil", ndi.uniform_filter(rank01(np.abs(gdi), valid), size=21))
    del gdi
    with rasterio.open(data_dir / "training_features.tif") as src:
        depth = src.read(15).astype(np.float32)
        depth[(depth <= SENTINEL) | ~np.isfinite(depth)] = np.nan
    push("depth_grad", rank01(_grad_mag(depth), valid))

    # ---------- patch-context features over the four responses ----------
    for rname, arr in {"scarp": scarp_resp, "xmag": xedge_agree,
                       "grav": r_grav, "rad": r_rad}.items():
        push(f"ctx_persist_{rname}", directional_persistence(arr, valid))
        push(f"ctx_support_{rname}", support_density(rank01(arr, valid), valid))
    del scarp_resp, xedge_agree, r_grav, r_rad

    names = [n for n, _ in feats]
    X = np.empty((n_valid, len(names)), np.float32)
    for j, (_, col) in enumerate(feats):
        X[:, j] = col
    del feats
    aux = {"has_lidar": has_lidar, "relief_decoded": relief, "depth": depth}
    return X, names, aux
