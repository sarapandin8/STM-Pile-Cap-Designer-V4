import plotly.graph_objects as go

PILE = "#5B8DEF"; COL = "#FF8A65"
COL_PLAN_FILL = "rgba(255,138,101,0.16)"
COL_LINE = "#D84315"
COL_TEXT = "#BF360C"
STRUT = "rgba(231,76,60,0.75)"; TIE = "rgba(46,204,113,0.9)"
CAP_FILL = "rgba(189,195,199,0.25)"; CAP_BORDER = "#34495E"
REBAR_X = "#E91E63"; REBAR_Y = "#3F51B5"
TOP_X   = "#FF8F00"   # amber — top face X bars
TOP_Y   = "#00897B"   # teal  — top face Y bars

def _normalize_col(c):                            
    """Accept dict or scalar; return (section, bx, by, diam)."""
    if isinstance(c, dict):
        return (c.get("section", "Square"),
                c.get("bx", 500.0), c.get("by", 500.0),
                c.get("diam", 500.0))
    return ("Square", float(c), float(c), float(c))


def _col_pos(c):
    if isinstance(c, dict):
        return float(c.get("x", 0.0)), float(c.get("y", 0.0))
    return 0.0, 0.0

def _normalize_pile(p):
    """Accept dict or scalar; return (section, bx, by, diam)."""
    if isinstance(p, dict):
        return (p.get("section", "Circular"),
                p.get("bx", 600.0), p.get("by", 600.0),
                p.get("diam", 600.0))
    return ("Circular", float(p), float(p), float(p))

def _circle_shape(cx, cy, r, fill, line):
    return {
        "type": "circle", "xref": "x", "yref": "y",
        "x0": cx-r, "y0": cy-r, "x1": cx+r, "y1": cy+r,
        "fillcolor": fill, "line": {"color": line, "width": 1.5},
        "layer": "above",
    }


def _add_cap(fig, lx, ly, cx, cy, polygon=None):
    if polygon:
        xs = [v[0] for v in polygon] + [polygon[0][0]]
        ys = [v[1] for v in polygon] + [polygon[0][1]]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself",
            fillcolor=CAP_FILL,
            line={"color": CAP_BORDER, "width": 2},
            hoverinfo="skip", showlegend=False))
    else:
        fig.add_shape(type="rect",
            x0=cx-lx/2, y0=cy-ly/2, x1=cx+lx/2, y1=cy+ly/2,
            fillcolor=CAP_FILL,
            line={"color": CAP_BORDER, "width": 2},
            layer="below")


