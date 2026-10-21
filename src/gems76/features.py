"""Lane G76 features: piedmont scarp-dipole surface from the pinned LiDAR stack.

Everything here is catalogue-free except two *scalar terrain quantiles* taken
from a caller-supplied visible-catalogue mask (relief p75, slope p80) — in
holdout folds the caller passes the fold-visible catalogue only.

Decode rule for the owner-derived uint8 stacks (``lidar_scarp_features.json``):
``q = 1 + round(254 * t(clip(x/xmax, 0, 1)))``, ``t`` in {sqrt, linear};
``q = 0`` means "no LiDAR".  Inversion used here: ``u = (q-1)/254``;
``x = xmax * u**2`` for sqrt bands, ``xmax * u`` for linear bands.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

# band order of lidar_scarp_features_u8.tif (verified from GeoTIFF descriptions)
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100",
               "strike", "valid"]
QUANT = {  # name: (xmax, transform) from lidar_scarp_features.json
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"),
    "downface_max": (1.0, "sqrt"), "upface_max": (1.0, "sqrt"),
    "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}


def decode_lidar(stack_u8: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Decode uint8 bands to float32 physical-ish units; NaN where q == 0."""
    out = {}
    for name, q in stack_u8.items():
        xmax, kind = QUANT[name]
        u = (q.astype(np.float32) - 1.0) / 254.0
        x = xmax * (u * u) if kind == "sqrt" else xmax * u
        x = np.where(q > 0, x, np.nan).astype(np.float32)
        out[name] = x
    return out


