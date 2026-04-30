import plotly.graph_objects as go

PILE = "#5B8DEF"; COL = "#FF8A65"
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
    if sec_c == "Circular":
        fig.add_shape(type="circle",
            x0=-cdm/2, y0=-cdm/2, x1=cdm/2, y1=cdm/2,
            fillcolor=COL, line={"color": "#D84315", "width": 2},
            layer="above")
    else:
        fig.add_shape(type="rect",
            x0=-cbx/2, y0=-cby/2, x1=cbx/2, y1=cby/2,
            fillcolor=COL, line={"color": "#D84315", "width": 2},
            layer="above")
        
    fig.add_annotation(x=0, y=0, text="<b>COL</b>", showarrow=False,
                       font={"color": "white", "size": 11})

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

    pad = max(lx, ly)*0.15 + 300

    # ── Center axes (crosshair at origin) ──────────────────────
    # ความยาวแกน = ครึ่งหนึ่งของฐานรากแต่ละด้าน พอดีกับขอบ cap
    _ax_half_x = lx / 2
    _ax_half_y = ly / 2
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
    # Arrow + label ที่ปลายแกน ใช้ pixel-offset (ax, ay) เพื่อไม่ให้ label หาย
    fig.add_annotation(
        x=_ax_half_x, y=0, xref="x", yref="y",
        ax=-30, ay=0,
        text="<b>X</b>", showarrow=True,
        arrowhead=2, arrowsize=1.2, arrowwidth=1.5,
        arrowcolor=_AXIS_COLOR_X,
        font={"color": _AXIS_COLOR_X, "size": 11},
        xanchor="left")
    fig.add_annotation(
        x=0, y=_ax_half_y, xref="x", yref="y",
        ax=0, ay=30,
        text="<b>Y</b>", showarrow=True,
        arrowhead=2, arrowsize=1.2, arrowwidth=1.5,
        arrowcolor=_AXIS_COLOR_Y,
        font={"color": _AXIS_COLOR_Y, "size": 11},
        yanchor="bottom")
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
               "range": [cx-lx/2-pad, cx+lx/2+pad],
               "gridcolor": "#ECEFF1"},
        yaxis={"title": "Y (mm)",
               "range": [cy-ly/2-pad, cy+ly/2+pad],
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
    for idx, s in enumerate(results.get("struts", [])):
        x, y = s["coord"]
        fig.add_trace(go.Scatter(
            x=[0, x], y=[0, y], mode="lines",
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
    x_min, x_max = min(xs)-pwid, max(xs)+pwid
    cap_top = h_cap

    fig.add_shape(type="rect", x0=x_min-200, y0=0,
                  x1=x_max+200, y1=cap_top,
                  fillcolor=CAP_FILL,
                  line={"color": CAP_BORDER, "width": 2},
                  layer="below")
    sec_c, cbx, cby, cdm = _normalize_col(col_size)
    cwid = cdm if sec_c == "Circular" else cbx
    fig.add_shape(type="rect", x0=-cwid/2, y0=cap_top,
                  x1=cwid/2, y1=cap_top+400,
                  fillcolor=COL,
                  line={"color": "#D84315", "width": 2})

    for x, _ in coords:
        fig.add_shape(type="rect",
                      x0=x-pwid/2, y0=-600, x1=x+pwid/2, y1=0,
                      fillcolor=PILE,
                      line={"color": "#1F4E89", "width": 2})
        fig.add_trace(go.Scatter(
            x=[0, x], y=[cap_top, pwid/2], mode="lines",
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
                      results, x_bar, x_n, y_bar, y_n, x_chk, y_chk):
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
    x_min, x_max = min(xs)-pwid_x, max(xs)+pwid_x
    y_min, y_max = min(ys)-pwid_y, max(ys)+pwid_y

    # X-direction bars: horizontal lines running along X, count = x_n, spaced in Y
    if x_n > 1:
        ys_bar = [y_min + (y_max-y_min)*i/(x_n-1) for i in range(x_n)]
    else:
        ys_bar = [(y_min+y_max)/2]
    for yb in ys_bar:
        fig.add_trace(go.Scatter(
            x=[x_min, x_max], y=[yb, yb], mode="lines",
            line={"color": REBAR_X, "width": 2},
            hoverinfo="text",
            text=["{} (X-dir)".format(x_bar)]*2, showlegend=False))

    # Y-direction bars: vertical lines running along Y, count = y_n, spaced in X
    if y_n > 1:
        xs_bar = [x_min + (x_max-x_min)*i/(y_n-1) for i in range(y_n)]
    else:
        xs_bar = [(x_min+x_max)/2]
    for xb in xs_bar:
        fig.add_trace(go.Scatter(
            x=[xb, xb], y=[y_min, y_max], mode="lines",
            line={"color": REBAR_Y, "width": 2, "dash": "dot"},
            hoverinfo="text",
            text=["{} (Y-dir)".format(y_bar)]*2, showlegend=False))

    sx = "OK" if x_chk["ok"] else "FAIL"
    sy = "OK" if y_chk["ok"] else "FAIL"
    fig.add_annotation(x=cx, y=cy+ly/2+150,
        text="<b>X-dir: {}-{}</b> As_prov={:.0f} / req={:.0f} mm² → {}".format(
            x_n, x_bar, x_chk["As_provided"], x_chk["As_required"], sx),
        showarrow=False, font={"color": REBAR_X, "size": 12})
    fig.add_annotation(x=cx, y=cy+ly/2+260,
        text="<b>Y-dir: {}-{}</b> As_prov={:.0f} / req={:.0f} mm² → {}".format(
            y_n, y_bar, y_chk["As_provided"], y_chk["As_required"], sy),
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
                 pile_length=1500.0, col_height=600.0):
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
    if sec_c == "Circular":
        fig.add_trace(_cylinder_mesh(
            0.0, 0.0, h_cap, h_cap+col_height, cdm/2,
            "#FF8A65", opacity=0.9, lighting=LIGHTING_CONCRETE))
    else:
        fig.add_trace(_box_mesh(
            -cbx/2, cbx/2, -cby/2, cby/2,
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
    
    STRUT_LOW = "#2980b9"   # ปรับสีให้เข้มขึ้นเล็กน้อย
    STRUT_MID = "#f39c12"
    STRUT_HIGH = "#c0392b"
    TIE_COLOR = "#27ae60"
    
    for s in results.get("struts", []):
        x, y = s["coord"]
        dcr_ratio = s["F_strut_kN"] / Fs_max if Fs_max > 0 else 0
        if dcr_ratio > 0.85:
            dcr_color = STRUT_HIGH
        elif dcr_ratio > 0.6:
            dcr_color = STRUT_MID
        else:
            dcr_color = STRUT_LOW
        fig.add_trace(go.Scatter3d(
            x=[0, x], y=[0, y], z=[col_top_z, pile_top_z],
            mode="lines",
            line=dict(color=dcr_color, width=8),
            hovertext=("Strut: F={:.0f}kN, θ={:.1f}°".format(
                s["F_strut_kN"], s["theta_deg"])),
            hoverinfo="text", showlegend=False, name="Strut"))

    tol = 1.0
    is_triangular_base = len(coords) == 3
    for i in range(len(coords)):
        for j in range(i+1, len(coords)):
            (x1, y1) = coords[i]; (x2, y2) = coords[j]
            if is_triangular_base or abs(x1 - x2) < tol or abs(y1 - y2) < tol:
                fig.add_trace(go.Scatter3d(
                    x=[x1, x2], y=[y1, y2],
                    z=[pile_top_z, pile_top_z],
                    mode="lines",
                    line=dict(color=TIE_COLOR, width=6, dash="dot"),
                    hovertext="Tie (P{}-P{})".format(i+1, j+1),
                    hoverinfo="text", showlegend=False))

    # Pile labels
    for idx, (px, py) in enumerate(coords, 1):
        fig.add_trace(go.Scatter3d(
            x=[px], y=[py], z=[-pile_length/2],
            mode="text", text=["P{}".format(idx)],
            textfont=dict(color="white", size=12),
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

    # Min bars from As requirement
    n_x = max(2, int(_m.ceil(As_x / A_bar))) if As_x > 0 else 2
    n_y = max(2, int(_m.ceil(As_y / A_bar))) if As_y > 0 else 2

    # Base cap outline
    fig = plot_layout_preview(coords, D, lx, ly, cx, cy, col_size,
                              "Top-Face Reinforcement (Plan)", cap_polygon)
    if not coords:
        return fig

    xs_p = [c[0] for c in coords]
    ys_p = [c[1] for c in coords]
    sec_p, pbx, pby, pdm = _normalize_pile(D)
    hw_x = (pdm if sec_p == "Circular" else pbx) / 2.0
    hw_y = (pdm if sec_p == "Circular" else pby) / 2.0
    x_min = min(xs_p) - hw_x
    x_max = max(xs_p) + hw_x
    y_min = min(ys_p) - hw_y
    y_max = max(ys_p) + hw_y

    # ── Top X-bars (horizontal solid amber) ─────────────────────
    if n_x > 1:
        ys_bar = [y_min + (y_max - y_min) * i / (n_x - 1)
                  for i in range(n_x)]
    else:
        ys_bar = [(y_min + y_max) / 2.0]

    for k, yb in enumerate(ys_bar):
        fig.add_trace(go.Scatter(
            x=[x_min, x_max], y=[yb, yb], mode="lines",
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
    if n_y > 1:
        xs_bar = [x_min + (x_max - x_min) * i / (n_y - 1)
                  for i in range(n_y)]
    else:
        xs_bar = [(x_min + x_max) / 2.0]

    for k, xb in enumerate(xs_bar):
        fig.add_trace(go.Scatter(
            x=[xb, xb], y=[y_min, y_max], mode="lines",
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
            "Top-Face Min. Reinforcement — {} "
            "(fy_d = {:.0f} MPa, s_max = {:.0f} mm)".format(
                bar, fy_d, s_max)),
        legend=dict(
            orientation="h", yanchor="bottom",
            y=1.02, xanchor="right", x=1))
    return fig