def plot_layout_preview(coords, D, lx, ly, cx=0.0, cy=0.0,
                        col_size=400, shape="Square",
                        cap_polygon=None, edge_info=None,
                        pile_loads=None):
    fig = go.Figure()
    _add_cap(fig, lx, ly, cx, cy, cap_polygon)

    sec_c, cbx, cby, cdm = _normalize_col(col_size)
    col_x, col_y = _col_pos(col_size)
    if sec_c == "Circular":
        fig.add_shape(type="circle",
            x0=col_x-cdm/2, y0=col_y-cdm/2,
            x1=col_x+cdm/2, y1=col_y+cdm/2,
            fillcolor=COL_PLAN_FILL, line={"color": COL_LINE, "width": 2},
            layer="above")
    else:
        fig.add_shape(type="rect",
            x0=col_x-cbx/2, y0=col_y-cby/2,
            x1=col_x+cbx/2, y1=col_y+cby/2,
            fillcolor=COL_PLAN_FILL, line={"color": COL_LINE, "width": 2},
            layer="above")
        
    fig.add_annotation(x=col_x, y=col_y, text="<b>COL</b>", showarrow=False,
                       font={"color": COL_TEXT, "size": 11})

    sec_p, pbx, pby, pdm = _normalize_pile(D)
    for i, (x, y) in enumerate(coords, 1):
        if sec_p == "Circular":
            fig.add_shape(_circle_shape(x, y, pdm/2.0, PILE, "#1F4E89"))
        elif sec_p == "Square":
            fig.add_shape(type="rect",
                x0=x-pbx/2, y0=y-pbx/2, x1=x+pbx/2, y1=y+pbx/2,
                fillcolor=PILE, line={"color": "#1F4E89", "width": 1.5},
                layer="above")
        else:
            fig.add_shape(type="rect",
                x0=x-pbx/2, y0=y-pby/2, x1=x+pbx/2, y1=y+pby/2,
                fillcolor=PILE, line={"color": "#1F4E89", "width": 1.5},
                layer="above")
        label = "<b>P{}</b>".format(i)
        if pile_loads is not None and i-1 < len(pile_loads):
            label += "<br>{:.0f}kN".format(pile_loads[i-1])
        fig.add_annotation(x=x, y=y, text=label, showarrow=False,
                           font={"color": "white", "size": 10})

    fig.add_annotation(x=cx, y=cy-ly/2-220,
                       text="<b>Lx = {:.0f} mm</b>".format(lx),
                       showarrow=False,
                       font={"size": 12, "color": CAP_BORDER})
    fig.add_annotation(x=cx-lx/2-220, y=cy,
                       text="<b>Ly = {:.0f} mm</b>".format(ly),
                       showarrow=False, textangle=-90,
                       font={"size": 12, "color": CAP_BORDER})

    if edge_info and not cap_polygon:
        el, er, et, eb = edge_info
        fig.add_annotation(x=cx-lx/2+el/2, y=cy,
                           text="e_L={:.0f}".format(el),
                           showarrow=False,
                           font={"size": 10, "color": "#0277BD"})
        fig.add_annotation(x=cx+lx/2-er/2, y=cy,
                           text="e_R={:.0f}".format(er),
                           showarrow=False,
                           font={"size": 10, "color": "#0277BD"})
        fig.add_annotation(x=cx, y=cy+ly/2-et/2,
                           text="e_T={:.0f}".format(et),
                           showarrow=False,
                           font={"size": 10, "color": "#0277BD"})
        fig.add_annotation(x=cx, y=cy-ly/2+eb/2,
                           text="e_B={:.0f}".format(eb),
                           showarrow=False,
                           font={"size": 10, "color": "#0277BD"})

    x_min_view = min(cx-lx/2, col_x)
    x_max_view = max(cx+lx/2, col_x)
    y_min_view = min(cy-ly/2, col_y)
    y_max_view = max(cy+ly/2, col_y)
    pad = max(lx, ly)*0.15 + 300

    # ── Center axes (crosshair at origin) ──────────────────────
    # ความยาวแกน = ครึ่งหนึ่งของฐานรากแต่ละด้าน พอดีกับขอบ cap
    _offset = max(lx, ly) * 0.10 + 150  # ระยะขยับออกนอก cap
    _ax_half_x = lx / 2 + _offset
    _ax_half_y = ly / 2 + _offset
    _AXIS_COLOR_X = "#E53935"   # red for X
    _AXIS_COLOR_Y = "#1E88E5"   # blue for Y
    # X-axis line
    fig.add_shape(type="line",
        x0=-_ax_half_x, y0=0, x1=_ax_half_x, y1=0,
        line={"color": _AXIS_COLOR_X, "width": 1.5, "dash": "dot"},
        layer="below")
    # Y-axis line
    fig.add_shape(type="line",
        x0=0, y0=-_ax_half_y, x1=0, y1=_ax_half_y,
        line={"color": _AXIS_COLOR_Y, "width": 1.5, "dash": "dot"},
        layer="below")
    # Arrow + label แยกกัน: arrow ไม่มีข้อความ / label วางที่ปลายลูกศรพอดี
    # X arrow
    fig.add_annotation(
        x=_ax_half_x, y=0, xref="x", yref="y",
        ax=-30, ay=0,
        text="", showarrow=True,
        arrowhead=2, arrowsize=1.2, arrowwidth=1.5,
        arrowcolor=_AXIS_COLOR_X)
    # X label ที่ปลายหัวลูกศร
    fig.add_annotation(
        x=_ax_half_x, y=0, xref="x", yref="y",
        text="<b>X</b>", showarrow=False,
        font={"color": _AXIS_COLOR_X, "size": 12},
        xanchor="left", xshift=8)
    # Y arrow
    fig.add_annotation(
        x=0, y=_ax_half_y, xref="x", yref="y",
        ax=0, ay=30,
        text="", showarrow=True,
        arrowhead=2, arrowsize=1.2, arrowwidth=1.5,
        arrowcolor=_AXIS_COLOR_Y)
    # Y label ที่ปลายหัวลูกศร
    fig.add_annotation(
        x=0, y=_ax_half_y, xref="x", yref="y",
        text="<b>Y</b>", showarrow=False,
        font={"color": _AXIS_COLOR_Y, "size": 12},
        yanchor="bottom", yshift=8)
    # Origin dot
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker={"symbol": "circle", "size": 6,
                "color": "#333333", "line": {"width": 1.5, "color": "white"}},
        hoverinfo="text", text=["Origin (0, 0)"],
        showlegend=False))

    fig.update_layout(
        title="Pile Cap Layout - {} ({} piles)".format(shape, len(coords)),
        xaxis={"scaleanchor": "y", "scaleratio": 1, "title": "X (mm)",
               "range": [x_min_view-pad, x_max_view+pad],
               "gridcolor": "#ECEFF1"},
        yaxis={"title": "Y (mm)",
               "range": [y_min_view-pad, y_max_view+pad],
               "gridcolor": "#ECEFF1"},
        plot_bgcolor="white", paper_bgcolor="white",
        height=560, margin={"l": 40, "r": 40, "t": 60, "b": 40},
        showlegend=False)
    return fig 


