"""Recognize held poses from finger geometry, independent of screen rotation."""

import math


def _point(landmark):
    return landmark.x, landmark.y, getattr(landmark, "z", 0)


def _subtract(first, second):
    return tuple(a - b for a, b in zip(first, second))


def _length(vector):
    return math.sqrt(sum(value * value for value in vector))


def _finger_state(landmarks, base, joint, tip):
    tip_index = tip
    wrist = _point(landmarks[0])
    base = _point(landmarks[base])
    joint = _point(landmarks[joint])
    tip = _point(landmarks[tip])
    upper = _subtract(base, joint)
    lower = _subtract(tip, joint)
    denominator = _length(upper) * _length(lower)
    if denominator < 1e-12:
        return "uncertain"

    cosine = sum(a * b for a, b in zip(upper, lower)) / denominator

    # A fingertip can curl back at the last joint while remaining farther from
    # the wrist than the middle joint. The old wrist-distance test missed this.
    distal = _point(landmarks[tip_index - 1])
    before_tip = _subtract(joint, distal)
    fingertip = _subtract(tip, distal)
    distal_denominator = _length(before_tip) * _length(fingertip)
    if distal_denominator > 1e-12:
        distal_cosine = sum(a * b for a, b in zip(before_tip, fingertip)) / distal_denominator
        if distal_cosine > 0:
            return "folded"

    palm_length = _length(_subtract(_point(landmarks[9]), wrist))
    finger_reach = _length(_subtract(tip, base))
    if palm_length > 1e-6 and finger_reach < palm_length * 0.75 and cosine > -0.8:
        return "folded"
    tip_distance = _length(_subtract(tip, wrist))
    joint_distance = _length(_subtract(joint, wrist))
    if cosine < -0.65 and tip_distance > joint_distance * 1.05:
        return "extended"
    if cosine > -0.2 or tip_distance < joint_distance * 0.95:
        return "folded"
    return "uncertain"


def detect_static_gesture(hand):
    fingers = [
        _finger_state(hand.landmark, base, joint, tip)
        for base, joint, tip in [(5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)]
    ]
    # Allow one uncertain finger instead of losing the whole pose for a frame.
    if fingers.count("extended") >= 3:
        return "OPEN_PALM"
    if fingers.count("folded") >= 3 and fingers[0] != "extended":
        return "CLOSED_FIST"
    if (
        fingers[0] == "extended"
        and fingers[1:].count("folded") >= 2
        and "extended" not in fingers[1:]
    ):
        return "SELECT_PRODUCT"
    return None
