import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon as MplPolygon
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def _norm_col(c):
    if isinstance(c, dict):
        return (c.get("section", "Square"),
                c.get("bx", 500.0), c.get("by", 500.0),
                c.get("diam", 500.0))
    return ("Square", float(c), float(c), float(c))

def _format_col(c):
    sec, bx, by, dm = _norm_col(c)
    if sec == "Circular":
        return "Circular, D = {:.0f} mm".format(dm)
    if sec == "Rectangular":
        return "Rectangular, {:.0f} x {:.0f} mm".format(bx, by)
    return "Square, {:.0f} mm side".format(bx)

def _norm_pile(p):
    if isinstance(p, dict):
        return (p.get("section", "Circular"),
                p.get("bx", 600.0), p.get("by", 600.0),
                p.get("diam", 600.0))
    return ("Circular", float(p), float(p), float(p))

def _format_pile(p):
    sec, bx, by, dm = _norm_pile(p)
    if sec == "Circular":
        return "Circular, D = {:.0f} mm".format(dm)
    if sec == "Square":
        return "Square, {:.0f} mm side".format(bx)
    return "Rectangular, {:.0f} x {:.0f} mm".format(bx, by)

def _plot_plan(coords, D, lx, ly, cx, cy, col_size, cap_polygon, results):
    fig, ax = plt.subplots(figsize=(7, 7))
    if cap_polygon:
        ax.add_patch(MplPolygon(cap_polygon, closed=True, fill=True,
            facecolor='#bdc3c7', edgecolor='#34495e',
            linewidth=2, alpha=0.4))
    else:
        ax.add_patch(patches.Rectangle(
            (cx-lx/2, cy-ly/2), lx, ly,
            facecolor='#bdc3c7', edgecolor='#34495e',
            linewidth=2, alpha=0.4))
    sec_c, cbx, cby, cdm = _norm_col(col_size)
    if sec_c == "Circular":
        ax.add_patch(patches.Circle(
            (0, 0), cdm/2,
            facecolor='#FF8A65', edgecolor='#D84315', linewidth=2))
    else:
        ax.add_patch(patches.Rectangle(
            (-cbx/2, -cby/2), cbx, cby,
            facecolor='#FF8A65', edgecolor='#D84315', linewidth=2))
    ax.text(0, 0, 'COL', ha='center', va='center',
            color='white', fontsize=9, fontweight='bold')
    pile_loads = results.get("pile_loads_kN", [])
    sec_p, pbx, pby, pdm = _norm_pile(D)
    for i, (x, y) in enumerate(coords, 1):
        if sec_p == "Circular":
            ax.add_patch(patches.Circle((x, y), pdm/2,
                facecolor='#5B8DEF', edgecolor='#1F4E89', linewidth=1.5))
        elif sec_p == "Square":
            ax.add_patch(patches.Rectangle(
                (x-pbx/2, y-pbx/2), pbx, pbx,
                facecolor='#5B8DEF', edgecolor='#1F4E89', linewidth=1.5))
        else:
            ax.add_patch(patches.Rectangle(
                (x-pbx/2, y-pby/2), pbx, pby,
                facecolor='#5B8DEF', edgecolor='#1F4E89', linewidth=1.5))
        lbl = 'P{}'.format(i)
        if i-1 < len(pile_loads):
            lbl += '\n{:.0f}kN'.format(pile_loads[i-1])
        ax.text(x, y, lbl, ha='center', va='center',
                color='white', fontsize=8, fontweight='bold')
        ax.plot([0, x], [0, y], 'r--', linewidth=1.5, alpha=0.7)
    pad = max(lx, ly)*0.15 + 300
    ax.set_xlim(cx-lx/2-pad, cx+lx/2+pad)
    ax.set_ylim(cy-ly/2-pad, cy+ly/2+pad)
    ax.set_aspect('equal')
    ax.set_title('Plan View - Pile Cap Layout & Struts')
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.grid(True, alpha=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def _plot_elev(coords, h_cap, D, col_size, results):
    fig, ax = plt.subplots(figsize=(8, 5))
    if not coords:
        plt.close(fig); return None
    xs = [c[0] for c in coords]
    sec_p, pbx, pby, pdm = _norm_pile(D)
    pwid = pdm if sec_p == "Circular" else pbx
    x_min, x_max = min(xs)-pwid, max(xs)+pwid
    ax.add_patch(patches.Rectangle(
        (x_min-200, 0), x_max-x_min+400, h_cap,
        facecolor='#bdc3c7', edgecolor='#34495e',
        linewidth=2, alpha=0.4))
    sec_c, cbx, cby, cdm = _norm_col(col_size)
    cwid = cdm if sec_c == "Circular" else cbx
    ax.add_patch(patches.Rectangle(
        (-cwid/2, h_cap), cwid, 400,
        facecolor='#FF8A65', edgecolor='#D84315', linewidth=2))
    for x, _ in coords:
        ax.add_patch(patches.Rectangle(
            (x-pwid/2, -600), pwid, 600,
            facecolor='#5B8DEF', edgecolor='#1F4E89', linewidth=2))
        ax.plot([0, x], [h_cap, pwid/2], 'r-', linewidth=3, alpha=0.8)
    if len(coords) >= 2:
        ax.plot([min(xs), max(xs)], [pwid/2, pwid/2], 'g-', linewidth=4)
        ax.text((min(xs)+max(xs))/2, pwid/2-150,
                'Tie F={:.0f}kN'.format(results['F_tie_max_kN']),
                ha='center', color='green', fontweight='bold')
    ax.set_aspect('equal')
    ax.set_title('Elevation - Struts (red) & Tie (green)')
    ax.set_xlabel('X (mm)'); ax.set_ylabel('Z (mm)')
    ax.grid(True, alpha=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


def _set_cell(cell, text, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(str(text))
    r.bold = bold
    r.font.size = Pt(10)


def _make_table(doc, headers, rows):
    tbl = doc.add_table(rows=1+len(rows), cols=len(headers))
    tbl.style = 'Light Grid Accent 1'
    for j, h in enumerate(headers):
        _set_cell(tbl.rows[0].cells[j], h, bold=True)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            _set_cell(tbl.rows[i+1].cells[j], v)
    return tbl


def generate_report(inputs, results, x_chk, y_chk, pairs,
                    anch_x=None, anch_y=None, opt_x=None, opt_y=None,
                    top_rebar=None):
    doc = Document()

    # Title
    h = doc.add_heading('Pile Cap Design Report', level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run('Strut-and-Tie Method per ACI 318-19')
    r.italic = True

    # 1. Inputs
    doc.add_heading('1. Design Inputs', level=1)
    doc.add_heading('1.1 Materials', level=2)
    _make_table(doc, ['Parameter', 'Value'], [
        ["Concrete strength f'c", "{} MPa".format(inputs['fc'])],
        ["Steel yield fy", "{} MPa".format(inputs['fy'])],
        ["Concrete cover", "{} mm".format(inputs['cover'])],
    ])

    doc.add_heading('1.2 Geometry', level=2)
    _make_table(doc, ['Parameter', 'Value'], [
        ["Pile section", _format_pile(inputs['D'])],
        ["Cap thickness h", "{} mm".format(inputs['h_cap'])],
        ["Column section", _format_col(inputs['col_size'])],
        ["Number of piles", "{}".format(results['n_piles'])],
        ["Cap shape", inputs['shape_label']],
        ["Cap Lx x Ly", "{:.0f} x {:.0f} mm".format(
            inputs['cap_lx'], inputs['cap_ly'])],
    ])

    doc.add_heading('1.3 Column Loads', level=2)
    _make_table(doc, ['Load', 'Value'], [
        ["Axial Pu", "{:.1f} kN".format(inputs['Pu'])],
        ["Moment Mux (about X-axis)", "{:.1f} kN-m".format(inputs['Mux'])],
        ["Moment Muy (about Y-axis)", "{:.1f} kN-m".format(inputs['Muy'])],
    ])

    # 2. Pile Layout
    doc.add_heading('2. Pile Layout & Reactions', level=1)
    _sec_p, _pbx, _pby, _pdm = _norm_pile(inputs['D'])
    if _sec_p == "Circular":
        _gov_min = _pdm
    elif _sec_p == "Square":
        _gov_min = _pbx
    else:
        _gov_min = min(_pbx, _pby)
    doc.add_paragraph(
        "Per ACI 318-19 §13.4.2.1, minimum pile center-to-center spacing "
        "is 2.5 x governing dim = {:.0f} mm.".format(2.5*_gov_min))

    img = _plot_plan(inputs['coords'], inputs['D'],
                     inputs['cap_lx'], inputs['cap_ly'],
                     inputs['cap_cx'], inputs['cap_cy'],
                     inputs['col_size'], inputs['cap_polygon'], results)
    doc.add_picture(img, width=Inches(5.5))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.add_run('Figure 1: Plan view of pile cap with struts').italic = True

    doc.add_heading('2.1 Pile-to-Pile Spacing Check', level=2)
    p = doc.add_paragraph(
        "Distance computed by: d_ij = sqrt((x_i - x_j)^2 + (y_i - y_j)^2)")
    rows = [["P{}-P{}".format(i, j), "{:.0f}".format(d),
             "OK" if ok else "FAIL"] for (i, j, d, ok) in pairs]
    _make_table(doc, ['Pair', 'Distance (mm)', 'Status'], rows)

    doc.add_heading('2.2 Pile Reactions (Rigid-Cap Elastic)', level=2)
    p = doc.add_paragraph()
    p.add_run('Formula: ').bold = True
    p.add_run("P_i = Pu/n + (Mux x y_i) / Σy_j² + (Muy x x_i) / Σx_j²")
    rows = [["P{}".format(i+1),
             "{:.0f}".format(c[0]),
             "{:.0f}".format(c[1]),
             "{:.1f}".format(P)]
            for i, (c, P) in enumerate(
                zip(inputs['coords'], results['pile_loads_kN']))]
    _make_table(doc, ['Pile', 'X (mm)', 'Y (mm)', 'P_i (kN)'], rows)
    if results['has_uplift']:
        p = doc.add_paragraph()
        rr = p.add_run("Warning: Uplift detected (P_min = {:.1f} kN). "
                       "Provide tension piles or anchorage.".format(
                           results['P_min_kN']))
        rr.font.color.rgb = RGBColor(0xC6, 0x28, 0x28)
        rr.bold = True

    # 3. STM Analysis
    doc.add_heading('3. Strut-and-Tie Analysis', level=1)
    p = doc.add_paragraph()
    p.add_run('Effective depth: ').bold = True
    _sp2, _pbx2, _pby2, _pdm2 = _norm_pile(inputs['D'])
    if _sp2 == "Circular":
        _gov_max = _pdm2
    elif _sp2 == "Square":
        _gov_max = _pbx2
    else:
        _gov_max = max(_pbx2, _pby2)
    p.add_run("d_eff = h - cover - db/2 = {} - {} - 12.5 = {:.0f} mm "
              "(ACI 318-19 §23.2, db assumed = DB25)".format(
                  inputs['h_cap'], inputs['cover'],
                  results['d_effective_mm']))

    img2 = _plot_elev(inputs['coords'], inputs['h_cap'],
                      inputs['D'], inputs['col_size'], results)
    if img2:
        doc.add_picture(img2, width=Inches(6))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.add_run('Figure 2: Elevation showing struts and bottom tie').italic = True

    doc.add_heading('3.1 Strut Forces', level=2)
    p = doc.add_paragraph()
    p.add_run("Each strut force: F_strut_i = P_i x L_strut / d_eff "
              "(equilibrium at column-pile node)")
    rows = []
    for i, s in enumerate(results['struts']):
        rows.append([
            "S{}".format(i+1),
            "{:.0f}".format(s['L_strut']),
            "{:.1f}".format(s['theta_deg']),
            "{:.1f}".format(s['F_strut_kN']),
            "{:.1f}".format(s['F_tie_x_kN']),
            "{:.1f}".format(s['F_tie_y_kN']),
        ])
    _make_table(doc, ['Strut', 'L (mm)', 'θ (deg)',
                      'F_strut (kN)', 'F_tie_x (kN)', 'F_tie_y (kN)'], rows)

    # 4. Capacity Checks
    doc.add_heading('4. Capacity Checks (ACI 318-19 Ch. 23)', level=1)
    p = doc.add_paragraph()
    p.add_run('Strut effective compressive strength: ').bold = True
    p.add_run("f_ce = 0.85 x β_s x f'c (ACI 318-19 Eq. 23.4.3a) "
              "= 0.85 x 0.75 x {:.0f} = {:.2f} MPa".format(
                  inputs['fc'], results['fce_strut_MPa']))
    p = doc.add_paragraph()
    p.add_run('Strength reduction factors: ').bold = True
    p.add_run("φ_STM = 0.75 (ACI 21.2.1), φ_bearing = 0.75 (ACI 21.2.1(e))")

    # Node type: CTT (βn=0.60) for n>=4 piles; CCT (βn=0.80) for n<4 piles
    _n_pile = results.get('n_piles', 4)
    _bn_pile = results.get('bn_pile', 0.60 if _n_pile >= 4 else 0.80)
    _node_label = "CTT, βn={:.2f}".format(_bn_pile)

    rows = [
        ["Strut compression (φFns)",
         "{:.0f}".format(results['phi_Fns_kN']),
         "{:.0f}".format(results['F_strut_max_kN']),
         "{:.2f}".format(results['strut_DCR']),
         "OK" if results['strut_DCR'] <= 1 else "FAIL"],
        ["Pile bearing ({})".format(_node_label),
         "{:.0f}".format(results['phi_Pn_bearing_kN']),
         "{:.0f}".format(results['P_max_kN']),
         "{:.2f}".format(results['bearing_DCR']),
         "OK" if results['bearing_DCR'] <= 1 else "FAIL"],
        ["Column bearing (CCC, βn=1.00)",
         "{:.0f}".format(results['phi_Pn_column_kN']),
         "{:.0f}".format(results['Pu_kN']),
         "{:.2f}".format(results['column_DCR']),
         "OK" if results['column_DCR'] <= 1 else "FAIL"],
        ["Min strut angle ≥25° ({:.1f}°)".format(
            results['min_strut_angle_deg']),
         "-", "-", "-",
         "OK" if results['angle_OK'] else "FAIL"],
    ]
    _make_table(doc, ['Check', 'Capacity (kN)',
                      'Demand (kN)', 'DCR', 'Status'], rows)

    # 5. Reinforcement
    doc.add_heading('5. Tie Reinforcement Design', level=1)
    p = doc.add_paragraph()
    p.add_run('Required steel: ').bold = True
    p.add_run("As_required = F_tie / (φ x fy)  (ACI 23.7.2)")
    if results.get("is_3pile_resultant"):
        p = doc.add_paragraph()
        p.add_run('Resultant tie force (3-pile): ').bold = True
        p.add_run("{:.1f} kN — √(Ftx²+Fty²), used for As_x = As_y".format(
            results['F_tie_res_kN']))
    _make_table(doc,
        ['Direction', 'F_tie (kN)', 'As req (mm²)', 'Selected',
         'As prov (mm²)', 'Ratio', 'Status'],
        [["X (along x-axis)",
          "{:.1f}".format(results['F_tie_x_max_kN'] if not results.get("is_3pile_resultant") else results['F_tie_res_kN']),
          "{:.0f}".format(results['As_x_required_mm2']),
          "{}-{}".format(x_chk['n_bars'], x_chk['bar_size']),
          "{:.0f}".format(x_chk['As_provided']),
          "{:.2f}".format(x_chk['ratio']),
          "OK" if x_chk['ok'] else "FAIL"],
         ["Y (along y-axis)",
          "{:.1f}".format(results['F_tie_y_max_kN'] if not results.get("is_3pile_resultant") else results['F_tie_res_kN']),
          "{:.0f}".format(results['As_y_required_mm2']),
          "{}-{}".format(y_chk['n_bars'], y_chk['bar_size']),
          "{:.0f}".format(y_chk['As_provided']),
          "{:.2f}".format(y_chk['ratio']),
          "OK" if y_chk['ok'] else "FAIL"]])
    
    # 5.5 Auto-Optimized Rebar (min weight)
    if opt_x and opt_y:
        doc.add_heading('5.5 Auto-Optimized Rebar (Minimum Weight)', level=2)
        p = doc.add_paragraph()
        p.add_run('Optimization criterion: ').bold = True
        p.add_run("Minimum total steel weight while As_provided ≥ As_required, "
                  "bar lengths assumed equal to cap span in each direction.")
        _make_table(doc,
            ['Direction', 'Optimal selection', 'As prov (mm²)',
             'Bar length (mm)', 'Weight (kg)', 'Status'],
            [["X (along x-axis)",
              "{}-{}".format(opt_x["n_bars"], opt_x["bar_size"]),
              "{:.0f}".format(opt_x["As_provided"]),
              "{:.0f}".format(opt_x["bar_length_mm"]),
              "{:.2f}".format(opt_x["weight_kg"]),
              "OK" if opt_x["ok"] else "FAIL"],
             ["Y (along y-axis)",
              "{}-{}".format(opt_y["n_bars"], opt_y["bar_size"]),
              "{:.0f}".format(opt_y["As_provided"]),
              "{:.0f}".format(opt_y["bar_length_mm"]),
              "{:.2f}".format(opt_y["weight_kg"]),
              "OK" if opt_y["ok"] else "FAIL"]])

    # 5.6 Anchorage / Development Length (ACI 25.4)
    if anch_x and anch_y:
        doc.add_heading('5.6 Anchorage at CCT Nodes (ACI 318-19 §25.4)', level=2)
        p = doc.add_paragraph()
        p.add_run('Per ACI 23.8.3, ').bold = True
        p.add_run("tie reinforcement shall develop fy at the point where the "
                  "centroid of the tie crosses the extended nodal zone. "
                  "Required ld and ldh are checked below:")
        p = doc.add_paragraph()
        p.add_run("• ld (straight)  ≈ (fy·ψs / 1.1λ√f'c·(cb+Ktr)/db)·db   "
                  "(ACI Eq. 25.4.2.3a)")
        p = doc.add_paragraph()
        p.add_run("• ldh (hook)     ≈ (fy / 23λ√f'c)·db^1.5             "
                  "(ACI Eq. 25.4.3.1a)")
        _make_table(doc,
            ['Direction', 'Bar', 'ld req (mm)', 'ldh req (mm)',
             'Avail straight (mm)', 'Avail hook (mm)', 'Recommended'],
            [["X",
              anch_x["bar_size"],
              "{:.0f}".format(anch_x["ld_required_mm"]),
              "{:.0f}".format(anch_x["ldh_required_mm"]),
              "{:.0f}".format(anch_x["available_straight_mm"]),
              "{:.0f}".format(anch_x["available_hook_mm"]),
              anch_x["recommended"]],
             ["Y",
              anch_y["bar_size"],
              "{:.0f}".format(anch_y["ld_required_mm"]),
              "{:.0f}".format(anch_y["ldh_required_mm"]),
              "{:.0f}".format(anch_y["available_straight_mm"]),
              "{:.0f}".format(anch_y["available_hook_mm"]),
              anch_y["recommended"]]])

    # 6. Top-Face Minimum Reinforcement
    doc.add_heading('6. Top-Face Minimum Reinforcement (ACI 318-19)', level=1)
    if top_rebar:
        tr = top_rebar
        p = doc.add_paragraph()
        p.add_run(
            "The top face of the pile cap is not part of the STM load path "
            "but requires minimum reinforcement per three ACI 318-19 criteria:"
        )

        doc.add_heading('6.1 Temperature & Shrinkage — §24.4.3.2 Table 24.4.3.2',
                        level=2)
        p = doc.add_paragraph()
        p.add_run("ρ_ts = {:.4f}  ".format(tr["rho_ts"])).bold = True
        p.add_run("(fy ≤ 420 MPa → ρ = 0.0018)")
        _make_table(doc, ['Direction', 'b (mm)', 'h (mm)',
                          'ρ_ts', 'As_req (mm²)'], [
            ['X', '{:.0f}'.format(inputs['cap_ly']),
             str(inputs['h_cap']), '{:.4f}'.format(tr['rho_ts']),
             '{:.0f}'.format(tr['As_ts_x_mm2'])],
            ['Y', '{:.0f}'.format(inputs['cap_lx']),
             str(inputs['h_cap']), '{:.4f}'.format(tr['rho_ts']),
             '{:.0f}'.format(tr['As_ts_y_mm2'])],
        ])

        doc.add_heading('6.2 Min Flexural Reinforcement — §9.6.1.2 (ref. §13.3.3.1)',
                        level=2)
        p = doc.add_paragraph()
        p.add_run("ρ_flex = max(0.25√f'c/fy, 1.4/fy) = "
                  "{:.4f}".format(tr['rho_flex'])).bold = True
        p.add_run(
            "  |  d_top = h − cover − db/2 "
            "= {} − {} − 12.5 = {:.0f} mm  (assumed DB25)".format(
                inputs['h_cap'], inputs['cover'], tr['d_top_mm']))
        _make_table(doc, ['Direction', 'b (mm)', 'd_top (mm)',
                          'ρ_flex', 'As_req (mm²)'], [
            ['X', '{:.0f}'.format(inputs['cap_ly']),
             '{:.0f}'.format(tr['d_top_mm']),
             '{:.4f}'.format(tr['rho_flex']),
             '{:.0f}'.format(tr['As_flex_x_mm2'])],
            ['Y', '{:.0f}'.format(inputs['cap_lx']),
             '{:.0f}'.format(tr['d_top_mm']),
             '{:.4f}'.format(tr['rho_flex']),
             '{:.0f}'.format(tr['As_flex_y_mm2'])],
        ])

        doc.add_heading('6.3 Crack-Control for STM — §23.5.1 (ρ_face ≥ 0.003)',
                        level=2)
        p = doc.add_paragraph()
        p.add_run(
            "Eq. 23.5.1: Σ(Asi/bsi)·sinγi ≥ 0.003 per orthogonal direction. "
            "Conservative simplification: ρ_face ≥ 0.003 each face."
        )
        _make_table(doc, ['Direction', 'b (mm)', 'h (mm)',
                          'ρ_cc', 'As_req (mm²)'], [
            ['X', '{:.0f}'.format(inputs['cap_ly']),
             str(inputs['h_cap']), '0.0030',
             '{:.0f}'.format(tr['As_cc_x_mm2'])],
            ['Y', '{:.0f}'.format(inputs['cap_lx']),
             str(inputs['h_cap']), '0.0030',
             '{:.0f}'.format(tr['As_cc_y_mm2'])],
        ])

        doc.add_heading('6.4 Governing Top-Face Reinforcement', level=2)
        _s_gov = tr.get("s_max_top_mm", min(3*inputs['h_cap'], 450))
        _s_ts  = tr.get("s_ts_max_mm",  min(3*inputs['h_cap'], 450))
        _s_cr  = tr.get("s_crack_mm",   9999)
        _fs    = tr.get("fs_service_mpa", (2/3)*tr.get("fy_design_mpa", 420))
        _fy_d  = tr.get("fy_design_mpa", 420)

        p = doc.add_paragraph()
        p.add_run("Bar selected: ").bold = True
        p.add_run("{} (fy_bar = {:.0f} MPa, fy_design = {:.0f} MPa — {})".format(
            tr.get("top_bar_size", "—"),
            tr.get("fy_bar_mpa", _fy_d), _fy_d,
            tr.get("fy_note", "")))

        _make_table(doc,
                    ['Direction', 'As_top req (mm²)', 'Governing Check'],
                    [['X', '{:.0f}'.format(tr['As_top_x_mm2']),
                      tr['governs_x']],
                     ['Y', '{:.0f}'.format(tr['As_top_y_mm2']),
                      tr['governs_y']]])

        doc.add_heading('6.5 Spacing Limits', level=2)
        _make_table(doc,
                    ['Check', 's_max (mm)', 'Active'],
                    [['§24.4.3.3  min(3h={:.0f}, 450)'.format(3*inputs['h_cap']),
                      '{:.0f}'.format(_s_ts), 'Always'],
                     ['§24.3.2  crack-width  (fs={:.0f} MPa)'.format(_fs),
                      '{:.0f}'.format(_s_cr),
                      'fy > 420' if _fy_d > 420 else 'Not active (fy ≤ 420)'],
                     ['Governing s_max', '{:.0f}'.format(_s_gov), '← use this']])

        p = doc.add_paragraph()
        p.add_run("Placement: ").bold = True
        p.add_run(
            "Top bars placed in both X and Y directions, "
            "uniformly distributed across the full cap width, "
            "at cover depth from the top surface. "
            "fy used in design per ACI §20.2.2.4: "
            "≤DB28 → 390 MPa, DB32 → 490 MPa, capped at 550 MPa.")
    else:
        doc.add_paragraph("Top reinforcement data not available.")

    # 7. Notes
    doc.add_heading('7. Important Notes', level=1)
    p = doc.add_paragraph()
    rr = p.add_run("Per ACI 318-19 §13.4.6.3: ")
    rr.bold = True
    p.add_run(
        "When the Strut-and-Tie Method (STM) is used to design a pile cap "
        "in accordance with ACI 318-19 Chapter 23, separate beam-shear and "
        "two-way (punching) shear checks are NOT required. The shear "
        "behavior is implicitly captured through the strength of struts "
        "and nodal zones in the STM model.")

    # 8. Conclusion
    doc.add_heading('8. Conclusion', level=1)
    p = doc.add_paragraph()
    if results['overall_OK'] and x_chk['ok'] and y_chk['ok']:
        rr = p.add_run("DESIGN OK. ")
        rr.bold = True
        rr.font.color.rgb = RGBColor(0x2E, 0x7D, 0x32)
        p.add_run("All STM capacity checks and reinforcement requirements "
                  "satisfied per ACI 318-19.")
    else:
        rr = p.add_run("DESIGN FAILS. ")
        rr.bold = True
        rr.font.color.rgb = RGBColor(0xC6, 0x28, 0x28)
        p.add_run("One or more checks unsatisfied. Increase cap thickness, "
                  "pile size, cap dimensions, or reinforcement.")

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out