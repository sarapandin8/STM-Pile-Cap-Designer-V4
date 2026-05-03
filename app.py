import json
import streamlit as st
import pandas as pd

from stm_calculations import (
    get_preset_layouts, get_truncated_triangle_equal,
    validate_pile_spacing, compute_cap_bounds_per_side,
    parse_custom_coords, stm_design,
    check_rebar, suggest_rebar, REBAR_DB,
    REBAR_FY, REBAR_DIAM_MM, FY_CAP_MPA,
    compute_pile_reactions,
    optimize_rebar, check_anchorage,
    compute_top_reinforcement,
)
def _cap_area_m2(cap_polygon, cap_lx, cap_ly):
    """คำนวณพื้นที่ฐานราก (m²)
    - มี cap_polygon (truncated triangle) → Shoelace formula (พื้นที่จริง)
    - ไม่มี cap_polygon → Lx × Ly (bounding box)"""
    if cap_polygon and len(cap_polygon) >= 3:
        pts = cap_polygon
        n = len(pts)
        area = abs(sum(pts[i][0]*pts[(i+1)%n][1] -
                       pts[(i+1)%n][0]*pts[i][1]
                       for i in range(n))) / 2.0
        return area / 1e6  # mm² → m²
    return (cap_lx / 1000.0) * (cap_ly / 1000.0)


from stm_visualization import (
    plot_layout_preview, plot_plan_view,
    plot_elevation, plot_rebar_layout, plot_3d_view,
    plot_top_rebar_layout,
)
from report_generator import generate_report

st.set_page_config(page_title="STM Pile Cap Designer",
                   layout="wide", page_icon="🏗️")

# --------- Session-state defaults (for save/load) ---------
DEFAULTS = {
    "fc": 28.0, "fy": 420.0, "cover": 75,
    "Pu": 5000.0, "Mux": 0.0, "Muy": 0.0,
    "col_size": 500, "D": 600, "h_cap": 900,
    "col_section": "Square",
    "col_bx": 500.0, "col_by": 500.0, "col_diam": 500.0,
    "col_x": 0.0, "col_y": 0.0,
    "pile_section": "Circular",
    "pile_bx": 600.0, "pile_by": 600.0, "pile_diam": 600.0,
    "preset_choice": "4-Pile (Square)",
    "spacing_factor": 2.5,
    "adv_spacing": False,
    "sf_x": 2.5, "sf_y": 2.5, "clear_min": 500.0,
    "e_left": 450.0, "e_right": 450.0,
    "e_top": 450.0, "e_bot": 450.0,
    "L_side": 4000, "w_trunc": 600, "e_trunc": 450.0,
    "custom_text": "1500,1500\n-1500,1500\n-1500,-1500\n1500,-1500",
    "custom_shape": "Square",
    "x_bar": "DB20", "x_n": 8,
    "y_bar": "DB20", "y_n": 8,
    "top_bar_size": "DB20",
    "wcap_uls_factor": 1.2,
}
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

st.title("🏗️ STM Pile Cap Designer")
st.caption("Strut-and-Tie Method - ACI 318-19 / CRSI Design Handbook")