def plot_plan_view(coords, D, lx, ly, col_size, results,
                   cx=0.0, cy=0.0, cap_polygon=None):
    fig = plot_layout_preview(coords, D, lx, ly, cx, cy, col_size,
                              "Result", cap_polygon,
                              pile_loads=results.get("pile_loads_kN"))
    # Struts (red dashed)
    col_x, col_y = _col_pos(col_size)
    for idx, s in enumerate(results.get("struts", [])):
        x, y = s["coord"]
        fig.add_trace(go.Scatter(
            x=[col_x, x], y=[col_y, y], mode="lines",
            line={"color": STRUT, "width": 3, "dash": "dash"},
            hoverinfo="text",
            text=["F={:.1f}kN θ={:.1f}°".format(
                s["F_strut_kN"], s["theta_deg"])]*2,
            name="Strut",
            showlegend=(idx==0)))
    # Ties (green solid) - same logic as 3D view
    tol = 1.0
    is_triangular = len(coords) == 3
    first_tie = True
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            x1, y1 = coords[i]; x2, y2 = coords[j]
            if is_triangular or abs(x1 - x2) < tol or abs(y1 - y2) < tol:
                fig.add_trace(go.Scatter(
                    x=[x1, x2], y=[y1, y2], mode="lines",
                    line={"color": TIE, "width": 3},
                    hoverinfo="skip",
                    name="Tie",
                    showlegend=first_tie))
                first_tie = False
    fig.update_layout(title="Plan View - Struts (red dashed) & Ties (green solid)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def plot_elevation(coords, h_cap, D, col_size, results):
    fig = go.Figure()
    if not coords:
        return fig
    xs = [c[0] for c in coords]
    sec_p, pbx, pby, pdm = _normalize_pile(D)
    pwid = pdm if sec_p == "Circular" else pbx
    col_x, _col_y = _col_pos(col_size)
    x_min = min(min(xs)-pwid, col_x-pwid)
    x_max = max(max(xs)+pwid, col_x+pwid)
    cap_top = h_cap

    fig.add_shape(type="rect", x0=x_min-200, y0=0,
                  x1=x_max+200, y1=cap_top,
                  fillcolor=CAP_FILL,
                  line={"color": CAP_BORDER, "width": 2},
                  layer="below")
    sec_c, cbx, cby, cdm = _normalize_col(col_size)
    cwid = cdm if sec_c == "Circular" else cbx
    fig.add_shape(type="rect", x0=col_x-cwid/2, y0=cap_top,
                  x1=col_x+cwid/2, y1=cap_top+400,
                  fillcolor=COL,
                  line={"color": "#D84315", "width": 2})

    for x, _ in coords:
        fig.add_shape(type="rect",
                      x0=x-pwid/2, y0=-600, x1=x+pwid/2, y1=0,
                      fillcolor=PILE,
                      line={"color": "#1F4E89", "width": 2})
        fig.add_trace(go.Scatter(
            x=[col_x, x], y=[cap_top, pwid/2], mode="lines",
            line={"color": STRUT, "width": 4},
            hoverinfo="skip", showlegend=False))

    if len(coords) >= 2:
        fig.add_trace(go.Scatter(
            x=[min(xs), max(xs)], y=[pwid/2, pwid/2], mode="lines",
            line={"color": TIE, "width": 5}, hoverinfo="text",
            text=["Tie F={:.1f}kN".format(
                max(results.get("F_tie_x_max_kN", 0),
                    results.get("F_tie_y_max_kN", 0)))]*2,
            showlegend=False))

    fig.update_layout(
        title="Elevation - Struts (red) and Tie (green)",
        xaxis={"title": "X (mm)", "scaleanchor": "y",
               "scaleratio": 1, "gridcolor": "#ECEFF1"},
        yaxis={"title": "Z (mm)", "gridcolor": "#ECEFF1"},
        plot_bgcolor="white", paper_bgcolor="white",
        height=480, margin={"l": 40, "r": 40, "t": 60, "b": 40})
    return fig

def plot_rebar_layout(coords, D, lx, ly, cx, cy, col_size, cap_polygon,
                      results, x_bar, x_n, y_bar, y_n, x_chk, y_chk,
                      cover_mm=75.0):
    fig = plot_layout_preview(coords, D, lx, ly, cx, cy, col_size,
                              "Reinforcement", cap_polygon)
    if not coords:
        return fig
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    sec_p, pbx, pby, pdm = _normalize_pile(D)
    if sec_p == "Circular":
        pwid_x = pwid_y = pdm
    elif sec_p == "Square":
        pwid_x = pwid_y = pbx
    else:
        pwid_x = pbx
        pwid_y = pby
    if cap_polygon:
        poly = list(cap_polygon)
        xs_cap = [p[0] for p in poly]
        ys_cap = [p[1] for p in poly]
        cap_x_min, cap_x_max = min(xs_cap), max(xs_cap)
        cap_y_min, cap_y_max = min(ys_cap), max(ys_cap)
    else:
        poly = [
            (cx - lx/2, cy - ly/2),
            (cx + lx/2, cy - ly/2),
            (cx + lx/2, cy + ly/2),
            (cx - lx/2, cy + ly/2),
        ]
        cap_x_min, cap_x_max = cx - lx/2, cx + lx/2
        cap_y_min, cap_y_max = cy - ly/2, cy + ly/2

    edge_inset = min(max(float(cover_mm), 25.0), 0.45 * min(lx, ly))

    def _linspace(a, b, n):
        if n <= 1 or b <= a:
            return [(a + b) / 2.0]
        return [a + (b - a) * i / (n - 1) for i in range(n)]

    def _horizontal_segment(y):
        hits = []
        for i, (x1, y1) in enumerate(poly):
            x2, y2 = poly[(i + 1) % len(poly)]
            if abs(y2 - y1) < 1e-9:
                continue
            if (y >= min(y1, y2)) and (y < max(y1, y2)):
                t = (y - y1) / (y2 - y1)
                hits.append(x1 + t * (x2 - x1))
        hits.sort()
        if len(hits) >= 2:
            return hits[0] + edge_inset, hits[-1] - edge_inset
        return cap_x_min + edge_inset, cap_x_max - edge_inset

    def _vertical_segment(x):
        hits = []
        for i, (x1, y1) in enumerate(poly):
            x2, y2 = poly[(i + 1) % len(poly)]
            if abs(x2 - x1) < 1e-9:
                continue
            if (x >= min(x1, x2)) and (x < max(x1, x2)):
                t = (x - x1) / (x2 - x1)
                hits.append(y1 + t * (y2 - y1))
        hits.sort()
        if len(hits) >= 2:
            return hits[0] + edge_inset, hits[-1] - edge_inset
        return cap_y_min + edge_inset, cap_y_max - edge_inset

    x_min = cap_x_min + edge_inset
    x_max = cap_x_max - edge_inset
    y_min = cap_y_min + edge_inset
    y_max = cap_y_max - edge_inset

    # X-direction bars: horizontal lines running along X, count = x_n, spaced in Y
    ys_bar = _linspace(y_min, y_max, x_n)
    for yb in ys_bar:
        x0, x1 = _horizontal_segment(yb)
        if x1 <= x0:
            continue
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[yb, yb], mode="lines",
            line={"color": REBAR_X, "width": 2},
            hoverinfo="text",
            text=["{} (X-dir)".format(x_bar)]*2, showlegend=False))

    # Y-direction bars: vertical lines running along Y, count = y_n, spaced in X
    xs_bar = _linspace(x_min, x_max, y_n)
    for xb in xs_bar:
        y0, y1 = _vertical_segment(xb)
        if y1 <= y0:
            continue
        fig.add_trace(go.Scatter(
            x=[xb, xb], y=[y0, y1], mode="lines",
            line={"color": REBAR_Y, "width": 2, "dash": "dot"},
            hoverinfo="text",
            text=["{} (Y-dir)".format(y_bar)]*2, showlegend=False))

    sx = "OK" if x_chk["ok"] else "FAIL"
    sy = "OK" if y_chk["ok"] else "FAIL"
    fig.add_annotation(x=cx, y=cy+ly/2+150,
        text="<b>X-dir: {}-{}</b> As_prov={:.0f} / req={:.0f} mm² ({}) → {}".format(
            x_n, x_bar, x_chk["As_provided"], x_chk["As_required"],
            results.get("As_x_governs", "governing"), sx),
        showarrow=False, font={"color": REBAR_X, "size": 12})
    fig.add_annotation(x=cx, y=cy+ly/2+260,
        text="<b>Y-dir: {}-{}</b> As_prov={:.0f} / req={:.0f} mm² ({}) → {}".format(
            y_n, y_bar, y_chk["As_provided"], y_chk["As_required"],
            results.get("As_y_governs", "governing"), sy),
        showarrow=False, font={"color": REBAR_Y, "size": 12})
    fig.update_layout(title="Reinforcement Layout (Plan)")
    return fig

