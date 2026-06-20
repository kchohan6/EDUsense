import os
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from fpdf import FPDF
from datetime import datetime
from collections import Counter


# ── Helpers ──────────────────────────────────────────────────────────────────

def safe(text):
    """Replace unicode characters that FPDF latin-1 cannot encode."""
    replacements = {
        "\u2014": "--",   # em dash —
        "\u2013": "-",    # en dash –
        "\u2018": "'",    # left single quote '
        "\u2019": "'",    # right single quote '
        "\u201c": '"',    # left double quote "
        "\u201d": '"',    # right double quote "
        "\u2022": "-",    # bullet •
        "\u2026": "...",  # ellipsis …
        "\u00a0": " ",    # non-breaking space
        "\u2192": "->",   # arrow →
        "\u2713": "OK",   # checkmark ✓
        "\u26a0": "!",    # warning ⚠
        "\U0001f525": "", # fire emoji 🔥
        "\U0001f44d": "", # thumbs up 👍
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Catch-all: remove any remaining non-latin-1 characters
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def seconds_to_hms(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def load_latest_session(session_dir="session_data"):
    """Load the most recent session CSV."""
    files = sorted([
        f for f in os.listdir(session_dir) if f.endswith(".csv")
    ])
    if not files:
        return [], "General"
    filepath = os.path.join(session_dir, files[-1])
    log = []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            log.append(row)
    subject = log[0].get("subject", "General") if log else "General"
    return log, subject


# ── Chart generators ─────────────────────────────────────────────────────────

STATE_COLORS = {
    "Focused":    "#2ecc71",
    "Distracted": "#e67e22",
    "Zoning Out": "#f1c40f",
    "Drowsy":     "#e74c3c",
}

def generate_timeline_chart(log, output_path="session_data/timeline.png"):
    """Generate attention state timeline chart."""
    states    = [r["state"] for r in log]
    x         = list(range(len(states)))
    state_map = {"Focused": 3, "Zoning Out": 2, "Distracted": 1, "Drowsy": 0}
    y         = [state_map.get(s, 2) for s in states]
    colors    = [STATE_COLORS.get(s, "#95a5a6") for s in states]

    fig, ax = plt.subplots(figsize=(12, 3))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    for i in range(len(x) - 1):
        ax.fill_between([x[i], x[i+1]], [y[i], y[i+1]], alpha=0.85,
                        color=colors[i])

    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["Drowsy", "Distracted", "Zoning Out", "Focused"],
                       color="white", fontsize=9)
    ax.set_xlabel("Time (seconds)", color="white", fontsize=9)
    ax.set_title("Attention Timeline", color="white", fontsize=12, pad=10)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    return output_path


def generate_pie_chart(log, output_path="session_data/pie.png"):
    """Generate attention state pie chart."""
    states = [r["state"] for r in log]
    count  = Counter(states)
    labels = list(count.keys())
    sizes  = list(count.values())
    colors = [STATE_COLORS.get(l, "#95a5a6") for l in labels]

    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=140,
        textprops={"color": "white", "fontsize": 10},
        wedgeprops={"edgecolor": "#1a1a2e", "linewidth": 2}
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(9)

    ax.set_title("Attention Distribution", color="white", fontsize=12, pad=10)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    return output_path


def generate_focus_bar(score, output_path="session_data/focusbar.png"):
    """Generate a focus score bar chart."""
    fig, ax = plt.subplots(figsize=(8, 1.5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    color = "#2ecc71" if score >= 70 else "#e67e22" if score >= 50 else "#e74c3c"
    ax.barh(["Focus Score"], [score],  color=color, height=0.5)
    ax.barh(["Focus Score"], [100],    color="#2c3e50", height=0.5)
    ax.barh(["Focus Score"], [score],  color=color, height=0.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Score / 100", color="white", fontsize=9)
    ax.tick_params(colors="white")
    ax.text(score + 1, 0, f"{score}/100", va="center",
            color="white", fontsize=11, fontweight="bold")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    return output_path


# ── PDF Builder ───────────────────────────────────────────────────────────────

class EduSensePDF(FPDF):
    def __init__(self, subject):
        super().__init__()
        self.subject = subject

    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(52, 152, 219)
        self.cell(0, 10, safe("EduSense - AI Focus Tracker Report"), align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(150, 150, 150)
        self.ln(5)
        self.cell(0, 6, safe(f"Subject: {self.subject}  |  Generated: "
                  f"{datetime.now().strftime('%d %b %Y, %I:%M %p')}"), align="C")
        self.ln(8)
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, safe(f"EduSense v1.0  |  Page {self.page_no()}"), align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(52, 152, 219)
        self.ln(4)
        self.cell(0, 8, safe(title))
        self.ln(2)
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        self.set_text_color(30, 30, 30)

    def kv_row(self, label, value, color=None):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 80, 80)
        self.cell(60, 7, safe(label))
        self.set_font("Helvetica", "", 10)
        if color:
            self.set_text_color(*color)
        else:
            self.set_text_color(30, 30, 30)
        self.cell(0, 7, safe(str(value)))
        self.ln(7)
        self.set_text_color(30, 30, 30)

    def tip_row(self, num, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(52, 152, 219)
        self.cell(8, 6, safe(f"{num}."))
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 6, safe(text))
        self.ln(1)


def generate_pdf_report(log, subject, score, tips,
                        output_path="session_data/EduSense_Report.pdf"):
    """Generate the full PDF session report."""

    os.makedirs("session_data", exist_ok=True)

    # ── Compute stats ─────────────────────────────────────────────────────────
    total        = len(log)
    states       = [r["state"] for r in log]
    state_count  = Counter(states)
    focused_s    = state_count.get("Focused",    0)
    distracted_s = state_count.get("Distracted", 0)
    zoning_s     = state_count.get("Zoning Out", 0)
    drowsy_s     = state_count.get("Drowsy",     0)

    reasons      = [r["reason"] for r in log if r["state"] != "Focused"]
    top_reasons  = Counter(reasons).most_common(3)

    streak = best_streak = 0
    for r in log:
        if r["state"] == "Focused":
            streak += 1; best_streak = max(best_streak, streak)
        else:
            streak = 0

    distraction_events = sum(
        1 for i in range(1, len(log))
        if log[i]["state"] != "Focused" and log[i-1]["state"] == "Focused"
    )
    recoveries = sum(
        1 for i in range(1, len(log))
        if log[i]["state"] == "Focused" and log[i-1]["state"] != "Focused"
    )
    recovery_rate = round(recoveries / max(distraction_events, 1) * 100)

    ears      = [float(r.get("ear", 0.3)) for r in log]
    avg_ear   = round(sum(ears) / len(ears), 3)
    blinks    = [float(r.get("blink_rate", 0)) for r in log]
    avg_blink = round(sum(blinks) / len(blinks), 1)

    quality   = ("Excellent" if score >= 85 else "Good" if score >= 70
                 else "Average" if score >= 50 else "Needs Improvement")
    q_color   = ((39,174,96) if score >= 85 else (41,128,185) if score >= 70
                 else (243,156,18) if score >= 50 else (231,76,60))

    # ── Generate charts ───────────────────────────────────────────────────────
    tl_path  = generate_timeline_chart(log)
    pie_path = generate_pie_chart(log)
    bar_path = generate_focus_bar(score)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    pdf = EduSensePDF(subject)
    pdf.set_margins(15, 20, 15)
    pdf.add_page()

    # Score banner
    pdf.set_fill_color(*q_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 18, safe(f"Focus Score: {score}/100  --  {quality}"),
             align="C", fill=True)
    pdf.ln(10)

    # Focus bar chart
    pdf.image(bar_path, x=15, w=180)
    pdf.ln(6)

    # ── Session Info ──────────────────────────────────────────────────────────
    pdf.section_title("Session Information")
    pdf.kv_row("Subject:",        subject)
    pdf.kv_row("Date & Time:",    datetime.now().strftime("%d %b %Y, %I:%M %p"))
    pdf.kv_row("Total Duration:", seconds_to_hms(total))
    pdf.kv_row("Frames Logged:",  f"{total} seconds")

    # ── Attention Breakdown ───────────────────────────────────────────────────
    pdf.section_title("Attention Breakdown")
    pdf.kv_row("Focused:",    f"{seconds_to_hms(focused_s)}  ({round(focused_s/max(total,1)*100)}%)",    (39,174,96))
    pdf.kv_row("Distracted:", f"{seconds_to_hms(distracted_s)}  ({round(distracted_s/max(total,1)*100)}%)", (231,76,60))
    pdf.kv_row("Zoning Out:", f"{seconds_to_hms(zoning_s)}  ({round(zoning_s/max(total,1)*100)}%)",     (243,156,18))
    pdf.kv_row("Drowsy:",     f"{seconds_to_hms(drowsy_s)}  ({round(drowsy_s/max(total,1)*100)}%)",     (192,57,43))

    # ── Session Insights ──────────────────────────────────────────────────────
    pdf.section_title("Session Insights")
    pdf.kv_row("Longest Focus Streak:", seconds_to_hms(best_streak))
    pdf.kv_row("Distraction Events:",   f"{distraction_events} times")
    pdf.kv_row("Recovery Rate:",        f"{recovery_rate}%")
    pdf.kv_row("Avg EAR:",              f"{avg_ear}  ({'Normal' if avg_ear > 0.25 else 'Low'})")
    pdf.kv_row("Avg Blink Rate:",       f"{avg_blink}/min")

    # ── Top Distractions ──────────────────────────────────────────────────────
    if top_reasons:
        pdf.section_title("Top Distraction Reasons")
        medals = ["1.", "2.", "3."]
        for i, (reason, count) in enumerate(top_reasons):
            pdf.kv_row(f"  {medals[i]}  {reason}:",
                       f"{count}s  ({round(count/total*100)}%)")

    # ── Charts ────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("Attention Timeline")
    pdf.image(tl_path, x=10, w=185)
    pdf.ln(8)

    pdf.section_title("Attention Distribution")
    pdf.image(pie_path, x=55, w=100)
    pdf.ln(8)

    # ── Recommendations ───────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("Personalized Study Recommendations")
    for i, tip in enumerate(tips, 1):
        pdf.tip_row(i, tip)

    pdf.ln(5)
    pdf.section_title("Next Steps")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 6, safe(
        "- Complete 5 sessions to unlock your Personal Focus Fingerprint\n"
        "- Open dashboard.py in Streamlit to view your progress over time\n"
        "- Share this PDF with your study group or mentor\n"
        "- Try studying at different times to find your peak focus window"
    ))

    pdf.output(output_path)
    print(f"\n✅ PDF Report saved: {output_path}")
    return output_path


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from attention import compute_focus_score, generate_recommendations
    from datetime import datetime

    log, subject = load_latest_session()
    if not log:
        print("No session data found. Run main.py first!")
    else:
        score = compute_focus_score(log)
        hour  = datetime.now().hour
        tips  = generate_recommendations(log, subject, hour)
        generate_pdf_report(log, subject, score, tips)