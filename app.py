"""
K-State Baseball — Arm Care Command Center (Streamlit)
Run in VS Code:  press ▶ on run.py   — or —   streamlit run app.py
Everything saves automatically the moment it's entered.

Team · Pitchers · Position Players.  Touch a player to open his file:
  Daily Throwing Log (pitchers) · Performance Metrics · Performance Assessment · Correctives
"""
from __future__ import annotations

import base64
import io
from functools import partial
import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

import assess as ax
import model as m
import storage as db

HERE = os.path.dirname(os.path.abspath(__file__))
PURPLE, KSU, LAVENDER, DARK_GRAY, LIGHT_GRAY = "#330a57", "#512888", "#a67eea", "#a7a9ac", "#e2e3e4"
TAB_KEY = "player_tab"

st.set_page_config(page_title="Arm Care Command Center", page_icon="⚾", layout="wide")
st.markdown(f"""<style>
.block-container {{ padding-top: 3.2rem; max-width: 1320px; }}
h1, h2, h3 {{ color: {PURPLE}; }}
div[data-testid="stMetric"] {{ background: rgba(51,10,87,.05); border-radius: 6px; padding: .5rem .9rem; }}
.jersey {{ background:{PURPLE}; color:#fff; font-weight:800; font-size:2.3rem; line-height:1; border-radius:6px;
  min-width:64px; height:64px; display:flex; align-items:center; justify-content:center; padding:0 8px; }}
.pname {{ font-size:1.9rem !important; font-weight:800; color:{PURPLE}; line-height:1.1; margin:0 0 .15rem 0; }}
.pmeta {{ color:#666; }}
.pill {{ display:inline-block; padding:3px 11px; border-radius:999px; font-weight:700; font-size:.85rem; white-space:nowrap; }}
.zone {{ padding:.65rem 1rem; border-radius:8px; margin:.2rem 0 .6rem 0; }}
.zone b {{ display:block; }}
.z-Undertrained {{ background:#e6eefb; color:#1d4f91; }} .z-Sweet {{ background:#e4f3e8; color:#1b6632; }}
.z-Caution {{ background:#fff2d1; color:#7d5300; }} .z-High {{ background:#fde6e6; color:#a3191c; }}
.z-Insufficient, .z-none, .z-Building {{ background:#eceaef; color:#3d3845; }}
.plan {{ background:rgba(51,10,87,.06); border-radius:8px; padding:.6rem .9rem; margin-bottom:.45rem; }}
.saved {{ color:#1b6632; font-weight:700; font-size:.85rem; }}
.preview {{ background:rgba(51,10,87,.07); border-radius:8px; padding:.7rem 1rem; display:flex; gap:1.6rem; flex-wrap:wrap; align-items:baseline; }}
.preview .k {{ display:block; font-size:.72rem; text-transform:uppercase; letter-spacing:.07em; color:#666; }}
.preview .big {{ font-size:2rem; font-weight:800; color:{PURPLE}; line-height:1; }}
button[data-baseweb="tab"] p {{ font-size:.95rem; }}
/* Command Center */
.cc-hero {{ background:linear-gradient(155deg,{LAVENDER} 0%,{KSU} 55%,{PURPLE} 100%); color:#fff; border-radius:14px;
  padding:18px 22px; display:flex; align-items:center; gap:18px; margin-bottom:1rem; }}
.cc-hero img {{ height:58px; }}
.cc-hero .eyebrow {{ font-size:.72rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#e4d6f5; }}
.cc-hero h1 {{ color:#fff; margin:0; padding:0; font-size:2rem; line-height:1.05; }}
.cc-hero .sub {{ color:#e4d6f5; font-size:.9rem; }}
.avatar {{ width:84px; height:84px; border-radius:50%; overflow:hidden; margin:2px auto 6px; background:#ece4f6; color:{KSU};
  display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.6rem; border:3px solid #e2d8ef; }}
.avatar img {{ width:100%; height:100%; object-fit:cover; }}
.avatar.big {{ width:112px; height:112px; font-size:2.2rem; margin:0; }}
.tile-name {{ text-align:center; font-weight:700; line-height:1.2; }}
.tile-meta {{ text-align:center; color:#666; font-size:.8rem; margin-bottom:4px; }}
.tile-pills {{ text-align:center; min-height:26px; }}
.lv-high {{ background:{PURPLE}; color:#fff; }} .lv-mid {{ background:#e3d7ef; color:{PURPLE}; }} .lv-ok {{ background:#eceaef; color:#5b5266; }}
.flag {{ display:inline-block; font-size:.8rem; font-weight:700; padding:4px 11px; border-radius:20px; margin:0 6px 6px 0; }}
.crit {{ background:rgba(51,10,87,.05); border-radius:8px; padding:.6rem .9rem; font-size:.88rem; color:#444; margin-bottom:.4rem; }}
.crit b {{ color:{KSU}; display:block; }}
.bm-wrap {{ display:flex; gap:14px; justify-content:center; flex-wrap:wrap; }}
.bm-wrap .lbl {{ font-size:.7rem; font-weight:700; color:#666; text-align:center; letter-spacing:.05em; text-transform:uppercase; }}
.legend-dot {{ display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:6px; vertical-align:-1px; }}
.fc-card {{ border:1px solid #e2d8ef; border-radius:10px; padding:.7rem .9rem; margin-bottom:.6rem; }}
.fc-card .l {{ font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:#666; font-weight:700; }}
.fc-card .v {{ font-size:1.8rem; font-weight:700; color:{PURPLE}; line-height:1.15; }}
.fc-card .v small {{ font-size:.8rem; color:#666; font-weight:500; margin-left:4px; }}
.fc-card .t {{ font-size:.82rem; color:#555; }}
footer-note {{ font-size:.8rem; color:#666; }}
</style>""", unsafe_allow_html=True)


# ───────────────────────── first run ─────────────────────────
db.seed_if_empty(os.path.join(HERE, "data", "ACWR Throwing Plan Fall 2026.xlsx"),
                 os.path.join(HERE, "data", "seed_command_center.json"))

for msg in st.session_state.pop("_toasts", []):
    st.toast(msg, icon="✅")


# ───────────────────────── helpers ─────────────────────────
def chicago_today() -> date:
    return datetime.now(ZoneInfo("America/Chicago")).date()


def fmt(x, d=1, dash="—"):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return dash
    return f"{x:,.{d}f}"