# ==============================================================
# 3D INTERACTIVE VIEW
# ==============================================================
# แทนที่ฟังก์ชัน _box_mesh
def _box_mesh(x0, x1, y0, y1, z0, z1, color, opacity=0.4, lighting=None):
    """Return Mesh3d trace for an axis-aligned box."""
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [z0, z0, z0, z0, z1, z1, z1, z1]
    
    # ดัชนีการเชื่อมจุดที่แก้ไขแล้ว (จากข้อ 1)
    i = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1]
    j = [1, 2, 5, 6, 1, 3, 3, 7, 3, 7, 2, 6]
    k = [2, 3, 7, 7, 5, 4, 7, 6, 7, 4, 6, 5]
    
    kwargs = {
        "x": x, "y": y, "z": z, "i": i, "j": j, "k": k,
        "color": color, "opacity": opacity,
        "flatshading": True, # ใช้ True เพื่อให้มุมดูคม
        "hoverinfo": "skip", "showlegend": False
    }
    if lighting:
        kwargs["lighting"] = lighting
        
    return go.Mesh3d(**kwargs)

# แทนที่ฟังก์ชัน _polygon_extrude_mesh
def _polygon_extrude_mesh(polygon, z0, z1, color, opacity=0.4, lighting=None):
    """Extrude a 2D polygon between z0..z1 (fan triangulation)."""
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    xs, ys, zs = [], [], []
    for (px, py) in polygon:
        xs.append(px); ys.append(py); zs.append(z0)
    for (px, py) in polygon:
        xs.append(px); ys.append(py); zs.append(z1)
    xs.extend([cx, cx]); ys.extend([cy, cy]); zs.extend([z0, z1])
    bc, tc = 2*n, 2*n+1
    i, j, k = [], [], []
    for a in range(n):
        b = (a + 1) % n
        i += [bc]; j += [b]; k += [a]
        i += [tc]; j += [n + a]; k += [n + b]
        i += [a, a]; j += [b, n + b]; k += [n + b, n + a]
        
    kwargs = {
        "x": xs, "y": ys, "z": zs, "i": i, "j": j, "k": k,
        "color": color, "opacity": opacity,
        "flatshading": True, "hoverinfo": "skip", "showlegend": False
    }
    if lighting:
        kwargs["lighting"] = lighting
    return go.Mesh3d(**kwargs)

