import math

def get_head_pose(landmarks, w, h):

    nose = landmarks[1]

    left_face = landmarks[234]
    right_face = landmarks[454]

    top_face = landmarks[10]
    bottom_face = landmarks[152]

    # YAW
    left_dist = abs(nose.x - left_face.x)
    right_dist = abs(right_face.x - nose.x)

    yaw = (left_dist - right_dist) * 100

    # PITCH
    top_dist = abs(nose.y - top_face.y)
    bottom_dist = abs(bottom_face.y - nose.y)

    pitch = (top_dist - bottom_dist) * 100

    roll = 0

    return yaw, pitch, roll

def get_pose_label(yaw, pitch):

    # LEFT / RIGHT
    if yaw > 8:
        return "Looking Left"

    elif yaw < -8:
        return "Looking Right"

    # UP / DOWN
    if pitch > 10:
        return "Looking Up"

    elif pitch < -10:
        return "Looking Down"

    return "Straight"