"""Gesture intent and BLE range checks, independent of a webcam or radio."""
import asyncio
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from hand_input import HandInput
from link_health import SignalGuard
import test_bluetooth as fixtures


class HandIntentTests(unittest.TestCase):
    def test_one_finger_hold_selects_once_at_any_camera_rate(self):
        for fps in (10, 20, 60):
            hand = HandInput()
            events = [hand.step("select", .5, .5, n / fps) for n in range(fps * 2)]
            self.assertEqual(sum(e["action"] == "select" for e in events), 1, fps)

    def test_select_needs_release_and_a_still_hand(self):
        hand = HandInput()
        hand.step("select", .5, .5, 0)
        self.assertEqual(hand.step("select", .5, .5, .4)["action"], "select")
        self.assertNotEqual(hand.step("select", .5, .5, 1.5)["action"], "select")
        hand.step("pause", .5, .5, 1.6)
        hand.step("pause", .5, .5, 1.9)   # released for longer than the grace period
        hand.step("select", .5, .5, 2.0)
        self.assertEqual(hand.step("select", .5, .5, 2.4)["action"], "select")
        # Moving the hand around (not a swipe) keeps restarting the hold.
        hand = HandInput()
        events = [hand.step("select", .3 + n * .03, .5, n / 20) for n in range(12)]
        self.assertFalse(any(e["action"] == "select" for e in events))

    def test_select_survives_one_frame_of_tracking_flicker(self):
        hand = HandInput()
        poses = ["select", "select", "pause", "select", "scroll", "select", "select", "select"]
        events = [hand.step(pose, .5, .5, n / 20) for n, pose in enumerate(poses)]
        self.assertEqual(sum(e["action"] == "select" for e in events), 1)

    def test_small_wobble_while_raising_the_finger_still_selects(self):
        hand = HandInput()
        events = [hand.step("select", .5 + (n % 3) * .025, .5 + (n % 2) * .02, n / 20) for n in range(10)]
        self.assertEqual(sum(e["action"] == "select" for e in events), 1)

    def test_fast_palm_movement_is_one_swipe_in_its_direction(self):
        for (dx, dy), direction in (((.3, 0), "right"), ((-.3, 0), "left"), ((0, .3), "down"), ((0, -.3), "up")):
            hand = HandInput()
            events = [hand.step("menu", .5 + dx * n / 6, .5 + dy * n / 6, n / 30) for n in range(7)]
            events += [hand.step("menu", .5 + dx, .5 + dy, .2 + n / 30) for n in range(10)]
            swipes = [e["direction"] for e in events if e["action"] == "swipe"]
            self.assertEqual(swipes, [direction])
            self.assertFalse(any(e["action"] == "shortcut" for e in events))

    def test_fist_is_one_back_action_per_hold_and_small_two_finger_moves_only_scroll(self):
        hand = HandInput()
        events = [hand.step("back", .5, .5, t / 10) for t in range(20)]
        self.assertEqual(sum(e["action"] == "back" for e in events), 1)
        hand.step("scroll", .5, .5, 3)
        event = hand.step("scroll", .5, .53, 3.1)
        self.assertEqual(event["action"], "scroll")
        self.assertGreater(event["delta"], 0)