# แทนที่ฟังก์ชัน _cylinder_mesh
def _cylinder_mesh(cx, cy, z0, z1, r, color, opacity=0.85, lighting=None, n=24):
    """Vertical cylinder mesh."""
    import math as _m
    xs, ys, zs = [], [], []
    for k_ in range(n):
        a = 2*_m.pi*k_/n
        xs.append(cx + r*_m.cos(a)); ys.append(cy + r*_m.sin(a))
        zs.append(z0)
    for k_ in range(n):
        a = 2*_m.pi*k_/n
        xs.append(cx + r*_m.cos(a)); ys.append(cy + r*_m.sin(a))
        zs.append(z1)
    xs += [cx, cx]; ys += [cy, cy]; zs += [z0, z1]
    bc, tc = 2*n, 2*n+1
    i, j, k = [], [], []
    for a in range(n):
        b = (a+1) % n
        i += [bc]; j += [b]; k += [a]
        i += [tc]; j += [n+a]; k += [n+b]
        i += [a, a]; j += [b, n+b]; k += [n+b, n+a]
        
    kwargs = {
        "x": xs, "y": ys, "z": zs, "i": i, "j": j, "k": k,
        "color": color, "opacity": opacity,
        "flatshading": True, "hoverinfo": "skip", "showlegend": False
    }
    if lighting:
        kwargs["lighting"] = lighting
    return go.Mesh3d(**kwargs)





