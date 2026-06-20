import threading
import time

# ── Check pyttsx3 availability ────────────────────────────────────────────────
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# ── State tracking ────────────────────────────────────────────────────────────
_last_alert_time  = 0
_speaking         = False
COOLDOWN          = 55       # seconds between distraction alerts
MILESTONE_COOLDOWN = 30      # seconds between milestone alerts

# ── Alert message pools ───────────────────────────────────────────────────────
ALERTS = {
    "Distracted": [
        "Hey, please focus on your screen.",
        "You seem distracted. Come back to your studies.",
        "Stay focused. You can do this.",
        "Refocus now. Your goal is waiting.",
        "Put away distractions and get back to work.",
    ],
    "Zoning Out": [
        "You are zoning out. Take a breath and refocus.",
        "Hey! You seem to be spacing out. Stay with it.",
        "Your mind is wandering. Bring it back.",
        "Stay present. You are almost there.",
        "Snap out of it and get back to studying.",
    ],
    "Drowsy": [
        "You look sleepy. Sit up straight and take a deep breath.",
        "Feeling tired? Stand up for 30 seconds and stretch.",
        "Wake up! Your study session is still running.",
        "Splash cold water on your face to wake up.",
        "Do not fall asleep! Stay alert.",
    ],
}

MILESTONES = {
    600:  "Great job! You have been focused for 10 minutes. Keep it up!",
    1200: "Excellent! 20 minutes of solid focus. You are doing amazing!",
    1800: "Incredible! 30 minutes of focused study. Consider a short break soon.",
    2400: "Wow! 40 minutes of focus. You are on fire today!",
    3000: "Outstanding! 50 minutes focused. Take a 5 minute break soon.",
}

# ── Rotation counters ─────────────────────────────────────────────────────────
_alert_index = {"Distracted": 0, "Zoning Out": 0, "Drowsy": 0}
_fired_milestones = set()   # track which milestones already fired


def _speak(text):
    """
    Speak text in a fresh daemon thread.
    Creates a NEW pyttsx3 engine every call — fixes the stuck-after-first-use bug.
    """
    global _speaking

    if not TTS_AVAILABLE or _speaking:
        return

    def _run():
        global _speaking
        _speaking = True
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate',   155)
            engine.setProperty('volume', 1.0)
            # Try to use a female voice if available
            voices = engine.getProperty('voices')
            for v in voices:
                name = v.name.lower()
                if 'zira' in name or 'hazel' in name or 'female' in name:
                    engine.setProperty('voice', v.id)
                    break
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[Voice] Error: {e}")
        finally:
            _speaking = False

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def maybe_alert(state, focused_streak_seconds=0):
    """
    Call every frame from main.py.
    Fires voice alert when:
      - Student has been non-focused long enough (cooldown passed)
      - Student hits a new focus milestone

    Returns alert message string if fired, else None.
    """
    global _last_alert_time

    now = time.time()

    # ── Milestone alerts (only fire once each) ────────────────────────────────
    if state == "Focused":
        for secs, msg in MILESTONES.items():
            # Fire when streak crosses the milestone second exactly
            if (focused_streak_seconds >= secs and
                    secs not in _fired_milestones and
                    now - _last_alert_time > MILESTONE_COOLDOWN):
                _fired_milestones.add(secs)
                _last_alert_time = now
                print(f"[Voice] Milestone: {msg}")
                _speak(msg)
                return msg
        return None

    # ── Distraction / drowsy / zoning alerts ─────────────────────────────────
    if state not in ALERTS:
        return None

    # Cooldown check
    if now - _last_alert_time < COOLDOWN:
        return None

    _last_alert_time = now

    # Rotate through messages
    idx  = _alert_index[state] % len(ALERTS[state])
    msg  = ALERTS[state][idx]
    _alert_index[state] += 1

    print(f"[Voice] Alert ({state}): {msg}")
    _speak(msg)
    return msg


def reset_milestones():
    """Call this when a new session starts."""
    global _fired_milestones, _last_alert_time
    _fired_milestones.clear()
    _last_alert_time = 0
    for k in _alert_index:
        _alert_index[k] = 0


def install_check():
    """Print TTS status at session start."""
    if TTS_AVAILABLE:
        print("Voice alerts ready (pyttsx3)")
    else:
        print("Voice alerts unavailable. Run: pip install pyttsx3")