def none_if_nan(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


def zkey(zone):
    return (zone or "none").split()[0]


def zshort(zone):
    return (zone or "").split(" (")[0].replace("Insufficient history", "Building history")


def pill(zone):
    return f'<span class="pill z-{zkey(zone)}">● {zshort(zone)}</span>'


def zone_box(zone, guidance):
    return f'<div class="zone z-{zkey(zone)}"><b>Zone: {zone}</b>{guidance}</div>'


def toast(msg):
    st.session_state.setdefault("_toasts", []).append(msg)


def bump(k):
    st.session_state[k] = st.session_state.get(k, 0) + 1


def stamp():
    return datetime.now().strftime("%-I:%M:%S %p") if os.name != "nt" else datetime.now().strftime("%I:%M:%S %p")


def calc_log(pid, avg):
    df = db.load_log(pid)
    calc = pd.DataFrame([m.calc_row(r, avg) for r in df.to_dict("records")], columns=list(m.calc_row({}, None).keys()))
    out = pd.concat([df.reset_index(drop=True), calc], axis=1)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    return out


def daily_of(pid, avg):
    return m.daily_totals(calc_log(pid, avg))


def tab_label(p):
    return f"{p['number']}  {p['name']}" if p.get("number") not in (None, "") else p["name"]


def to_time(s):
    if not s or (isinstance(s, float) and pd.isna(s)):
        return None
    h, mi = map(int, str(s)[:5].split(":"))
    return time(h, mi)


def time_txt(s):
    t = to_time(s)
    return t.strftime("%I:%M %p").lstrip("0") if t else ""



def img_b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


@st.cache_data(show_spinner=False)
def logo_b64(name):
    return img_b64(os.path.join(HERE, "assets", name))


@st.cache_data(show_spinner=False)
def photo_b64(pid, ver):
    b = db.get_photo(pid)
    return base64.b64encode(b).decode() if b else None


def initials(name):
    return "".join(w[0].upper() for w in (name or "?").split()[:2])


def avatar_html(p, big=False):
    b = photo_b64(p["id"], st.session_state.get(f"photov_{p['id']}", 0)) if p.get("has_photo") else None
    inner = f"<img src='data:image/jpeg;base64,{b}'>" if b else initials(p["name"])
    return f"<div class='avatar{' big' if big else ''}'>{inner}</div>"


def lvl_pill(level):
    return f"<span class='pill lv-{level}'>{ax.LEVEL_TXT[level]}</span>"


def go(view=None, player=None):
    if view:
        st.session_state["nav"] = view
    st.session_state["player"] = player


players = db.load_players()
for _c in ("number", "position", "year", "bt", "throws_hand", "grp"):
    players[_c] = players[_c].fillna("").astype(str)
ASSESS = db.all_assess()
FLAGS = {pid: ax.compute_flags(a) for pid, a in ASSESS.items()}
PINCH_VALS = [float(a["pinch"]) for a in ASSESS.values() if a.get("pinch") not in (None, "")]
TEAM_PINCH = sum(PINCH_VALS) / len(PINCH_VALS) if PINCH_VALS else None

# ───────────────────────── sidebar ─────────────────────────
NAV = ["Team", "Pitchers", "Position Players"]
st.session_state.setdefault("nav", "Pitchers")
st.session_state.setdefault("player", None)
with st.sidebar:
    st.markdown(f"<div style='display:flex;gap:12px;align-items:center'><img src='data:image/png;base64,{logo_b64('ks_mark.png')}' "
                f"style='height:52px'><img src='data:image/png;base64,{logo_b64('powercat.png')}' style='height:46px'></div>",
                unsafe_allow_html=True)
    st.markdown("### Arm Care Command Center")
    st.radio("Go to", NAV, key="nav", on_change=lambda: st.session_state.update(player=None), label_visibility="collapsed")
    today = st.date_input("Today's date", value=chicago_today(), key="today", format="MM/DD/YYYY")
    st.caption("Everything you enter saves automatically.")
    st.divider()
    with st.expander("Import / backup"):
        up = st.file_uploader("ACWR throwing workbook (.xlsx)", type=["xlsx"], key="up_wb")
        if up is not None and st.button("Import workbook", type="primary"):
            n_p, n_r = db.import_workbook(io.BytesIO(up.getvalue()))
            toast(f"Imported velo for {n_p} players and {n_r} throw-log rows")
            st.rerun()
        upf = st.file_uploader("ForceDecks CMJ export (.csv)", type=["csv"], key="up_fd")
        if upf is not None and st.button("Import force-plate tests"):
            try:
                n, unmatched = db.import_force_csv(upf, players)
                toast(f"Imported {n} force-plate tests" + (f" · unmatched: {', '.join(unmatched)}" if unmatched else ""))
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if st.button("Prepare Excel backup"):
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                players.drop(columns=["active", "sort", "assess", "corrective", "corrective_history", "has_photo"],
                             errors="ignore").to_excel(xw, sheet_name="Roster", index=False)
                frames = []
                for p in players[players["grp"] == "pitcher"].to_dict("records"):
                    lg = calc_log(p["id"], none_if_nan(p["avg_top_velo"])).drop(columns=["id", "created"])
                    lg.insert(0, "player", p["name"])
                    frames.append(lg)
                (pd.concat(frames) if frames else pd.DataFrame()).to_excel(xw, sheet_name="Throw Log", index=False)
                pd.DataFrame([dict(player=players.set_index("id").loc[k, "name"], **v) for k, v in ASSESS.items()
                              if k in set(players["id"])]).to_excel(xw, sheet_name="Assessment", index=False)
                rows = []
                for p in players.to_dict("records"):
                    for e in db.get_corrective(p["id"]).get("exercises", []):
                        rows.append(dict(player=p["name"], **e))
                pd.DataFrame(rows).to_excel(xw, sheet_name="Correctives", index=False)
                db.load_force().to_excel(xw, sheet_name="Force Plate", index=False)
                db.load_library().to_excel(xw, sheet_name="Exercise Library", index=False)
            st.session_state["_backup"] = buf.getvalue()
        if st.session_state.get("_backup"):
            st.download_button("Download backup (.xlsx)", st.session_state["_backup"],
                               file_name=f"command_center_backup_{today.isoformat()}.xlsx", width="stretch")
    st.caption("Set Workload = Throws × Distance/Mound Factor × Intensity Factor. ACWR = 7-day avg ÷ 28-day avg. "
               "Assessment fields came from scanned intake forms; a flag means \"go verify the original form,\" not a diagnosis. "
               "Internal K-State Baseball sports medicine use only.")


# ═════════════════════════ THROW LOG ═════════════════════════
def ek(rid, f):
    return f"ed_{rid}_{f}"


EDIT_FIELDS = ["date", "session_type", "distance", "start_time", "end_time", "actual_throws", "velo_low", "velo_high",
               "warm_throws", "warm_velo_low", "warm_velo_high", "sixty_throws", "sixty_velo_low", "sixty_velo_high", "notes"]


def read_editor(rid, base: dict) -> dict:
    """Current editor values (only the widgets on screen) merged over the saved row."""
    rec = dict(base)
    for f in EDIT_FIELDS:
        k = ek(rid, f)
        if k in st.session_state:
            rec[f] = st.session_state[k]
    if st.session_state.get(ek(rid, "mode")) == "Time it":
        rec["actual_throws"] = None
    if rec.get("session_type") in m.MOUND_TYPES:
        rec["distance"] = None
    return rec


def save_editor(pid, rid):
    base = db.get_row(rid)
    if not base:
        return
    rec = read_editor(rid, base)
    db.update_row(rid, {f: rec.get(f) for f in EDIT_FIELDS})
    st.session_state[f"saved_{rid}"] = f"✓ Saved {stamp()}"


def new_session(pid, copy_from=None):
    rec = dict(copy_from or {"session_type": "Long Toss"})
    rec["date"] = st.session_state.get("today") or chicago_today()
    rec.pop("created", None)
    rid = db.add_row(pid, rec)
    st.session_state[f"edit_{pid}"] = rid
    st.session_state[f"saved_{rid}"] = "✓ New session created — fill it in, it saves as you go"
    st.session_state.pop(f"del_{pid}", None)


def close_editor(pid):
    st.session_state.pop(f"edit_{pid}", None)
    st.session_state.pop(f"del_{pid}", None)
    bump(f"logsel_{pid}")


def delete_session(pid, rid):
    db.delete_row(rid)
    close_editor(pid)
    toast("Session deleted")


def pick_row(pid, key, ids):
    rows = st.session_state[key].selection.rows
    if rows:
        st.session_state[f"edit_{pid}"] = ids[rows[0]]
        st.session_state.pop(f"del_{pid}", None)


def editor(p, avg):
    pid, rid = p["id"], st.session_state.get(f"edit_{p['id']}")
    r = db.get_row(rid) if rid else None
    if not r:
        return
    cb = dict(on_change=save_editor, args=(pid, rid))
    mound = r["session_type"] in m.MOUND_TYPES
    with st.container(border=True):
        h = st.columns([3, 2, 1, 1, 1], vertical_alignment="center")
        d = date.fromisoformat(r["date"]) if r.get("date") else None
        h[0].markdown(f"#### {d.strftime('%A, %b %-d') if d and os.name != 'nt' else (d.strftime('%A, %b %d') if d else 'New session')}")
        h[1].markdown(f"<span class='saved'>{st.session_state.get(f'saved_{rid}', '')}</span>", unsafe_allow_html=True)
        h[2].button("Copy as new", key=f"copy_{rid}", on_click=new_session, args=(pid, r), width="stretch")
        if st.session_state.get(f"del_{pid}"):
            h[3].button("Delete it", key=f"dely_{rid}", type="primary", on_click=delete_session, args=(pid, rid), width="stretch")
            h[4].button("Keep", key=f"deln_{rid}", on_click=lambda: st.session_state.pop(f"del_{pid}", None), width="stretch")
        else:
            h[3].button("Delete", key=f"del_{rid}", on_click=lambda: st.session_state.update({f"del_{pid}": True}), width="stretch")
            h[4].button("Done", key=f"done_{rid}", type="primary", on_click=close_editor, args=(pid,), width="stretch")

        c = st.columns([1.2, 1.6, 1.2, 2])
        c[0].date_input("Date", value=d, key=ek(rid, "date"), format="MM/DD/YYYY", **cb)
        c[1].selectbox("Session type", m.SESSION_TYPES, index=m.SESSION_TYPES.index(r["session_type"]) if r["session_type"] in m.SESSION_TYPES else 1,
                       key=ek(rid, "session_type"), **cb)
        stype = st.session_state.get(ek(rid, "session_type"), r["session_type"])
        mound, rest = stype in m.MOUND_TYPES, stype == "No Throw"
        if not rest:
            if mound:
                c[2].text_input("Distance", "Mound (60′6″)", disabled=True, key=ek(rid, "mound_note"),
                                help="Bullpen/Game use the flat Mound Factor instead of distance")
            else:
                c[2].number_input("Distance (ft)", 0, 400, none_if_nan(r["distance"]) and int(r["distance"]), 5,
                                  key=ek(rid, "distance"), placeholder="e.g. 120", **cb)
            default_mode = "Exact count" if (none_if_nan(r["actual_throws"]) is not None or (mound and not r["start_time"])) else "Time it"
            c[3].segmented_control("Throw count", ["Time it", "Exact count"], default=default_mode, required=True,
                                   key=ek(rid, "mode"), on_change=save_editor, args=(pid, rid),
                                   help="Time a group session (throws estimated from pace) or type the exact count")
            mode = st.session_state.get(ek(rid, "mode"), default_mode)
            c2 = st.columns(4)
            if mode == "Time it":
                c2[0].time_input("Start", value=to_time(r["start_time"]), key=ek(rid, "start_time"), step=60, **cb)
                c2[1].time_input("End", value=to_time(r["end_time"]), key=ek(rid, "end_time"), step=60, **cb)
            else:
                c2[0].number_input("Throws (live + in-game WU)" if stype == "Game" else "Actual throws", 0, 400,
                                   none_if_nan(r["actual_throws"]) and int(r["actual_throws"]), 1,
                                   key=ek(rid, "actual_throws"), placeholder="e.g. 25", **cb)
            c2[2].number_input("Velo low (mph)", 0.0, 110.0, none_if_nan(r["velo_low"]), 1.0, format="%.1f", key=ek(rid, "velo_low"), placeholder="e.g. 75", **cb)
            c2[3].number_input("Velo high (mph)", 0.0, 110.0, none_if_nan(r["velo_high"]), 1.0, format="%.1f", key=ek(rid, "velo_high"), placeholder="e.g. 81", **cb)
            e1, e2 = st.columns(2)
            with e1.expander("Pen warm-up before entering (game days)", expanded=stype == "Game" or none_if_nan(r["warm_throws"]) is not None):
                st.caption("Scored at the Bullpen Mound Factor.")
                w = st.columns(3)
                w[0].number_input("Throws", 0, 200, none_if_nan(r["warm_throws"]) and int(r["warm_throws"]), 1, key=ek(rid, "warm_throws"), **cb)
                w[1].number_input("Velo low", 0.0, 110.0, none_if_nan(r["warm_velo_low"]), 1.0, format="%.1f", key=ek(rid, "warm_velo_low"), **cb)
                w[2].number_input("Velo high", 0.0, 110.0, none_if_nan(r["warm_velo_high"]), 1.0, format="%.1f", key=ek(rid, "warm_velo_high"), **cb)
            with e2.expander("Finished working back in at 60′", expanded=none_if_nan(r["sixty_throws"]) is not None):
                st.caption("Same entry, scored at the 60 ft Distance Factor.")
                w = st.columns(3)
                w[0].number_input("Throws", 0, 200, none_if_nan(r["sixty_throws"]) and int(r["sixty_throws"]), 1, key=ek(rid, "sixty_throws"), **cb)
                w[1].number_input("Velo low", 0.0, 110.0, none_if_nan(r["sixty_velo_low"]), 1.0, format="%.1f", key=ek(rid, "sixty_velo_low"), **cb)
                w[2].number_input("Velo high", 0.0, 110.0, none_if_nan(r["sixty_velo_high"]), 1.0, format="%.1f", key=ek(rid, "sixty_velo_high"), **cb)
        else:
            st.caption("Rest day. It's saved so the day counts as zero in your log.")
        st.text_input("Notes (arm feel, RPE, etc.)", value=r["notes"] or "", key=ek(rid, "notes"), **cb)

        cur = read_editor(rid, r)
        if rest:
            st.markdown("<div class='preview'>Rest day: workload 0</div>", unsafe_allow_html=True)
        else:
            cc = m.calc_row(cur, avg)
            est = f" <span style='color:#666'>({fmt(cc['duration_min'], 0)} min)</span>" if cc["duration_min"] is not None and cur.get("actual_throws") is None else ""
            off = f" <span style='color:#666'>({fmt(cc['velo_deficit'])} mph off)</span>" if cc["velo_deficit"] is not None else ""
            hint = "" if cc["set_workload"] is not None else "<div style='flex-basis:100%;color:#666;font-size:.85rem'>Add throws (or start + end time) and velo to see the workload.</div>"
            st.markdown(f"""<div class='preview'>
              <div><span class='k'>Set Workload</span><span class='big'>{fmt(cc['set_workload'])}</span></div>
              <div><span class='k'>Throws</span><b>{fmt(cc['throws_used'], 0)}</b>{est}</div>
              <div><span class='k'>{'Mound' if mound else 'Distance'} factor</span><b>{fmt(cc['dist_mound_factor'])}</b></div>
              <div><span class='k'>Intensity factor</span><b>{fmt(cc['intensity_factor'])}</b>{off}</div>{hint}</div>""", unsafe_allow_html=True)


def throw_log_tab(p, avg):
    pid = p["id"]
    a, b = st.columns([1, 3], vertical_alignment="center")
    a.button("＋ Log a session", type="primary", on_click=new_session, args=(pid,), key=f"new_{pid}", width="stretch")
    b.caption("Everything saves automatically as you type: press Enter or click out of a box.")
    editor(p, avg)

    st.markdown("### My throw log")
    log = calc_log(pid, avg)
    if log.empty:
        st.info("No sessions logged yet. Tap **＋ Log a session** after you throw. Your workload, ACWR and plan fill in from here.")
    else:
        view = pd.DataFrame({
            "Date": log["date"], "Session Type": log["session_type"], "Set Workload": log["set_workload"],
            "Distance": [("Mound" if s in m.MOUND_TYPES else ("" if pd.isna(d) else f"{d:.0f}")) for s, d in zip(log["session_type"], log["distance"])],
            "Start": log["start_time"].map(time_txt), "End": log["end_time"].map(time_txt), "Throws Used": log["throws_used"],
            "Velo": [("" if pd.isna(lo) else f"{lo:g}" + ("" if pd.isna(hi) else f"–{hi:g}")) for lo, hi in zip(log["velo_low"], log["velo_high"])],
            "Deficit": log["velo_deficit"], "Dist/Mound F.": log["dist_mound_factor"], "Intensity F.": log["intensity_factor"],
            "Pen WU": log["warm_throws"], "60′": log["sixty_throws"], "Notes": log["notes"].fillna("")})
        ids = list(log["id"])
        key = f"logtable_{pid}_{st.session_state.get(f'logsel_{pid}', 0)}"
        st.dataframe(view, hide_index=True, width="stretch", height=min(520, 38 + 35 * len(view)),
                     on_select=partial(pick_row, pid, key, ids), selection_mode="single-row", key=key,
                     column_config={"Date": st.column_config.DateColumn(format="ddd MM/DD/YY"),
                                    "Set Workload": st.column_config.NumberColumn(format="%.1f"),
                                    "Throws Used": st.column_config.NumberColumn(format="%.0f"),
                                    "Deficit": st.column_config.NumberColumn(format="%.1f"),
                                    "Dist/Mound F.": st.column_config.NumberColumn(format="%.1f"),
                                    "Intensity F.": st.column_config.NumberColumn(format="%.1f"),
                                    "Pen WU": st.column_config.NumberColumn(format="%.0f"),
                                    "60′": st.column_config.NumberColumn(format="%.0f"),
                                    "Notes": st.column_config.TextColumn(width="large")})
        st.caption("Click a row (the box at its left edge) to edit it.")
    with st.expander("How to log (long toss, game days, 60′ finish)"):
        st.markdown("""
- **One entry per throwing set.** Long toss = two entries: *Long Toss* at the farthest distance working back, then *Compression/Pulldowns* at the working-in distance.
- **Time it or count it.** Start/End time estimates throws from pace (Long Toss 3/min, Compression 3/min, Moderate 3.5/min, Recovery 4.5/min). An exact count always overrides.
- **Bullpen / Game:** no distance. A flat Mound Factor is used (Bullpen 3.0, Game 3.2). Enter the exact pitch count.
- **Game day = one entry.** Throws = live pitches + in-game warm-ups (8 entering, +5 for each extra inning). Pen warm-ups before entering go in the *Pen warm-up* section.
- **Finished working back in at 60′?** Use the 60′ section on the same entry.
- **Velo:** enter a range, e.g. 70–74. The midpoint is compared to your Avg Top Velo to set intensity.""")


# ═════════════════════════ DASHBOARD ═════════════════════════
def dashboard_tab(p, avg, daily):
    as_of = st.date_input("As of date", value=today, key=f"asof_{p['id']}", format="MM/DD/YYYY")
    s = m.status(daily, as_of)
    c = st.columns(5)
    c[0].metric("Today's workload", fmt(s["today"]))
    c[1].metric("Acute · 7-day avg/day", fmt(s["acute"]))
    c[2].metric("Chronic · 28-day avg/day", fmt(s["chronic"]))
    c[3].metric("ACWR · acute ÷ chronic", fmt(s["acwr"], 2, "N/A"))
    c[4].metric("Spike · today ÷ chronic", fmt(s["spike"], 2, "N/A"))
    st.markdown(zone_box(s["zone"], s["guidance"]), unsafe_allow_html=True)
    if s["spike_flag"]:
        st.markdown(f"<div class='zone z-{'Sweet' if s['spike_flag'] == 'OK' else 'High'}'><b>Spike flag: {s['spike_flag']}</b></div>",
                    unsafe_allow_html=True)
    st.markdown("### 28-day trend")
    days = [as_of - timedelta(days=27 - i) for i in range(28)]
    trend = pd.DataFrame({"Day": [d.strftime("%m/%d") for d in days], "Weekday": [d.strftime("%a") for d in days],
                          "Daily Workload": [daily.get(d, 0.0) for d in days]})
    bars = alt.Chart(trend).mark_bar(color=DARK_GRAY, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Day:O", title=None, sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("Daily Workload:Q", title="Daily workload"),
        tooltip=["Weekday", "Day", alt.Tooltip("Daily Workload:Q", format=".1f")])
    lines = pd.DataFrame({"Line": [f"Acute (7d avg) {s['acute']:.1f}", f"Chronic (28d avg) {s['chronic']:.1f}"], "v": [s["acute"], s["chronic"]]})
    rules = alt.Chart(lines).mark_rule(strokeWidth=2.5).encode(
        y="v:Q", color=alt.Color("Line:N", scale=alt.Scale(range=[PURPLE, "#555555"]), legend=alt.Legend(title=None, orient="top")),
        strokeDash=alt.StrokeDash("Line:N", scale=alt.Scale(range=[[1, 0], [7, 5]]), legend=None))
    st.altair_chart((bars + rules).properties(height=300), width="stretch")


# ═════════════════════════ DAY TYPE TEMPLATES ═════════════════════════
def templates_tab(p, avg):
    st.caption(f"Velo targets shown for **{p['name']}**" + (f" (Avg Top Velo {fmt(avg)} mph)." if avg else " (set your Avg Top Velo to see mph targets).") +
               " Workloads come from distance and mph-deficit bands, so they're the same for every pitcher. Low, Medium and High "
               "Non-Bullpen days finish at 60 ft working all pitches; High Bullpen and Game days skip that finish.")
    rows = m.template_rows(avg or 0)
    plans = {}
    for r in rows:
        plans.setdefault((r["category"], r["example"]), []).append(m.segment_text(r, avg))
    summ = m.template_summary(avg)
    st.markdown("### Day type quick reference")
    st.dataframe(pd.DataFrame([{"Day Type": s["day_type"], "Avg Projected Workload": s["avg"],
                                "Example 1": "  +  ".join(plans[(s["day_type"], 1)]), "Ex 1": s["ex1"],
                                "Example 2": "  +  ".join(plans[(s["day_type"], 2)]), "Ex 2": s["ex2"]} for s in summ]),
                 hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="%.1f") for k in ("Avg Projected Workload", "Ex 1", "Ex 2")}
                 | {"Example 1": st.column_config.TextColumn(width="large"), "Example 2": st.column_config.TextColumn(width="large")})
    st.caption("Low Bullpen = low-intent mound work (feel pen, about 7–12 mph under Avg Top Velo). Same Mound Factor as any bullpen; "
               "the lower Intensity Factor keeps its workload near a Medium day.")
    st.markdown("### Segment detail")
    det = pd.DataFrame([{"Category": r["category"], "Ex": r["example"], "Seg": r["segment"], "Segment Type": r["segment_type"],
                         "Distance": "Mound" if r["distance"] is None else f"{r['distance']} ft",
                         "Throws": f"{r['throws_low']}–{r['throws_high']}", "Deficit (mph)": f"{r['deficit_low']}–{r['deficit_high']}",
                         "Velo (mph)": f"{r['velo_low']:.0f}–{r['velo_high']:.0f}" if avg else "—",
                         "Dist/Mound F.": r["factor"], "Intensity F.": r["intensity"], "Projected Workload": r["workload"]} for r in rows])
    st.dataframe(det, hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="%.1f") for k in ("Dist/Mound F.", "Intensity F.", "Projected Workload")})
    st.caption("Deficit = mph below Avg Top Velo: 0–3 max effort (×2.0), 4–6 compete (×1.5), 7–9 building (×1.0), 10+ easy/recovery (×0.6).")


