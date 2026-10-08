"""
Arm Care assessment logic — flags, grading criteria, body maps.
Thresholds copied exactly from the Arm Care Command Center page.
"""
from __future__ import annotations

import re

GRADING_CRITERIA = [
    ("Task scale", "1 = performs well · 0 = assistance required · -1 = unable to perform"),
    ("Dominant hip extension", "Below 0° can increase stress on the anterior shoulder structures."),
    ("Elbow extension", "Monitor a side-to-side difference greater than 5°."),
    ("GIRD", "Loss of internal rotation (10–18°+) together with a loss of total rotational motion (5–8°+)."),
    ("Shoulder flexion deficit", "Non-dominant flexion not ≥5° greater than dominant → increased elbow-injury risk. "
                                 "Not flagged when both sides measure 180°."),
    ("Shoulder ext. rotation deficit", "Dominant ER not ≥5° greater than non-dominant → 4× greater risk of shoulder surgery."),
]

CATEGORIES = [
    ("shoulder", "Shoulder", "Flags: IR loss >10° with total-arc loss >5° (pathological GIRD), non-dom shoulder flexion not "
                             "≥5° greater than dominant, or dominant ER not ≥5° greater than non-dominant."),
    ("elbow", "Elbow", "Flags: elbow extension side-to-side asymmetry greater than 5°."),
    ("hip", "Hip", "Flags: dominant-side hip extension below 0°, which can shift stress onto the anterior shoulder."),
    ("mobility", "Trunk & Mobility", "Flags: failed T-spine extension/rotation screen, or a -1 (unable) score on the inline "
                                     "dying bug, single-leg squat, overhead squat, or trunk stability push-up."),
]

MLB_GRIP_AVG_LB, MLB_GRIP_AVG_SD_LB = 144.0, 20.8
MLB_GRIP_SOURCE = "Erickson et al., Am J Sports Med 2024 (n=213 pitchers, single MLB organization, dominant-arm grip)"

# All assessment fields stored per player (numbers are degrees / lb)
NUM_FIELDS = ["domER", "nonER", "domIR", "nonIR", "domArc", "nonArc", "domFlex", "nonFlex",
              "domElbowExt", "nonElbowExt", "domHipExt", "nonHipExt",
              "erDiff", "irDiff", "flexDiff", "elbowExtDiff", "domGrip", "nonGrip", "pinch", "oh", "trunk"]
TEXT_FIELDS = ["sls", "idb", "tspineRotFail", "note", "sourceBatch"]
BOOL_FIELDS = ["tspineExtFail"]
CONCERN_CATS = ("shoulder", "elbow", "hip", "mobility", "back")


def _n(a, k):
    v = a.get(k)
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def _g(v):
    """Pretty number: 8.0 -> 8"""
    return int(v) if v is not None and float(v).is_integer() else v


def compute_flags(a: dict) -> list[dict]:
    f = []
    dom_hip, elbow, ir = _n(a, "domHipExt"), _n(a, "elbowExtDiff"), _n(a, "irDiff")
    dom_arc, non_arc = _n(a, "domArc"), _n(a, "nonArc")
    flex, er = _n(a, "flexDiff"), _n(a, "erDiff")
    arc_loss = (non_arc - dom_arc) if (non_arc is not None and dom_arc is not None) else 0
    gird_ir = ir is not None and ir > 10
    gird_arc = non_arc is not None and arc_loss > 5
    both_full = _n(a, "domFlex") == 180 and _n(a, "nonFlex") == 180
    note = a.get("note") or ""

    if dom_hip is not None and dom_hip < 0:
        f.append(dict(cat="hip", label=f"Hip ext deficit ({_g(dom_hip)}°)", level="high" if dom_hip <= -8 else "mid"))
    if elbow is not None and abs(elbow) > 5:
        f.append(dict(cat="elbow", label=f"Elbow ext asymmetry ({_g(elbow)}°)", level="mid"))
    if gird_ir and gird_arc:
        f.append(dict(cat="shoulder", label=f"GIRD + total-arc loss (IR {_g(ir)}° / arc {_g(arc_loss)}°)", level="high"))
    elif gird_ir:
        f.append(dict(cat="shoulder", label=f"IR loss ({_g(ir)}°), arc preserved", level="mid"))
    if flex is not None and flex < 5 and not both_full:
        f.append(dict(cat="shoulder", label=f"Flexion deficit (diff {_g(flex)}°)", level="mid"))
    if er is not None and er < 5:
        f.append(dict(cat="shoulder", label=f"ER deficit (diff {_g(er)}°)", level="mid"))
    rot = a.get("tspineRotFail") or "none"
    if a.get("tspineExtFail") or rot != "none":
        f.append(dict(cat="mobility", label="T-spine restriction", level="mid"))
    if _n(a, "oh") == -1 or "-1" in (a.get("sls") or "") or "-1" in (a.get("idb") or ""):
        f.append(dict(cat="mobility", label="Failed squat/stability screen", level="mid"))
    if re.search(r"Tommy John|FAI|cam lesion|surgical scar|surgery", note, re.I):
        f.append(dict(cat="history", label="Documented surgical/injury history", level="high"))
    m = re.search(r"(L|R|left|right)?\s*scap(ular)?\s*wing", note, re.I)
    if m:
        raw = (m.group(1) or "").lower()
        side = "left" if raw in ("l", "left") else ("right" if raw in ("r", "right") else "unspecified side")
        f.append(dict(cat="back", label=f"Scapular winging ({side})", level="mid", side=side))
    return f


