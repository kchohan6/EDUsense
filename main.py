import cv2
import mediapipe as mp
import time
import os
from datetime import datetime

from gaze      import (get_eye_landmarks, calculate_EAR,
                        get_gaze_direction, LEFT_EYE, RIGHT_EYE)
from head_pose import get_head_pose, get_pose_label
from attention import (classify_attention, get_state_color, calibrate,
                        compute_focus_score, generate_recommendations)
from logger    import SessionLogger
from voice     import maybe_alert, install_check, reset_milestones

# ── Session start ─────────────────────────────────────────────────────────────
os.system('cls' if os.name == 'nt' else 'clear')
print("=" * 50)
print("       EduSense v1.0 - Focus Tracker")
print("=" * 50)

subject = input("\nWhat subject are you studying today? ").strip() or "General"
install_check()
reset_milestones()
print(f"\nStarting session for: {subject}")
print("Press 'q' to end session.\n")
time.sleep(1)

logger = SessionLogger(subject=subject)

# ── MediaPipe ─────────────────────────────────────────────────────────────────
mp_face_mesh = mp.solutions.face_mesh
cap          = cv2.VideoCapture(0)

# ── Variables ─────────────────────────────────────────────────────────────────
EAR_THRESHOLD  = 0.25
CONSEC_FRAMES  = 2
blink_counter  = 0
blink_frames   = 0
blink_rate     = 0
last_minute    = time.time()
last_log_time  = time.time()
ear_buffer     = []
zone_out_timer = 0
last_state     = "Focused"
focused_streak = 0
alert_message      = ""
alert_display_time = 0

# ── Calibration ───────────────────────────────────────────────────────────────
CALIB_SECONDS    = 3
calib_gaze_list  = []
calib_pitch_list = []
calib_done       = False
calib_start      = time.time()

