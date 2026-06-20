import csv
import os
import time
from datetime import datetime

class SessionLogger:
    def __init__(self, subject="General"):
        self.subject    = subject
        self._log       = []
        self.start_time = time.time()

        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = f"session_data/session_{timestamp}.csv"
        os.makedirs("session_data", exist_ok=True)

        with open(self.filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "subject", "state", "reason",
                "ear", "blink_rate", "yaw", "gaze_offset"
            ])

    def log_frame(self, state, reason, ear,
                  blink_rate, yaw, gaze_offset):
        row = {
            "timestamp":   datetime.now().strftime("%H:%M:%S"),
            "subject":     self.subject,
            "state":       state,
            "reason":      reason,
            "ear":         round(ear, 3),
            "blink_rate":  blink_rate,
            "yaw":         round(yaw, 2),
            "gaze_offset": round(gaze_offset, 3),
        }
        self._log.append(row)

        with open(self.filepath, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)

    def get_log(self):
        return self._log

    def get_duration(self):
        elapsed = int(time.time() - self.start_time)
        mins    = elapsed // 60
        secs    = elapsed  % 60
        return f"{mins:02d}:{secs:02d}"