def concern_count(flags):
    return sum(1 for x in flags if x["cat"] in CONCERN_CATS)


def overall_level(flags):
    if any(x["level"] == "high" for x in flags):
        return "high"
    return "mid" if concern_count(flags) else "ok"


def region_severity(flags, cat):
    cf = [x for x in flags if x["cat"] == cat]
    if any(x["level"] == "high" for x in cf):
        return "high"
    return "mid" if cf else "ok"


LEVEL_TXT = {"high": "High", "mid": "Monitor", "ok": "Clear"}


def grip_text(dom_grip):
    if dom_grip is None:
        return "—"
    diff = dom_grip - MLB_GRIP_AVG_LB
    return f"{'+' if diff > 0 else ''}{diff:.1f} lb ({round(dom_grip / MLB_GRIP_AVG_LB * 100)}% of MLB avg)"


def pinch_text(pinch, team_avg):
    if pinch is None or team_avg is None:
        return "—"
    diff = pinch - team_avg
    return f"{round(pinch / team_avg * 100)}% of team avg ({'+' if diff > 0 else ''}{diff:.1f} lb)"


# ───────── body maps (same geometry as the Command Center) ─────────
HIGH, MID, BASE, LINE = "#512888", "#a67eea", "#f1eef6", "#c9bfd9"


def _sev(level):
    return HIGH if level == "high" else (MID if level == "mid" else BASE)


def _limbs(neutral, left_arm=None, right_arm=None):
    la, ra = left_arm or neutral, right_arm or neutral
    return f"""
    <line x1="92" y1="80" x2="55" y2="150" stroke="{la}" stroke-width="14" stroke-linecap="round"/>
    <line x1="55" y1="150" x2="45" y2="225" stroke="{la}" stroke-width="12" stroke-linecap="round"/>
    <line x1="168" y1="80" x2="205" y2="150" stroke="{ra}" stroke-width="14" stroke-linecap="round"/>
    <line x1="205" y1="150" x2="215" y2="225" stroke="{ra}" stroke-width="12" stroke-linecap="round"/>
    <line x1="112" y1="212" x2="108" y2="330" stroke="{neutral}" stroke-width="16" stroke-linecap="round"/>
    <line x1="148" y1="212" x2="152" y2="330" stroke="{neutral}" stroke-width="16" stroke-linecap="round"/>
    <line x1="108" y1="330" x2="104" y2="440" stroke="{neutral}" stroke-width="13" stroke-linecap="round"/>
    <line x1="152" y1="330" x2="156" y2="440" stroke="{neutral}" stroke-width="13" stroke-linecap="round"/>"""


def _torso(spine_fill):
    return f"""
    <circle cx="130" cy="34" r="26" fill="{BASE}" stroke="{LINE}" stroke-width="2"/>
    <rect x="90" y="64" width="80" height="130" rx="26" fill="{BASE}" stroke="{LINE}" stroke-width="2"/>
    <rect x="122" y="72" width="16" height="112" rx="8" fill="{spine_fill}" opacity="0.9"/>"""


TXT = 'font-family="sans-serif" font-size="11" fill="#5b5266"'


def _flat(svg):
    """One line, no indentation — Streamlit markdown would otherwise treat indented SVG as a code block."""
    return " ".join(line.strip() for line in svg.splitlines() if line.strip())


def body_map_svg(flags, w=170, h=310):
    sh, el, hip, sp = (region_severity(flags, c) for c in ("shoulder", "elbow", "hip", "mobility"))
    return _flat(f"""<svg width="{w}" height="{h}" viewBox="0 0 260 480" xmlns="http://www.w3.org/2000/svg">
    {_torso(_sev(sp))}
    <text x="150" y="128" {TXT}>T-spine</text>
    {_limbs(BASE, right_arm=_sev(el))}
    <circle cx="82" cy="92" r="15" fill="{BASE}"/><circle cx="55" cy="150" r="12" fill="{BASE}"/>
    <circle cx="178" cy="92" r="15" fill="{_sev(sh)}"/><circle cx="205" cy="150" r="13" fill="{_sev(el)}"/>
    <text x="8" y="66" {TXT}>Glove side</text><text x="186" y="66" {TXT}>Throw side</text>
    <circle cx="130" cy="204" r="13" fill="{_sev(hip)}"/>
    <text x="150" y="215" {TXT}>Dom hip</text></svg>""")


def back_map_svg(flags, w=170, h=310):
    scap = next((x for x in flags if x["cat"] == "back"), None)
    side = scap.get("side") if scap else None
    lc = _sev(scap["level"]) if scap and side in ("left", "unspecified side") else BASE
    rc = _sev(scap["level"]) if scap and side in ("right", "unspecified side") else BASE
    return _flat(f"""<svg width="{w}" height="{h}" viewBox="0 0 260 480" xmlns="http://www.w3.org/2000/svg">
    {_torso(_sev(region_severity(flags, 'mobility')))}
    <text x="150" y="128" {TXT}>Spine</text>
    <ellipse cx="103" cy="98" rx="16" ry="22" fill="{rc}" transform="rotate(-15 103 98)"/>
    <ellipse cx="157" cy="98" rx="16" ry="22" fill="{lc}" transform="rotate(15 157 98)"/>
    <text x="14" y="66" {TXT}>R scapula</text><text x="190" y="66" {TXT}>L scapula</text>
    {_limbs(BASE)}</svg>""")
