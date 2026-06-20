import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import csv
from datetime import datetime
from collections import Counter
from report import (generate_pdf_report, seconds_to_hms)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduSense Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Color Palette (Complementary) ─────────────────────────────────────────────
COLORS = {
    "bg":         "#0D1B2A",
    "card":       "#1B2A3B",
    "teal":       "#00B4D8",
    "teal_dark":  "#0077A8",
    "amber":      "#F4A261",
    "coral":      "#E63946",
    "mint":       "#2EC4B6",
    "purple":     "#7B2D8B",
    "yellow":     "#FFD166",
    "white":      "#F0F4F8",
    "muted":      "#8899AA",
    "focused":    "#2EC4B6",
    "distracted": "#E63946",
    "zoning":     "#FFD166",
    "drowsy":     "#7B2D8B",
}

STATE_COLORS = {
    "Focused":    COLORS["focused"],
    "Distracted": COLORS["coral"],
    "Zoning Out": COLORS["zoning"],
    "Drowsy":     COLORS["drowsy"],
}

st.markdown(f"""
<style>
  html, body, [data-testid="stAppViewContainer"] {{
      background-color: {COLORS['bg']};
      color: {COLORS['white']};
  }}
  [data-testid="stSidebar"] {{
      background-color: {COLORS['card']};
      border-right: 2px solid {COLORS['teal']};
  }}
  .block-container {{ padding-top: 1.2rem; }}
  .sec-header {{
      font-size: 1.05rem; font-weight: 700; color: {COLORS['white']};
      background: linear-gradient(90deg, {COLORS['teal']}, {COLORS['teal_dark']});
      padding: 8px 16px; border-radius: 6px; margin-bottom: 14px; letter-spacing: 0.5px;
  }}
  .box-teal {{
      background-color: {COLORS['teal']}; color: #000000; font-weight: 700;
      font-size: 1rem; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; text-align: center;
  }}
  .box-amber {{
      background-color: {COLORS['amber']}; color: #000000; font-weight: 700;
      font-size: 1rem; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; text-align: center;
  }}
  .box-coral {{
      background-color: {COLORS['coral']}; color: #ffffff; font-weight: 700;
      font-size: 1rem; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; text-align: center;
  }}
  .box-mint {{
      background-color: {COLORS['mint']}; color: #000000; font-weight: 700;
      font-size: 1rem; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; text-align: center;
  }}
  .box-purple {{
      background-color: {COLORS['purple']}; color: #ffffff; font-weight: 700;
      font-size: 1rem; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; text-align: center;
  }}
  .box-yellow {{
      background-color: {COLORS['yellow']}; color: #000000; font-weight: 700;
      font-size: 1rem; padding: 14px 18px; border-radius: 10px; margin-bottom: 10px; text-align: center;
  }}
  .tag-1 {{ display:inline-block; background:{COLORS['coral']}; color:#fff; font-weight:700;
      padding:6px 14px; border-radius:20px; margin:4px; font-size:0.85rem; }}
  .tag-2 {{ display:inline-block; background:{COLORS['amber']}; color:#000; font-weight:700;
      padding:6px 14px; border-radius:20px; margin:4px; font-size:0.85rem; }}
  .tag-3 {{ display:inline-block; background:{COLORS['purple']}; color:#fff; font-weight:700;
      padding:6px 14px; border-radius:20px; margin:4px; font-size:0.85rem; }}
  .tip-card {{
      background: {COLORS['card']}; border-left: 5px solid {COLORS['teal']};
      color: {COLORS['white']}; padding: 12px 16px; border-radius: 8px;
      margin-bottom: 10px; font-size: 0.92rem; line-height: 1.5;
  }}
  div[data-testid="stMetric"] {{
      background: {COLORS['card']}; border-left: 4px solid {COLORS['teal']};
      border-radius: 10px; padding: 12px 16px;
  }}
  .sidebar-label {{ color: {COLORS['teal']}; font-weight: 700; font-size: 0.9rem; margin-bottom: 4px; }}
  .sidebar-val   {{ color: {COLORS['white']}; font-size: 0.95rem; margin-bottom: 12px; }}
</style>
""", unsafe_allow_html=True)


def load_session(filepath):
    log = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            log.append(row)
    return log

def list_sessions(session_dir="session_data"):
    if not os.path.exists(session_dir):
        return []
    return sorted([f for f in os.listdir(session_dir) if f.endswith(".csv")], reverse=True)

def compute_focus_score(log):
    if not log: return 0
    total   = len(log)
    focused = sum(1 for r in log if r["state"] == "Focused")
    zoning  = sum(1 for r in log if r["state"] == "Zoning Out")
    score   = ((focused * 1.0) + (zoning * 0.3)) / total * 100
    streak = best = 0
    for r in log:
        streak = streak + 1 if r["state"] == "Focused" else 0
        best   = max(best, streak)
    if best >= 1200: score += 5
    return min(round(score, 1), 100)