# --------- Save / Load JSON ---------
with st.sidebar:
    st.subheader("💾 Save / Load Design")
    sl1, sl2 = st.columns(2)
    state_for_save = {k: st.session_state[k] for k in DEFAULTS}
    sl1.download_button(
        "💾 Save",
        data=json.dumps(state_for_save, indent=2),
        file_name="pile_cap_design.json",
        mime="application/json",
        use_container_width=True)
    up = sl2.file_uploader("📂 Open File", type="json",
                           label_visibility="visible",
                           key="json_uploader")
    if up is not None and up.file_id != st.session_state.get(
            "_last_upload_id"):
        try:
            data = json.loads(up.read().decode("utf-8"))
            for k in DEFAULTS:
                if k in data:
                    st.session_state[k] = data[k]
            st.session_state["_last_upload_id"] = up.file_id
            st.success("Loaded — refreshing...")
            st.rerun()
        except Exception as exc:
            st.error("Load failed: {}".format(exc))
    st.caption("💡 ไฟล์จะถูกบันทึกที่ Downloads folder "
               "หากต้องการเลือก folder เอง ให้เปิด "
               "\"Ask where to save\" ในการตั้งค่า Browser")

    st.divider()
    st.header("⚙️ Inputs")

    with st.expander("Materials", expanded=True):
        st.number_input("f'c (MPa)", 21.0, 80.0, step=1.0, key="fc")
        st.number_input("fy (MPa)", 280.0, 700.0, step=10.0, key="fy")
        st.number_input("Cover (mm)", 50, 200, step=5, key="cover")

    with st.expander("Column Loads", expanded=True):
        st.number_input("Pu — axial (kN)",
                        100.0, 50000.0, step=100.0, key="Pu")
        st.number_input("Mux — moment about X (kN·m)",
                        -50000.0, 50000.0, step=10.0, key="Mux",
                        help="P_i ∝ +y_i when Mux > 0")
        st.number_input("Muy — moment about Y (kN·m)",
                        -50000.0, 50000.0, step=10.0, key="Muy",
                        help="P_i ∝ +x_i when Muy > 0")
        
        st.selectbox("Column section",
                     ["Square", "Rectangular", "Circular"],
                     key="col_section")
        if st.session_state.col_section == "Square":
            st.number_input("Column side b (mm)",
                            200.0, 2000.0, step=50.0, key="col_bx")
            st.session_state.col_by = st.session_state.col_bx
        elif st.session_state.col_section == "Rectangular":
            cc1, cc2 = st.columns(2)
            cc1.number_input("bx (mm)", 200.0, 2000.0,
                             step=50.0, key="col_bx")
            cc2.number_input("by (mm)", 200.0, 2000.0,
                             step=50.0, key="col_by")
        else:
            st.number_input("Diameter D_c (mm)",
                            200.0, 2000.0, step=50.0, key="col_diam")
        pc1, pc2 = st.columns(2)
        pc1.number_input("Column X (mm)",
                         -10000.0, 10000.0, step=50.0, key="col_x",
                         help="Column/load point coordinate measured from layout origin.")
        pc2.number_input("Column Y (mm)",
                         -10000.0, 10000.0, step=50.0, key="col_y",
                         help="Column/load point coordinate measured from layout origin.")

    with st.expander("Pile & Cap", expanded=True):
        st.selectbox("Pile section",
                     ["Circular", "Square", "Rectangular"],
                     key="pile_section")
        if st.session_state.pile_section == "Circular":
            st.number_input("Pile diameter D (mm)",
                            200.0, 3500.0, step=50.0, key="pile_diam")
        elif st.session_state.pile_section == "Square":
            st.number_input("Pile side b (mm)",
                            200.0, 3500.0, step=50.0, key="pile_bx")
            st.session_state.pile_by = st.session_state.pile_bx
        else:
            pp1, pp2 = st.columns(2)
            pp1.number_input("Pile bx (mm)",
                             200.0, 3500.0, step=50.0, key="pile_bx")
            pp2.number_input("Pile by (mm)",
                             200.0, 3500.0, step=50.0, key="pile_by")
        st.number_input("Cap thickness (mm)", 400, 3000, step=50,
                        key="h_cap")
        st.number_input(
            "W_cap ULS factor (γ)",
            min_value=1.0, max_value=2.0, step=0.05,
            key="wcap_uls_factor",
            help="W_cap(ULS) = Lx × Ly × h × 24 × γ  "
                 "ค่าแนะนำ: 1.2 (DL factor) หรือ 1.35 (Eurocode)")

    fc = st.session_state.fc
    fy = st.session_state.fy
    cover = st.session_state.cover
    Pu = st.session_state.Pu
    Mux = st.session_state.Mux
    Muy = st.session_state.Muy
    col_size = {
        "section": st.session_state.col_section,
        "bx": float(st.session_state.col_bx),
        "by": float(st.session_state.col_by),
        "diam": float(st.session_state.col_diam),
        "x": float(st.session_state.col_x),
        "y": float(st.session_state.col_y),
    }
    D = {
        "section": st.session_state.pile_section,
        "bx": float(st.session_state.pile_bx),
        "by": float(st.session_state.pile_by),
        "diam": float(st.session_state.pile_diam),
    }
    h_cap = st.session_state.h_cap

    st.divider()
    st.header("📐 Pile Arrangement")

    if D["section"] == "Circular":
        _gov_max = D["diam"]
    elif D["section"] == "Square":
        _gov_max = D["bx"]
    else:
        _gov_max = max(D["bx"], D["by"])
    e_def = max(150.0, 0.75 * _gov_max)
    presets_init = get_preset_layouts(
        D, sf=2.5, clear_min=st.session_state.clear_min,
        e_left=e_def, e_right=e_def, e_top=e_def, e_bot=e_def)
    options = list(presets_init.keys()) + [
        "3-Pile (Truncated Triangle - Equal corners)",
        "Custom (User-defined coords)",
    ]
    if st.session_state.preset_choice not in options:
        st.session_state.preset_choice = options[3]
    st.selectbox("Preset", options, key="preset_choice")
    chosen = st.session_state.preset_choice

    is_custom = chosen.startswith("Custom")
    is_trunc = chosen.startswith("3-Pile (Truncated")

    st.slider("Spacing factor (xD)", 2.5, 5.0, step=0.1,
              key="spacing_factor",
              disabled=(is_custom or is_trunc))

    with st.expander("⚙️ Advanced spacing (Manual override)",
                     expanded=False):
        st.checkbox(
            "Enable per-axis override (sf_x / sf_y)",
            key="adv_spacing",
            disabled=(is_custom or is_trunc),
            help="When OFF: same factor applied to both X and Y. "
                 "When ON: control X and Y spacing factors independently "
                 "(useful for Rectangular/Barrette piles).")
        _adv_off = (not st.session_state.adv_spacing)             or is_custom or is_trunc
        ax1, ax2 = st.columns(2)
        ax1.slider("sf_x (× pile_X)", 1.5, 6.0, step=0.1,
                   key="sf_x", disabled=_adv_off)
        ax2.slider("sf_y (× pile_Y)", 1.5, 6.0, step=0.1,
                   key="sf_y", disabled=_adv_off)
        st.number_input(
            "Min clear edge-to-edge (mm)",
            100.0, 2000.0, step=50.0, key="clear_min",
            disabled=(is_custom or is_trunc),
            help="Anti-collision: pile edges never closer than this. "
                 "Default 500 mm.")
        st.caption(
            "Auto-fix rule: s = max(sf × pile_dim, pile_dim + clear_min). "
            "For 300×1000 piles → spacing auto-expands along the long axis "
            "to prevent overlap.")

    st.markdown("**Edge distance per side (mm)**")
    c1, c2 = st.columns(2)
    c1.number_input("e_left", 50.0, 1000.0, step=10.0, key="e_left")
    c2.number_input("e_right", 50.0, 1000.0, step=10.0, key="e_right")
    c1.number_input("e_top", 50.0, 1000.0, step=10.0, key="e_top")
    c2.number_input("e_bot", 50.0, 1000.0, step=10.0, key="e_bot")
    e_left = st.session_state.e_left
    e_right = st.session_state.e_right
    e_top = st.session_state.e_top
    e_bot = st.session_state.e_bot
    spacing_factor = st.session_state.spacing_factor

    coords = []
    shape_label = "Custom"
    cap_lx = cap_ly = 1500.0
    cap_cx = cap_cy = 0.0
    cap_polygon = None
    trunc_extra = ""

    if is_trunc:
        st.markdown("**Truncated Equilateral Triangle**")
        st.number_input("Side L (mm)", 1000, 10000, step=50, key="L_side")
        st.number_input("Truncation w (mm)", 100, 3000, step=25,
                        key="w_trunc")
        st.number_input("Pile-to-edge e (mm)", 50.0, 1500.0, step=10.0,
                        key="e_trunc")
        cfg = get_truncated_triangle_equal(
            D, float(st.session_state.L_side),
            float(st.session_state.w_trunc),
            float(st.session_state.e_trunc))
        coords = list(cfg["coords"])
        shape_label = cfg["shape"]
        cap_lx, cap_ly = cfg["lx"], cfg["ly"]
        cap_cx, cap_cy = cfg["cx"], cfg["cy"]
        cap_polygon = cfg["cap_polygon"]
        trunc_extra = (
            "d_p = R - w·√3/2 - e - D/2 = {:.0f} mm  |  "
            "Pile spacing = d_p·√3 = {:.0f} mm".format(
                cfg['d_p'], cfg['pile_spacing']))
        if cfg['d_p'] <= 0:
            st.error("Triangle too small. Increase L.")
    elif not is_custom:
        _sfx = st.session_state.sf_x if st.session_state.adv_spacing else None
        _sfy = st.session_state.sf_y if st.session_state.adv_spacing else None
        presets = get_preset_layouts(
            D, sf=spacing_factor,
            clear_min=st.session_state.clear_min,
            sf_x=_sfx, sf_y=_sfy,
            e_left=e_left, e_right=e_right,
            e_top=e_top, e_bot=e_bot)
        cfg = presets[chosen]
        coords = list(cfg["coords"])
        shape_label = cfg["shape"]
        cap_lx, cap_ly = cfg["lx"], cfg["ly"]
        cap_cx, cap_cy = cfg["cx"], cfg["cy"]
    else:
        st.markdown("**Custom coordinates (mm)** (one `x, y` per line)")
        st.caption(
            "Default = 4 piles in a 3×3 m square arrangement. "
            "Edit, then click Update to apply.")
        _default_custom = "1500,1500\n-1500,1500\n-1500,-1500\n1500,-1500"
        _applied_txt = st.session_state.get("custom_text", "") or ""
        if not _applied_txt.strip():
            _applied_txt = _default_custom
            st.session_state.custom_text = _applied_txt
        if st.session_state.get("_custom_text_applied_seen") != _applied_txt:
            st.session_state.custom_text_draft = _applied_txt
            st.session_state._custom_text_applied_seen = _applied_txt
        st.text_area("Coords", height=140,
                     label_visibility="collapsed",
                     key="custom_text_draft")
        draft_txt = st.session_state.get("custom_text_draft", "")
        draft_coords = parse_custom_coords(draft_txt)
        b_apply, b_status = st.columns([1, 2])
        if b_apply.button("Update pile coordinates",
                          use_container_width=True,
                          key="apply_custom_coords"):
            if len(draft_coords) < 2:
                st.error("Please enter at least 2 valid pile coordinates.")
            else:
                st.session_state.custom_text = draft_txt
                st.session_state._custom_text_applied_seen = draft_txt
                st.session_state.pop("_stm_results", None)
                st.rerun()
        if draft_txt != _applied_txt:
            b_status.warning(
                "Draft not applied yet. Click Update to refresh the plot.")
        else:
            b_status.caption(
                "Applied coordinates: {} pile(s).".format(len(draft_coords)))
        coords = parse_custom_coords(st.session_state.custom_text)
        st.selectbox("Cap shape (visual)",
                     ["Square", "Rectangular", "Triangular"],
                     key="custom_shape")
        shape_label = st.session_state.custom_shape
        if coords:
            cap_lx, cap_ly, cap_cx, cap_cy = compute_cap_bounds_per_side(
                coords, e_left, e_right, e_top, e_bot, D)

    st.divider()
    st.subheader("🔩 Rebar Selection")
    bar_options = list(REBAR_DB.keys())
    cA, cB = st.columns(2)
    cA.selectbox("X-dir bar", bar_options, key="x_bar")
    cA.number_input("X-dir count", 2, 400, step=1, key="x_n")
    cB.selectbox("Y-dir bar", bar_options, key="y_bar")
    cB.number_input("Y-dir count", 2, 400, step=1, key="y_n")
    x_bar = st.session_state.x_bar
    x_n = st.session_state.x_n
    y_bar = st.session_state.y_bar
    y_n = st.session_state.y_n

    st.divider()
    calc_btn = st.button("🧮 Calculate STM",
                         type="primary", use_container_width=True)