# ═════════════════════════ NEXT OUTING PLANNER ═════════════════════════
def save_planner(pid):
    k = lambda f: st.session_state.get(f"pl_{pid}_{f}")
    fields = {"target_type": k("type"), "target_date": k("date")}
    if f"pl_{pid}_pitches" in st.session_state:
        fields["planned_pitches"] = k("pitches")
    if f"pl_{pid}_innings" in st.session_state:
        fields["planned_innings"] = k("innings")
    db.update_player(pid, **fields)
    st.session_state[f"plsaved_{pid}"] = f"✓ Saved {stamp()}"


def save_overrides(pid, key, dates):
    for i, ch in st.session_state[key]["edited_rows"].items():
        if "override" in ch:
            db.save_override(pid, dates[int(i)], ch["override"])
    st.session_state[f"plsaved_{pid}"] = f"✓ Override saved {stamp()}"
    bump(f"plv_{pid}")


def clear_all_overrides(pid):
    db.clear_overrides(pid)
    bump(f"plv_{pid}")
    st.session_state[f"plsaved_{pid}"] = "✓ Overrides cleared"


def planner_tab(p, avg, daily):
    pid = p["id"]
    cb = dict(on_change=save_planner, args=(pid,))
    c = st.columns([1.4, 1.2, 1, 1, 1.4], vertical_alignment="bottom")
    ttype = c[0].selectbox("Next high-intent day", m.HIGH_INTENT_TYPES, key=f"pl_{pid}_type",
                           index=m.HIGH_INTENT_TYPES.index(p["target_type"]) if p["target_type"] in m.HIGH_INTENT_TYPES else 0, **cb)
    tdate = c[1].date_input("Date", value=p["target_date"], key=f"pl_{pid}_date", format="MM/DD/YYYY", **cb)
    pitches, innings = p["planned_pitches"], p["planned_innings"]
    if ttype == "Game":
        pitches = c[2].number_input("Planned pitches", 0, 150, pitches and int(pitches), 1, key=f"pl_{pid}_pitches", placeholder="optional", **cb)
        innings = c[3].number_input("Planned innings", 0.0, 9.0, innings, 1.0, format="%.1f", key=f"pl_{pid}_innings", placeholder="optional", **cb)
    c[4].markdown(f"<span class='saved'>{st.session_state.get(f'plsaved_{pid}', '')}</span>", unsafe_allow_html=True)

    s = m.status(daily, today)
    za = m.zone_adjustment(s["zone"])
    st.markdown("### Current status, last 7 / last 28 days")
    cc = st.columns(4)
    cc[0].metric("Acute · 7-day", fmt(s["acute"]))
    cc[1].metric("Chronic · 28-day", fmt(s["chronic"]))
    cc[2].metric("ACWR", fmt(s["acwr"], 2, "N/A"))
    cc[3].metric("Zone adjustment", f"{za:+d}" if za else "0")
    st.markdown(zone_box(s["zone"], s["guidance"]), unsafe_allow_html=True)

    if not tdate:
        st.info("Pick the date of your next Game outing or High Bullpen day to build the plan.")
        return
    if tdate <= today:
        st.warning("That date is today or already past. Update it to your **next** outing or bullpen day and the whole plan regenerates.")
        return
    plan = m.build_plan(daily, today, tdate, za, db.load_overrides(pid), avg)
    st.markdown("### Quick glance")
    if plan:
        r0 = plan[0]
        st.markdown(f"<div class='plan'><b>Tomorrow, {r0['date']:%a %m/%d}: {r0['final']}</b><br>{r0['plan']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='plan'><b>Outing / bullpen day</b><br>{m.outing_text(ttype, tdate, avg, pitches, innings)}</div>",
                unsafe_allow_html=True)
    st.markdown("### This week's plan")
    if not plan:
        st.caption("Your High-Intent Day is tomorrow, so there are no days to plan in between.")
        return
    df = pd.DataFrame(plan)
    view = pd.DataFrame({"Date": df["date"], "Days until": df["days_until"], "Baseline": df["baseline"],
                         "Day type": df["final"], "override": df["override"], "Suggested plan (Example 1)": df["plan"]})
    key = f"plan_{pid}_{st.session_state.get(f'plv_{pid}', 0)}"
    st.data_editor(view, hide_index=True, width="stretch", key=key, on_change=save_overrides, args=(pid, key, list(df["date"])),
                   disabled=["Date", "Days until", "Baseline", "Day type", "Suggested plan (Example 1)"],
                   column_config={"Date": st.column_config.DateColumn(format="ddd MM/DD"),
                                  "override": st.column_config.SelectboxColumn("Manual override ✎", options=m.OVERRIDE_CHOICES, required=True,
                                                                               help="Pick a day type. It saves and every day after re-plans around it."),
                                  "Suggested plan (Example 1)": st.column_config.TextColumn(width="large")})
    a, b = st.columns([1, 3])
    a.button("Clear all overrides", key=f"clr_{pid}", on_click=clear_all_overrides, args=(pid,))
    if b.toggle("Show the math behind each day", key=f"math_{pid}"):
        st.dataframe(pd.DataFrame({"Date": df["date"], "Baseline tier": df["baseline_tier"], "Prior day type": df["prior_type"],
                                   "Prior planned": df["prior_planned"], "Prior actual": df["prior_actual"], "Actual/planned": df["ratio"],
                                   "Prior-day adj": df["prior_adj"], "Plan shift": df["plan_shift"], "Zone adj": df["zone_adj"],
                                   "Combined": df["combined"], "Clamped": df["clamped"], "Final tier": df["final_tier"]}),
                     hide_index=True, width="stretch",
                     column_config={"Date": st.column_config.DateColumn(format="ddd MM/DD"),
                                    "Prior planned": st.column_config.NumberColumn(format="%.1f"),
                                    "Prior actual": st.column_config.NumberColumn(format="%.1f"),
                                    "Actual/planned": st.column_config.NumberColumn(format="%.2f")})
    with st.expander("How the plan is built"):
        x, y = st.columns(2)
        x.dataframe(pd.DataFrame([{"Days until": k, "Default day type": v[0], "Why": v[1]} for k, v in m.TAPER_RULE.items()]), hide_index=True)
        y.dataframe(pd.DataFrame([{"(Days−6) mod 3": k, "Day type (6+ days out)": v[0], "Why": v[1]} for k, v in m.FAR_OUT_CYCLE.items()]), hide_index=True)
        st.markdown("""
- Each day starts from its baseline, then moves one tier (Low → Medium → High Non-Bullpen).
- **Prior-day plan shift:** if the day before ended harder or easier than its own baseline (for example from an override), that decides the adjustment on its own.
- Otherwise it takes the more conservative of: yesterday's actual logged workload vs. plan (more than 20% over = −1, more than 20% under = +1) and the zone (Caution/High Risk −1, Undertrained +1). A downgrade needs one signal; an upgrade needs both.
- The day before the high-intent day can only be downgraded. An upgrade out of Medium goes to High Non-Bullpen, never a bullpen.""")



