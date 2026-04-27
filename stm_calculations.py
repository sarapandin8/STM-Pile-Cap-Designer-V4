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

def validate_pile_spacing(coords, D, mf=2.5, clear_min=500.0):
    """ACI-style center-to-center spacing check.
       Rule (per ACI / common practice for barrette piles):
           required c/c distance  >=  mf * pile_min_dim
       For Rectangular (Barrette) piles -> mf * shorter side.
       For Circular / Square            -> mf * D (or side).
       NOTE: anti-collision (edge-to-edge) is enforced inside
       get_preset_layouts() by construction, so the validator
       only checks the standard ACI distance rule.
       'clear_min' kept in signature for API compatibility (unused)."""
    _ = clear_min  # reserved for future use
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
            pairs.append((i+1, j+1, d, d >= req-1e-3))
            if d < mn:
                mn = d
            if d < req-1e-3:
                viol.append((i+1, j+1, d))
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


def compute_pile_reactions(coords, Pu, Mux_kNm, Muy_kNm):
    """Rigid-cap elastic distribution.
       P_i = Pu/n + Mux*y_i/Σy² + Muy*x_i/Σx²
       Mux/Muy in kN·m; coords in mm. Result in kN."""
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


def stm_design(coords, Pu, Mux, Muy, fc, fy, D, col, h_cap,
               cover=75.0, beta_s=0.75):
    """STM design per ACI 318-19 Ch. 23. No separate punching/beam shear
       check (per ACI §13.4.6.3 — covered by strut & node strength)."""
    n = len(coords)
    if n < 2:
        return {"error": "Need at least 2 piles."}

    pile_loads = compute_pile_reactions(coords, Pu, Mux, Muy)
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
        L_h = math.hypot(x, y)
        L_s = math.hypot(L_h, d_eff)
        th = math.degrees(math.atan2(d_eff, L_h)) if L_h > 0 else 90.0
        F_s = Pi * (L_s/d_eff)
        F_tx = Pi * abs(x)/d_eff
        F_ty = Pi * abs(y)/d_eff
        struts.append({
            "coord": (x, y), "P_i_kN": pile_loads[i],
            "L_h": L_h, "L_strut": L_s, "theta_deg": th,
            "F_strut_kN": F_s,
            "F_tie_x_kN": F_tx, "F_tie_y_kN": F_ty,
        })

    # PATCHED 2026-04-27: use Σ Pi·x/d instead of max per pile
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

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
    fce_s = fce_strut(fc, bs=beta_s)
    Fns = fce_s * A_s / 1000.0
    phi_Fns = PHI_STM * Fns
    strut_dcr = Fs_max/phi_Fns if phi_Fns > 0 else float("inf")

    # Node type at pile: CTT when ties exist in both X and Y (n>=4 pile caps)
    # ACI 318-19 Table 23.9.2a: CCT βn=0.80, CTT βn=0.60
    bn_pile = 0.60 if n >= 4 else 0.80
    Pn_pile = fce_node(fc, bn_pile) * A_s / 1000.0
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
    col_dcr = Pu/phi_Pn_col if phi_Pn_col > 0 else float("inf")

    As_x = (Ftx_max * 1000.0) / (PHI_STM * fy) if fy > 0 else 0.0
    As_y = (Fty_max * 1000.0) / (PHI_STM * fy) if fy > 0 else 0.0

    # --- 3-pile resultant tie force (user request 2026-04-27) ---
    # For triangular caps, use vector resultant so reinforcement is
    # isotropic and independent of coordinate rotation
    is_3pile_resultant = False
    F_res = 0.0
    As_res = 0.0
    if n == 3:
        F_res = math.hypot(Ftx_max, Fty_max)
        As_res = (F_res * 1000.0) / (PHI_STM * fy) if fy > 0 else 0.0
        As_x = As_y = As_res
        is_3pile_resultant = True

    min_a = min(s["theta_deg"] for s in struts)
    a_ok = min_a >= 25.0

    return {
        "n_piles": n,
        "Pu_kN": Pu, "Mux_kNm": Mux, "Muy_kNm": Muy,
        "pile_loads_kN": pile_loads,
        "P_max_kN": P_max, "P_min_kN": P_min,
        "has_uplift": has_uplift,
        "d_effective_mm": d_eff, "struts": struts,
        "F_tie_x_max_kN": Ftx_max, "F_tie_y_max_kN": Fty_max,
        "F_tie_max_kN": max(Ftx_max, Fty_max),
        "F_tie_res_kN": F_res,
        "is_3pile_resultant": is_3pile_resultant,
        "As_x_required_mm2": As_x, "As_y_required_mm2": As_y,
        "As_required_mm2": max(As_x, As_y),
        "fce_strut_MPa": fce_s, "phi_Fns_kN": phi_Fns,
        "F_strut_max_kN": Fs_max, "strut_DCR": strut_dcr,
        "bn_pile": bn_pile,
        "phi_Pn_bearing_kN": phi_Pn_pile, "bearing_DCR": bear_dcr,
        "phi_Pn_column_kN": phi_Pn_col, "column_DCR": col_dcr,
        "min_strut_angle_deg": min_a, "angle_OK": a_ok,
        "overall_OK": (strut_dcr <= 1 and bear_dcr <= 1 and
                       col_dcr <= 1 and a_ok),
    }