# ===== Validation =====
ok_sp, mn_sp, viol, mn_req, pairs = validate_pile_spacing(
    coords, D, mf=2.5, clear_min=st.session_state.clear_min)
mn_clear = min((p[3] for p in pairs), default=0.0)

# ===== Layout & Status =====
left, right = st.columns([3, 2], gap="large")
with left:
    st.subheader("📍 Layout Preview (Live)")
    if not coords:
        st.warning("No piles defined.")
    else:
        W_cap_preview = _cap_area_m2(cap_polygon, cap_lx, cap_ly) \
                        * (h_cap/1000.0) * 24.0 \
                        * st.session_state.wcap_uls_factor
        pile_loads_preview = compute_pile_reactions(
            coords, Pu + W_cap_preview, Mux, Muy,
            load_point=(col_size["x"], col_size["y"]))
        st.plotly_chart(
            plot_layout_preview(
                coords, D, cap_lx, cap_ly, cap_cx, cap_cy,
                col_size, shape_label,
                cap_polygon=cap_polygon,
                edge_info=(e_left, e_right, e_top, e_bot),
                pile_loads=pile_loads_preview),
            use_container_width=True)
        if trunc_extra:
            st.info(trunc_extra)

with right:
    st.subheader("✅ Layout Status")
    if not coords:
        st.error("No piles defined.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Piles", len(coords))
        c2.metric("Shape", shape_label)
        c1.metric("Min spacing", "{:.0f} mm".format(mn_sp))
        c2.metric("Required (2.5 × D_short)",
                  "{:.0f} mm".format(mn_req),
                  help="ACI rule: 2.5 × pile_min_dim "
                       "(shorter side for Barrette piles)")
        c1.metric("Min clear", "{:.0f} mm".format(mn_clear))
        c2.metric("Required clear", "{:.0f} mm".format(st.session_state.clear_min))
        if ok_sp:
            st.success(
                "All pile-pair distances and edge clearances satisfy limits.")
        else:
            st.error("{} pile spacing/clearance violation(s).".format(len(viol)))
            for _i, _j, _d, _clear, _reason in viol[:5]:
                st.caption("P{}-P{}: {}".format(_i, _j, _reason))
        st.markdown("**Pile-Pair Distances** (d = √(Δx² + Δy²))")
        if pairs:
            pdf = pd.DataFrame([{
                "Pair": "P{}-P{}".format(i, j),
                "d (mm)": "{:.0f}".format(d),
                "Clear (mm)": "{:.0f}".format(clear),
                "c/c OK?": "✅" if ctc_ok else "❌",
                "Clear OK?": "✅" if clear_ok else "❌",
                "OK?": "✅" if ok else "❌",
            } for (i, j, d, clear, ctc_ok, clear_ok, ok) in pairs])
            st.dataframe(pdf, use_container_width=True, hide_index=True,
                         height=min(35*len(pairs)+38, 240))

st.info(
    "ℹ️ **ACI 318-19 §13.4.6.3 Note:** When the Strut-and-Tie Method (STM) "
    "is used to design a pile cap in accordance with ACI 318-19 Chapter 23, "
    "separate **beam-shear** and **two-way (punching)** shear checks are "
    "**NOT required**. The shear behavior is implicitly captured through "
    "the strength of struts and nodal zones in the STM model.")

st.divider()