class TwoFingerMoveTests(unittest.TestCase):
    def moves(self, path, fps=10):
        hand = HandInput()
        events = [hand.step("scroll", x, y, n / fps) for n, (x, y) in enumerate(path)]
        return [e["direction"] for e in events if e["action"] == "swipe"], events

    def test_two_fingers_move_the_highlight_in_all_four_directions(self):
        for (dx, dy), direction in (((-.02, 0), "left"), ((.02, 0), "right"), ((0, .02), "down"), ((0, -.02), "up")):
            steps, events = self.moves([(.5 + dx * n, .5 + dy * n) for n in range(20)])
            self.assertIn(len(steps), (2, 3), direction)    # 2 s of travel, >= .7 s apart
            self.assertEqual(set(steps), {direction})
            self.assertTrue(all(e.get("source") == "scroll" for e in events if e["action"] == "swipe"))

    def test_fast_two_finger_movement_waits_between_steps(self):
        steps, _ = self.moves([(.7 - n * .03, .5) for n in range(20)], fps=30)
        self.assertEqual(len(steps), 1)                    # .57 of travel in .63 s -> one step

    def test_slow_drift_and_jitter_do_not_move_the_highlight(self):
        steps, _ = self.moves([(.5 + n * .002 + (n % 2) * .01, .5 + (n % 3) * .008) for n in range(60)], fps=20)
        self.assertEqual(steps, [])

    def test_swipes_are_at_least_a_second_apart(self):
        hand = HandInput()
        t, fired = 0.0, []
        for _ in range(6):                                 # back-and-forth swipes every .3 s
            for n in range(7):
                event = hand.step("menu", .3 + .4 * n / 6 * (1 if len(fired) % 2 == 0 else -1) + (0 if len(fired) % 2 == 0 else .4), .5, t)
                if event["action"] == "swipe":
                    fired.append(t)
                t += 1 / 30
            t += .1
        gaps = [b - a for a, b in zip(fired, fired[1:])]
        self.assertTrue(fired)
        self.assertTrue(all(gap >= 1.0 for gap in gaps), gaps)


class ShortcutGestureTests(unittest.TestCase):
    """Synthetic upright hands: wrist at the bottom, knuckles across y=.6."""
    THUMBS = {"tucked": (.47, .58), "up": (.40, .33), "down": (.40, .85), "side": (.22, .62),
              "c": (.50, .66), "ok": (.43, .61)}

    @classmethod
    def hand(cls, fingers, thumb):
        pts = [SimpleNamespace(x=.5, y=.9) for _ in range(21)]
        for state, (mcp, x) in zip(fingers, ((5, .42), (9, .48), (13, .54), (17, .60))):
            pts[mcp] = SimpleNamespace(x=x, y=.6)
            pts[mcp + 1] = SimpleNamespace(x=x, y=.5)
            if state == "up":
                pts[mcp + 2], pts[mcp + 3] = SimpleNamespace(x=x, y=.45), SimpleNamespace(x=x, y=.35)
            elif state == "curve":  # bent ~90 degrees, as in a C
                pts[mcp + 2], pts[mcp + 3] = SimpleNamespace(x=x + .03, y=.46), SimpleNamespace(x=x + .09, y=.46)
            else:  # folded into the palm
                pts[mcp + 2], pts[mcp + 3] = SimpleNamespace(x=x, y=.6), SimpleNamespace(x=x, y=.62)
        pts[4] = SimpleNamespace(x=cls.THUMBS[thumb][0], y=cls.THUMBS[thumb][1])
        return SimpleNamespace(landmark=pts)

    def poses(self, fingers, thumb):
        hand = HandInput()
        return [hand.from_landmarks(self.hand(fingers, thumb), t / 10) for t in range(12)]

    def test_each_gesture_from_the_guide_fires_once_per_hold(self):
        down, up, curve = "down", "up", "curve"
        cases = {
            "menu": ([up, up, up, up], "side"),            # open palm
            "add": ([down] * 4, "up"),                      # thumbs up
            "decline": ([down] * 4, "down"),                # thumbs down
            "cart": ([curve, curve, curve, curve], "c"),    # C shape
            "games": ([up, down, down, up], "tucked"),      # rock sign
            "rewards": ([up, up, up, down], "tucked"),      # three fingers
        }
        for name, (fingers, thumb) in cases.items():
            events = self.poses(fingers, thumb)
            self.assertEqual(events[0]["pose"], name)
            fired = [e["shortcut"] for e in events if e["action"] == "shortcut"]
            self.assertEqual(fired, [name], name)

    def test_ok_sign_is_checkout_after_its_hold(self):
        hand = HandInput()
        ok = self.hand(["down", "up", "up", "up"], "ok")
        events = [hand.from_landmarks(ok, t / 10) for t in range(12)]
        self.assertEqual(events[0]["pose"], "checkout")
        self.assertEqual([e.get("shortcut") for e in events if e["action"] == "shortcut"], ["checkout"])

    def test_fist_is_back_and_one_finger_selects(self):
        events = self.poses(["down"] * 4, "tucked")
        self.assertEqual(events[0]["pose"], "back")
        self.assertEqual(sum(e["action"] == "back" for e in events), 1)
        events = self.poses(["up", "down", "down", "down"], "tucked")
        self.assertEqual(events[0]["pose"], "select")
        self.assertEqual(sum(e["action"] == "select" for e in events), 1)