def rank01(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Average-tie ranks scaled to [0, 1] over finite ``valid`` cells; 0 else."""
    a = np.asarray(values)
    m = np.asarray(valid, bool) & np.isfinite(a)
    out = np.zeros(a.shape, np.float32)
    n = int(m.sum())
    if n > 1:
        out[m] = ((rankdata(a[m], method="average") - 1.0) / (n - 1)).astype(np.float32)
    return out


def fill_nearest(a: np.ndarray) -> np.ndarray:
    """Fill NaN by nearest finite neighbour (EDT indices)."""
    good = np.isfinite(a)
    if not good.any():
        raise ValueError("no finite cells to fill from")
    idx = ndi.distance_transform_edt(~good, return_distances=False, return_indices=True)
    return np.asarray(a[tuple(idx)], np.float32)


def _line_kernels(half: int = 2, n_az: int = 8):
    """Length-(2*half+1) line kernels at ``n_az`` azimuths over [0, 180)."""
    size = 2 * half + 1
    kernels = []
    for b in range(n_az):
        az = np.deg2rad(b * 180.0 / n_az)  # azimuth of the line direction
        k = np.zeros((size, size), np.float32)
        for t in range(-half, half + 1):
            dy = int(round(-t * np.cos(az)))  # row axis points south
            dx = int(round(t * np.sin(az)))
            k[half + dy, half + dx] = 1.0
        kernels.append(k / k.sum())
    return kernels


def strike_persistence(response: np.ndarray, strike_deg: np.ndarray,
                       domain: np.ndarray) -> np.ndarray:
    """Smooth ``response`` along the per-pixel strike azimuth (500 m support).

    Pixels without a decoded strike fall back to an isotropic 3x3 mean.
    """
    r = np.where(np.isfinite(response), response, 0.0).astype(np.float32)
    kernels = _line_kernels()
    iso = ndi.uniform_filter(r, size=3)
    out = iso.copy()
    az = np.where(np.isfinite(strike_deg), strike_deg, 0.0)
    bin_id = np.floor(np.mod(az, 180.0) / 22.5).astype(np.int32)
    have = domain & np.isfinite(strike_deg)
    for b, k in enumerate(kernels):
        conv = ndi.convolve(r, k, mode="nearest")
        sel = have & (bin_id == b)
        out[sel] = conv[sel]
    return np.where(domain, out, 0.0).astype(np.float32)


def fallback_response(det_elev: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """Non-LiDAR stratum: |LoG| dipole proxy x structure-tensor coherence.

    ``det_elev`` must already be sentinel-cleaned (NaN outside its finite set).
    """
    z = fill_nearest(np.where(np.isfinite(det_elev), det_elev, np.nan))
    log = -ndi.gaussian_laplace(z.astype(np.float64), 1.0)
    gy = ndi.gaussian_filter(z, 1.0, order=(1, 0))
    gx = ndi.gaussian_filter(z, 1.0, order=(0, 1))
    jxx = ndi.gaussian_filter(gx * gx, 2.0)
    jxy = ndi.gaussian_filter(gx * gy, 2.0)
    jyy = ndi.gaussian_filter(gy * gy, 2.0)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum(((jxx - jyy) * 0.5) ** 2 + jxy * jxy, 0.0))
    coh = np.divide(2.0 * disc, tr, out=np.zeros_like(tr), where=tr > 0)
    resp = (np.abs(log).astype(np.float32) * (0.5 + 0.5 * coh.astype(np.float32)))
    return np.where(domain, resp, 0.0).astype(np.float32)


def quantile_match(source: np.ndarray, src_domain: np.ndarray,
                     reference: np.ndarray, ref_domain: np.ndarray) -> np.ndarray:
    """Map ``source`` values on ``src_domain`` onto the reference distribution."""
    q = np.linspace(0.0, 1.0, 1001)
    s_q = np.quantile(source[src_domain], q)
    r_q = np.quantile(reference[ref_domain], q)
    out = np.zeros(source.shape, np.float32)
    out[src_domain] = np.interp(source[src_domain], s_q, r_q).astype(np.float32)
    return out


def build_surface(lidar: dict[str, np.ndarray], det_elev: np.ndarray,
                  det_elev_slope: np.ndarray, footprint: np.ndarray,
                  visible_catalogue: np.ndarray) -> tuple[np.ndarray, dict]:
    """Build the frozen Lane-G76 belief surface and its named components.

    Returns ``(surface_rank01, components)`` where components are the raw
    fields used for leakage canaries.  ``visible_catalogue`` is used ONLY for
    two scalar terrain quantiles (relief p75 inside LiDAR, slope p80 outside).
    """
    fp = np.asarray(footprint, bool)
    has_lidar = fp & np.isfinite(lidar["valid"]) & (lidar["valid"] > 0)
    no_lidar = fp & ~has_lidar & np.isfinite(det_elev)

    step = np.nan_to_num(lidar["step_max"])
    lapneg = np.nan_to_num(lidar["lapneg_max"])
    lappos = np.nan_to_num(lidar["lappos_max"])
    dipole = np.sqrt(np.maximum(lapneg, 0.0) * np.maximum(lappos, 0.0)).astype(np.float32)
    face = np.maximum(np.nan_to_num(lidar["upface_max"]), np.nan_to_num(lidar["downface_max"]))
    cross = np.nan_to_num(lidar["cross_max"])
    polarity = (face / (face + cross + 1e-6)).astype(np.float32)
    coh = np.nan_to_num(lidar["coh100"])
    relief = lidar["relief"]

    base = (step * dipole).astype(np.float32)
    persisted = strike_persistence(base, lidar["strike"], has_lidar)

    # Piedmont gates: scalar quantiles from the VISIBLE catalogue only.
    cat_lidar = visible_catalogue & has_lidar & np.isfinite(relief)
    relief_q75 = float(np.quantile(relief[cat_lidar], 0.75)) if cat_lidar.any() else np.inf
    gate_lidar = has_lidar & np.isfinite(relief) & (relief <= relief_q75)

    fb = fallback_response(det_elev, no_lidar)
    cat_slope = visible_catalogue & np.isfinite(det_elev_slope)
    slope_q80 = (float(np.quantile(det_elev_slope[cat_slope], 0.80))
                 if cat_slope.any() else np.inf)
    gate_fb = no_lidar & np.isfinite(det_elev_slope) & (det_elev_slope <= slope_q80)

    # Merge strata in physical-response space (label-free quantile match).
    resp = np.zeros(fp.shape, np.float32)
    resp[gate_lidar] = (persisted[gate_lidar]
                        * (0.5 + 0.5 * polarity[gate_lidar])
                        * (0.5 + 0.5 * coh[gate_lidar]))
    if gate_lidar.any() and gate_fb.any():
        fb_matched = quantile_match(fb, gate_fb, resp, gate_lidar)
        resp[gate_fb] = fb_matched[gate_fb]

    domain = gate_lidar | gate_fb
    surface = rank01(resp, domain)
    components = {
        "step_max": np.where(has_lidar, step, 0).astype(np.float32),
        "dipole": np.where(has_lidar, dipole, 0).astype(np.float32),
        "polarity": np.where(has_lidar, polarity, 0).astype(np.float32),
        "coh100": np.where(has_lidar, coh, 0).astype(np.float32),
        "persisted": persisted,
        "fallback": fb,
        "surface": surface,
        "_domain": domain,
        "_has_lidar": has_lidar,
        "_relief_q75": relief_q75,
        "_slope_q80": slope_q80,
    }
    return surface, components