# ===== Calculate =====
# ===== Calculate =====
if calc_btn:
    if not coords:
        st.error("Cannot calculate: no piles.")
    elif not ok_sp:
        st.error("Cannot calculate: spacing or pile-clearance violations.")
    else:
        # น้ำหนักตัวเอง Pile Cap (ULS): W = Area × h × γc × γ_ULS
        # Area = พื้นที่จริงของ cap (Shoelace สำหรับ polygon, Lx×Ly สำหรับสี่เหลี่ยม)
        _W_cap_nom = _cap_area_m2(cap_polygon, cap_lx, cap_ly) * (h_cap/1000.0) * 24.0
        W_cap_kN = _W_cap_nom * st.session_state.wcap_uls_factor
        _fy_x = min(REBAR_FY.get(x_bar, fy), FY_CAP_MPA)
        _fy_y = min(REBAR_FY.get(y_bar, fy), FY_CAP_MPA)
        _res = stm_design(coords, Pu, Mux, Muy, fc, fy, D,
                          col_size, h_cap, cover, W_cap_kN=W_cap_kN,
                          fy_x=_fy_x, fy_y=_fy_y,
                          x_bar_size=x_bar, y_bar_size=y_bar)
        if "error" in _res:
            st.error(_res["error"])
            st.session_state.pop("_stm_results", None)
        else:
            st.session_state["_stm_results"] = _res

