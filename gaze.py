import math

# LEFT EYE landmarks
LEFT_EYE = [362, 385, 387, 263, 373, 380]

# RIGHT EYE landmarks
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def get_eye_landmarks(landmarks, eye_indices, w, h):

    points = []

    for idx in eye_indices:

        x = int(landmarks[idx].x * w)
        y = int(landmarks[idx].y * h)

        points.append((x, y))

    return points

def euclidean(p1, p2):

    return math.sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2
    )


def calculate_EAR(eye):

    A = euclidean(eye[1], eye[5])
    B = euclidean(eye[2], eye[4])

    C = euclidean(eye[0], eye[3])

    ear = (A + B) / (2.0 * C)

    return ear

def get_gaze_direction(landmarks, w, h):

    # LEFT IRIS
    left_iris = landmarks[468]

    iris_x = left_iris.x

    # CENTER RANGE
    if 0.42 <= iris_x <= 0.58:

        return "Looking at Screen", 0

    elif iris_x < 0.42:

        return "Looking Left", -1

    else:

        return "Looking Right", 1