def compute_top_reinforcement(lx_mm, ly_mm, h_cap_mm, fy_mpa, fc_mpa,
                              cover_mm=75.0, top_bar_size="DB20"):
    """Minimum top-face reinforcement for STM pile cap — ACI 318-19.

    Three independent As checks + one spacing check are evaluated.

    ─────────────────────────────────────────────────────────────────
    (A) Temperature & Shrinkage  ─  ACI 318-19 §24.4.3.2 Table 24.4.3.2
        ρ_ts = 0.0018              fy_d ≤ 420 MPa
        ρ_ts = 0.0018 × 420 / fy_d  fy_d > 420 MPa  (min 0.0014)
        As = ρ_ts × b × h_cap

    (B) Minimum Flexural Reinforcement  ─  ACI 318-19 §9.6.1.2
        ρ_flex = max(0.25√f'c / fy_d,  1.4 / fy_d)
        As = ρ_flex × b × d_top
        d_top = h_cap − cover − db_top/2

    (C) Crack-Control for STM  ─  ACI 318-19 §23.5.1
        Conservative: ρ_face ≥ 0.003 per orthogonal direction per face
        As = 0.003 × b × h_cap

    (D) Spacing Limit (crack-width control)  ─  ACI 318-19 §24.3.2
        fs = (2/3) fy_d  (service stress, ACI default)
        s ≤ min(380×(280/fs), 300×(280/fs)) mm
        Combined with §24.4.3.3: s ≤ min(3h, 450 mm, s_crack)
    ─────────────────────────────────────────────────────────────────
    fy_d = min(REBAR_FY[top_bar_size], FY_CAP_MPA)
         → fy_d ≤ 420 uses fy from REBAR_FY directly
         → fy_d > 420 automatically adjusted per checks above
         → hard cap at 550 MPa per ACI §20.2.2.4
    """
    # ── fy for design: bar-specific then ACI cap ──────────────────
    fy_bar  = REBAR_FY.get(top_bar_size, fy_mpa)   # from REBAR_FY dict
    fy_d    = min(fy_bar, FY_CAP_MPA)               # ACI §20.2.2.4 cap
    db_top  = REBAR_DIAM_MM.get(top_bar_size, 20.0) # nominal diameter

    # ── (A) T&S ─ §24.4.3.2 Table 24.4.3.2 ─────────────────────
    if fy_d <= 420.0:
        rho_ts = 0.0018
    else:
        rho_ts = max(0.0014, 0.0018 * 420.0 / fy_d)

    As_ts_x = rho_ts * ly_mm * h_cap_mm
    As_ts_y = rho_ts * lx_mm * h_cap_mm

    # ── (B) Min Flexural As ─ §9.6.1.2 (ref. §13.3.3.1) ─────────
    d_top   = max(1.0, h_cap_mm - cover_mm - db_top / 2.0)
    rho_flex = max(0.25 * math.sqrt(fc_mpa) / fy_d,
                   1.4 / fy_d)
    As_flex_x = rho_flex * ly_mm * d_top
    As_flex_y = rho_flex * lx_mm * d_top

    # ── (C) Crack-control ─ §23.5.1 (ρ_face ≥ 0.003) ────────────
    rho_cc  = 0.003
    As_cc_x = rho_cc * ly_mm * h_cap_mm
    As_cc_y = rho_cc * lx_mm * h_cap_mm

    # ── Controlling As ────────────────────────────────────────────
    As_top_x = max(As_ts_x, As_flex_x, As_cc_x)
    As_top_y = max(As_ts_y, As_flex_y, As_cc_y)

    def _governs(ts_v, flex_v, cc_v):
        if cc_v >= ts_v and cc_v >= flex_v:
            return "§23.5.1 crack-control  (ρ = 0.003)"
        if flex_v >= ts_v:
            return "§9.6.1.2 min-flex  (ρ = {:.4f})".format(rho_flex)
        return "§24.4.3.2 T&S  (ρ = {:.4f})".format(rho_ts)

    # ── (D) Spacing limits ────────────────────────────────────────
    # §24.4.3.3: s ≤ min(3h, 450 mm)
    s_ts_max  = min(3.0 * h_cap_mm, 450.0)
    # §24.3.2: crack-width control (service stress = 2/3 × fy_d)
    fs_serv   = (2.0 / 3.0) * fy_d
    s_crack_1 = 380.0 * (280.0 / fs_serv)   # eq. (a)
    s_crack_2 = 300.0 * (280.0 / fs_serv)   # eq. (b) — governs
    s_crack   = min(s_crack_1, s_crack_2)
    s_max_top = min(s_ts_max, s_crack)       # combined governing spacing

    # flag if fy_bar was capped
    fy_was_capped = (fy_bar > FY_CAP_MPA)
    fy_note = ""
    if fy_was_capped:
        fy_note = ("fy_bar={:.0f} MPa capped to {:.0f} MPa "
                   "(ACI §20.2.2.4)".format(fy_bar, FY_CAP_MPA))
    elif fy_d > 420.0:
        fy_note = ("fy={:.0f} MPa > 420 → ρ_ts reduced "
                   "(§24.4.3.2); spacing checked §24.3.2".format(fy_d))
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
        "rho_ts":   rho_ts,
        "rho_flex": rho_flex,
        "rho_cc":   rho_cc,
        "d_top_mm": d_top,
        # Per-check As (mm²)
        "As_ts_x_mm2":   As_ts_x,   "As_ts_y_mm2":   As_ts_y,
        "As_flex_x_mm2": As_flex_x, "As_flex_y_mm2": As_flex_y,
        "As_cc_x_mm2":   As_cc_x,   "As_cc_y_mm2":   As_cc_y,
        # Controlling
        "As_top_x_mm2": As_top_x,
        "As_top_y_mm2": As_top_y,
        "governs_x": _governs(As_ts_x, As_flex_x, As_cc_x),
        "governs_y": _governs(As_ts_y, As_flex_y, As_cc_y),
        # Spacing limits (mm)
        "s_ts_max_mm":    s_ts_max,
        "s_crack_mm":     s_crack,
        "s_max_top_mm":   s_max_top,
        "fs_service_mpa": fs_serv,
    }