# ===== Display (persists across reruns — dropdown-safe) =====
if "_stm_results" in st.session_state:
    results = st.session_state["_stm_results"]

    ok = results["overall_OK"]
    tag = "\u2705 DESIGN OK" if ok else "\u274c DESIGN FAILS"
    msg = ("{} - Strut DCR={:.2f}, Bearing DCR={:.2f}, "
           "Column DCR={:.2f}").format(
        tag, results["strut_DCR"],
        results["bearing_DCR"], results["column_DCR"])
    (st.success if ok else st.error)(msg)
    if results["has_uplift"]:
        st.warning("\u26a0\ufe0f Uplift detected (P_min = {:.1f} kN). "
                   "Provide tension piles or anchorage.".format(
                       results["P_min_kN"]))
    if not results.get("reaction_equilibrium_OK", True):
        st.error(
            "Pile reaction equilibrium cannot satisfy the applied moments. "
            "Residuals: Mux={:.1f} kN·m, Muy={:.1f} kN·m.".format(
                results.get("reaction_equilibrium_residual_Mux_kNm", 0.0),
                results.get("reaction_equilibrium_residual_Muy_kNm", 0.0)))
    for _warning in results.get("reaction_warnings", []):
        st.warning(_warning)
    if results.get("capacity_model_note"):
        st.info(results["capacity_model_note"])
    if (results.get("x_bar_size") and
            (results.get("x_bar_size") != x_bar or
             results.get("y_bar_size") != y_bar)):
        st.warning(
            "Bottom bar size changed after the last calculation. "
            "Click Calculate STM again to refresh As demand with the selected fy.")
    _calc_col = results.get("column_position", (0.0, 0.0))
    if (abs(_calc_col[0] - col_size["x"]) > 1e-6 or
            abs(_calc_col[1] - col_size["y"]) > 1e-6):
        st.warning(
            "Column position changed after the last calculation. "
            "Click Calculate STM again to refresh reactions, struts, and ties.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pu (column)",
              "{:.0f} kN".format(results["Pu_kN"]))
    m2.metric("W_cap (self-wt)",
              "{:.0f} kN".format(results["W_cap_kN"]),
              help="Lx × Ly × h × 24 kN/m³")
    m3.metric("Pu_total",
              "{:.0f} kN".format(results["Pu_total_kN"]),
              help="Pu + W_cap — used for pile reaction calculation")
    m4.metric("P_max (pile)",
              "{:.0f} kN".format(results["P_max_kN"]))
    col_x_res, col_y_res = results.get("column_position", (0.0, 0.0))
    st.caption("Column/load point = ({:.0f}, {:.0f}) mm".format(
        col_x_res, col_y_res))
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Tie X max",
              "{:.0f} kN".format(results["F_tie_x_max_kN"]))
    m6.metric("Tie Y max",
              "{:.0f} kN".format(results["F_tie_y_max_kN"]))
    m7.metric("d_eff",
              "{:.0f} mm".format(results["d_effective_mm"]))
    m8.metric("Min strut angle",
              "{:.1f}°".format(results["min_strut_angle_deg"]),
              help="ACI requires ≥ 25°")

    x_chk = check_rebar(x_bar, int(x_n),
                        results["As_x_required_mm2"],
                        fy_mpa=results.get("fy_x_design_mpa", fy),
                        force_req_kN=results.get("F_tie_x_design_kN"))
    y_chk = check_rebar(y_bar, int(y_n),
                        results["As_y_required_mm2"],
                        fy_mpa=results.get("fy_y_design_mpa", fy),
                        force_req_kN=results.get("F_tie_y_design_kN"))

    # Auto-optimize
    opt_x, opts_x = optimize_rebar(
        results["As_x_required_mm2"], cap_lx,
        force_req_kN=results.get("F_tie_x_design_kN"))
    opt_y, opts_y = optimize_rebar(
        results["As_y_required_mm2"], cap_ly,
        force_req_kN=results.get("F_tie_y_design_kN"))

    # Anchorage check
    # use D/4 (inner face of CCT node) not D/2
    avail_str_x = min(e_left, e_right) + _gov_max/4.0 - cover
    avail_hook_x = avail_str_x - cover
    avail_str_y = min(e_top, e_bot) + _gov_max/4.0 - cover
    avail_hook_y = avail_str_y - cover
    anch_x = check_anchorage(x_bar, fc, results.get("fy_x_design_mpa", fy),
                             avail_str_x, avail_hook_x)
    anch_y = check_anchorage(y_bar, fc, results.get("fy_y_design_mpa", fy),
                             avail_str_y, avail_hook_y)

    # Top-face reinforcement — always recomputed fresh (dropdown-safe)
    top_rebar = compute_top_reinforcement(
        lx_mm=cap_lx, ly_mm=cap_ly,
        h_cap_mm=h_cap, fy_mpa=fy, fc_mpa=fc,
        cover_mm=cover,
        top_bar_size=st.session_state.get("top_bar_size", "DB20"))

    t1, t2, t6, t3, t4, t7, t5 = st.tabs([
        "📊 Plan", "📈 Elevation", "🎲 3D View",
        "🔩 Reinforcement", "⚓ Anchorage",
        "🪟 Top Rebar", "📋 Detail"])

    with t1:
        st.plotly_chart(
            plot_plan_view(coords, D, cap_lx, cap_ly,
                           col_size, results,
                           cap_cx, cap_cy, cap_polygon),
            use_container_width=True)
        st.markdown("**Pile Reactions** (rigid-cap formula)")
        st.code("P_i = Pu_total/n + Mux,c*y'_i / sum(y'_j^2) + Muy,c*x'_i / sum(x'_j^2)")
        rdf = pd.DataFrame([{
            "Pile": "P{}".format(i+1),
            "X (mm)": "{:.0f}".format(c[0]),
            "Y (mm)": "{:.0f}".format(c[1]),
            "x' (mm)": "{:.0f}".format(
                results.get("reaction_coords", [(0, 0)]*len(coords))[i][0]),
            "y' (mm)": "{:.0f}".format(
                results.get("reaction_coords", [(0, 0)]*len(coords))[i][1]),
            "P_i (kN)": "{:.1f}".format(P),
        } for i, (c, P) in enumerate(
            zip(coords, results["pile_loads_kN"]))])
        st.dataframe(rdf, use_container_width=True, hide_index=True)

    with t2:
        st.plotly_chart(
            plot_elevation(coords, h_cap, D, col_size, results),
            use_container_width=True)
    
    with t6:
        st.plotly_chart(
            plot_3d_view(coords, D, cap_lx, cap_ly,
                         cap_cx, cap_cy, col_size, h_cap,
                         cap_polygon, results),
            use_container_width=True)
        st.caption(
            "🖱️ **Drag** to rotate | **Scroll** to zoom | "
            "**Shift+drag** to pan | **Double-click** to reset view")
        st.markdown(
            "**Color legend (Struts):** "
            "🟢 DCR < 60% | 🟠 60–85% | 🔴 > 85%  &nbsp;&nbsp; "
            "**Ties** shown as dotted green lines.")
    
    with t3:
        st.markdown("### Required Reinforcement")
        if results.get("is_3pile_resultant"):
            tie_x_display = tie_y_display = results["F_tie_res_kN"]
            note = " (Resultant)"
        else:
            tie_x_display = results["F_tie_x_max_kN"]
            tie_y_display = results["F_tie_y_max_kN"]
            note = ""
        req_df = pd.DataFrame([
            {"Direction": "X"+note,
             "Tie (kN)":
                 "{:.1f}".format(tie_x_display),
             "As req (mm²)":
                 "{:.0f}".format(results["As_x_required_mm2"]),
             "fy used (MPa)":
                 "{:.0f}".format(results.get("fy_x_design_mpa", fy)),
             "Selected": "{}-{}".format(int(x_n), x_bar),
             "As prov (mm²)":
                 "{:.0f}".format(x_chk["As_provided"]),
             "Ratio": "{:.2f}".format(x_chk["ratio"]),
             "Status": "✅ OK" if x_chk["ok"] else "❌ FAIL"},
            {"Direction": "Y"+note,
             "Tie (kN)":
                 "{:.1f}".format(tie_y_display),
             "As req (mm²)":
                 "{:.0f}".format(results["As_y_required_mm2"]),
             "fy used (MPa)":
                 "{:.0f}".format(results.get("fy_y_design_mpa", fy)),
             "Selected": "{}-{}".format(int(y_n), y_bar),
             "As prov (mm²)":
                 "{:.0f}".format(y_chk["As_provided"]),
             "Ratio": "{:.2f}".format(y_chk["ratio"]),
             "Status": "✅ OK" if y_chk["ok"] else "❌ FAIL"},
        ])
        st.dataframe(req_df, use_container_width=True,
                     hide_index=True)
        if results.get("is_3pile_resultant"):
            st.info("ฐาน 3 เข็ม: แรงออกแบบใช้ F_res = √(Ftx²+Fty²) = {:.1f} kN; As แต่ละทิศคำนวณด้วย fy ของเหล็กที่เลือกในทิศนั้น".format(results["F_tie_res_kN"]))

        st.markdown("### 🤖 Auto-Optimized Rebar (Min Weight)")
        col_o1, col_o2, col_o3 = st.columns([2, 2, 1])
        col_o1.success(
            "**X-dir optimal:** {}-{} | "
            "As={:.0f} mm² | Wt={:.2f} kg".format(
                opt_x["n_bars"], opt_x["bar_size"],
                opt_x["As_provided"], opt_x["weight_kg"]))
        col_o2.success(
            "**Y-dir optimal:** {}-{} | "
            "As={:.0f} mm² | Wt={:.2f} kg".format(
                opt_y["n_bars"], opt_y["bar_size"],
                opt_y["As_provided"], opt_y["weight_kg"]))
        if col_o3.button("Back To Rebar Selection", use_container_width=True):
            st.session_state.x_bar = opt_x["bar_size"]
            st.session_state.x_n = int(opt_x["n_bars"])
            st.session_state.y_bar = opt_y["bar_size"]
            st.session_state.y_n = int(opt_y["n_bars"])
            st.rerun()

        with st.expander("All optimization candidates"):
            cox, coy = st.columns(2)
            cox.markdown("**X-direction**")
            cox.dataframe(pd.DataFrame([{
                "Bar": o["bar_size"], "n": o["n_bars"],
                "As (mm²)": "{:.0f}".format(o["As_provided"]),
                "Wt (kg)": "{:.2f}".format(o["weight_kg"]),
                "OK": "✅" if o["ok"] else "❌",
            } for o in opts_x]), hide_index=True,
                use_container_width=True)
            coy.markdown("**Y-direction**")
            coy.dataframe(pd.DataFrame([{
                "Bar": o["bar_size"], "n": o["n_bars"],
                "As (mm²)": "{:.0f}".format(o["As_provided"]),
                "Wt (kg)": "{:.2f}".format(o["weight_kg"]),
                "OK": "✅" if o["ok"] else "❌",
            } for o in opts_y]), hide_index=True,
                use_container_width=True)

        st.markdown("### Reinforcement Layout (Plan)")
        st.plotly_chart(
            plot_rebar_layout(coords, D, cap_lx, cap_ly,
                cap_cx, cap_cy, col_size, cap_polygon, results,
                x_bar, int(x_n), y_bar, int(y_n), x_chk, y_chk),
            use_container_width=True)

    with t4:
        st.markdown("### Anchorage / Development Length")
        st.markdown(
            "Per **ACI 318-19 §23.8.3** tie reinforcement must "
            "develop fy at the point where the centroid of the tie "
            "crosses the extended nodal zone (CCT node above pile).")
        st.code(
            "ld  ≈ (fy·ψs / 1.1·λ·√f'c · (cb+Ktr)/db) · db   "
            "(ACI 25.4.2.3)\n"
            "ldh ≈ (fy / 23·λ·√f'c) · db^1.5                "
            "(ACI 25.4.3.1)")

        anch_df = pd.DataFrame([
            {"Direction": "X", "Bar": anch_x["bar_size"],
             "ld req (mm)":
                 "{:.0f}".format(anch_x["ld_required_mm"]),
             "ldh req (mm)":
                 "{:.0f}".format(anch_x["ldh_required_mm"]),
             "Avail. straight":
                 "{:.0f}".format(anch_x["available_straight_mm"]),
             "Avail. hook":
                 "{:.0f}".format(anch_x["available_hook_mm"]),
             "Recommended": anch_x["recommended"],
             "Status": "✅" if anch_x["ok"] else "❌"},
            {"Direction": "Y", "Bar": anch_y["bar_size"],
             "ld req (mm)":
                 "{:.0f}".format(anch_y["ld_required_mm"]),
             "ldh req (mm)":
                 "{:.0f}".format(anch_y["ldh_required_mm"]),
             "Avail. straight":
                 "{:.0f}".format(anch_y["available_straight_mm"]),
             "Avail. hook":
                 "{:.0f}".format(anch_y["available_hook_mm"]),
             "Recommended": anch_y["recommended"],
             "Status": "✅" if anch_y["ok"] else "❌"},
        ])
        st.dataframe(anch_df, use_container_width=True,
                     hide_index=True)

        if not (anch_x["ok"] and anch_y["ok"]):
            st.warning(
                "⚠️ Anchorage insufficient. Consider: "
                "(a) larger cap dimensions, "
                "(b) using 90°/180° standard hooks, "
                "(c) headed bars (ACI 25.4.4), "
                "or (d) smaller bar diameter.")

        with st.expander("Assumptions used"):
            st.markdown(
                "- λ = 1.0 (normal-weight concrete)\n"
                "- ψt=1.0 (bottom bars), ψe=1.0 (uncoated), "
                "ψg=1.0 (Gr 420), ψr=ψo=ψc=1.0\n"
                "- (cb+Ktr)/db = 1.5 (conservative typical value)\n"
                "- Available straight = min edge dist + D/4 − cover  # PATCHED: inner face of CCT node\n"
                "- Available hook = available straight − cover")

    with t7:
        st.markdown("## 🪟 Top-Face Minimum Reinforcement")
        st.markdown(
            "เหล็กผิวบนของ pile cap ไม่ได้รับแรงดึงจาก STM โดยตรง "
            "แต่ ACI 318-19 กำหนดเหล็กขั้นต่ำ **3 เกณฑ์ + 1 spacing check** "
            "โดย fy ที่ใช้คำนวณขึ้นอยู่กับ **ขนาดเหล็กที่เลือก** ตามเงื่อนไขจริง")

        # ── Bar selector ─────────────────────────────────────
        st.markdown("### เลือกขนาดเหล็กผิวบน")
        _bar_options = list(REBAR_DB.keys())  # DB12…DB32
        _cur_bar = st.session_state.get("top_bar_size", "DB20")
        _sel_col, _info_col = st.columns([2, 3])
        with _sel_col:
            _chosen_bar = st.selectbox(
                "Top bar size",
                options=_bar_options,
                index=_bar_options.index(_cur_bar),
                key="top_bar_size",
                help="เหล็ก ≤ DB28 → fy = 390 MPa | DB32 → fy = 490 MPa")
        with _info_col:
            _fy_chosen = REBAR_FY[_chosen_bar]
            _fy_capped = min(_fy_chosen, FY_CAP_MPA)
            if _fy_chosen > 420:
                st.warning(
                    "**{} : fy = {:.0f} MPa > 420 MPa**  \n"
                    "ACI §24.4.3.2 → ρ_ts ลดลง  \n"
                    "ACI §20.2.2.4 → cap ที่ {:.0f} MPa  \n"
                    "ACI §24.3.2   → spacing limit เพิ่มเติม".format(
                        _chosen_bar, _fy_chosen, FY_CAP_MPA))
            else:
                st.info(
                    "**{} : fy = {:.0f} MPa ≤ 420 MPa**  \n"
                    "ρ_ts = 0.0018  |  ไม่มี spacing penalty".format(
                        _chosen_bar, _fy_chosen))

        # ── Recompute with selected bar ───────────────────────
        tr = compute_top_reinforcement(
            lx_mm=cap_lx, ly_mm=cap_ly,
            h_cap_mm=h_cap, fy_mpa=fy, fc_mpa=fc,
            cover_mm=cover, top_bar_size=_chosen_bar)

        # ── Code Reference Expander ──────────────────────────
        with st.expander("📖 Code Basis (ACI 318-19) — คลิกเพื่อดูรายละเอียด"):
            st.markdown("""
**Check A — Temperature & Shrinkage  §24.4.3.2 Table 24.4.3.2**
```
ρ_ts = 0.0018              fy_d ≤ 420 MPa
ρ_ts = 0.0018×420/fy_d    fy_d > 420 MPa  (min 0.0014)
As_req = ρ_ts × b × h_cap
```
**Check B — Min Flexural Reinforcement  §9.6.1.2 (ref. §13.3.3.1)**
```
ρ_flex = max(0.25√f'c / fy_d,  1.4 / fy_d)
As_req = ρ_flex × b × d_top  ;  d_top = h_cap − cover − db/2
```
**Check C — Crack-Control for STM  §23.5.1**
```
ρ_face ≥ 0.003 per direction per face  (conservative per CRSI)
As_req = 0.003 × b × h_cap
```
**Check D — Spacing Limits**
```
§24.4.3.3 : s ≤ min(3h, 450 mm)
§24.3.2   : s ≤ min(380×(280/fs), 300×(280/fs))  where fs = (2/3)fy_d
    (only becomes active when fy_d > 420 MPa)
§20.2.2.4 : fy_d used in design capped at 550 MPa
```
            """)

        # ── Numeric Results ──────────────────────────────────
        st.markdown("### ผลการคำนวณ  (fy_d = {:.0f} MPa — {})".format(
            tr["fy_design_mpa"], tr["fy_note"]))

        res_df = pd.DataFrame([
            {"Check": "A: T&S §24.4.3.2",
             "ρ used": "{:.4f}".format(tr["rho_ts"]),
             "As_X req (mm²)": "{:.0f}".format(tr["As_ts_x_mm2"]),
             "As_Y req (mm²)": "{:.0f}".format(tr["As_ts_y_mm2"])},
            {"Check": "B: Min-Flex §9.6.1.2",
             "ρ used": "{:.4f}".format(tr["rho_flex"]),
             "As_X req (mm²)": "{:.0f}".format(tr["As_flex_x_mm2"]),
             "As_Y req (mm²)": "{:.0f}".format(tr["As_flex_y_mm2"])},
            {"Check": "C: Crack-ctrl §23.5.1",
             "ρ used": "{:.4f}".format(tr["rho_cc"]),
             "As_X req (mm²)": "{:.0f}".format(tr["As_cc_x_mm2"]),
             "As_Y req (mm²)": "{:.0f}".format(tr["As_cc_y_mm2"])},
        ])
        st.dataframe(res_df, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        c1.success(
            "**X-dir  As_top = {:.0f} mm²**  \n"
            "Governs: {}".format(
                tr["As_top_x_mm2"], tr["governs_x"]))
        c2.success(
            "**Y-dir  As_top = {:.0f} mm²**  \n"
            "Governs: {}".format(
                tr["As_top_y_mm2"], tr["governs_y"]))

        # ── Spacing Check ────────────────────────────────────
        st.markdown("### ตรวจสอบระยะห่างสูงสุด")
        _s_ts   = tr["s_ts_max_mm"]
        _s_cr   = tr["s_crack_mm"]
        _s_gov  = tr["s_max_top_mm"]
        _fs     = tr["fs_service_mpa"]
        spac_df = pd.DataFrame([
            {"เกณฑ์": "§24.4.3.3  min(3h, 450)",
             "s_max (mm)": "{:.0f}".format(_s_ts),
             "Active": "✅ เสมอ"},
            {"เกณฑ์": "§24.3.2  crack-width  (fs={:.0f} MPa)".format(_fs),
             "s_max (mm)": "{:.0f}".format(_s_cr),
             "Active": "⚠️ fy > 420" if tr["fy_design_mpa"] > 420
                       else "— (fy ≤ 420)"},
        ])
        st.dataframe(spac_df, use_container_width=True, hide_index=True)
        if tr["fy_design_mpa"] > 420:
            st.warning(
                "**s_max governing = {:.0f} mm** "
                "(§24.3.2 controls เนื่องจาก fy = {:.0f} MPa)".format(
                    _s_gov, tr["fy_design_mpa"]))
        else:
            st.info(
                "**s_max governing = {:.0f} mm** "
                "(§24.4.3.3 controls)".format(_s_gov))

        # ── Bar Suggestions ──────────────────────────────────
        st.markdown("### แนะนำขนาดเหล็กผิวบน  (Bar = {})".format(
            _chosen_bar))
        _top_bars = ("DB12", "DB16", "DB20", "DB25", "DB28", "DB32")
        _top_sx = suggest_rebar(tr["As_top_x_mm2"],
                                preferred=_top_bars)
        _top_sy = suggest_rebar(tr["As_top_y_mm2"],
                                preferred=_top_bars)

        def _spac_check(n, width, s_max):
            """Estimate actual spacing and flag if over limit."""
            if n <= 1:
                return "—"
            s_act = (width - 2*cover) / (n - 1)
            ok = s_act <= s_max
            return "{:.0f} mm {}".format(s_act, "✅" if ok else "❌ > {:.0f}".format(s_max))

        sug_df = pd.DataFrame([
            {"ทิศทาง": "X", "ขนาด": sz,
             "fy (MPa)": "{:.0f}".format(REBAR_FY.get(sz, fy)),
             "จำนวน (เส้น)": n,
             "As prov (mm²)": "{:.0f}".format(a),
             "As req (mm²)": "{:.0f}".format(tr["As_top_x_mm2"]),
             "Ratio": "{:.2f}".format(
                 a / tr["As_top_x_mm2"] if tr["As_top_x_mm2"] else 0),
             "Spacing (est.)": _spac_check(n, cap_ly, _s_gov),
             "Status": "✅" if a >= tr["As_top_x_mm2"] else "❌"}
            for sz, n, a in _top_sx
        ] + [
            {"ทิศทาง": "Y", "ขนาด": sz,
             "fy (MPa)": "{:.0f}".format(REBAR_FY.get(sz, fy)),
             "จำนวน (เส้น)": n,
             "As prov (mm²)": "{:.0f}".format(a),
             "As req (mm²)": "{:.0f}".format(tr["As_top_y_mm2"]),
             "Ratio": "{:.2f}".format(
                 a / tr["As_top_y_mm2"] if tr["As_top_y_mm2"] else 0),
             "Spacing (est.)": _spac_check(n, cap_lx, _s_gov),
             "Status": "✅" if a >= tr["As_top_y_mm2"] else "❌"}
            for sz, n, a in _top_sy
        ])
        st.dataframe(sug_df, use_container_width=True,
                     hide_index=True)

        # ── Plan View Diagram ────────────────────────────────
        st.markdown("### แผนผังเหล็กผิวบน (Plan View)")
        st.plotly_chart(
            plot_top_rebar_layout(
                coords, D, cap_lx, cap_ly,
                cap_cx, cap_cy, col_size, cap_polygon,
                tr, cover_mm=cover),
            use_container_width=True)

        # ── Placement Guide ──────────────────────────────────
        st.markdown("### ตำแหน่งและรูปแบบการวาง")
        st.markdown("""
| ตำแหน่ง | รายละเอียด | อ้างอิง ACI |
|---|---|---|
| **ผิวบน แนว X** | วางแนวนอน กระจายตลอดความกว้าง ly | §24.4.3.2, §23.5.1 |
| **ผิวบน แนว Y** | วางแนวขวาง กระจายตลอดความกว้าง lx | §24.4.3.2, §23.5.1 |
| **ระยะ cover ผิวบน** | ≥ 50 mm (exposed) ตามสภาพแวดล้อม | §20.6.1.3 |
| **ระยะห่างเหล็ก** | ≤ s_max governing (ดูตาราง spacing ด้านบน) | §24.4.3.3, §24.3.2 |
| **ต่อทับ** | ≥ 1.3 × ld (Class B splice) | §25.5.2 |
| **fy ใช้ออกแบบ** | ≤DB28 → 390 MPa, DB32 → 490 MPa, cap 550 MPa | §20.2.2.4 |
""")
        st.info(
            "💡 **หมายเหตุ:** กรณีเลือก DB32 (fy=490 MPa) "
            "ระยะห่างเหล็กถูกจำกัดเพิ่มเติมโดย §24.3.2 "
            "ซึ่งอาจทำให้ต้องเพิ่มจำนวนเหล็กแม้ว่า As จะเพียงพอแล้ว")

    with t5:
        st.markdown("### Strut Forces")
        rows = []
        for i, s in enumerate(results["struts"]):
            rows.append({
                "Strut": "S{}".format(i+1),
                "X (mm)": round(s["coord"][0],1), "Y (mm)": round(s["coord"][1],1),
                "dx_col (mm)": round(s.get("dx_from_col", s["coord"][0]), 1),
                "dy_col (mm)": round(s.get("dy_from_col", s["coord"][1]), 1),
                "P_i (kN)": round(s["P_i_kN"], 1),
                "L (mm)": round(s["L_strut"], 0),
                "θ (°)": round(s["theta_deg"], 1),
                "F_strut (kN)": round(s["F_strut_kN"], 1),
            })
        st.dataframe(pd.DataFrame(rows),
                     use_container_width=True, hide_index=True)

        st.markdown("### Tie Design Forces (for reinforcement)")
        tie_rows = [
            {"Direction": "X",
             "Tie force (kN)": "{:.1f}".format(results["F_tie_x_max_kN"]),
             "Formula": "Σ Pi·|dx_col|/d (controlling side)"},
            {"Direction": "Y",
             "Tie force (kN)": "{:.1f}".format(results["F_tie_y_max_kN"]),
             "Formula": "Σ Pi·|dy_col|/d (controlling side)"},
        ]
        if results.get("is_3pile_resultant"):
            tie_rows.append({
                "Direction": "Resultant (3-pile)",
                "Tie force (kN)": "{:.1f}".format(results["F_tie_res_kN"]),
                "Formula": "√(Ftx²+Fty²) — used for As_x = As_y"
            })
        tie_df = pd.DataFrame(tie_rows)
        st.dataframe(tie_df, use_container_width=True, hide_index=True)
        if results.get("is_3pile_resultant"):
            st.info("ฐาน 3 เข็ม: ใช้แรงลัพธ์ F_res เพื่อลดผลของการหมุนพิกัด แล้วคำนวณ As แยกตาม fy ของเหล็กแต่ละทิศ")
        st.caption("หมายเหตุ: ตาราง Strut แสดงแรงอัดในแต่ละ strut เท่านั้น ส่วนแรงดึงที่ใช้ออกแบบเหล็กคือค่า Tie ด้านบน")

        st.markdown("### Capacity Checks")
        _bn = results.get("bn_pile", 0.60)
        _node_lbl = "CTT βn={:.2f}".format(_bn) if results["n_piles"] >= 4 else "CCT βn={:.2f}".format(_bn)
        ck = pd.DataFrame([
            {"Check": "Strut compression",
             "Capacity (kN)":
                 "{:.0f}".format(results["phi_Fns_kN"]),
             "Demand (kN)":
                 "{:.0f}".format(results["F_strut_max_kN"]),
             "DCR": "{:.2f}".format(results["strut_DCR"]),
             "Status": "✅" if results["strut_DCR"] <= 1
                       else "❌"},
            {"Check": "Pile bearing ({})".format(_node_lbl),
             "Capacity (kN)":
                 "{:.0f}".format(results["phi_Pn_bearing_kN"]),
             "Demand (kN)":
                 "{:.0f}".format(results["P_max_kN"]),
             "DCR": "{:.2f}".format(results["bearing_DCR"]),
             "Status": "✅" if results["bearing_DCR"] <= 1
                       else "❌"},
            {"Check": "Column bearing (CCC)",
             "Capacity (kN)":
                 "{:.0f}".format(results["phi_Pn_column_kN"]),
             "Demand (kN)":
                 "{:.0f}".format(results["Pu_kN"]),
             "DCR": "{:.2f}".format(results["column_DCR"]),
             "Status": "✅" if results["column_DCR"] <= 1
                       else "❌"},
            {"Check": "Strut angle ≥25° ({:.1f}°)".format(
                results["min_strut_angle_deg"]),
             "Capacity (kN)": "-", "Demand (kN)": "-", "DCR": "-",
             "Status": "✅" if results["angle_OK"] else "❌"},
        ])
        extra_checks = [
            {"Check": "Uplift / tension pile",
             "Capacity (kN)": "-", "Demand (kN)": "{:.0f}".format(results["P_min_kN"]),
             "DCR": "-", "Status": "✅" if not results["has_uplift"] else "❌"},
            {"Check": "Reaction equilibrium",
             "Capacity (kN)": "-", "Demand (kN)": "-", "DCR": "-",
             "Status": "✅" if results.get("reaction_equilibrium_OK", True) else "❌"},
        ]
        ck = pd.concat([ck, pd.DataFrame(extra_checks)], ignore_index=True)
        st.dataframe(ck, use_container_width=True, hide_index=True)

    # Export Report
    st.divider()
    st.subheader("📄 Export Report")
    inputs_dict = {
        "fc": fc, "fy": fy, "cover": cover,
        "Pu": Pu, "Mux": Mux, "Muy": Muy,
        "W_cap_kN": results["W_cap_kN"],
        "W_cap_nom_kN": _cap_area_m2(cap_polygon, cap_lx, cap_ly) * (h_cap/1000.0) * 24.0,
        "wcap_uls_factor": st.session_state.wcap_uls_factor,
        "Pu_total_kN": results["Pu_total_kN"],
        "D": D, "h_cap": h_cap, "col_size": col_size,
        "coords": coords,
        "cap_lx": cap_lx, "cap_ly": cap_ly,
        "cap_cx": cap_cx, "cap_cy": cap_cy,
        "cap_polygon": cap_polygon,
        "shape_label": shape_label,
    }
    try:
        docx_buf = generate_report(
            inputs_dict, results, x_chk, y_chk, pairs,
            anch_x=anch_x, anch_y=anch_y,
            opt_x=opt_x, opt_y=opt_y,
            top_rebar=top_rebar)
        st.download_button(
            "⬇️ Download Word Report (.docx)",
            data=docx_buf,
            file_name="pile_cap_design_report.docx",
            mime=("application/vnd.openxmlformats-officedocument."
                  "wordprocessingml.document"),
            use_container_width=True, type="secondary")
    except Exception as exc:
        st.error("Report generation failed: {}".format(exc))
else:
    st.info("Set inputs in sidebar and click **Calculate STM**. "
            "Layout preview & pile reactions update live.")