# ── Main loop ─────────────────────────────────────────────────────────────────
with mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame  = cv2.flip(frame, 1)
        h, w   = frame.shape[:2]
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            # Eyes & EAR
            left_pts  = get_eye_landmarks(landmarks, LEFT_EYE,  w, h)
            right_pts = get_eye_landmarks(landmarks, RIGHT_EYE, w, h)
            ear       = (calculate_EAR(left_pts) + calculate_EAR(right_pts)) / 2.0
            ear_buffer.append(ear)
            if len(ear_buffer) > 5: ear_buffer.pop(0)
            smooth_ear = sum(ear_buffer) / len(ear_buffer)

            # Blink
            if smooth_ear < EAR_THRESHOLD:
                blink_frames += 1
            else:
                if blink_frames >= CONSEC_FRAMES: blink_counter += 1
                blink_frames = 0
            if time.time() - last_minute >= 60:
                blink_rate = blink_counter
                blink_counter = 0
                last_minute = time.time()

            # Gaze & pose
            gaze_text, gaze_offset = get_gaze_direction(landmarks, w, h)
            # DEBUG — remove after fixing
            print(f"iris_x={gaze_offset:.3f}  state={last_state}", end='\r')
            yaw, pitch, roll       = get_head_pose(landmarks, w, h)
            pose_label             = get_pose_label(yaw, pitch)

            # ── CALIBRATION ───────────────────────────────────────────────────
            if not calib_done:
                elapsed = time.time() - calib_start
                calib_gaze_list.append(gaze_offset)
                calib_pitch_list.append(pitch)
                remaining = max(1, CALIB_SECONDS - int(elapsed) + 1)

                cv2.rectangle(frame, (0, 0), (w, h), (10, 10, 10), -1)
                cv2.putText(frame, "CALIBRATING",
                    (w//2-150, h//2-80), cv2.FONT_HERSHEY_SIMPLEX,
                    1.5, (0, 220, 255), 3)
                cv2.putText(frame, "Look straight at your screen",
                    (w//2-210, h//2-20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 255), 2)
                cv2.putText(frame, "Sit in your normal study position",
                    (w//2-230, h//2+25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.70, (200, 200, 200), 1)
                cv2.putText(frame, f"Starting in {remaining}...",
                    (w//2-120, h//2+90), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 255, 150), 2)

                if elapsed >= CALIB_SECONDS and len(calib_gaze_list) > 0:
                    avg_gaze  = sum(calib_gaze_list)  / len(calib_gaze_list)
                    avg_pitch = sum(calib_pitch_list)  / len(calib_pitch_list)
                    calibrate(0, avg_pitch, avg_gaze)
                    calib_done = True
                    print(f"Calibrated: Gaze={avg_gaze:.2f}  Pitch={avg_pitch:.1f}")

                cv2.imshow("EduSense - Focus Tracker", frame)
                cv2.waitKey(1)
                continue

            # Zone out timer
            if last_state in ("Zoning Out", "Focused") and smooth_ear > EAR_THRESHOLD:
                zone_out_timer += 1
            else:
                zone_out_timer = 0

            # Classify
            state, reason = classify_attention(
                smooth_ear, blink_rate, yaw, pitch,
                gaze_offset, zone_out_timer
            )
            last_state  = state
            state_color = get_state_color(state)

            # Focused streak & voice
            focused_streak = focused_streak + 1 if state == "Focused" else 0
            fired = maybe_alert(state, focused_streak)
            if fired:
                alert_message      = fired
                alert_display_time = time.time()

            # Log every second
            if time.time() - last_log_time >= 1.0:
                logger.log_frame(state, reason, smooth_ear,
                                 blink_rate, yaw, gaze_offset)
                last_log_time = time.time()

            # Focus score
            score = compute_focus_score(logger.get_log())

            # ── UI ────────────────────────────────────────────────────────────
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (370, 235), (15, 15, 15), -1)
            cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

            # Score bar
            cv2.rectangle(frame, (10, 244), (360, 262), (50,50,50), -1)
            bar_c = (0,200,100) if score>=70 else (0,165,255) if score>=50 else (0,0,220)
            cv2.rectangle(frame, (10,244), (10+int(score/100*350),262), bar_c, -1)
            cv2.putText(frame, f"Focus: {score}%",
                (15,259), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1)

            cv2.putText(frame, f"EduSense  |  {subject}",
                (10,25),  cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255,255,255), 1)
            cv2.putText(frame, f"Time    : {logger.get_duration()}",
                (10,55),  cv2.FONT_HERSHEY_SIMPLEX, 0.58, (200,200,200), 1)
            cv2.putText(frame, f"State   : {state}",
                (10,85),  cv2.FONT_HERSHEY_SIMPLEX, 0.60, state_color,   1)
            cv2.putText(frame, f"Reason  : {reason}",
                (10,112), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (180,180,180), 1)
            cv2.putText(frame, f"Gaze    : {gaze_text}",
                (10,140), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0,255,255),   1)
            cv2.putText(frame, f"Head    : {pose_label}",
                (10,167), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255,200,0),   1)
            cv2.putText(frame, f"Blinks  : {blink_rate}/min",
                (10,194), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200,200,200), 1)
            cv2.putText(frame, f"EAR     : {smooth_ear:.2f}",
                (10,221), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200,200,200), 1)

            if alert_message and time.time() - alert_display_time < 5:
                cv2.rectangle(frame, (0,h-52),(w,h),(0,0,160),-1)
                cv2.putText(frame, alert_message,
                    (12,h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.60,(255,255,255),1)

            for pt in left_pts + right_pts:
                cv2.circle(frame, pt, 2, (0,255,255), -1)

        else:
            cv2.rectangle(frame,(0,0),(w,55),(20,20,20),-1)
            cv2.putText(frame, "No face detected — sit in front of camera",
                (12,35), cv2.FONT_HERSHEY_SIMPLEX, 0.62,(0,100,255),1)

        cv2.imshow("EduSense - Focus Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()

# ── Session summary ───────────────────────────────────────────────────────────
log          = logger.get_log()
score        = compute_focus_score(log)
duration_sec = len(log)
tips         = generate_recommendations(log, subject, datetime.now().hour)
total        = max(len(log), 1)
states       = [r.get("state","") for r in log]

def hms(s):
    m, s = divmod(s, 60)
    return f"{m}m {s}s" if m else f"{s}s"

W = 55
print(f"\n{'='*W}")
print(f"{'  EDUSENSE SESSION COMPLETE':^{W}}")
print(f"{'='*W}")
print(f"  Subject      : {subject}")
print(f"  Date & Time  : {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
print(f"  Duration     : {hms(duration_sec)}")
print(f"  Focus Score  : {score}/100")
print(f"  {'─'*50}")
print(f"  Focused      : {hms(states.count('Focused')):>10}  ({round(states.count('Focused')/total*100)}%)")
print(f"  Distracted   : {hms(states.count('Distracted')):>10}  ({round(states.count('Distracted')/total*100)}%)")
print(f"  Zoning Out   : {hms(states.count('Zoning Out')):>10}  ({round(states.count('Zoning Out')/total*100)}%)")
print(f"  Drowsy       : {hms(states.count('Drowsy')):>10}  ({round(states.count('Drowsy')/total*100)}%)")
print(f"  {'─'*50}")
print(f"  Recommendations:")
for i, tip in enumerate(tips, 1):
    print(f"    {i}. {tip}")
print(f"\n  Session saved : {logger.filepath}")
print(f"  Dashboard     : streamlit run dashboard.py")
print(f"{'='*W}\n")