# ═════════════════════════ DAILY THROWING LOG (pitcher file) ═════════════════════════
def save_avg(pid):
    db.update_player(pid, avg_top_velo=st.session_state.get(f"avg_{pid}"))
    toast("Avg Top Velo saved")


def throwing_section(p):
    pid, avg = p["id"], none_if_nan(p["avg_top_velo"])
    daily = daily_of(pid, avg)
    s = m.status(daily, today)
    with st.container(border=True):
        h = st.columns([1.5, 1.1, 1.1, 1.3, 1.6], vertical_alignment="center")
        h[0].number_input("Avg Top Velo (mph)", 40.0, 110.0, avg, 0.1, format="%.1f", key=f"avg_{pid}", placeholder="set this first",
                          on_change=save_avg, args=(pid,))
        h[1].metric("Today", fmt(s["today"]))
        h[2].metric("ACWR", fmt(s["acwr"], 2, "N/A"))
        h[3].markdown(f"<div style='font-size:.85rem;color:#666'>Zone</div>{pill(s['zone'])}", unsafe_allow_html=True)
        with h[4].popover("Throwing-log file", width="stretch"):
            throwing_file_box(pid)
    if not avg:
        st.warning("Enter the **Avg Top Velo** above (the average of his hardest, most competitive readings, not one peak). "
                   "Intensity and workload can't be calculated without it.")
    sub = st.segmented_control("Section", ["Throw Log", "Dashboard", "Day Type Templates", "Next Outing Planner"],
                               default="Throw Log", required=True, key="sub", label_visibility="collapsed")
    if sub == "Dashboard":
        dashboard_tab(p, avg, daily)
    elif sub == "Day Type Templates":
        templates_tab(p, avg)
    elif sub == "Next Outing Planner":
        planner_tab(p, avg, daily)
    else:
        throw_log_tab(p, avg)


def file_box(pid, kind, label, types):
    f = db.get_file(pid, kind)
    if f:
        st.markdown(f"**{f['name']}**")
        a, b = st.columns(2)
        a.download_button("Open / download", f["data"], file_name=f["name"], mime=f["mime"] or None,
                          key=f"dl_{kind}_{pid}", width="stretch")
        if b.button("Remove", key=f"rmf_{kind}_{pid}", width="stretch"):
            db.delete_file(pid, kind)
            toast("File removed")
            st.rerun()
    upl = st.file_uploader(("Replace" if f else "Attach") + f" {label}", type=types, key=f"upf_{kind}_{pid}_{st.session_state.get(f'fv_{pid}', 0)}")
    if upl is not None:
        db.save_file(pid, kind, upl.name, upl.type, upl.getvalue())
        bump(f"fv_{pid}")
        toast(f"Saved {upl.name}")
        st.rerun()
    return f


def throwing_file_box(pid):
    st.caption("Attach this pitcher's own throwing-log / ACWR workbook so it's on his file too.")
    file_box(pid, "throwlog", "workbook", ["xlsx", "xls", "csv", "pdf"])


# ═════════════════════════ PERFORMANCE METRICS (force plate) ═════════════════════════
FORCE_METRICS = [
    ("jumpHeightCm", "Jump height", "cm", 1, True,
     "Jump Height (Imp-Mom): from the velocity of the centre of mass at take-off and body mass."),
    ("peakPowerWkg", "Peak power", "W/kg", 1, True, "Highest power produced during the movement, divided by body mass."),
    ("rsiMod", "RSI-modified", "m/s", 2, True, "Jump height (from flight time) divided by contraction time."),
    ("concImpulseNs", "Concentric impulse", "N·s", 1, True, "Total net force applied from the start of the concentric phase to take-off."),
    ("eccAsymPct", "Eccentric force asymmetry", "%", 1, False, "Side-to-side difference in eccentric peak force, as a percentage."),
    ("cmDepth", "Countermovement depth", "cm", 1, False, "Distance moved down from the start position to the lowest point."),
    ("bwLb", "Body weight", "lb", 1, False, ""),
]
FM = {k: dict(label=l, unit=u, dec=d, rank=r, defn=df) for k, l, u, d, r, df in FORCE_METRICS}


@st.cache_data(show_spinner=False)
def force_df(_ver):
    df = db.load_force()
    if df.empty:
        return df
    df["cmDepth"] = df["cmDepthCm"].abs() if "cmDepthCm" in df else None
    return df[~df["excluded"]]