def plot_3d_view(coords, D, cap_lx, cap_ly, cap_cx, cap_cy,
                 col_size, h_cap, cap_polygon, results,
                 pile_length=1500.0, col_height=600.0,
                 show_force_labels=True):
    """3D interactive view: cap, piles, column, struts, ties."""
    fig = go.Figure()

    # --- การตั้งค่าแสงเงา (Lighting) สำหรับให้ดูสมจริง ---
    # ambient: แสงโดยรอบ, diffuse: แสงกระจาย, roughness: ความหยาบของผิว, specular: แสงสะท้อน
    LIGHTING_CONCRETE = dict(
        ambient=0.4, diffuse=0.8, roughness=0.5, 
        fresnel=0.1, specular=0.1
    )

    # --- 1. Ground Plane (พื้นดิน) ---
    # สร้างผิวดินสีน้ำตาล/ดินโปร่งแสงที่ฐานของเสาเข็ม
    ground_size = max(cap_lx, cap_ly) * 2.0  # ขนาดพื้นดิน 2 เท่าของฐาน
    z_ground = -pile_length
    # ใช้ Mesh3d สร้างระนาบ 2 สามเหลี่ยม
    fig.add_trace(go.Mesh3d(
        x=[-ground_size, ground_size, ground_size, -ground_size],
        y=[-ground_size, -ground_size, ground_size, ground_size],
        z=[z_ground, z_ground, z_ground, z_ground],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color='#5D4037', # สีดิน (Brownish)
        opacity=0.3,      # โปร่งแสงเล็กน้อย
        lighting=LIGHTING_CONCRETE,
        hoverinfo="skip", showlegend=False
    ))

    # --- 2. Cap (ฐานรองรับ) ---
    # ปรับ Opacity = 0.25 เพื่อให้โปร่งแสง และเห็น Strut ภายในได้ชัด
    if cap_polygon:
        fig.add_trace(_polygon_extrude_mesh(
            cap_polygon, 0.0, h_cap, "#bdc3c7", 
            opacity=0.25, lighting=LIGHTING_CONCRETE))
    else:
        fig.add_trace(_box_mesh(
            cap_cx-cap_lx/2, cap_cx+cap_lx/2,
            cap_cy-cap_ly/2, cap_cy+cap_ly/2,
            0.0, h_cap, "#bdc3c7", 
            opacity=0.25, lighting=LIGHTING_CONCRETE))

    # --- 3. Column (เสาคอนกรีต) ---
    sec_c, cbx, cby, cdm = _normalize_col(col_size)
    col_x, col_y = _col_pos(col_size)
    if sec_c == "Circular":
        fig.add_trace(_cylinder_mesh(
            col_x, col_y, h_cap, h_cap+col_height, cdm/2,
            "#FF8A65", opacity=0.9, lighting=LIGHTING_CONCRETE))
    else:
        fig.add_trace(_box_mesh(
            col_x-cbx/2, col_x+cbx/2,
            col_y-cby/2, col_y+cby/2,
            h_cap, h_cap+col_height, "#FF8A65", 
            opacity=0.9, lighting=LIGHTING_CONCRETE))

    # --- 4. Piles (เสาเข็ม) ---
    # ปรับ Opacity = 0.95 เพื่อให้ดูเป็นของแข็งแท้
    sec_p, pbx, pby, pdm = _normalize_pile(D)
    for (px, py) in coords:
        if sec_p == "Circular":
            fig.add_trace(_cylinder_mesh(
                px, py, -pile_length, 0.0, pdm/2,
                "#5B8DEF", opacity=0.95, lighting=LIGHTING_CONCRETE))
        elif sec_p == "Square":
            fig.add_trace(_box_mesh(
                px-pbx/2, px+pbx/2, py-pbx/2, py+pbx/2,
                -pile_length, 0.0, "#5B8DEF", 
                opacity=0.95, lighting=LIGHTING_CONCRETE))
        else:
            fig.add_trace(_box_mesh(
                px-pbx/2, px+pbx/2, py-pby/2, py+pby/2,
                -pile_length, 0.0, "#5B8DEF", 
                opacity=0.95, lighting=LIGHTING_CONCRETE))

    # --- 5. Struts & Ties (ส่วนที่เหลือเหมือนเดิม) ---
    col_top_z = h_cap + col_height/2
    pile_top_z = (pdm if sec_p == "Circular" else pbx) / 2.0
    Fs_max = max((s["F_strut_kN"] for s in results.get("struts", [])), default=1.0)
    struts = results.get("struts", [])
    
    STRUT_LOW = "#2980b9"   # ปรับสีให้เข้มขึ้นเล็กน้อย
    STRUT_MID = "#f39c12"
    STRUT_HIGH = "#c0392b"
    TIE_COLOR = "#27ae60"
    LABEL_FONT = "Arial Black, Arial, sans-serif"
    FORCE_LABEL_COLOR = "#111827"
    TIE_LABEL_COLOR = "#064e3b"

    def _force_text(prefix, value):
        return "<b>{}</b><br><b>{:.0f} kN</b>".format(
            prefix, float(value))

    def _add_force_label(x, y, z, text, color, size=12):
        if not show_force_labels:
            return
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z], mode="markers+text", text=[text],
            textfont=dict(color=color, size=size, family=LABEL_FONT),
            textposition="middle center",
            marker=dict(
                size=max(3, (size - 6) / 2.0),
                color="rgba(255,255,255,0.96)",
                line=dict(color=color, width=2)),
            hoverinfo="skip", showlegend=False))
    
    for idx, s in enumerate(struts, 1):
        x, y = s["coord"]
        dcr_ratio = s["F_strut_kN"] / Fs_max if Fs_max > 0 else 0
        if dcr_ratio > 0.85:
            dcr_color = STRUT_HIGH
        elif dcr_ratio > 0.6:
            dcr_color = STRUT_MID
        else:
            dcr_color = STRUT_LOW
        fig.add_trace(go.Scatter3d(
            x=[col_x, x], y=[col_y, y], z=[col_top_z, pile_top_z],
            mode="lines",
            line=dict(color=dcr_color, width=8),
            hovertext=("Strut: F={:.0f}kN, θ={:.1f}°".format(
                s["F_strut_kN"], s["theta_deg"])),
            hoverinfo="text", showlegend=False, name="Strut"))
        _add_force_label(
            (col_x + x) / 2.0, (col_y + y) / 2.0,
            (col_top_z + pile_top_z) / 2.0,
            _force_text("S{}".format(idx), s["F_strut_kN"]),
            FORCE_LABEL_COLOR, size=14)

    def _tie_force_and_name(i, j, x1, y1, x2, y2):
        if i >= len(struts) or j >= len(struts):
            return 0.0, "Tie"
        sx_i = abs(struts[i].get("F_tie_x_kN", 0.0))
        sx_j = abs(struts[j].get("F_tie_x_kN", 0.0))
        sy_i = abs(struts[i].get("F_tie_y_kN", 0.0))
        sy_j = abs(struts[j].get("F_tie_y_kN", 0.0))
        if abs(y1 - y2) < tol:
            return max(sx_i, sx_j), "Tie X"
        if abs(x1 - x2) < tol:
            return max(sy_i, sy_j), "Tie Y"
        if results.get("is_3pile_resultant"):
            return results.get("F_tie_res_kN", 0.0), "Tie R"
        return max((sx_i**2 + sy_i**2)**0.5,
                   (sx_j**2 + sy_j**2)**0.5), "Tie R"

    tol = 1.0
    is_triangular_base = len(coords) == 3
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            (x1, y1) = coords[i]; (x2, y2) = coords[j]
            if is_triangular_base or abs(x1 - x2) < tol or abs(y1 - y2) < tol:
                tie_force, tie_name = _tie_force_and_name(i, j, x1, y1, x2, y2)
                fig.add_trace(go.Scatter3d(
                    x=[x1, x2], y=[y1, y2],
                    z=[pile_top_z, pile_top_z],
                    mode="lines",
                    line=dict(color=TIE_COLOR, width=6, dash="dot"),
                    hovertext=(
                        "{} (P{}-P{}): F≈{:.0f} kN".format(
                            tie_name, i+1, j+1, tie_force)),
                    hoverinfo="text", showlegend=False))
                _add_force_label(
                    (x1 + x2) / 2.0, (y1 + y2) / 2.0,
                    pile_top_z + max(60.0, 0.04 * h_cap),
                    _force_text("T{}-{}".format(i+1, j+1), tie_force),
                    TIE_LABEL_COLOR, size=12)

    # Pile labels
    for idx, (px, py) in enumerate(coords, 1):
        fig.add_trace(go.Scatter3d(
            x=[px], y=[py], z=[-pile_length/2],
            mode="text", text=["P{}".format(idx)],
            textfont=dict(color="white", size=13, family=LABEL_FONT),
            hoverinfo="skip", showlegend=False))

    fig.update_layout(
        title="3D Interactive View — drag to rotate, scroll to zoom",
        scene=dict(
            xaxis_title="X (mm)", yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
            # ปรับมุมกล้องให้มองเห็นมิติดีขึ้น
            camera=dict(eye=dict(x=1.8, y=-1.8, z=0.8)), 
        ),
        height=650,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(itemsizing="constant"),
    )
    
    # Legend dummy traces
    for nm, clr in [("Strut (low DCR)", "#2980b9"),
                    ("Strut (mid DCR)", "#f39c12"),
                    ("Strut (high DCR)", "#c0392b"),
                    ("Tie", "#27ae60")]:
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None],
            mode="lines", line=dict(color=clr, width=6),
            name=nm, showlegend=True))
    return fig


