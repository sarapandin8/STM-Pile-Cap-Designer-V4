import math

PHI_STM = 0.75
PHI_BEARING = 0.75  # PATCHED 2026-04-27: ACI 21.2.1(e) STM uses φ=0.75 for nodes

REBAR_DB = {
    "DB12": 113.10, "DB16": 201.06, "DB20": 314.16,
    "DB25": 490.87, "DB28": 615.75, "DB32": 804.25,
}

# Nominal diameter (mm) for each bar size — used for cover/spacing checks
REBAR_DIAM_MM = {
    "DB12": 12.0, "DB16": 16.0, "DB20": 20.0,
    "DB25": 25.0, "DB28": 28.0, "DB32": 32.0,
}

# Yield strength per bar size (user-defined: ≤DB28 → 390 MPa, DB32 → 490 MPa)
# ACI 318-19 §20.2.2.4: fy used in design shall not exceed 550 MPa.
FY_CAP_MPA = 550.0
REBAR_FY = {
    "DB12": 390.0, "DB16": 390.0, "DB20": 390.0,
    "DB25": 390.0, "DB28": 390.0, "DB32": 490.0,
}


def _bbox(coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return min(xs), max(xs), min(ys), max(ys)


def _cap_from_coords(coords, D, e_left, e_right, e_top, e_bot):
    if not coords:
        return 0.0, 0.0, 0.0, 0.0
    xmin, xmax, ymin, ymax = _bbox(coords)
    if isinstance(D, dict):
        sec_p, pbx, pby, pdm = normalize_pile(D)
        if sec_p == "Rectangular":
            hx = pbx / 2.0; hy = pby / 2.0
        elif sec_p == "Square":
            hx = pbx / 2.0; hy = pbx / 2.0
        else:
            hx = pdm / 2.0; hy = pdm / 2.0
    else:
        hx = float(D) / 2.0; hy = float(D) / 2.0
    x0 = xmin - hx - e_left
    x1 = xmax + hx + e_right
    y0 = ymin - hy - e_bot
    y1 = ymax + hy + e_top
    return (x1 - x0), (y1 - y0), (x0 + x1) / 2.0, (y0 + y1) / 2.0


def get_preset_layouts(D, sf=2.5, clear_min=500.0,
                       sf_x=None, sf_y=None,
                       e_left=None, e_right=None, e_top=None, e_bot=None):
    """Generate preset pile layouts with anti-overlap protection.

    Spacing rule (center-to-center):
        s_axis = max(sf_axis * pile_dim_along_axis,
                     pile_dim_along_axis + clear_min)
        s_diag = max(sf * pile_min_dim, pile_max_dim + clear_min)
                 # used for triangular & hexagonal (non-axis-aligned)

    Args:
        D          : pile dict {"section","bx","by","diam"} or scalar
        sf         : default spacing factor (used if sf_x/sf_y not given)
        clear_min  : minimum clear edge-to-edge distance (mm), default 500
        sf_x, sf_y : per-axis override (Manual mode); None -> use sf
    """
    if isinstance(D, dict):
        sec_p, pbx, pby, pdm = normalize_pile(D)
        if sec_p == "Rectangular":
            pile_x, pile_y = pbx, pby
        elif sec_p == "Square":
            pile_x = pile_y = pbx
        else:  # Circular
            pile_x = pile_y = pdm
        gov_min = pile_min_dim(sec_p, pbx, pby, pdm)
        gov_max = pile_max_dim(sec_p, pbx, pby, pdm)
    else:
        pile_x = pile_y = float(D)
        gov_min = gov_max = float(D)

    sfx = sf if sf_x is None else sf_x
    sfy = sf if sf_y is None else sf_y

    # Center-to-center spacings (anti-overlap guaranteed)
    sx_a = max(sfx * pile_x, pile_x + clear_min)   # X-axis grid
    sy_a = max(sfy * pile_y, pile_y + clear_min)   # Y-axis grid
    s_d  = max(sf  * gov_min, gov_max + clear_min) # diagonal/non-axis

    e_def = max(150.0, 0.75 * gov_max)
    el = e_def if e_left  is None else e_left
    er = e_def if e_right is None else e_right
    et = e_def if e_top   is None else e_top
    eb = e_def if e_bot   is None else e_bot
    layouts = {}

    def add(name, coords, shape):
        lx, ly, cx, cy = _cap_from_coords(coords, D, el, er, et, eb)
        layouts[name] = {
            "coords": coords, "shape": shape, "n": len(coords),
            "lx": lx, "ly": ly, "cx": cx, "cy": cy, "cap_polygon": None,
        }

    # 2-Pile linear (along X)
    add("2-Pile (Linear)",
        [(-sx_a/2, 0.0), (sx_a/2, 0.0)], "Rectangular")

    # 3-Pile equilateral triangle (side = s_d)
    h = s_d * math.sqrt(3) / 2.0
    add("3-Pile (Triangular Equilateral)",
        [(-s_d/2, -h/3), (s_d/2, -h/3), (0.0, 2*h/3)], "Triangular")

    # 3-Pile linear (along X)
    add("3-Pile (Linear)",
        [(-sx_a, 0.0), (0.0, 0.0), (sx_a, 0.0)], "Rectangular")

    # 4-Pile linear (single row along X)
    add("4-Pile (Linear)",
        [(-1.5*sx_a, 0.0), (-0.5*sx_a, 0.0),
         ( 0.5*sx_a, 0.0), ( 1.5*sx_a, 0.0)], "Rectangular")

    # 4-Pile square grid (sx_a × sy_a)
    add("4-Pile (Square)",
        [(-sx_a/2, -sy_a/2), ( sx_a/2, -sy_a/2),
         (-sx_a/2,  sy_a/2), ( sx_a/2,  sy_a/2)], "Square")

    # 4-Pile rectangular (X stretched 1.5×)
    sx_4r = 1.5 * sx_a
    add("4-Pile (Rectangular)",
        [(-sx_4r/2, -sy_a/2), ( sx_4r/2, -sy_a/2),
         (-sx_4r/2,  sy_a/2), ( sx_4r/2,  sy_a/2)], "Rectangular")

    # 5-Pile (Square corners + Center)
    add("5-Pile (Square + Center)",
        [(-sx_a, -sy_a), ( sx_a, -sy_a),
         (-sx_a,  sy_a), ( sx_a,  sy_a),
         (0.0, 0.0)], "Square")

    # 6-Pile (2 rows × 3 cols)
    six = []
    for ix in (-sx_a, 0.0, sx_a):
        for iy in (-sy_a/2, sy_a/2):
            six.append((ix, iy))
    add("6-Pile (2x3)", six, "Rectangular")

    # 7-Pile hexagonal (radius = s_d)
    seven = [(0.0, 0.0)]
    for i in range(6):
        a = math.radians(60*i)
        seven.append((s_d*math.cos(a), s_d*math.sin(a)))
    add("7-Pile (Hexagonal)", seven, "Rectangular")

    # 8-Pile (2 rows × 4 cols)
    eight = []
    for ix in (-1.5*sx_a, -0.5*sx_a, 0.5*sx_a, 1.5*sx_a):
        for iy in (-sy_a/2, sy_a/2):
            eight.append((ix, iy))
    add("8-Pile (2x4)", eight, "Rectangular")

    # 9-Pile (3 × 3 grid)
    nine = []
    for ix in (-sx_a, 0.0, sx_a):
        for iy in (-sy_a, 0.0, sy_a):
            nine.append((ix, iy))
    add("9-Pile (3x3)", nine, "Square")

    return layouts

def get_truncated_triangle_equal(D, L=4000.0, w=600.0, e=None):
    """Equilateral triangle (side L) with all 3 corners truncated by width w.
       Returns hexagonal cap with 3 piles, one near each truncated corner.
       Origin = pile-group centroid (= triangle centroid)."""
    if isinstance(D, dict):
        sec_p, pbx, pby, pdm = normalize_pile(D)
        D_max = pile_max_dim(sec_p, pbx, pby, pdm)
        D_half = D_max / 2.0
    else:
        D_max = float(D)
        D_half = D_max / 2.0
    e_def = max(150.0, 0.75 * D_max)
    e = e_def if e is None else e

    R = L / math.sqrt(3.0)  # circumradius (centroid -> vertex)

    V1 = (0.0, R)
    V2 = (-L/2.0, -R/2.0)
    V3 = (L/2.0, -R/2.0)

    def along(P, Q, dist):
        dx = Q[0] - P[0]; dy = Q[1] - P[1]
        Lpq = math.hypot(dx, dy)
        if Lpq < 1e-6:
            return P
        f = dist / Lpq
        return (P[0] + f*dx, P[1] + f*dy)

    A1 = along(V1, V2, w)
    A2 = along(V2, V1, w)
    A3 = along(V2, V3, w)
    A4 = along(V3, V2, w)
    A5 = along(V3, V1, w)
    A6 = along(V1, V3, w)
    cap_polygon = [A1, A2, A3, A4, A5, A6]

    # Pile distance from origin (along each vertex direction)
    d_p = R - w*math.sqrt(3.0)/2.0 - e - D_half
    if d_p < 0:
        d_p = 0.0

    P1 = (0.0, d_p)
    P2 = (-d_p*math.sqrt(3.0)/2.0, -d_p/2.0)
    P3 = (d_p*math.sqrt(3.0)/2.0, -d_p/2.0)
    coords = [P1, P2, P3]

    xs = [v[0] for v in cap_polygon]
    ys = [v[1] for v in cap_polygon]
    lx = max(xs) - min(xs)
    ly = max(ys) - min(ys)
    cx = (max(xs)+min(xs))/2.0
    cy = (max(ys)+min(ys))/2.0
    pile_spacing = d_p * math.sqrt(3.0)

    return {
        "coords": coords,
        "shape": "Triangular (Truncated Equilateral)", "n": 3,
        "lx": lx, "ly": ly, "cx": cx, "cy": cy,
        "cap_polygon": cap_polygon,
        "L": L, "w": w, "e_pile": e,
        "d_p": d_p, "pile_spacing": pile_spacing, "R": R,
    }

def _pile_half_dims(D):
    if isinstance(D, dict):
        sec_p, pbx, pby, pdm = normalize_pile(D)
    else:
        sec_p, pbx, pby, pdm = normalize_pile(float(D))
    if sec_p == "Circular":
        return sec_p, pdm / 2.0, pdm / 2.0, pdm
    if sec_p == "Square":
        return sec_p, pbx / 2.0, pbx / 2.0, pbx
    return sec_p, pbx / 2.0, pby / 2.0, min(pbx, pby)


def _edge_clearance_same_pile_shape(dx, dy, D):
    """Minimum edge-to-edge clearance between two identical pile sections."""
    sec_p, hx, hy, diam = _pile_half_dims(D)
    adx = abs(dx)
    ady = abs(dy)
    if sec_p == "Circular":
        return math.hypot(dx, dy) - diam

    sx = adx - 2.0 * hx
    sy = ady - 2.0 * hy
    if sx >= 0.0 and sy >= 0.0:
        return math.hypot(sx, sy)
    if sx >= 0.0:
        return sx
    if sy >= 0.0:
        return sy
    return max(sx, sy)


def validate_pile_spacing(coords, D, mf=2.5, clear_min=500.0):
    """Check pile center spacing and true edge-to-edge clearance."""
    n = len(coords)
    if isinstance(D, dict):
        sec_p, pbx, pby, pdm = normalize_pile(D)
        gov_dim = pile_min_dim(sec_p, pbx, pby, pdm)
    else:
        gov_dim = float(D)
    req = mf * gov_dim
    pairs = []
    viol = []
    mn = float("inf")
    for i in range(n):
        for j in range(i+1, n):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            d = math.hypot(dx, dy)
            clear = _edge_clearance_same_pile_shape(dx, dy, D)
            ctc_ok = d >= req-1e-3
            clear_ok = clear >= clear_min-1e-3
            ok = ctc_ok and clear_ok
            pairs.append((i+1, j+1, d, clear, ctc_ok, clear_ok, ok))
            if d < mn:
                mn = d
            if not ok:
                reasons = []
                if not ctc_ok:
                    reasons.append("c/c < {:.0f} mm".format(req))
                if not clear_ok:
                    reasons.append("clear < {:.0f} mm".format(clear_min))
                viol.append((i+1, j+1, d, clear, "; ".join(reasons)))
    if mn == float("inf"):
        mn = 0.0
    return (len(viol) == 0, mn, viol, req, pairs)


def compute_cap_bounds_per_side(coords, e_left, e_right, e_top, e_bot, D):
    return _cap_from_coords(coords, D, e_left, e_right, e_top, e_bot)


def parse_custom_coords(text):
    out = []
    for line in text.strip().splitlines():
        line = line.strip().replace("\t", ",").replace(";", ",")
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if len(parts) < 2:
            continue
        try:
            out.append((float(parts[0]), float(parts[1])))
        except ValueError:
            pass
    return out


def fce_strut(fc, bs=0.75):
    """Effective compressive strength of strut.
    ACI 318-19 Eq. 23.4.3a: fce = 0.85 * βs * f'c
    βs = 0.75 bottle-shaped with crack-control rebar (ACI Table 23.4.3a)
    βs = 0.60 bottle-shaped without crack-control rebar."""
    return 0.85 * bs * fc


def fce_node(fc, bn=0.80):
    return 0.85 * bn * fc


def _compute_pile_reactions_legacy(coords, Pu, Mux_kNm, Muy_kNm):
    """Legacy origin-based reaction distribution kept for comparison only."""
    n = len(coords)
    if n == 0:
        return []
    sum_x2 = sum(c[0]**2 for c in coords)
    sum_y2 = sum(c[1]**2 for c in coords)
    Mux_kNmm = Mux_kNm * 1000.0
    Muy_kNmm = Muy_kNm * 1000.0
    out = []
    for (x, y) in coords:
        P = Pu / n
        if sum_y2 > 1e-6:
            P += Mux_kNmm * y / sum_y2
        if sum_x2 > 1e-6:
            P += Muy_kNmm * x / sum_x2
        out.append(P)
    return out


def _design_fy(fy_mpa):
    return min(float(fy_mpa), FY_CAP_MPA)


def compute_pile_reactions(coords, Pu, Mux_kNm, Muy_kNm,
                           about_centroid=True, return_info=False,
                           load_point=(0.0, 0.0)):
    """Rigid-cap elastic distribution with centroid/eccentricity handling."""
    n = len(coords)
    load_x, load_y = load_point
    if n == 0:
        if return_info:
            return [], {
                "centroid": (0.0, 0.0),
                "load_point": (load_x, load_y),
                "reaction_coords": [],
                "Mux_about_centroid_kNm": 0.0,
                "Muy_about_centroid_kNm": 0.0,
                "equilibrium_residual_Mux_kNm": 0.0,
                "equilibrium_residual_Muy_kNm": 0.0,
                "equilibrium_OK": True,
                "warnings": [],
            }
        return []

    cx = sum(c[0] for c in coords) / n if about_centroid else 0.0
    cy = sum(c[1] for c in coords) / n if about_centroid else 0.0
    rel = [(x - cx, y - cy) for x, y in coords]
    sum_x2 = sum(x**2 for x, _ in rel)
    sum_y2 = sum(y**2 for _, y in rel)
    Mux_kNmm = Mux_kNm * 1000.0
    Muy_kNmm = Muy_kNm * 1000.0
    Mux_eff = Mux_kNmm + Pu * (load_y - cy) if about_centroid else Mux_kNmm
    Muy_eff = Muy_kNmm + Pu * (load_x - cx) if about_centroid else Muy_kNmm
    out = []
    warnings = []

    for (x, y) in rel:
        P = Pu / n
        if sum_y2 > 1e-6:
            P += Mux_eff * y / sum_y2
        elif abs(Mux_eff) > 1e-6:
            warnings.append("Pile layout has no Y lever arm for Mux.")
        if sum_x2 > 1e-6:
            P += Muy_eff * x / sum_x2
        elif abs(Muy_eff) > 1e-6:
            warnings.append("Pile layout has no X lever arm for Muy.")
        out.append(P)

    sum_p = sum(out)
    target_mx = Mux_kNmm + Pu * load_y
    target_my = Muy_kNmm + Pu * load_x
    mx_resisted = sum(p * y for p, (_, y) in zip(out, coords))
    my_resisted = sum(p * x for p, (x, _) in zip(out, coords))
    residual_mx = (mx_resisted - target_mx) / 1000.0
    residual_my = (my_resisted - target_my) / 1000.0
    tol_mx = max(1.0, 0.001 * max(abs(Mux_kNm), abs(Pu * load_y / 1000.0)))
    tol_my = max(1.0, 0.001 * max(abs(Muy_kNm), abs(Pu * load_x / 1000.0)))
    equilibrium_ok = (
        abs(sum_p - Pu) <= max(1e-3, 1e-6 * abs(Pu)) and
        abs(residual_mx) <= tol_mx and
        abs(residual_my) <= tol_my
    )

    if return_info:
        return out, {
            "centroid": (cx, cy),
            "load_point": (load_x, load_y),
            "reaction_coords": rel,
            "Mux_about_centroid_kNm": Mux_eff / 1000.0,
            "Muy_about_centroid_kNm": Muy_eff / 1000.0,
            "equilibrium_residual_Mux_kNm": residual_mx,
            "equilibrium_residual_Muy_kNm": residual_my,
            "equilibrium_OK": equilibrium_ok,
            "warnings": list(dict.fromkeys(warnings)),
        }
    return out


def stm_design(coords, Pu, Mux, Muy, fc, fy, D, col, h_cap,
               cover=75.0, beta_s=0.75, W_cap_kN=0.0,
               fy_x=None, fy_y=None, x_bar_size=None, y_bar_size=None,
               cap_lx_mm=None, cap_ly_mm=None):
    """STM design per ACI 318-19 Ch. 23. No separate punching/beam shear
       check (per ACI §13.4.6.3 — covered by strut & node strength).
       W_cap_kN: self-weight of pile cap (kN), added to Pu for pile reactions.
       Note: W_cap is NOT included in column node check (col_DCR) because
       cap self-weight is distributed load, not transmitted through column."""
    n = len(coords)
    if n < 2:
        return {"error": "Need at least 2 piles."}

    if isinstance(col, dict):
        col_x = float(col.get("x", 0.0))
        col_y = float(col.get("y", 0.0))
        if cap_lx_mm is None:
            cap_lx_mm = col.get("_cap_lx_mm")
        if cap_ly_mm is None:
            cap_ly_mm = col.get("_cap_ly_mm")
    else:
        col_x = 0.0
        col_y = 0.0

    # Pu_total = column load + pile cap self-weight
    Pu_total = Pu + W_cap_kN
    pile_loads, reaction_info = compute_pile_reactions(
        coords, Pu_total, Mux, Muy, return_info=True,
        load_point=(col_x, col_y))
    P_max = max(pile_loads)
    P_min = min(pile_loads)
    has_uplift = P_min < -1e-3

    # d_eff = h - cover - db/2  (ACI 318-19 §23.2)
    # Bar diameter assumed DB25 (25 mm) for initial design iteration.
    # This is the distance from compression face to centroid of tie steel.
    DB_ASSUMED_MM = 25.0
    d_eff = h_cap - cover - DB_ASSUMED_MM / 2.0
    if d_eff <= 0:
        return {"error": "Effective depth <= 0. Increase cap thickness."}

    struts = []
    for i, (x, y) in enumerate(coords):
        Pi = max(0.0, pile_loads[i])  # uplift handled separately
        dx = x - col_x
        dy = y - col_y
        L_h = math.hypot(dx, dy)
        L_s = math.hypot(L_h, d_eff)
        th = math.degrees(math.atan2(d_eff, L_h)) if L_h > 0 else 90.0
        F_s = Pi * (L_s/d_eff)
        F_tx = Pi * abs(dx)/d_eff
        F_ty = Pi * abs(dy)/d_eff
        struts.append({
            "coord": (x, y), "P_i_kN": pile_loads[i],
            "column_coord": (col_x, col_y),
            "dx_from_col": dx, "dy_from_col": dy,
            "L_h": L_h, "L_strut": L_s, "theta_deg": th,
            "F_strut_kN": F_s,
            "F_tie_x_kN": F_tx, "F_tie_y_kN": F_ty,
        })

    # PATCHED 2026-04-27: use Σ Pi·x/d instead of max per pile
    xs = [c[0] - col_x for c in coords]
    ys = [c[1] - col_y for c in coords]

    Ftx_right = sum(p * x / d_eff for p, x in zip(pile_loads, xs) if x > 0 and p > 0)
    Ftx_left = sum(p * -x / d_eff for p, x in zip(pile_loads, xs) if x < 0 and p > 0)
    Ftx_max = max(Ftx_right, Ftx_left)

    Fty_front = sum(p * y / d_eff for p, y in zip(pile_loads, ys) if y > 0 and p > 0)
    Fty_back = sum(p * -y / d_eff for p, y in zip(pile_loads, ys) if y < 0 and p > 0)
    Fty_max = max(Fty_front, Fty_back)

    Fs_max = max(s["F_strut_kN"] for s in struts)

    if isinstance(D, dict):
        sec_p, pbx, pby, pdm = normalize_pile(D)
        A_s = pile_area(sec_p, pbx, pby, pdm)
    else:
        A_s = math.pi * (float(D)/2.0)**2
    A_strut_eff = A_s
    A_node_pile_eff = A_s
    fce_s = fce_strut(fc, bs=beta_s)
    Fns = fce_s * A_strut_eff / 1000.0
    phi_Fns = PHI_STM * Fns
    strut_dcr = Fs_max/phi_Fns if phi_Fns > 0 else float("inf")

    # Node type at pile: CTT when ties exist in both X and Y (n>=4 pile caps)
    # ACI 318-19 Table 23.9.2a: CCT βn=0.80, CTT βn=0.60
    bn_pile = 0.60 if n >= 4 else 0.80
    Pn_pile = fce_node(fc, bn_pile) * A_node_pile_eff / 1000.0
    phi_Pn_pile = PHI_BEARING * Pn_pile
    bear_dcr = P_max/phi_Pn_pile if phi_Pn_pile > 0 else float("inf")

    if isinstance(col, dict):
        sec_ = col.get("section", "Square")
        cbx_ = col.get("bx", 500.0)
        cby_ = col.get("by", 500.0)
        cdm_ = col.get("diam", 500.0)
        A_col = column_area(sec_, cbx_, cby_, cdm_)
    else:
        A_col = float(col) ** 2
    Pn_col = fce_node(fc, 1.00) * A_col / 1000.0
    phi_Pn_col = PHI_BEARING * Pn_col
    col_dcr = Pu/phi_Pn_col if phi_Pn_col > 0 else float("inf")  # Pu only — W_cap not through column node

    fy_x_design = _design_fy(fy if fy_x is None else fy_x)
    fy_y_design = _design_fy(fy if fy_y is None else fy_y)
    As_x_stm = (Ftx_max * 1000.0) / (PHI_STM * fy_x_design) if fy_x_design > 0 else 0.0
    As_y_stm = (Fty_max * 1000.0) / (PHI_STM * fy_y_design) if fy_y_design > 0 else 0.0

    # --- 3-pile resultant tie force (user request 2026-04-27) ---
    # For triangular caps, use vector resultant so reinforcement is
    # isotropic and independent of coordinate rotation
    is_3pile_resultant = False
    F_res = 0.0
    As_res = 0.0
    if n == 3:
        F_res = math.hypot(Ftx_max, Fty_max)
        As_res = (F_res * 1000.0) / (PHI_STM * fy_x_design) if fy_x_design > 0 else 0.0
        As_x_stm = As_res
        As_y_stm = (F_res * 1000.0) / (PHI_STM * fy_y_design) if fy_y_design > 0 else 0.0
        is_3pile_resultant = True

    if cap_lx_mm is None or cap_ly_mm is None:
        xmin, xmax, ymin, ymax = _bbox(coords)
        if cap_lx_mm is None:
            cap_lx_mm = max(0.0, xmax - xmin)
        if cap_ly_mm is None:
            cap_ly_mm = max(0.0, ymax - ymin)

    rho_bottom_min = 0.0018
    Ag_x = float(cap_ly_mm) * h_cap
    Ag_y = float(cap_lx_mm) * h_cap
    As_x_min = rho_bottom_min * Ag_x
    As_y_min = rho_bottom_min * Ag_y
    As_x = max(As_x_stm, As_x_min)
    As_y = max(As_y_stm, As_y_min)
    As_x_governs = "STM tie" if As_x_stm >= As_x_min else "0.0018Ag minimum"
    As_y_governs = "STM tie" if As_y_stm >= As_y_min else "0.0018Ag minimum"

    min_a = min(s["theta_deg"] for s in struts)
    a_ok = min_a >= 25.0

    return {
        "n_piles": n,
        "Pu_kN": Pu, "Mux_kNm": Mux, "Muy_kNm": Muy,
        "W_cap_kN": W_cap_kN,
        "Pu_total_kN": Pu_total,
        "pile_loads_kN": pile_loads,
        "column_position": (col_x, col_y),
        "pile_group_centroid": reaction_info["centroid"],
        "reaction_load_point": reaction_info["load_point"],
        "reaction_coords": reaction_info["reaction_coords"],
        "Mux_about_centroid_kNm": reaction_info["Mux_about_centroid_kNm"],
        "Muy_about_centroid_kNm": reaction_info["Muy_about_centroid_kNm"],
        "reaction_equilibrium_OK": reaction_info["equilibrium_OK"],
        "reaction_equilibrium_residual_Mux_kNm": reaction_info["equilibrium_residual_Mux_kNm"],
        "reaction_equilibrium_residual_Muy_kNm": reaction_info["equilibrium_residual_Muy_kNm"],
        "reaction_warnings": reaction_info["warnings"],
        "P_max_kN": P_max, "P_min_kN": P_min,
        "has_uplift": has_uplift,
        "d_effective_mm": d_eff, "struts": struts,
        "F_tie_x_max_kN": Ftx_max, "F_tie_y_max_kN": Fty_max,
        "F_tie_max_kN": max(Ftx_max, Fty_max),
        "F_tie_res_kN": F_res,
        "is_3pile_resultant": is_3pile_resultant,
        "F_tie_x_design_kN": F_res if is_3pile_resultant else Ftx_max,
        "F_tie_y_design_kN": F_res if is_3pile_resultant else Fty_max,
        "fy_x_design_mpa": fy_x_design,
        "fy_y_design_mpa": fy_y_design,
        "x_bar_size": x_bar_size,
        "y_bar_size": y_bar_size,
        "bottom_min_rho": rho_bottom_min,
        "bottom_Ag_x_mm2": Ag_x,
        "bottom_Ag_y_mm2": Ag_y,
        "As_x_stm_required_mm2": As_x_stm,
        "As_y_stm_required_mm2": As_y_stm,
        "As_x_min_required_mm2": As_x_min,
        "As_y_min_required_mm2": As_y_min,
        "As_x_required_mm2": As_x, "As_y_required_mm2": As_y,
        "As_required_mm2": max(As_x, As_y),
        "As_x_governs": As_x_governs,
        "As_y_governs": As_y_governs,
        "fce_strut_MPa": fce_s, "phi_Fns_kN": phi_Fns,
        "A_strut_eff_mm2": A_strut_eff,
        "F_strut_max_kN": Fs_max, "strut_DCR": strut_dcr,
        "bn_pile": bn_pile,
        "A_node_pile_eff_mm2": A_node_pile_eff,
        "phi_Pn_bearing_kN": phi_Pn_pile, "bearing_DCR": bear_dcr,
        "phi_Pn_column_kN": phi_Pn_col, "column_DCR": col_dcr,
        "min_strut_angle_deg": min_a, "angle_OK": a_ok,
        "capacity_model": "PRELIMINARY_FULL_PILE_HEAD_AREA",
        "capacity_model_note": (
            "Preliminary STM check: strut and pile-node capacities use the "
            "full pile head area as the effective concrete area. Final design "
            "should verify nodal-zone and strut geometry explicitly."),
        "overall_OK": (strut_dcr <= 1 and bear_dcr <= 1 and
                       col_dcr <= 1 and a_ok and not has_uplift and
                       reaction_info["equilibrium_OK"]),
    }


def compute_top_reinforcement(lx_mm, ly_mm, h_cap_mm, fy_mpa, fc_mpa,
                              cover_mm=75.0, top_bar_size="DB20"):
    """Minimum top-face reinforcement for an STM pile cap.

    Bottom reinforcement is checked against 0.0018Ag in each direction. The
    top face uses half of that gross-area minimum: As_top = (0.0018Ag)/2.
    """
    # ── fy for design: bar-specific then ACI cap ──────────────────
    fy_bar  = REBAR_FY.get(top_bar_size, fy_mpa)   # from REBAR_FY dict
    fy_d    = min(fy_bar, FY_CAP_MPA)               # ACI §20.2.2.4 cap
    db_top  = REBAR_DIAM_MM.get(top_bar_size, 20.0) # nominal diameter

    # ── User design basis: top mat = 1/2 of 0.0018Ag ────────────
    rho_full_min = 0.0018
    rho_top = rho_full_min / 2.0
    Ag_x = ly_mm * h_cap_mm
    Ag_y = lx_mm * h_cap_mm
    As_full_min_x = rho_full_min * Ag_x
    As_full_min_y = rho_full_min * Ag_y
    As_top_x = rho_top * Ag_x
    As_top_y = rho_top * Ag_y

    # ── (B) Min flexural As, reference only ─────────────────────
    d_top   = max(1.0, h_cap_mm - cover_mm - db_top / 2.0)
    rho_flex = max(0.25 * math.sqrt(fc_mpa) / fy_d,
                   1.4 / fy_d)
    As_flex_x = rho_flex * ly_mm * d_top
    As_flex_y = rho_flex * lx_mm * d_top

    # ── (C) STM distributed reinforcement, reference only ───────
    rho_cc  = 0.003
    As_cc_x = rho_cc * ly_mm * h_cap_mm
    As_cc_y = rho_cc * lx_mm * h_cap_mm

    # ── Governing As ────────────────────────────────────────────
    top_basis = "(0.0018Ag)/2 top-face minimum  (ρ = {:.4f})".format(rho_top)
    top_note = (
        "Top-face As is calculated as one-half of the 0.0018Ag minimum in "
        "each direction. Bottom-face reinforcement is checked separately "
        "against the full 0.0018Ag minimum and STM tie demand."
    )

    # ── (D) Spacing limits ────────────────────────────────────────
    # §24.4.3.3: s ≤ min(3h, 450 mm)
    s_ts_max  = min(3.0 * h_cap_mm, 450.0)
    # §24.3.2: crack-width control (service stress = 2/3 × fy_d)
    fs_serv   = (2.0 / 3.0) * fy_d
    s_crack_1 = 380.0 * (280.0 / fs_serv)   # eq. (a)
    s_crack_2 = 300.0 * (280.0 / fs_serv)   # eq. (b) — governs
    s_crack   = min(s_crack_1, s_crack_2)
    s_max_top = min(s_ts_max, s_crack) if fy_d > 420.0 else s_ts_max

    A_top_bar = REBAR_DB.get(top_bar_size, REBAR_DB["DB20"])
    edge_inset = min(max(float(cover_mm), float(db_top)),
                     0.45 * min(float(lx_mm), float(ly_mm)))
    usable_x = max(0.0, float(lx_mm) - 2.0 * edge_inset)
    usable_y = max(0.0, float(ly_mm) - 2.0 * edge_inset)

    def _top_bar_count(As_req, distribution_width):
        n_area = max(2, int(math.ceil(As_req / A_top_bar))) if As_req > 0 else 2
        if s_max_top > 0:
            n_spacing = max(2, int(math.ceil(distribution_width / s_max_top)) + 1)
        else:
            n_spacing = n_area
        n = max(n_area, n_spacing)
        spacing = distribution_width / (n - 1) if n > 1 else 0.0
        return n, spacing, n * A_top_bar, n_area, n_spacing

    # X-bars run horizontally and are distributed across Ly.
    top_x_n, top_x_spacing, top_x_As, top_x_n_area, top_x_n_spacing = (
        _top_bar_count(As_top_x, usable_y))
    # Y-bars run vertically and are distributed across Lx.
    top_y_n, top_y_spacing, top_y_As, top_y_n_area, top_y_n_spacing = (
        _top_bar_count(As_top_y, usable_x))

    # flag if fy_bar was capped
    fy_was_capped = (fy_bar > FY_CAP_MPA)
    fy_note = ""
    if fy_was_capped:
        fy_note = ("fy_bar={:.0f} MPa capped to {:.0f} MPa "
                   "(ACI §20.2.2.4)".format(fy_bar, FY_CAP_MPA))
    elif fy_d > 420.0:
        fy_note = ("fy={:.0f} MPa > 420 MPa "
                   "(spacing checked §24.3.2)".format(fy_d))
    else:
        fy_note = "fy={:.0f} MPa ≤ 420 MPa".format(fy_d)

    return {
        # Bar info
        "top_bar_size":  top_bar_size,
        "fy_bar_mpa":    fy_bar,
        "fy_design_mpa": fy_d,
        "db_top_mm":     db_top,
        "fy_note":       fy_note,
        # Governing ratios
        "rho_ts":   rho_full_min,
        "rho_full_min": rho_full_min,
        "rho_top":  rho_top,
        "rho_flex": rho_flex,
        "rho_cc":   rho_cc,
        "d_top_mm": d_top,
        # Per-check As (mm²)
        "Ag_x_mm2": Ag_x, "Ag_y_mm2": Ag_y,
        "As_ts_x_mm2":   As_full_min_x,
        "As_ts_y_mm2":   As_full_min_y,
        "As_full_min_x_mm2": As_full_min_x,
        "As_full_min_y_mm2": As_full_min_y,
        "As_top_min_x_mm2": As_top_x,
        "As_top_min_y_mm2": As_top_y,
        "As_flex_x_mm2": As_flex_x, "As_flex_y_mm2": As_flex_y,
        "As_cc_x_mm2":   As_cc_x,   "As_cc_y_mm2":   As_cc_y,
        # Controlling
        "As_top_x_mm2": As_top_x,
        "As_top_y_mm2": As_top_y,
        "governs_x": top_basis,
        "governs_y": top_basis,
        "top_design_basis": "HALF_0018AG",
        "top_design_note": top_note,
        "flex_reference_note": (
            "Reference only unless a separate flexural check shows top-face "
            "tension demand."
        ),
        "stm_cc_reference_note": (
            "Reference only; evaluate distributed STM reinforcement with "
            "actual strut and nodal geometry."
        ),
        # Spacing limits (mm)
        "s_ts_max_mm":    s_ts_max,
        "s_crack_mm":     s_crack,
        "s_max_top_mm":   s_max_top,
        "fs_service_mpa": fs_serv,
        # Selected top-bar schedule for detailing
        "top_bar_area_mm2": A_top_bar,
        "top_edge_inset_mm": edge_inset,
        "top_usable_x_mm": usable_x,
        "top_usable_y_mm": usable_y,
        "top_x_n_bars": top_x_n,
        "top_y_n_bars": top_y_n,
        "top_x_spacing_mm": top_x_spacing,
        "top_y_spacing_mm": top_y_spacing,
        "top_x_As_provided_mm2": top_x_As,
        "top_y_As_provided_mm2": top_y_As,
        "top_x_n_area": top_x_n_area,
        "top_y_n_area": top_y_n_area,
        "top_x_n_spacing": top_x_n_spacing,
        "top_y_n_spacing": top_y_n_spacing,
        "top_x_spacing_OK": top_x_spacing <= s_max_top + 1e-6,
        "top_y_spacing_OK": top_y_spacing <= s_max_top + 1e-6,
    }


def check_rebar(bar_size, n_bars, As_req, fy_mpa=None,
                force_req_kN=None, phi=PHI_STM):
    A_per = REBAR_DB[bar_size]
    As_prov = A_per * n_bars
    ratio = (As_prov/As_req) if As_req > 0 else float("inf")
    fy_design = _design_fy(REBAR_FY.get(bar_size, fy_mpa if fy_mpa else 420.0))
    force_capacity = phi * As_prov * fy_design / 1000.0
    force_ok = True if force_req_kN is None else force_capacity >= force_req_kN
    return {
        "bar_size": bar_size, "n_bars": n_bars,
        "As_per_bar": A_per, "As_provided": As_prov,
        "As_required": As_req, "ratio": ratio,
        "fy_design_mpa": fy_design,
        "force_required_kN": force_req_kN,
        "force_capacity_kN": force_capacity,
        "force_ok": force_ok,
        "area_ok": As_prov >= As_req,
        "ok": As_prov >= As_req and force_ok,
    }


def suggest_rebar(As_req, preferred=("DB16", "DB20", "DB25")):
    out = []
    for sz in preferred:
        A = REBAR_DB[sz]
        n = max(2, int(math.ceil(As_req/A))) if As_req > 0 else 2
        out.append((sz, n, n*A))
    return out

# ==============================================================
# AUTO-OPTIMIZE REBAR (minimum total weight)
# ==============================================================
BAR_WEIGHT_PER_M = {
    "DB12": 0.888, "DB16": 1.578, "DB20": 2.466,
    "DB25": 3.853, "DB28": 4.834, "DB32": 6.313,
}


def optimize_rebar(As_req, bar_length_mm, sizes=None,
                   force_req_kN=None, phi=PHI_STM,
                   min_As_req=None):
    """Pick min-weight (bar_size, n) combo satisfying As/force demand.
       Returns (best_dict, all_options_list)."""
    if sizes is None:
        sizes = list(REBAR_DB.keys())
    options = []
    best = None
    min_area_req = As_req if min_As_req is None else min_As_req
    for sz in sizes:
        A = REBAR_DB[sz]
        fy_design = _design_fy(REBAR_FY.get(sz, 420.0))
        As_force_req = 0.0
        if force_req_kN is not None and fy_design > 0:
            As_force_req = force_req_kN * 1000.0 / (phi * fy_design)
        As_req_for_size = max(float(min_area_req), float(As_force_req))
        if As_req_for_size <= 0:
            n = 2
        else:
            n = max(2, int(math.ceil(As_req_for_size / A)))
        wt_per = BAR_WEIGHT_PER_M[sz]
        total_wt = n * (bar_length_mm / 1000.0) * wt_per
        force_capacity = phi * n * A * fy_design / 1000.0
        force_ok = True if force_req_kN is None else force_capacity >= force_req_kN
        area_ok = (n * A) >= min_area_req
        governs = "force" if As_force_req > min_area_req else "0.0018Ag minimum"
        opt = {
            "bar_size": sz, "n_bars": n,
            "As_per_bar": A, "As_provided": n * A,
            "As_required": As_req_for_size,
            "As_min_required": min_area_req,
            "As_force_required": As_force_req,
            "governs": governs,
            "fy_design_mpa": fy_design,
            "force_required_kN": force_req_kN,
            "force_capacity_kN": force_capacity,
            "bar_length_mm": bar_length_mm,
            "weight_kg": total_wt,
            "area_ok": area_ok,
            "force_ok": force_ok,
            "ok": (n * A) >= As_req_for_size and force_ok,
        }
        options.append(opt)
        if opt["ok"] and (best is None or total_wt < best["weight_kg"]):
            best = opt
    if best is None:  # nothing satisfies (shouldn't happen with DB32+n)
        best = max(options, key=lambda o: o["As_provided"])
    return best, options


# ==============================================================
# DEVELOPMENT LENGTH & ANCHORAGE (ACI 318-19 §25.4)
# ==============================================================
def development_length(bar_size_str, fc_mpa, fy_mpa,
                       hooked=False, cb_Ktr_over_db=1.5, lambda_c=1.0):
    """Compute required development length per ACI 318-19 §25.4.
       hooked=False -> ld (straight, §25.4.2.3)
       hooked=True  -> ldh (90°/180° hook, §25.4.3.1)
       Result in mm."""
    db = float(bar_size_str.replace("DB", ""))
    sqfc = math.sqrt(fc_mpa)
    if hooked:
        # Eq. 25.4.3.1a, simplified ψe=ψr=ψo=ψc=1.0
        ldh = (fy_mpa / (23.0 * lambda_c * sqfc)) * (db ** 1.5)
        return max(ldh, 8.0 * db, 150.0)
    else:
        psi_s = 0.8 if db <= 20.0 else 1.0  # §25.4.2.5
        cb = max(1.0, min(2.5, cb_Ktr_over_db))
        ld = (fy_mpa * psi_s / (1.1 * lambda_c * sqfc * cb)) * db
        return max(ld, 300.0)


def check_anchorage(bar_size, fc, fy,
                    available_straight_mm, available_hook_mm):
    """Verify CCT-node anchorage at piles per ACI 318-19 §23.8.3 + §25.4."""
    ld = development_length(bar_size, fc, fy, hooked=False)
    ldh = development_length(bar_size, fc, fy, hooked=True)
    straight_ok = available_straight_mm >= ld
    hook_ok = available_hook_mm >= ldh
    if straight_ok:
        rec = "Straight bar OK"
    elif hook_ok:
        rec = "Use 90° or 180° standard hook"
    else:
        rec = "INSUFFICIENT — increase cap dim or use larger hook"
    return {
        "bar_size": bar_size,
        "ld_required_mm": ld, "ldh_required_mm": ldh,
        "available_straight_mm": available_straight_mm,
        "available_hook_mm": available_hook_mm,
        "straight_ok": straight_ok, "hook_ok": hook_ok,
        "ok": straight_ok or hook_ok,
        "recommended": rec,
    }

# ==============================================================
# COLUMN SECTION HELPER (Phase 1)
# ==============================================================
def column_area(section, bx=500.0, by=500.0, diam=500.0):
    """Cross-section area of column (mm²)."""
    if section == "Rectangular":
        return bx * by
    if section == "Circular":
        return math.pi * (diam / 2.0) ** 2
    return bx * bx  # Square (bx as side)

# 🔵 START Patch 5A — ADD ที่ท้ายไฟล์


# ==============================================================
# PILE SECTION HELPERS (Phase 2)
# ==============================================================
def normalize_pile(p):
    """Accept dict or scalar; return (section, bx, by, diam)."""
    if isinstance(p, dict):
        return (p.get("section", "Circular"),
                p.get("bx", 600.0), p.get("by", 600.0),
                p.get("diam", 600.0))
    return ("Circular", float(p), float(p), float(p))


def pile_area(section, bx=600.0, by=600.0, diam=600.0):
    """Cross-section area of pile (mm²) — full section bearing."""
    if section == "Square":
        return bx * bx
    if section == "Rectangular":
        return bx * by
    return math.pi * (diam / 2.0) ** 2  # Circular


def pile_min_dim(section, bx=600.0, by=600.0, diam=600.0):
    """Governing dimension for spacing rule (2.5 × this)."""
    if section == "Square":
        return bx
    if section == "Rectangular":
        return min(bx, by)
    return diam


def pile_max_dim(section, bx=600.0, by=600.0, diam=600.0):
    """Governing dimension for cap edge / bounding box."""
    if section == "Square":
        return bx
    if section == "Rectangular":
        return max(bx, by)
    return diam

# 🔴 END Patch 5A