def score_label(score):
    if score >= 85: return "Excellent 🔥", COLORS["mint"]
    if score >= 70: return "Good 👍",      COLORS["teal"]
    if score >= 50: return "Average 😐",   COLORS["amber"]
    return "Needs Improvement ⚠️",          COLORS["coral"]

def chart_style(ax, fig):
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["card"])
    ax.tick_params(colors=COLORS["white"])
    ax.xaxis.label.set_color(COLORS["white"])
    ax.yaxis.label.set_color(COLORS["white"])
    for spine in ax.spines.values():
        spine.set_edgecolor(COLORS["teal"] + "55")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,{COLORS["teal"]},{COLORS["teal_dark"]});
        border-radius:14px;padding:22px 20px 16px 20px;margin-bottom:6px;
        text-align:center;box-shadow:0 4px 16px rgba(0,180,216,0.35);'>
        <div style='font-size:2.8rem;margin-bottom:6px'>🎓</div>
        <div style='font-size:2.2rem;font-weight:900;color:#ffffff;
            letter-spacing:3px;line-height:1.1;'>EduSense</div>
        <div style='font-size:0.82rem;color:#d0f4ff;margin-top:8px;
            font-weight:500;letter-spacing:1.5px;'>AI-Powered Focus Tracker</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    sessions = list_sessions()
    if not sessions:
        st.warning("No sessions found. Run main.py first!")
        st.stop()

    session_labels = {}
    for s in sessions:
        name = s.replace("session_", "").replace(".csv", "")
        try:
            dt    = datetime.strptime(name, "%Y%m%d_%H%M%S")
            label = dt.strftime("%d %b %Y, %I:%M %p")
        except:
            label = name
        session_labels[label] = s

    selected_label = st.selectbox("📂 Select Session", list(session_labels.keys()))
    selected_file  = session_labels[selected_label]
    log            = load_session(os.path.join("session_data", selected_file))
    subject        = log[0].get("subject", "General") if log else "General"

    st.markdown(f"<p class='sidebar-label'>Subject</p><p class='sidebar-val'>{subject}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='sidebar-label'>Frames Logged</p><p class='sidebar-val'>{len(log)} seconds</p>", unsafe_allow_html=True)
    st.divider()

    if st.button("📄 Generate PDF Report", use_container_width=True, type="primary"):
        from attention import generate_recommendations
        score = compute_focus_score(log)
        hour  = datetime.now().hour
        tips  = generate_recommendations(log, subject, hour)
        path  = generate_pdf_report(log, subject, score, tips)
        with open(path, "rb") as f:
            st.download_button("⬇️ Download PDF", data=f, file_name="EduSense_Report.pdf",
                               mime="application/pdf", use_container_width=True)

if not log:
    st.error("No data in this session.")
    st.stop()

total        = len(log)
states       = [r["state"] for r in log]
state_count  = Counter(states)
focused_s    = state_count.get("Focused",    0)
distracted_s = state_count.get("Distracted", 0)
zoning_s     = state_count.get("Zoning Out", 0)
drowsy_s     = state_count.get("Drowsy",     0)
score        = compute_focus_score(log)
lbl, _       = score_label(score)

reasons      = [r["reason"] for r in log if r["state"] != "Focused"]
top_reasons  = Counter(reasons).most_common(3)

streak = best_streak = 0
for r in log:
    if r["state"] == "Focused": streak += 1; best_streak = max(best_streak, streak)
    else: streak = 0

distraction_events = sum(1 for i in range(1, len(log))
    if log[i]["state"] != "Focused" and log[i-1]["state"] == "Focused")
recoveries = sum(1 for i in range(1, len(log))
    if log[i]["state"] == "Focused" and log[i-1]["state"] != "Focused")
recovery_rate = round(recoveries / max(distraction_events, 1) * 100)

ears      = [float(r.get("ear", 0.3)) for r in log]
avg_ear   = round(sum(ears) / len(ears), 3)
blinks    = [float(r.get("blink_rate", 0)) for r in log]
avg_blink = round(sum(blinks) / len(blinks), 1)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='color:{COLORS['white']};margin-bottom:4px'>📊 EduSense Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:{COLORS['muted']}'>Session: <b style='color:{COLORS['teal']}'>{selected_label}</b>  |  Subject: <b style='color:{COLORS['amber']}'>{subject}</b></p>", unsafe_allow_html=True)
st.divider()