class RangeTests(unittest.TestCase):
    def test_persistent_weak_signal_disconnects_but_single_dip_does_not(self):
        health = SignalGuard()
        self.assertFalse(health.observe(-90, 0))
        self.assertFalse(health.observe(-45, .5))
        self.assertFalse(health.observe(-45, 1))
        self.assertFalse(health.observe(-45, 5))
        health = SignalGuard()
        decisions = [health.observe(-90, t / 2) for t in range(10)]
        self.assertFalse(any(decisions[:8]))
        self.assertTrue(decisions[-1])

    def test_missing_adverts_and_windows_sentinel_are_not_distance(self):
        health = SignalGuard()
        self.assertFalse(health.observe(-127, 0))
        self.assertIsNone(health.snapshot(1)["rssi"])
        self.assertFalse(health.observe(-90, 1))
        self.assertEqual(health.snapshot(5)["mode"], "link")
        self.assertFalse(health.observe(-90, 8))

    def test_signal_recovery_cancels_pending_disconnect(self):
        health = SignalGuard()
        health.observe(-85, 0)
        for n in range(1, 8):
            self.assertFalse(health.observe(-40, n / 2))
        self.assertIsNone(health.weak_since)


class LiveLinkChecks(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.BluetoothWorkerTests.asyncSetUp
    asyncTearDown = fixtures.BluetoothWorkerTests.asyncTearDown
    scan = fixtures.BluetoothWorkerTests.scan
    next_event = fixtures.BluetoothWorkerTests.next_event
    async def test_failed_uncached_reads_disconnect_a_stuck_native_link(self):
        with patch('bluetooth_connection.LINK_CHECK_INTERVAL', .01):
            await self.scan()
            self.monitor.connect("AA")
            _, connection_id = await self.next_event("connected")
            self.clients[-1].read_gatt_char = AsyncMock(side_effect=TimeoutError())
            result = await self.next_event("disconnected")
            self.assertEqual(result["session_id"], connection_id)
            self.assertIn("no longer responding", result["message"])
            self.assertFalse(self.monitor.is_connected)
            self.assertGreaterEqual(self.clients[-1].read_gatt_char.await_count, 2)

    async def test_an_identity_change_locks_instead_of_switching_users(self):
        with patch('bluetooth_connection.LINK_CHECK_INTERVAL', .01):
            await self.scan()
            self.monitor.connect("AA")
            await self.next_event("connected")
            self.clients[-1].identity = b"another-phone"
            self.assertIn("identity changed", (await self.next_event("disconnected"))["message"])

    async def test_only_the_connected_phone_can_trigger_a_range_disconnect(self):
        watchers = []

        class Scanner(fixtures.FakeScanner):
            def __init__(self, detection_callback):
                self.callback = detection_callback
                self.stopped = False
                watchers.append(self)
            async def start(self): pass
            async def stop(self): self.stopped = True

        self.monitor._scanner = Scanner
        with patch('bluetooth_connection.SignalGuard', lambda: SignalGuard(grace=.02)):
            await self.scan()
            self.monitor.connect("AA")
            await self.next_event("connected")
            await self.next_event("signal")
            watcher = watchers[-1]
            watcher.callback(SimpleNamespace(address="ZZ"), SimpleNamespace(rssi=-95))
            self.assertTrue(self.monitor.is_connected)
            for _ in range(4):
                watcher.callback(SimpleNamespace(address="AA"), SimpleNamespace(rssi=-90))
                await asyncio.sleep(.015)
            self.assertFalse(self.monitor.is_connected)
            self.assertIn("signal stayed weak", (await self.next_event("disconnected"))["message"])
            await asyncio.sleep(.05)
            self.assertTrue(watcher.stopped)


if __name__ == '__main__':
    unittest.main()
