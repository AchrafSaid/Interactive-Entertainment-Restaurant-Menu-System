import unittest

from gesture_controller import GestureController


class GestureControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = GestureController()
        self.now = 0

    def frame(self, pose, position, finger_x=None):
        self.now += 1 / 30
        command = self.controller.update(pose, position, self.now, finger_x)
        # Model the menu's successful acknowledgement for controller-only tests.
        if command in ("OPEN_PALM", "CLOSED_FIST"):
            self.controller.confirm_menu_state(command == "OPEN_PALM")
        return command

    def hold(self, pose, position=(0.2, 0.5), finger_x=None, frames=20):
        commands = []
        for _ in range(frames):
            command = self.frame(pose, position, finger_x)
            if command:
                commands.append(command)
        return commands

    def test_open_palm_is_sent_once_per_hold(self):
        self.assertEqual(self.hold("OPEN_PALM", frames=90), ["OPEN_PALM"])
        self.assertTrue(self.controller.menu_open)

    def test_open_palm_swipes_right(self):
        self.hold("OPEN_PALM")
        commands = [
            self.frame("OPEN_PALM", (0.2 + index * 0.02, 0.5))
            for index in range(1, 16)
        ]
        self.assertEqual([command for command in commands if command], ["SWIPE_RIGHT"])

    def test_open_palm_swipes_left(self):
        self.hold("OPEN_PALM", (0.8, 0.5))
        commands = [
            self.frame("OPEN_PALM", (0.8 - index * 0.02, 0.5))
            for index in range(1, 16)
        ]
        self.assertEqual([command for command in commands if command], ["SWIPE_LEFT"])

    def test_pointing_while_swiping_does_not_select(self):
        self.hold("OPEN_PALM")
        commands = [
            self.frame("SELECT_PRODUCT", (0.2 + index * 0.02, 0.5))
            for index in range(1, 16)
        ]
        self.assertEqual([command for command in commands if command], ["SWIPE_RIGHT"])

    def test_pointing_can_select_every_product(self):
        self.hold("OPEN_PALM")
        for finger_x, index in [(0.1, 0), (0.5, 1), (0.9, 2)]:
            self.assertEqual(
                self.hold("SELECT_PRODUCT", finger_x=finger_x),
                [f"SELECT_PRODUCT:{index}"],
            )
            self.assertEqual(self.hold("OPEN_PALM"), ["OPEN_PALM"])

    def test_can_select_again_after_returning_to_menu(self):
        self.hold("OPEN_PALM")
        self.assertEqual(self.hold("SELECT_PRODUCT"), ["SELECT_PRODUCT:0"])
        self.assertEqual(self.hold("OPEN_PALM"), ["OPEN_PALM"])
        self.assertEqual(self.hold("SELECT_PRODUCT"), ["SELECT_PRODUCT:0"])

    def test_small_hand_jitter_does_not_navigate(self):
        self.hold("OPEN_PALM")
        commands = [
            self.frame("OPEN_PALM", (0.2 + (-1) ** index * 0.002, 0.5))
            for index in range(60)
        ]
        self.assertFalse(any(commands))

    def test_vertical_movement_does_not_navigate(self):
        self.hold("OPEN_PALM")
        commands = [
            self.frame("OPEN_PALM", (0.2, 0.5 + index * 0.02))
            for index in range(1, 16)
        ]
        self.assertFalse(any(commands))

    def test_lost_hand_does_not_create_a_swipe_on_return(self):
        self.hold("OPEN_PALM")
        self.frame(None, None)
        commands = self.hold("OPEN_PALM", (0.8, 0.5))
        self.assertNotIn("SWIPE_RIGHT", commands)
        self.assertNotIn("SWIPE_LEFT", commands)

    def test_pointing_cannot_select_with_menu_closed(self):
        self.assertEqual(self.hold("SELECT_PRODUCT"), [])
        self.hold("OPEN_PALM")
        self.assertEqual(self.hold("CLOSED_FIST"), ["CLOSED_FIST"])
        self.assertFalse(self.controller.menu_open)
        self.assertEqual(self.hold("SELECT_PRODUCT"), [])

    def test_product_index_is_clamped_at_camera_edges(self):
        self.assertEqual(self.controller.product_index(-0.1), 0)
        self.assertEqual(self.controller.product_index(1.1), 2)

    def test_hold_survives_one_uncertain_frame_at_a_time(self):
        commands = [
            self.frame(None if index % 6 == 0 else "OPEN_PALM", (0.2, 0.5))
            for index in range(30)
        ]
        self.assertEqual([command for command in commands if command], ["OPEN_PALM"])

    def test_selection_survives_jitter_at_an_item_boundary(self):
        self.hold("OPEN_PALM")
        commands = [
            self.frame("SELECT_PRODUCT", (0.2, 0.5), 1 / 3 + (-1) ** index * 0.008)
            for index in range(30)
        ]
        selections = [command for command in commands if command]
        self.assertEqual(len(selections), 1)
        self.assertTrue(selections[0].startswith("SELECT_PRODUCT:"))

    def test_small_tremor_does_not_prevent_a_held_pose(self):
        commands = [
            self.frame("OPEN_PALM", (0.2 + (-1) ** index * 0.016, 0.5))
            for index in range(30)
        ]
        self.assertEqual([command for command in commands if command], ["OPEN_PALM"])

    def test_hold_survives_brief_tracking_dropout(self):
        commands = [
            self.frame("OPEN_PALM", None if index % 7 == 0 else (0.2, 0.5))
            for index in range(30)
        ]
        self.assertEqual([command for command in commands if command], ["OPEN_PALM"])

    def test_swipes_work_at_five_frames_per_second(self):
        self.hold("OPEN_PALM")
        commands = []
        for index in range(1, 8):
            self.now += 0.2
            command = self.controller.update(
                "OPEN_PALM", (0.2 + index * 0.04, 0.5), self.now
            )
            if command:
                commands.append(command)
        self.assertEqual(commands, ["SWIPE_RIGHT"])

    def test_menu_state_changes_only_after_confirmation(self):
        commands = [
            self.controller.update("OPEN_PALM", (0.2, 0.5), index / 30)
            for index in range(20)
        ]
        self.assertIn("OPEN_PALM", commands)
        self.assertFalse(self.controller.menu_open)
        self.controller.confirm_menu_state(True)
        self.assertTrue(self.controller.menu_open)

    def test_wrong_pose_for_one_frame_does_not_reset_hold(self):
        commands = [
            self.frame("CLOSED_FIST" if index % 6 == 0 else "OPEN_PALM", (0.2, 0.5))
            for index in range(30)
        ]
        self.assertEqual([command for command in commands if command], ["OPEN_PALM"])

    def test_slow_swipes_in_both_directions(self):
        for direction, expected in [(1, "SWIPE_RIGHT"), (-1, "SWIPE_LEFT")]:
            with self.subTest(direction=direction):
                self.setUp()
                self.hold("OPEN_PALM", (0.5, 0.5))
                commands = [
                    self.frame("OPEN_PALM", (0.5 + direction * index * 0.004, 0.5))
                    for index in range(1, 36)
                ]
                self.assertEqual([command for command in commands if command], [expected])

    def test_short_fast_swipes_need_only_three_tracked_frames(self):
        for direction, expected in [(1, "SWIPE_RIGHT"), (-1, "SWIPE_LEFT")]:
            with self.subTest(direction=direction):
                self.setUp()
                self.hold("OPEN_PALM", (0.5, 0.5))
                commands = []
                for index in range(1, 3):
                    self.now += 0.125
                    command = self.controller.update(
                        "OPEN_PALM", (0.5 + direction * index * 0.05, 0.5), self.now
                    )
                    if command:
                        commands.append(command)
                self.assertEqual(commands, [expected])

    def test_fist_can_close_while_the_hand_drifts(self):
        self.hold("OPEN_PALM")
        commands = [
            self.frame("CLOSED_FIST", (0.2 + index * 0.006, 0.5 + index * 0.005))
            for index in range(1, 31)
        ]
        self.assertEqual([command for command in commands if command], ["CLOSED_FIST"])
        self.assertFalse(self.controller.menu_open)


if __name__ == "__main__":
    unittest.main()