# ── Score Banner ──────────────────────────────────────────────────────────────
bg_grad = (f"linear-gradient(135deg,{COLORS['teal']},{COLORS['mint']})" if score >= 70
           else f"linear-gradient(135deg,{COLORS['amber']},{COLORS['yellow']})" if score >= 50
           else f"linear-gradient(135deg,{COLORS['coral']},{COLORS['purple']})")
st.markdown(
    f"<div style='background:{bg_grad};color:#000;font-size:1.9rem;font-weight:900;"
    f"text-align:center;padding:20px;border-radius:14px;margin-bottom:18px;"
    f"box-shadow:0 4px 20px rgba(0,0,0,0.4)'>🎯 Focus Score: {score}/100 — {lbl}</div>",
    unsafe_allow_html=True
)

# ── 5 Metric Boxes ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
boxes = [
    (c1, "box-teal",   "⏱️ Duration",       seconds_to_hms(total)),
    (c2, "box-mint",   "✅ Focused",         f"{round(focused_s/total*100)}% ({seconds_to_hms(focused_s)})"),
    (c3, "box-coral",  "🚨 Distracted",      f"{round(distracted_s/total*100)}% ({seconds_to_hms(distracted_s)})"),
    (c4, "box-yellow", "😶 Zoning Out",       f"{round(zoning_s/total*100)}% ({seconds_to_hms(zoning_s)})"),
    (c5, "box-purple", "🔗 Best Streak",      seconds_to_hms(best_streak)),
]
for col, cls, lbl2, val in boxes:
    with col:
        st.markdown(
            f"<div class='{cls}'><div style='font-size:0.78rem;font-weight:600;margin-bottom:4px;opacity:0.85'>{lbl2}</div>"
            f"<div style='font-size:1.05rem'>{val}</div></div>", unsafe_allow_html=True)

st.divider()

# ── Timeline ──────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-header">📈 Attention Timeline</div>', unsafe_allow_html=True)
state_map = {"Focused": 3, "Zoning Out": 2, "Distracted": 1, "Drowsy": 0}
y_vals = [state_map.get(s, 2) for s in states]
x_vals = list(range(len(states)))
clrs   = [STATE_COLORS.get(s, "#888") for s in states]

fig, ax = plt.subplots(figsize=(14, 3.2))
chart_style(ax, fig)
for i in range(len(x_vals) - 1):
    ax.fill_between([x_vals[i], x_vals[i+1]], 0, [y_vals[i], y_vals[i+1]], alpha=0.88, color=clrs[i])
ax.set_yticks([0, 1, 2, 3])
ax.set_yticklabels(["Drowsy", "Distracted", "Zoning Out", "Focused"], color=COLORS["white"], fontsize=10)
ax.set_xlabel("Time (seconds)", color=COLORS["white"], fontsize=10)
legend_patches = [mpatches.Patch(color=c, label=s) for s, c in STATE_COLORS.items()]
ax.legend(handles=legend_patches, loc="upper right", facecolor=COLORS["card"],
          labelcolor=COLORS["white"], fontsize=9, edgecolor=COLORS["teal"])
plt.tight_layout()
st.pyplot(fig)
plt.close()

st.divider()

# ── Pie + Breakdown + Insights ────────────────────────────────────────────────
col_l, col_m, col_r = st.columns([1.1, 1.2, 0.9])

with col_l:
    st.markdown('<div class="sec-header">🥧 Attention Distribution</div>', unsafe_allow_html=True)
    fig2, ax2 = plt.subplots(figsize=(4.5, 4.5))
    fig2.patch.set_facecolor(COLORS["bg"])
    ax2.set_facecolor(COLORS["bg"])
    labels_ = list(state_count.keys())
    sizes_  = list(state_count.values())
    clrs_   = [STATE_COLORS.get(l, "#888") for l in labels_]
    wedges, texts, autotexts = ax2.pie(
        sizes_, labels=labels_, colors=clrs_, autopct="%1.1f%%", startangle=140,
        textprops={"color": COLORS["white"], "fontsize": 10, "fontweight": "bold"},
        wedgeprops={"edgecolor": COLORS["bg"], "linewidth": 3})
    for at in autotexts:
        at.set_color("#000000"); at.set_fontweight("bold")
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close()