# ==============================================================
# TOP-FACE REINFORCEMENT PLAN VIEW
# ==============================================================
def plot_top_rebar_layout(coords, D, lx, ly, cx, cy, col_size,
                          cap_polygon, top_rebar, cover_mm=75.0):
    """Plan-view diagram of top-face minimum reinforcement.

    Shows:
    - Cap outline (same as other plan views)
    - Top X-bars  (amber solid lines, horizontal)
    - Top Y-bars  (teal dashed lines, vertical)
    - Governing spacing limit annotation
    - As / fy annotation per direction

    top_rebar dict keys used:
        top_bar_size, fy_design_mpa, db_top_mm,
        As_top_x_mm2, As_top_y_mm2,
        governs_x, governs_y,
        s_max_top_mm, fy_note,
        rebar_db  (optional — passed for area lookup)
    """
    import math as _m

    # ── REBAR_DB inline (avoid circular import from stm_calculations) ──
    _DB = {"DB12": 113.10, "DB16": 201.06, "DB20": 314.16,
           "DB25": 490.87, "DB28": 615.75, "DB32": 804.25}

    bar   = top_rebar.get("top_bar_size", "DB20")
    A_bar = _DB.get(bar, 314.16)
    fy_d  = top_rebar.get("fy_design_mpa", 390.0)
    db_t  = top_rebar.get("db_top_mm", 20.0)
    As_x  = top_rebar.get("As_top_x_mm2", 0.0)
    As_y  = top_rebar.get("As_top_y_mm2", 0.0)
    s_max = top_rebar.get("s_max_top_mm", 450.0)

    # Bar counts include both area demand and maximum spacing demand.
    n_x_area = max(2, int(_m.ceil(As_x / A_bar))) if As_x > 0 else 2
    n_y_area = max(2, int(_m.ceil(As_y / A_bar))) if As_y > 0 else 2
    n_x = int(top_rebar.get("top_x_n_bars", n_x_area))
    n_y = int(top_rebar.get("top_y_n_bars", n_y_area))

    # Base cap outline
    fig = plot_layout_preview(coords, D, lx, ly, cx, cy, col_size,
                              "Top-Face Reinforcement (Plan)", cap_polygon)
    if not coords:
        return fig

    if cap_polygon:
        poly = list(cap_polygon)
        xs_cap = [p[0] for p in poly]
        ys_cap = [p[1] for p in poly]
        cap_x_min, cap_x_max = min(xs_cap), max(xs_cap)
        cap_y_min, cap_y_max = min(ys_cap), max(ys_cap)
    else:
        poly = [
            (cx - lx/2, cy - ly/2),
            (cx + lx/2, cy - ly/2),
            (cx + lx/2, cy + ly/2),
            (cx - lx/2, cy + ly/2),
        ]
        cap_x_min, cap_x_max = cx - lx/2, cx + lx/2
        cap_y_min, cap_y_max = cy - ly/2, cy + ly/2

    edge_inset = min(max(float(cover_mm), db_t), 0.45 * min(lx, ly))

    def _linspace(a, b, n):
        if n <= 1 or b <= a:
            return [(a + b) / 2.0]
        return [a + (b - a) * i / (n - 1) for i in range(n)]

    def _horizontal_segment(y):
        hits = []
        for i, (x1, y1) in enumerate(poly):
            x2, y2 = poly[(i + 1) % len(poly)]
            if abs(y2 - y1) < 1e-9:
                continue
            if (y >= min(y1, y2)) and (y < max(y1, y2)):
                t = (y - y1) / (y2 - y1)
                hits.append(x1 + t * (x2 - x1))
        hits.sort()
        if len(hits) >= 2:
            return hits[0] + edge_inset, hits[-1] - edge_inset
        return cap_x_min + edge_inset, cap_x_max - edge_inset

    def _vertical_segment(x):
        hits = []
        for i, (x1, y1) in enumerate(poly):
            x2, y2 = poly[(i + 1) % len(poly)]
            if abs(x2 - x1) < 1e-9:
                continue
            if (x >= min(x1, x2)) and (x < max(x1, x2)):
                t = (x - x1) / (x2 - x1)
                hits.append(y1 + t * (y2 - y1))
        hits.sort()
        if len(hits) >= 2:
            return hits[0] + edge_inset, hits[-1] - edge_inset
        return cap_y_min + edge_inset, cap_y_max - edge_inset

    x_min = cap_x_min + edge_inset
    x_max = cap_x_max - edge_inset
    y_min = cap_y_min + edge_inset
    y_max = cap_y_max - edge_inset
    if not (
            float(top_rebar.get("top_x_spacing_mm") or 0.0) > 0.0 and
            float(top_rebar.get("top_x_As_provided_mm2") or 0.0) > 0.0):
        n_x_spacing = max(2, int(_m.ceil((y_max - y_min) / s_max)) + 1) if s_max > 0 else n_x_area
        n_x = max(n_x_area, n_x_spacing)
    if not (
            float(top_rebar.get("top_y_spacing_mm") or 0.0) > 0.0 and
            float(top_rebar.get("top_y_As_provided_mm2") or 0.0) > 0.0):
        n_y_spacing = max(2, int(_m.ceil((x_max - x_min) / s_max)) + 1) if s_max > 0 else n_y_area
        n_y = max(n_y_area, n_y_spacing)

    # ── Top X-bars (horizontal solid amber) ─────────────────────
    ys_bar = _linspace(y_min, y_max, n_x)

    for k, yb in enumerate(ys_bar):
        x0, x1 = _horizontal_segment(yb)
        if x1 <= x0:
            continue
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[yb, yb], mode="lines",
            line={"color": TOP_X, "width": 2.5},
            hovertemplate=(
                "Top X-bar {}/{}  {}<br>"
                "As_prov={:.0f} mm²  "
                "fy={:.0f} MPa<extra></extra>".format(
                    k + 1, n_x, bar,
                    n_x * A_bar, fy_d)),
            showlegend=(k == 0),
            name="Top X ({} × {})".format(n_x, bar)))

    # ── Top Y-bars (vertical teal dashed) ───────────────────────
    xs_bar = _linspace(x_min, x_max, n_y)

    for k, xb in enumerate(xs_bar):
        y0, y1 = _vertical_segment(xb)
        if y1 <= y0:
            continue
        fig.add_trace(go.Scatter(
            x=[xb, xb], y=[y0, y1], mode="lines",
            line={"color": TOP_Y, "width": 2.5, "dash": "dash"},
            hovertemplate=(
                "Top Y-bar {}/{}  {}<br>"
                "As_prov={:.0f} mm²  "
                "fy={:.0f} MPa<extra></extra>".format(
                    k + 1, n_y, bar,
                    n_y * A_bar, fy_d)),
            showlegend=(k == 0),
            name="Top Y ({} × {})".format(n_y, bar)))

    # ── Spacing limit annotation ─────────────────────────────────
    # Draw a reference dimension line showing s_max
    s_ref_x0 = x_min
    s_ref_x1 = x_min + s_max
    s_ref_y  = y_max + 200
    fig.add_shape(type="line",
        x0=s_ref_x0, y0=s_ref_y, x1=s_ref_x1, y1=s_ref_y,
        line={"color": "#795548", "width": 2, "dash": "dot"})
    fig.add_annotation(
        x=(s_ref_x0 + s_ref_x1) / 2, y=s_ref_y + 120,
        text="s_max = {:.0f} mm".format(s_max),
        showarrow=False,
        font={"color": "#795548", "size": 11})

    # ── Per-direction summary annotations ───────────────────────
    ann_y_base = cy + ly / 2 + 320
    fig.add_annotation(
        x=cx, y=ann_y_base,
        text=(
            "<b>Top X: {} × {}  "
            "As_prov={:.0f} / req={:.0f} mm²  "
            "fy={:.0f} MPa</b>  — {}".format(
                n_x, bar,
                n_x * A_bar, As_x,
                fy_d,
                top_rebar.get("governs_x", ""))),
        showarrow=False,
        font={"color": TOP_X, "size": 11})
    fig.add_annotation(
        x=cx, y=ann_y_base + 160,
        text=(
            "<b>Top Y: {} × {}  "
            "As_prov={:.0f} / req={:.0f} mm²  "
            "fy={:.0f} MPa</b>  — {}".format(
                n_y, bar,
                n_y * A_bar, As_y,
                fy_d,
                top_rebar.get("governs_y", ""))),
        showarrow=False,
        font={"color": TOP_Y, "size": 11})

    # fy warning badge if fy > 420
    if fy_d > 420:
        fig.add_annotation(
            x=cx, y=ann_y_base + 300,
            text="⚠️ fy = {:.0f} MPa → spacing limited to {:.0f} mm (§24.3.2)".format(
                fy_d, s_max),
            showarrow=False,
            font={"color": "#D84315", "size": 11},
            bgcolor="rgba(255,224,178,0.8)",
            bordercolor="#E65100", borderwidth=1)

    fig.update_layout(
        title=(
            "Top-Face Min. Reinforcement — {} | (0.0018Ag)/2 "
            "(fy_d = {:.0f} MPa, s_max = {:.0f} mm)".format(
                bar, fy_d, s_max)),
        legend=dict(
            orientation="h", yanchor="bottom",
            y=1.02, xanchor="right", x=1))
    return fig