def force_view(df, day, window):
    """One row per athlete: the test on `day`, or the average of his tests over the last `window` test days."""
    dates = sorted(df["date"].unique())
    if window and window > 1:
        keep = [d for d in dates if d <= day][-window:]
        sub = df[df["date"].isin(keep)]
    else:
        sub = df[df["date"] == day]
    keys = [k for k in FM if k in sub]
    out = sub.groupby("playerId").agg({**{k: "mean" for k in keys}, "exportName": "first", "date": "max"}).reset_index()
    names = dict(zip(players["id"], players["name"]))
    grp = dict(zip(players["id"], players["grp"]))
    out["Player"] = [names.get(i, n + " (unmatched)") for i, n in zip(out["playerId"], out["exportName"])]
    out["Group"] = [("Pitcher" if grp.get(i) == "pitcher" else "Position") for i in out["playerId"]]
    return out


def team_force():
    df = force_df(st.session_state.get("forcev", 0))
    if df.empty:
        st.info("No force-plate tests yet. Import a ForceDecks CMJ export from **Sidebar ▸ Import / backup**.")
        return
    dates = sorted(df["date"].unique(), reverse=True)
    c = st.columns([1.3, 1.6, 1.4, 1.6])
    day = c[0].selectbox("Test day", dates, format_func=lambda d: datetime.fromisoformat(d).strftime("%a %b %-d, %Y"), key="fc_day")
    metric = c[1].selectbox("Metric", list(FM), format_func=lambda k: f"{FM[k]['label']} ({FM[k]['unit']})", key="fc_metric")
    window = c[2].selectbox("Window", [1, 3, 5], format_func=lambda w: "That day only" if w == 1 else f"Avg of last {w} test days", key="fc_win")
    who = c[3].segmented_control("Show", ["All", "Pitchers", "Position"], default="All", required=True, key="fc_who")
    v = force_view(df, day, window)
    if who != "All":
        v = v[v["Group"] == ("Pitcher" if who == "Pitchers" else "Position")]
    v = v.dropna(subset=[metric]).sort_values(metric, ascending=not FM[metric]["rank"] and metric != "eccAsymPct")
    if v.empty:
        st.info("No values for that metric on that day.")
        return
    mean = v[metric].mean()
    k = st.columns(4)
    k[0].metric("Athletes tested", len(v))
    k[1].metric(f"Team mean ({FM[metric]['unit']})", f"{mean:.{FM[metric]['dec']}f}")
    k[2].metric(f"Highest · {v.loc[v[metric].idxmax(), 'Player']}", f"{v[metric].max():.{FM[metric]['dec']}f}")
    k[3].metric(f"Lowest · {v.loc[v[metric].idxmin(), 'Player']}", f"{v[metric].min():.{FM[metric]['dec']}f}")
    if FM[metric]["defn"]:
        st.caption(f"**{FM[metric]['label']}** — {FM[metric]['defn']} (VALD ForceDecks)")
    order = list(v.sort_values(metric, ascending=False)["Player"])
    bars = alt.Chart(v).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
        y=alt.Y("Player:N", sort=order, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
        x=alt.X(f"{metric}:Q", title=f"{FM[metric]['label']} ({FM[metric]['unit']})"),
        color=alt.Color("Group:N", scale=alt.Scale(domain=["Pitcher", "Position"], range=[KSU, "#c9bfd9"]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=["Player", "Group", alt.Tooltip(f"{metric}:Q", format=f".{FM[metric]['dec']}f")])
    rule = alt.Chart(pd.DataFrame({"m": [mean]})).mark_rule(strokeDash=[4, 4], color="#555").encode(x="m:Q")
    st.altair_chart((bars + rule).properties(height=max(260, 26 * len(v))), width="stretch")
    st.caption("Dashed line = mean of the athletes shown.")

    with st.expander("Jump height vs. peak power (scatter)"):
        sc = alt.Chart(v.dropna(subset=["jumpHeightCm", "peakPowerWkg"])).mark_circle(size=90, opacity=.85).encode(
            x=alt.X("peakPowerWkg:Q", title="Peak power (W/kg)", scale=alt.Scale(zero=False)),
            y=alt.Y("jumpHeightCm:Q", title="Jump height (cm)", scale=alt.Scale(zero=False)),
            color=alt.Color("Group:N", scale=alt.Scale(domain=["Pitcher", "Position"], range=[KSU, "#b9aecb"]), legend=alt.Legend(title=None)),
            tooltip=["Player", alt.Tooltip("jumpHeightCm:Q", format=".1f"), alt.Tooltip("peakPowerWkg:Q", format=".1f")])
        st.altair_chart(sc.properties(height=380), width="stretch")

    tbl = v[["Player", "Group"] + [k for k in FM if k in v]].rename(columns={k: f"{FM[k]['label']} ({FM[k]['unit']})" for k in FM})
    labels = list(v["playerId"])
    key = f"fctbl_{st.session_state.get('fcsel', 0)}"
    st.dataframe(tbl, hide_index=True, width="stretch", key=key, selection_mode="single-row",
                 on_select=partial(open_from_table, key, labels, "fcsel"),
                 column_config={c_: st.column_config.NumberColumn(format="%.2f" if "RSI" in c_ else "%.1f") for c_ in tbl.columns[2:]})
    st.caption("Click a row to open that athlete's file.")
    st.download_button("Download this view (.csv)", tbl.to_csv(index=False).encode(), file_name=f"force_{day}_{metric}.csv")


def player_force(p):
    df = force_df(st.session_state.get("forcev", 0))
    mine = df[df["playerId"] == p["id"]].sort_values("date") if not df.empty else df
    if mine is None or mine.empty:
        st.info("No force-plate tests on file for this athlete yet.")
        return
    dates = sorted(mine["date"].unique(), reverse=True)
    day = st.selectbox("Test day", dates, format_func=lambda d: datetime.fromisoformat(d).strftime("%a %b %-d, %Y"), key=f"pfd_{p['id']}")
    team = force_view(df, day, 1)
    me = mine[mine["date"] == day].mean(numeric_only=True)
    prev_days = [d for d in dates if d < day]
    prev = mine[mine["date"] == prev_days[0]].mean(numeric_only=True) if prev_days else None
    cols = st.columns(3)
    for i, (k, f) in enumerate(FM.items()):
        val = me.get(k)
        if val is None or pd.isna(val):
            continue
        tv = team[k].dropna()
        rank = f"Rank {1 + int((tv > val).sum())} of {len(tv)} · " if f["rank"] and len(tv) else ""
        side = ""
        if k == "eccAsymPct":
            sides = mine[mine["date"] == day]["eccAsymSide"].dropna()
            side = f" {sides.iloc[0]}" if len(sides) else ""
        chg = ""
        if prev is not None and not pd.isna(prev.get(k)):
            d = val - prev[k]
            chg = f" · {'+' if d >= 0 else ''}{d:.{f['dec']}f} vs {datetime.fromisoformat(prev_days[0]):%m/%d}"
        cols[i % 3].markdown(f"<div class='fc-card'><div class='l'>{f['label']}</div><div class='v'>{val:.{f['dec']}f}"
                             f"<small>{f['unit']}{side}</small></div><div class='t'>{rank}Team mean {tv.mean():.{f['dec']}f}{chg}</div></div>",
                             unsafe_allow_html=True)
    st.markdown("### Trend")
    metric = st.segmented_control("Metric", [k for k in FM if k in mine], default="jumpHeightCm", required=True,
                                  format_func=lambda k: FM[k]["label"], key=f"pfm_{p['id']}")
    tr = mine.groupby("date")[metric].mean().reset_index()
    tr["Date"] = pd.to_datetime(tr["date"])
    tm = df.groupby("date")[metric].mean().reset_index()
    tm["Date"] = pd.to_datetime(tm["date"])
    line = alt.Chart(tr).mark_line(point=alt.OverlayMarkDef(size=70, color=KSU, filled=True), color=KSU, strokeWidth=2.5).encode(
        x=alt.X("Date:T", title=None), y=alt.Y(f"{metric}:Q", title=f"{FM[metric]['label']} ({FM[metric]['unit']})", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("Date:T", format="%b %d"), alt.Tooltip(f"{metric}:Q", format=f".{FM[metric]['dec']}f")])
    tline = alt.Chart(tm).mark_line(strokeDash=[5, 4], color="#888").encode(x="Date:T", y=f"{metric}:Q")
    st.altair_chart((tline + line).properties(height=280), width="stretch")
    st.caption("Purple = this athlete · dashed gray = team mean on each test day.")


# ═════════════════════════ PERFORMANCE ASSESSMENT ═════════════════════════
ROM_ROWS = [  # label, dom key, non key, diff key, diff formula
    ("External rotation", "domER", "nonER", "erDiff", lambda d, n: d - n),
    ("Internal rotation", "domIR", "nonIR", "irDiff", lambda d, n: n - d),
    ("Total rotational arc", "domArc", "nonArc", None, None),
    ("Supine flexion", "domFlex", "nonFlex", "flexDiff", lambda d, n: n - d),
    ("Elbow extension", "domElbowExt", "nonElbowExt", "elbowExtDiff", lambda d, n: n - d),
    ("Hip extension", "domHipExt", "nonHipExt", None, None),
]


def _num(v):
    try:
        return None if v is None or v == "" or (isinstance(v, float) and pd.isna(v)) else float(v)
    except (TypeError, ValueError):
        return None


def save_rom(pid, key):
    a = db.get_assess(pid)
    upd = {}
    for i, ch in st.session_state[key]["edited_rows"].items():
        label, dk, nk, diffk, fn = ROM_ROWS[int(i)]
        if "Dominant" in ch:
            upd[dk] = _num(ch["Dominant"])
        if "Non-dominant" in ch:
            upd[nk] = _num(ch["Non-dominant"])
        if diffk and "Difference" in ch:
            upd[diffk] = _num(ch["Difference"])
        elif diffk and ("Dominant" in ch or "Non-dominant" in ch):
            d, n = upd.get(dk, _num(a.get(dk))), upd.get(nk, _num(a.get(nk)))
            upd[diffk] = fn(d, n) if d is not None and n is not None else None
    db.update_assess(pid, **upd)
    st.session_state[f"asaved_{pid}"] = f"✓ Saved {stamp()}"
    bump(f"romv_{pid}")


def save_assess_field(pid, field, key):
    v = st.session_state.get(key)
    if field in ("domGrip", "nonGrip", "pinch"):
        v = _num(v)
    if field in ("oh", "trunk"):
        v = None if v in (None, "—") else int(v)
    if field == "tspineRotFail":
        v = {"Pass": "none", "Fail — R": "R", "Fail — L": "L", "Fail — both": "both"}.get(v, "none")
    if field == "tspineExtFail":
        v = v == "Fail"
    db.update_assess(pid, **{field: v})
    st.session_state[f"asaved_{pid}"] = f"✓ Saved {stamp()}"


def assessment_section(p):
    pid = p["id"]
    a = db.get_assess(pid)
    flags = ax.compute_flags(a)
    relevant = [f for f in flags if f["cat"] in ax.CONCERN_CATS]
    left, right = st.columns([1, 1.9], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### Body map")
            st.markdown(f"<div class='bm-wrap'><div><div class='lbl'>Front</div>{ax.body_map_svg(flags)}</div>"
                        f"<div><div class='lbl'>Back</div>{ax.back_map_svg(flags)}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<span class='legend-dot' style='background:{ax.HIGH}'></span>High &nbsp; "
                        f"<span class='legend-dot' style='background:{ax.MID}'></span>Monitor &nbsp; "
                        f"<span class='legend-dot' style='background:{ax.BASE};border:1px solid #ccc'></span>Clear",
                        unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### Assessment note")
            k = f"note_{pid}"
            st.text_area("Note", a.get("note") or "", key=k, height=110, label_visibility="collapsed",
                         placeholder="Injury history, surgical notes, screening observations…",
                         on_change=save_assess_field, args=(pid, "note", k))
            st.caption("Notes mentioning Tommy John / FAI / surgery or scap winging raise their own flags.")
        with st.container(border=True):
            st.markdown("#### Grading criteria")
            for lbl, txt in ax.GRADING_CRITERIA:
                st.markdown(f"<div class='crit'><b>{lbl}</b>{txt}</div>", unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            h = st.columns([3, 1.2])
            h[0].markdown("#### Flags")
            h[1].markdown(f"<span class='saved'>{st.session_state.get(f'asaved_{pid}', '')}</span>", unsafe_allow_html=True)
            if relevant or any(f["cat"] == "history" for f in flags):
                st.markdown("".join(f"<span class='flag lv-{f['level']}'>{f['label']}</span>" for f in flags), unsafe_allow_html=True)
            else:
                st.caption("No flags in the mapped criteria.")
        with st.container(border=True):
            st.markdown("#### Range of motion — dominant vs. non-dominant")
            rom = pd.DataFrame([{"Measure": lbl, "Dominant": _num(a.get(dk)), "Non-dominant": _num(a.get(nk)),
                                 "Difference": _num(a.get(diffk)) if diffk else None} for lbl, dk, nk, diffk, _ in ROM_ROWS])
            key = f"rom_{pid}_{st.session_state.get(f'romv_{pid}', 0)}"
            st.data_editor(rom, hide_index=True, width="stretch", key=key, on_change=save_rom, args=(pid, key),
                           disabled=["Measure"],
                           column_config={"Dominant": st.column_config.NumberColumn("Dominant ✎", format="%g°"),
                                          "Non-dominant": st.column_config.NumberColumn("Non-dominant ✎", format="%g°"),
                                          "Difference": st.column_config.NumberColumn(
                                              "Difference ✎", format="%g°",
                                              help="ER: dom − non · IR, flexion, elbow ext: non − dom. Recalculated when you change a side; "
                                                   "type over it to keep the value from the intake form.")})
            st.caption("Edits save as soon as you leave the cell. Differences come from the intake form; changing either side recalculates them.")
        with st.container(border=True):
            st.markdown("#### Grip & pinch strength")
            g = st.columns(3)
            for col, (fld, lbl) in zip(g, (("domGrip", "Grip — dominant (lb)"), ("nonGrip", "Grip — non-dom. (lb)"), ("pinch", "Pinch grip (lb)"))):
                k = f"{fld}_{pid}"
                col.number_input(lbl, 0.0, 400.0, _num(a.get(fld)), 1.0, format="%g", key=k,
                                 on_change=save_assess_field, args=(pid, fld, k))
            st.markdown(f"**Grip vs. MLB average:** {ax.grip_text(_num(a.get('domGrip')))} &nbsp;·&nbsp; "
                        f"**Pinch vs. team:** {ax.pinch_text(_num(a.get('pinch')), TEAM_PINCH)}")
            st.caption(f"MLB grip reference {ax.MLB_GRIP_AVG_LB} ± {ax.MLB_GRIP_AVG_SD_LB} lb ({ax.MLB_GRIP_SOURCE}) — a population "
                       f"reference, not an injury cutoff. Pinch compared with this roster's own average "
                       f"({fmt(TEAM_PINCH)} lb, n={len(PINCH_VALS)}).")
        with st.container(border=True):
            st.markdown("#### Screens")
            s = st.columns(3)
            k = f"tse_{pid}"
            s[0].selectbox("T-spine extension", ["Pass", "Fail"], index=1 if a.get("tspineExtFail") else 0, key=k,
                           on_change=save_assess_field, args=(pid, "tspineExtFail", k))
            rot_opts = ["Pass", "Fail — R", "Fail — L", "Fail — both"]
            cur = {"none": 0, "R": 1, "L": 2, "both": 3}.get(a.get("tspineRotFail") or "none", 0)
            k = f"tsr_{pid}"
            s[1].selectbox("T-spine rotation", rot_opts, index=cur, key=k, on_change=save_assess_field, args=(pid, "tspineRotFail", k))
            score = ["—", 1, 0, -1]
            for col, fld, lbl in ((s[2], "oh", "Overhead squat"),):
                k = f"{fld}_{pid}"
                v = a.get(fld)
                col.selectbox(lbl, score, index=score.index(int(v)) if v in (1, 0, -1) else 0, key=k,
                              on_change=save_assess_field, args=(pid, fld, k))
            s2 = st.columns(3)
            for col, fld, lbl in ((s2[0], "idb", "Inline dying bug (R/L)"), (s2[1], "sls", "Single-leg squat (R/L)")):
                k = f"{fld}_{pid}"
                col.text_input(lbl, a.get(fld) or "", key=k, placeholder="e.g. R1/L0", on_change=save_assess_field, args=(pid, fld, k))
            k = f"trunk_{pid}"
            v = a.get("trunk")
            s2[2].selectbox("Trunk stability push-up", score, index=score.index(int(v)) if v in (1, 0, -1) else 0, key=k,
                            on_change=save_assess_field, args=(pid, "trunk", k))
            st.caption("Task scale: 1 = performs well · 0 = assistance required · -1 = unable to perform.")
        if a.get("sourceBatch"):
            st.caption(f"Source: {a['sourceBatch']}")


# ═════════════════════════ CORRECTIVES ═════════════════════════
@st.cache_data(show_spinner=False)
def library(_ver):
    return db.load_library()


def save_program(pid, key):
    ed = st.session_state[key]
    cur = db.get_corrective(pid)
    ex = list(cur.get("exercises", []))
    for i, ch in ed["edited_rows"].items():
        i = int(i)
        if i < len(ex):
            ex[i] = {**ex[i], **{c: ("" if v is None else v) for c, v in ch.items()}}
    for row in ed["added_rows"]:
        ex.append({c: ("" if row.get(c) is None else row.get(c)) for c in ("name", "sets", "reps", "cues", "videoUrl")})
    for i in sorted(ed["deleted_rows"], reverse=True):
        if int(i) < len(ex):
            ex.pop(int(i))
    lib = {r["name"].lower(): r["video_url"] for r in library(st.session_state.get("libv", 0)).to_dict("records")}
    for e in ex:  # fill a blank video link from the library, like the Command Center's autofill
        if e.get("name") and not e.get("videoUrl") and lib.get(e["name"].strip().lower()):
            e["videoUrl"] = lib[e["name"].strip().lower()]
    cur["exercises"] = [e for e in ex if any(str(e.get(c) or "").strip() for c in ("name", "sets", "reps", "cues", "videoUrl"))]
    if not cur.get("startedAt"):
        cur["startedAt"] = datetime.utcnow().isoformat()
    db.save_corrective(pid, cur)
    st.session_state[f"csaved_{pid}"] = f"✓ Saved {stamp()}"
    bump(f"progv_{pid}")


def save_program_notes(pid, key):
    cur = db.get_corrective(pid)
    cur["notes"] = st.session_state.get(key) or ""
    db.save_corrective(pid, cur)
    st.session_state[f"csaved_{pid}"] = f"✓ Saved {stamp()}"


def add_from_library(pid, key):
    names = st.session_state.get(key) or []
    if not names:
        return
    lib = {r["name"]: r["video_url"] for r in library(st.session_state.get("libv", 0)).to_dict("records")}
    cur = db.get_corrective(pid)
    for n in names:
        cur["exercises"].append({"name": n, "sets": "", "reps": "", "cues": "", "videoUrl": lib.get(n, "")})
    if not cur.get("startedAt"):
        cur["startedAt"] = datetime.utcnow().isoformat()
    db.save_corrective(pid, cur)
    st.session_state[key] = []
    st.session_state[f"csaved_{pid}"] = f"✓ Added {len(names)} exercise{'s' if len(names) > 1 else ''}"
    bump(f"progv_{pid}")


def fmt_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "")).strftime("%b %-d, %Y")
    except (TypeError, ValueError):
        return ""


def correctives_section(p):
    pid = p["id"]
    cur = db.get_corrective(pid)
    h = st.columns([3, 1.3])
    h[0].markdown("#### Corrective exercise program" + (f" · since {fmt_iso(cur['startedAt'])}" if cur.get("startedAt") else ""))
    h[1].markdown(f"<span class='saved'>{st.session_state.get(f'csaved_{pid}', '')}</span>", unsafe_allow_html=True)
    with st.expander("Program file (PDF, image or video of the full program)", expanded=db.get_file(pid, "program") is not None):
        f = file_box(pid, "program", "program file", ["pdf", "png", "jpg", "jpeg", "mp4", "mov"])
        if f and (f["mime"] or "").startswith("image"):
            st.image(f["data"])
        elif f and (f["mime"] or "").startswith("video"):
            st.video(f["data"])
        elif f and (f["name"] or "").lower().endswith(".pdf") and hasattr(st, "pdf"):
            if st.toggle("Preview PDF", key=f"pdfprev_{pid}"):
                try:
                    st.pdf(f["data"], height=640)
                except Exception:
                    st.caption("PDF preview needs `pip install streamlit[pdf]`; use Open / download.")
    ex = pd.DataFrame(cur.get("exercises", []), columns=["name", "sets", "reps", "cues", "videoUrl"]).fillna("")
    key = f"prog_{pid}_{st.session_state.get(f'progv_{pid}', 0)}"
    st.data_editor(ex, hide_index=True, width="stretch", num_rows="dynamic", key=key, on_change=save_program, args=(pid, key),
                   column_config={"name": st.column_config.TextColumn("Exercise ✎", width="large"),
                                  "sets": st.column_config.TextColumn("Sets ✎", width="small"),
                                  "reps": st.column_config.TextColumn("Reps/Time ✎"),
                                  "cues": st.column_config.TextColumn("Notes / cues ✎", width="medium"),
                                  "videoUrl": st.column_config.LinkColumn("Video ✎", display_text="▶ watch", width="small")})
    st.caption("Add a row at the bottom, edit any cell, or select rows and press Delete. A blank video link fills from the library when the name matches.")
    lib = library(st.session_state.get("libv", 0))
    a, b = st.columns([3, 1], vertical_alignment="bottom")
    lk = f"libpick_{pid}"
    a.multiselect("Add from the exercise library", list(lib["name"]), key=lk, placeholder=f"Search {len(lib)} exercises…")
    b.button("Add to program", key=f"libadd_{pid}", on_click=add_from_library, args=(pid, lk), width="stretch")
    nk = f"pnotes_{pid}"
    st.text_area("Program notes", cur.get("notes") or "", key=nk, placeholder="General cueing, precautions, physician restrictions…",
                 on_change=save_program_notes, args=(pid, nk))
    hist = db.get_corrective_history(pid)
    c = st.columns([1.2, 1.4, 3])
    if st.session_state.get(f"newprog_{pid}"):
        if c[0].button("Archive & start new", type="primary", key=f"npy_{pid}"):
            db.start_new_program(pid)
            st.session_state.pop(f"newprog_{pid}", None)
            bump(f"progv_{pid}")
            toast("Program archived — new program started")
            st.rerun()
        if c[1].button("Keep current", key=f"npn_{pid}"):
            st.session_state.pop(f"newprog_{pid}", None)
            st.rerun()
    elif c[0].button("Start new program", key=f"np_{pid}"):
        st.session_state[f"newprog_{pid}"] = True
        st.rerun()
    with st.expander(f"Program history ({len(hist)})"):
        if not hist:
            st.caption("No archived programs yet. **Start new program** archives the current one here.")
        for h_ in hist:
            st.markdown(f"**{fmt_iso(h_.get('startedAt')) or '—'} → {fmt_iso(h_.get('archivedAt')) or '—'}**")
            st.markdown("\n".join(f"- {e.get('name')} — {e.get('sets') or ''}{' × ' if e.get('sets') and e.get('reps') else ''}{e.get('reps') or ''}"
                                  for e in h_.get("exercises", [])) or "_no exercises_")
            if h_.get("notes"):
                st.caption(h_["notes"])
    with st.expander("Manage exercise library"):
        library_manager(lib)


def save_lib(key, ids):
    ed = st.session_state[key]
    cur = library(st.session_state.get("libv", 0))
    for i, ch in ed["edited_rows"].items():
        r = cur.iloc[int(i)]
        name, url = ch.get("name", r["name"]), ch.get("video_url", r["video_url"])
        if name != r["name"]:
            db.delete_library_item(r["id"])
        db.save_library_item(name, url)
    for row in ed["added_rows"]:
        db.save_library_item(row.get("name") or "", row.get("video_url") or "")
    for i in ed["deleted_rows"]:
        db.delete_library_item(ids[int(i)])
    bump("libv")
    library.clear()
    toast("Library saved")


def library_manager(lib):
    key = f"lib_{st.session_state.get('libv', 0)}"
    st.data_editor(lib[["name", "video_url"]], hide_index=True, width="stretch", num_rows="dynamic", key=key, height=360,
                   on_change=save_lib, args=(key, list(lib["id"])),
                   column_config={"name": st.column_config.TextColumn("Exercise ✎", width="large"),
                                  "video_url": st.column_config.LinkColumn("Video link ✎", display_text="▶ watch")})
    st.caption(f"{len(lib)} exercises shared by every athlete's program. Edits save when you leave the cell.")


# ═════════════════════════ PLAYER FILE ═════════════════════════
def save_photo(pid, key):
    upl = st.session_state.get(key)
    if upl is None:
        return
    from PIL import Image
    im = Image.open(io.BytesIO(upl.getvalue())).convert("RGB")
    im.thumbnail((480, 480))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    db.update_player(pid, photo=buf.getvalue())
    bump(f"photov_{pid}")
    toast("Photo saved")


def save_profile(pid, field, key):
    db.update_player(pid, **{field: st.session_state.get(key)})
    toast("Saved")


def player_file(p):
    pid = p["id"]
    pitcher = p["grp"] == "pitcher"
    flags = FLAGS.get(pid, [])
    n = ax.concern_count(flags)
    back = "Team" if st.session_state.get("from_team") else ("Pitchers" if pitcher else "Position Players")
    st.button(f"← Back to {back.lower() if back != 'Team' else 'team'}", on_click=go, args=(back, None))
    with st.container(border=True):
        h = st.columns([0.9, 0.7, 3, 1.6, 1.3], vertical_alignment="center")
        h[0].markdown(avatar_html(p, big=True), unsafe_allow_html=True)
        h[1].markdown(f"<div class='jersey'>{p['number'] or '–'}</div>", unsafe_allow_html=True)
        meta = " · ".join(x for x in (p.get("position"), p.get("year"), p.get("bt") or (f"Throws {p['throws_hand']}" if p.get("throws_hand") else None)) if x)
        h[2].markdown(f"<div class='pname'>{p['name']}</div><span class='pmeta'>{meta} · {n} area{'s' if n != 1 else ''} of concern</span>",
                      unsafe_allow_html=True)
        h[3].markdown(f"<div style='font-size:.85rem;color:#666'>Assessment</div>{lvl_pill(ax.overall_level(flags))}", unsafe_allow_html=True)
        with h[4].popover("Edit profile", width="stretch"):
            k = f"photo_{pid}_{st.session_state.get(f'photov_{pid}', 0)}"
            st.file_uploader("Photo", type=["jpg", "jpeg", "png", "heic", "webp"], key=k, on_change=save_photo, args=(pid, k))
            for fld, lbl in (("name", "Name"), ("number", "Jersey #"), ("position", "Position"), ("year", "Year"), ("bt", "Bats/Throws")):
                k = f"pf_{fld}_{pid}"
                st.text_input(lbl, p.get(fld) or "", key=k, on_change=save_profile, args=(pid, fld, k))
            k = f"pf_grp_{pid}"
            st.selectbox("Group", ["pitcher", "position"], index=0 if pitcher else 1, key=k, on_change=save_profile, args=(pid, "grp", k),
                         format_func=lambda g: "Pitcher (has a Daily Throwing Log)" if g == "pitcher" else "Position player")
            st.divider()
            if st.session_state.get(f"rmconf_{pid}"):
                st.warning(f"Remove {p['name']} from the roster? His file and throw log are kept and come back if he's re-added.")
                x, y = st.columns(2)
                if x.button("Remove", type="primary", key=f"rmy_{pid}"):
                    db.remove_player(pid)
                    go(back, None)
                    toast(f"Removed {p['name']}")
                    st.rerun()
                if y.button("Keep", key=f"rmn_{pid}"):
                    st.session_state.pop(f"rmconf_{pid}", None)
                    st.rerun()
            elif st.button("Remove from roster", key=f"rm_{pid}"):
                st.session_state[f"rmconf_{pid}"] = True
                st.rerun()
    tabs = (["Daily Throwing Log"] if pitcher else []) + ["Performance Metrics", "Performance Assessment", "Correctives"]
    if st.session_state.get("pdtab") not in tabs:
        st.session_state["pdtab"] = tabs[0]
    tab = st.segmented_control("File section", tabs, required=True, key="pdtab", label_visibility="collapsed")
    if tab == "Daily Throwing Log":
        throwing_section(p)
    elif tab == "Performance Metrics":
        player_force(p)
    elif tab == "Performance Assessment":
        assessment_section(p)
    else:
        correctives_section(p)


# ═════════════════════════ ROSTER GRIDS ═════════════════════════
def open_player(pid, from_team=False):
    st.session_state["player"] = pid
    st.session_state["from_team"] = from_team


def open_from_table(key, ids, counter):
    rows = st.session_state[key].selection.rows
    if rows and not str(ids[rows[0]]).startswith("unmatched"):
        open_player(ids[rows[0]], from_team=st.session_state.get("nav") == "Team")
        bump(counter)


def zone_cache():
    out = {}
    for p in players[players["grp"] == "pitcher"].to_dict("records"):
        out[p["id"]] = m.status(daily_of(p["id"], none_if_nan(p["avg_top_velo"])), today)
    return out


def tile_grid(lst, key, from_team=False, zones=None):
    c = st.columns([3, 1.3])
    q = c[0].text_input("Search", key=f"q_{key}", placeholder="Search by name or position…", label_visibility="collapsed")
    sort = c[1].selectbox("Sort", ["Name (A–Z)", "Highest risk first", "Position"], key=f"s_{key}", label_visibility="collapsed")
    if q.strip():
        ql = q.strip().lower()
        lst = [p for p in lst if ql in p["name"].lower() or ql in (p.get("position") or "").lower()]
    rank = {"high": 0, "mid": 1, "ok": 2}
    if sort == "Highest risk first":
        lst.sort(key=lambda p: (-ax.concern_count(FLAGS.get(p["id"], [])), rank[ax.overall_level(FLAGS.get(p["id"], []))], p["name"]))
    elif sort == "Position":
        lst.sort(key=lambda p: ((p.get("position") or ""), p["name"]))
    else:
        lst.sort(key=lambda p: p["name"])
    ncol = 6
    for i in range(0, len(lst), ncol):
        cols = st.columns(ncol)
        for col, p in zip(cols, lst[i:i + ncol]):
            fl = FLAGS.get(p["id"], [])
            with col.container(border=True):
                meta = " · ".join(x for x in (f"#{p['number']}" if p.get("number") else None, p.get("position")) if x)
                zp = ""
                if zones and p["id"] in zones:
                    z = zones[p["id"]]["zone"]
                    zp = " " + pill(z) if not z.startswith("Insufficient") else ""
                st.markdown(f"{avatar_html(p)}<div class='tile-name'>{p['name']}</div><div class='tile-meta'>{meta or '—'}</div>"
                            f"<div class='tile-pills'>{lvl_pill(ax.overall_level(fl))}{zp}</div>", unsafe_allow_html=True)
                st.button("Open file", key=f"open_{key}_{p['id']}", on_click=open_player, args=(p["id"], from_team), width="stretch")
    if not lst:
        st.caption("No athletes match.")


def roster_page(group):
    pitcher = group == "pitcher"
    hero("Pitchers" if pitcher else "Position Players")
    lst = [p for p in players.to_dict("records") if (p["grp"] == "pitcher") == pitcher]
    tile_grid(lst, group, zones=zone_cache() if pitcher else None)
    with st.expander("＋ Add player"):
        with st.form(f"add_{group}", clear_on_submit=True, border=False):
            f = st.columns([1, 2.4, 1.2, 1.4])
            num = f[0].text_input("Jersey #")
            name = f[1].text_input("Name")
            pos = f[2].text_input("Position", "RHP" if pitcher else "")
            avg = f[3].number_input("Avg Top Velo", 40.0, 110.0, None, 0.1, format="%.1f") if pitcher else None
            if st.form_submit_button("Add player", type="primary"):
                if name.strip():
                    db.add_player(name, num.strip(), pos.strip(), avg_top=avg, grp=group)
                    toast(f"Added {name.strip()}")
                    st.rerun()
                else:
                    st.error("Type a name first.")


def hero(sub):
    st.markdown(f"""<div class='cc-hero'><img src='data:image/png;base64,{logo_b64("ks_mark.png")}'>
      <div><div class='eyebrow'>K-State Baseball · Sports Medicine</div><h1>Arm Care Command Center</h1>
      <div class='sub'>{sub} · Touch a player to open their file.</div></div></div>""", unsafe_allow_html=True)


# ═════════════════════════ TEAM ═════════════════════════
def save_roster(key, ids):
    for i, ch in st.session_state[key]["edited_rows"].items():
        fields = {}
        for col, f in (("#", "number"), ("Position", "position"), ("Avg Top Velo", "avg_top_velo"), ("Peak Velo", "peak_velo")):
            if col in ch:
                fields[f] = ch[col]
        db.update_player(ids[int(i)], **fields)
    toast("Roster saved")


def team_throwing():
    pit = players[players["grp"] == "pitcher"]
    st.markdown(f"### Staff throwing overview · {today:%A, %b %d}")
    rows = []
    for p in pit.to_dict("records"):
        avg = none_if_nan(p["avg_top_velo"])
        daily = daily_of(p["id"], avg)
        s = m.status(daily, today)
        nxt = tmr = "—"
        td = p["target_date"] if isinstance(p["target_date"], date) else None
        if td and td > today:
            nxt = f"{p['target_type'] or 'Game'} · {td:%a %m/%d}"
            plan = m.build_plan(daily, today, td, m.zone_adjustment(s["zone"]), db.load_overrides(p["id"]), avg)
            tmr = plan[0]["final"] if plan else (p["target_type"] or "Game")
        zone = zshort(s["zone"])
        rows.append({"#": p["number"], "Player": p["name"], "Pos": p["position"], "Avg Top Velo": avg,
                     "Sessions": len(db.load_log(p["id"])), "Today": s["today"], "ACWR": s["acwr"],
                     "Zone": {"Sweet Spot": "🟢 ", "Caution": "🟡 ", "High Risk": "🔴 ", "Undertrained": "🔵 "}.get(zone, "⚪ ") + zone,
                     "Spike": "🔴 Spike" if s["spike_flag"] not in ("", "OK") else (s["spike_flag"] or "—"),
                     "Next high-intent day": nxt, "Tomorrow": tmr})
    ids = list(pit["id"])
    key = f"team_{st.session_state.get('teamsel', 0)}"
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=38 + 35 * len(rows), key=key,
                 on_select=partial(open_from_table, key, ids, "teamsel"), selection_mode="single-row",
                 column_config={"Avg Top Velo": st.column_config.NumberColumn(format="%.1f"),
                                "Today": st.column_config.NumberColumn(format="%.1f"),
                                "ACWR": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Click a pitcher's row to open his file.")
    st.markdown("### Pitching staff velo")
    st.caption("**Avg Top Velo** drives the Intensity Factor: the average of several of his hardest, most competitive readings, "
               "not a single peak. Peak Velo is reference only. Edits save as soon as you leave the cell.")
    ros = pd.DataFrame({"#": pit["number"], "Name": pit["name"], "Position": pit["position"],
                        "Avg Top Velo": pit["avg_top_velo"], "Peak Velo": pit["peak_velo"]})
    rkey = f"roster_{st.session_state.get('rosv', 0)}"
    st.data_editor(ros, hide_index=True, width="stretch", key=rkey, on_change=save_roster, args=(rkey, ids),
                   disabled=["Name"], column_config={
                       "Avg Top Velo": st.column_config.NumberColumn("Avg Top Velo ✎", format="%.1f", min_value=40, max_value=110),
                       "Peak Velo": st.column_config.NumberColumn("Peak Velo ✎", format="%.1f", min_value=40, max_value=110),
                       "#": st.column_config.TextColumn("# ✎"), "Position": st.column_config.TextColumn("Position ✎")})


def team_assessment():
    cats = ax.CATEGORIES
    plist = players.to_dict("records")
    counts = {k: sum(1 for p in plist if any(f["cat"] == k for f in FLAGS.get(p["id"], []))) for k, _, _ in cats}
    cat = st.segmented_control("Region", [k for k, _, _ in cats], default="shoulder", required=True, key="region",
                               format_func=lambda k: f"{dict((c[0], c[1]) for c in cats)[k]} · {counts[k]}")
    st.markdown(f"<div class='crit'><b>{dict((c[0], c[1]) for c in cats)[cat]} criteria</b>{dict((c[0], c[2]) for c in cats)[cat]}</div>",
                unsafe_allow_html=True)
    rows, ids = [], []
    order = {"high": 0, "mid": 1, "ok": 2}
    for p in plist:
        a, fl = ASSESS.get(p["id"], {}), FLAGS.get(p["id"], [])
        cf = [f for f in fl if f["cat"] == cat]
        lv = ax.region_severity(fl, cat)
        r = {"Athlete": p["name"], "Pos": p.get("position") or "", "Throws": p.get("throws_hand") or ""}
        g = lambda k: _num(a.get(k))
        if cat == "shoulder":
            r.update({"ER diff": g("erDiff"), "IR diff": g("irDiff"), "Flex diff": g("flexDiff"),
                      "Dom / Non arc": f"{a.get('domArc') if a.get('domArc') is not None else '—'} / {a.get('nonArc') if a.get('nonArc') is not None else '—'}"})
        elif cat == "elbow":
            r.update({"Elbow ext diff": g("elbowExtDiff")})
        elif cat == "hip":
            r.update({"Dom hip ext": g("domHipExt")})
        else:
            rot = a.get("tspineRotFail") or "none"
            r.update({"T-spine ext": "Fail" if a.get("tspineExtFail") else "Pass",
                      "T-spine rot": "Pass" if rot == "none" else ("Fail (both)" if rot == "both" else f"Fail ({rot})"),
                      "IDB": a.get("idb") or "—", "SLS": a.get("sls") or "—", "OH squat": g("oh"), "Trunk stab.": g("trunk")})
        r.update({"Status": {"high": "🟣 High", "mid": "🟪 Monitor", "ok": "⚪ Clear"}[lv], "Flags": "; ".join(f["label"] for f in cf) or "—",
                  "_o": order[lv]})
        rows.append(r)
        ids.append(p["id"])
    df = pd.DataFrame(rows)
    df["_id"] = ids
    df = df.sort_values(["_o", "Athlete"])
    key = f"reg_{cat}_{st.session_state.get('regsel', 0)}"
    st.dataframe(df.drop(columns=["_o", "_id"]), hide_index=True, width="stretch", height=38 + 35 * len(df), key=key,
                 on_select=partial(open_from_table, key, list(df["_id"]), "regsel"), selection_mode="single-row",
                 column_config={c: st.column_config.NumberColumn(format="%g°") for c in ("ER diff", "IR diff", "Flex diff", "Elbow ext diff", "Dom hip ext")}
                 | {"Flags": st.column_config.TextColumn(width="large"), "Status": st.column_config.TextColumn(width=110)})
    st.caption("Click a row to open that athlete's file.")
    st.download_button("Download full-team assessment (.csv)",
                       pd.DataFrame([dict(Athlete=p["name"], Group=p["grp"], **ASSESS.get(p["id"], {}),
                                          Flags="; ".join(f["label"] for f in FLAGS.get(p["id"], [])))
                                     for p in plist]).to_csv(index=False).encode(), file_name="full_team_assessment.csv")
    st.markdown("### Grading criteria")
    cc = st.columns(3)
    for i, (lbl, txt) in enumerate(ax.GRADING_CRITERIA):
        cc[i % 3].markdown(f"<div class='crit'><b>{lbl}</b>{txt}</div>", unsafe_allow_html=True)


def team_page():
    hero("Full team")
    plist = players.to_dict("records")
    fl = [FLAGS.get(p["id"], []) for p in plist]
    k = st.columns(5)
    k[0].metric("Athletes", len(plist))
    k[1].metric("High priority", sum(1 for f in fl if any(x["level"] == "high" for x in f)))
    for col, cat, lbl in ((k[2], "shoulder", "Shoulder flags"), (k[3], "hip", "Hip flags"), (k[4], "elbow", "Elbow flags")):
        col.metric(lbl, sum(1 for f in fl if any(x["cat"] == cat for x in f)))
    sec = st.segmented_control("Team section", ["Full team", "Throwing", "Performance Metrics", "Performance Assessment"],
                               default="Full team", required=True, key="teamsec", label_visibility="collapsed")
    if sec == "Throwing":
        team_throwing()
    elif sec == "Performance Metrics":
        team_force()
    elif sec == "Performance Assessment":
        team_assessment()
    else:
        tile_grid(plist, "team", from_team=True, zones=zone_cache())


# ═════════════════════════ LAYOUT ═════════════════════════
pid = st.session_state.get("player")
cur = next((p for p in players.to_dict("records") if p["id"] == pid), None) if pid else None
if cur:
    player_file(cur)
elif st.session_state["nav"] == "Team":
    team_page()
elif st.session_state["nav"] == "Position Players":
    roster_page("position")
else:
    roster_page("pitcher")

st.markdown("<div style='margin-top:2.5rem;padding-top:.8rem;border-top:1px solid #e2d8ef;font-size:.8rem;color:#666'>"
            "<b>Data note:</b> assessment fields were extracted from scanned intake forms; treat any flag here as "
            "“go verify the original form,” not a diagnosis. GIRD and total-arc-loss flags use the low end of each clinical range "
            "so nothing near the threshold gets missed. For internal K-State Baseball sports medicine staff use only.</div>",
            unsafe_allow_html=True)