with col_m:
    st.markdown('<div class="sec-header">📊 State Breakdown</div>', unsafe_allow_html=True)
    df = pd.DataFrame({
        "State":   ["Focused", "Distracted", "Zoning Out", "Drowsy"],
        "Time":    [seconds_to_hms(focused_s), seconds_to_hms(distracted_s),
                    seconds_to_hms(zoning_s),  seconds_to_hms(drowsy_s)],
        "Share":   [f"{round(focused_s/total*100)}%", f"{round(distracted_s/total*100)}%",
                    f"{round(zoning_s/total*100)}%",  f"{round(drowsy_s/total*100)}%"]
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown('<div class="sec-header" style="margin-top:16px">🚫 Top Distractions</div>', unsafe_allow_html=True)
    tag_cls = ["tag-1", "tag-2", "tag-3"]
    if top_reasons:
        for i, (reason, count) in enumerate(top_reasons):
            pct = round(count / total * 100)
            st.markdown(f'<span class="{tag_cls[i % 3]}">{reason} — {count}s ({pct}%)</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="box-mint" style="text-align:left;padding:10px 14px">🎉 No significant distractions!</div>', unsafe_allow_html=True)

with col_r:
    st.markdown('<div class="sec-header">⚡ Session Insights</div>', unsafe_allow_html=True)
    blink_note = ("Normal" if 12 <= avg_blink <= 20 else "Low - eye strain" if avg_blink < 12 else "High - stress")
    insight_boxes = [
        ("box-teal",   "🔄 Recovery Rate",      f"{recovery_rate}%"),
        ("box-amber",  "🚨 Distraction Events",  f"{distraction_events} times"),
        ("box-mint",   "👁️ Avg EAR",             f"{avg_ear}"),
        ("box-yellow", "😑 Avg Blink Rate",      f"{avg_blink}/min"),
        ("box-coral",  "Blink Health",            blink_note),
    ]
    for cls, lbl3, val in insight_boxes:
        st.markdown(
            f"<div class='{cls}' style='padding:10px 14px;margin-bottom:8px'>"
            f"<span style='font-size:0.78rem;opacity:0.85'>{lbl3}</span><br>"
            f"<span style='font-size:1.05rem'>{val}</span></div>", unsafe_allow_html=True)

st.divider()

# ── Recommendations ───────────────────────────────────────────────────────────
st.markdown('<div class="sec-header">💡 Personalized Recommendations</div>', unsafe_allow_html=True)
from attention import generate_recommendations
hour = datetime.now().hour
tips = generate_recommendations(log, subject, hour)
tip_cols = st.columns(2)
for i, tip in enumerate(tips):
    with tip_cols[i % 2]:
        st.markdown(f'<div class="tip-card">💡 {tip}</div>', unsafe_allow_html=True)

st.divider()

# ── Trend Chart ───────────────────────────────────────────────────────────────
st.markdown('<div class="sec-header">📅 Focus Score Trend (All Sessions)</div>', unsafe_allow_html=True)
all_sessions = list_sessions()
if len(all_sessions) > 1:
    trend_dates, trend_scores = [], []
    for sf in reversed(all_sessions):
        try:
            sl   = load_session(os.path.join("session_data", sf))
            sc   = compute_focus_score(sl)
            name = sf.replace("session_", "").replace(".csv", "")
            dt   = datetime.strptime(name, "%Y%m%d_%H%M%S")
            trend_dates.append(dt.strftime("%d %b\n%H:%M"))
            trend_scores.append(sc)
        except:
            pass
    if trend_scores:
        fig3, ax3 = plt.subplots(figsize=(13, 3.5))
        chart_style(ax3, fig3)
        bar_colors = [(COLORS["mint"] if s >= 70 else COLORS["amber"] if s >= 50 else COLORS["coral"]) for s in trend_scores]
        bars = ax3.bar(trend_dates, trend_scores, color=bar_colors, width=0.55,
                       zorder=2, edgecolor=COLORS["bg"], linewidth=1.5)
        ax3.plot(trend_dates, trend_scores, color=COLORS["teal"], linewidth=2.5,
                 marker="o", markersize=7, markerfacecolor=COLORS["yellow"],
                 markeredgecolor=COLORS["teal"], zorder=3)
        for bar, sc in zip(bars, trend_scores):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                     f"{sc}%", ha="center", va="bottom", color=COLORS["white"],
                     fontsize=9, fontweight="bold")
        ax3.axhline(70, color=COLORS["mint"], linestyle="--", linewidth=1.2,
                    label="Good threshold (70)", alpha=0.7)
        ax3.set_ylim(0, 112)
        ax3.set_ylabel("Focus Score", color=COLORS["white"])
        ax3.legend(facecolor=COLORS["card"], labelcolor=COLORS["white"],
                   fontsize=9, edgecolor=COLORS["teal"])
        plt.tight_layout()
        st.pyplot(fig3)
        plt.close()
else:
    st.markdown(
        f'<div class="box-teal" style="text-align:left;font-size:0.95rem;padding:14px 18px">'
        '📈 Complete more sessions to unlock your focus score trend over time!</div>',
        unsafe_allow_html=True)

st.markdown(f"<p style='text-align:center;color:{COLORS['muted']};font-size:0.8rem;margin-top:20px'>"
            "EduSense v1.0 — Built with OpenCV, MediaPipe & Streamlit</p>", unsafe_allow_html=True)