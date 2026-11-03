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
    def test_one_click_per_pinch_at_different_camera_rates(self):
        for fps in (10, 20, 60):
            hand = HandInput()
            events = [hand.update(.4, .5, .8, "point", 0)]
            events += [hand.update(.41, .51, .2, "point", n / fps) for n in range(1, fps * 2)]
            clicks = [event for event in events if event["action"] == "click"]
            self.assertEqual(len(clicks), 1, fps)
            self.assertAlmostEqual(clicks[0]["x"], events[1]["x"])

    def test_pinch_must_open_before_first_click_and_after_hand_loss(self):
        hand = HandInput()
        for t in (0, .5, 1):
            self.assertNotEqual(hand.update(.5, .5, .2, "point", t)["action"], "click")
        hand.update(.5, .5, .8, "point", 1.1)
        hand.update(.5, .5, .2, "point", 1.2)
        self.assertEqual(hand.update(.5, .5, .2, "point", 1.4)["action"], "click")
        hand.lost()
        self.assertNotEqual(hand.update(.5, .5, .2, "point", 3)["action"], "click")

    def test_release_allows_another_pinch_and_jitter_does_not_click(self):
        hand = HandInput()
        hand.update(.3, .3, .8, "point", 0)
        hand.update(.3, .3, .2, "point", .1)
        self.assertNotEqual(hand.update(.3, .3, .8, "point", .15)["action"], "click")
        hand.update(.3, .3, .2, "point", .2)
        self.assertEqual(hand.update(.3, .3, .2, "point", .4)["action"], "click")
        hand.update(.3, .3, .8, "point", 1)
        hand.update(.3, .3, .2, "point", 1.1)
        self.assertEqual(hand.update(.3, .3, .2, "point", 1.3)["action"], "click")

    def test_fist_is_one_back_action_per_hold_and_scroll_never_selects(self):
        hand = HandInput()
        events = [hand.update(.5, .5, .1, "back", t / 10) for t in range(20)]
        self.assertEqual(sum(e["action"] == "back" for e in events), 1)
        hand.update(.5, .5, .8, "scroll", 3)
        event = hand.update(.5, .4, .8, "scroll", 3.1)
        self.assertEqual(event["action"], "scroll")
        self.assertGreater(event["delta"], 0)


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
