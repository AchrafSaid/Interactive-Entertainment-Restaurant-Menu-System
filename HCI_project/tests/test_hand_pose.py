import math
from types import SimpleNamespace
import unittest

from hand_pose import detect_static_gesture


def hand(states, rotation=0):
    points = [(0, 0)] * 21
    for index, state in enumerate(states):
        base = 5 + index * 4
        x, y = (index - 1.5) * 0.3, 0.7
        points[base] = x, y
        points[base + 1] = x, y + 0.3
        if state == "extended":
            points[base + 2] = x, y + 0.5
            points[base + 3] = x, y + 0.7
        elif state == "folded":
            points[base + 2] = x, y + 0.1
            points[base + 3] = x, y - 0.1
        elif state == "hooked":
            points[base + 2] = x, y + 0.5
            points[base + 3] = x, y + 0.4
        elif state == "relaxed_fold":
            points[base + 2] = x + 0.12, y + 0.42
            points[base + 3] = x + 0.17, y + 0.4
        else:
            points[base + 3] = x + 0.25, y + 0.3 + 0.25 / math.sqrt(3)
            points[base + 2] = x + 0.125, y + 0.3 + 0.125 / math.sqrt(3)
    angle = math.radians(rotation)
    return SimpleNamespace(landmark=[
        SimpleNamespace(x=x * math.cos(angle) - y * math.sin(angle),
                        y=x * math.sin(angle) + y * math.cos(angle), z=0)
        for x, y in points
    ])


class HandPoseTests(unittest.TestCase):
    def test_poses_work_when_the_hand_is_rotated(self):
        for rotation in [0, 45, 90, 135, 180, 270]:
            for states, expected in [
                (["extended"] * 4, "OPEN_PALM"),
                (["folded"] * 4, "CLOSED_FIST"),
                (["extended", "folded", "folded", "folded"], "SELECT_PRODUCT"),
            ]:
                with self.subTest(rotation=rotation, expected=expected):
                    self.assertEqual(detect_static_gesture(hand(states, rotation)), expected)

    def test_an_uncertain_pinky_does_not_lose_selection(self):
        self.assertEqual(detect_static_gesture(hand(
            ["extended", "folded", "folded", "uncertain"]
        )), "SELECT_PRODUCT")

    def test_an_uncertain_finger_does_not_lose_open_or_closed_pose(self):
        self.assertEqual(detect_static_gesture(hand(
            ["extended", "extended", "extended", "uncertain"]
        )), "OPEN_PALM")
        self.assertEqual(detect_static_gesture(hand(
            ["folded", "folded", "folded", "uncertain"]
        )), "CLOSED_FIST")

    def test_two_extended_fingers_are_not_a_point_or_palm(self):
        self.assertIsNone(detect_static_gesture(hand(
            ["extended", "extended", "folded", "folded"]
        )))

    def test_degenerate_landmarks_do_not_close_menu(self):
        empty = SimpleNamespace(landmark=[SimpleNamespace(x=0, y=0, z=0)] * 21)
        self.assertIsNone(detect_static_gesture(empty))

    def test_curled_fingertips_are_a_fist_even_above_middle_joints(self):
        for rotation in [0, 45, 90, 180]:
            with self.subTest(rotation=rotation):
                self.assertEqual(
                    detect_static_gesture(hand(["hooked"] * 4, rotation)), "CLOSED_FIST"
                )

    def test_compact_fist_does_not_require_perfect_joint_angles(self):
        for rotation in [0, 45, 90, 180]:
            with self.subTest(rotation=rotation):
                self.assertEqual(
                    detect_static_gesture(hand(["relaxed_fold"] * 4, rotation)), "CLOSED_FIST"
                )

    def test_fist_tolerates_one_misread_non_index_finger(self):
        self.assertEqual(detect_static_gesture(hand(
            ["folded", "folded", "folded", "extended"]
        )), "CLOSED_FIST")

    def test_pointing_with_curled_other_fingers_still_selects(self):
        self.assertEqual(detect_static_gesture(hand(
            ["extended", "hooked", "hooked", "hooked"]
        )), "SELECT_PRODUCT")


if __name__ == "__main__":
    unittest.main()