def check_rebar(bar_size, n_bars, As_req):
    A_per = REBAR_DB[bar_size]
    As_prov = A_per * n_bars
    ratio = (As_prov/As_req) if As_req > 0 else float("inf")
    return {
        "bar_size": bar_size, "n_bars": n_bars,
        "As_per_bar": A_per, "As_provided": As_prov,
        "As_required": As_req, "ratio": ratio,
        "ok": As_prov >= As_req,
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


def optimize_rebar(As_req, bar_length_mm, sizes=None):
    """Pick min-weight (bar_size, n) combo satisfying As_req.
       Returns (best_dict, all_options_list)."""
    if sizes is None:
        sizes = list(REBAR_DB.keys())
    options = []
    best = None
    for sz in sizes:
        A = REBAR_DB[sz]
        if As_req <= 0:
            n = 2
        else:
            n = max(2, int(math.ceil(As_req / A)))
        wt_per = BAR_WEIGHT_PER_M[sz]
        total_wt = n * (bar_length_mm / 1000.0) * wt_per
        opt = {
            "bar_size": sz, "n_bars": n,
            "As_per_bar": A, "As_provided": n * A,
            "As_required": As_req,
            "bar_length_mm": bar_length_mm,
            "weight_kg": total_wt,
            "ok": (n * A) >= As_req,
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