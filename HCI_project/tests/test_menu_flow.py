import socket
import threading
import time
import json
import select
import tkinter as tk
import unittest
from concurrent.futures import Future
from unittest.mock import patch

from gesture_controller import GestureController
from menu_connection import MenuConnection
from menu_server_gui import GestureRequest, gesture_queue, handle_client, process_gestures
from menu_ui import RestaurantMenuUI
from pathlib import Path


class MenuFlowTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = RestaurantMenuUI(self.root)
        self.connections = []
        self.workers = []

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        for worker in self.workers:
            worker.join(timeout=2)
        for callback in self.root.tk.call("after", "info"):
            self.root.after_cancel(callback)
        self.root.destroy()
        while not gesture_queue.empty():
            gesture_queue.get_nowait()

    def connection(self):
        server_end, client_end = socket.socketpair()
        client_end.settimeout(2)
        with patch("menu_connection.socket.create_connection", return_value=client_end):
            connection = MenuConnection()
        worker = threading.Thread(
            target=handle_client, args=(server_end, "integration test"), daemon=True
        )
        worker.start()
        self.connections.append(connection)
        self.workers.append(worker)
        self.root.after(0, process_gestures, self.root, self.app)
        return connection

    def request(self, connection, command):
        result = Future()

        def send():
            try:
                result.set_result(connection.request(command))
            except Exception as error:
                result.set_exception(error)

        threading.Thread(target=send, daemon=True).start()
        deadline = time.monotonic() + 3
        while not result.done() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.001)
        self.assertTrue(result.done(), "Menu did not acknowledge the command")
        return result.result()

    def button(self, text):
        return self.app.action(text=text)

    def test_open_navigate_select_back_and_close(self):
        self.app.handle_gesture("OPEN_PALM")
        self.assertTrue(self.app.menu_open)
        self.app.handle_gesture("SWIPE_RIGHT")
        self.assertEqual(self.app.categories[self.app.current_index], "Snacks")
        self.app.handle_gesture("SELECT_PRODUCT:2")
        self.assertEqual(self.app.selected_item, "House burger")
        self.app.handle_gesture("OPEN_PALM")
        self.assertIsNone(self.app.selected_item)
        self.assertEqual(self.button("Drinks").cget("text"), "Drinks")
        self.app.handle_gesture("SWIPE_LEFT")
        self.assertEqual(self.app.current_index, 1)
        self.app.handle_gesture("CLOSED_FIST")
        self.assertFalse(self.app.menu_open)
        self.assertFalse(self.app.main_frame.winfo_manager())

    def test_mouse_buttons_still_navigate_and_select(self):
        self.app.show_menu()
        self.button("Drinks").invoke()
        self.assertEqual(self.app.current_index, 3)
        self.app.action(key="select:1").invoke()
        self.assertEqual(self.app.selected_item, "Hibiscus cooler")
        self.button("BACK TO MENU").invoke()
        self.button("Desserts").invoke()
        self.assertEqual(self.app.current_index, 4)

    def test_invalid_product_does_not_break_next_gesture(self):
        self.app.handle_gesture("OPEN_PALM")
        for command in ["SELECT_PRODUCT:bad", "SELECT_PRODUCT:-1", "SELECT_PRODUCT:99"]:
            self.app.handle_gesture(command)
            self.assertIsNone(self.app.selected_item)
        self.app.handle_gesture("SELECT_PRODUCT")
        self.assertEqual(self.app.selected_item, "House burger")

    def test_detected_motion_reaches_menu_through_socket_and_gui_queue(self):
        controller = GestureController()
        connection = self.connection()
        now = 0

        def feed(pose, positions, finger_x=None):
            nonlocal now
            for position in positions:
                now += 1 / 30
                command = controller.update(pose, position, now, finger_x)
                if command:
                    response = self.request(connection, command)
                    self.assertTrue(response["ok"])
                    self.assertEqual(response["gesture"], command)
                    controller.confirm_menu_state(response["state"]["menu_open"])

        feed("OPEN_PALM", [(0.2, 0.5)] * 20)
        self.assertTrue(self.app.menu_open)
        feed("OPEN_PALM", [(0.2 + i * 0.02, 0.5) for i in range(1, 16)])
        self.assertEqual(self.app.current_index, 2)
        feed("SELECT_PRODUCT", [(0.5, 0.5)] * 40, finger_x=0.5)
        self.assertEqual(self.app.selected_item, "Lemon grilled chicken")
        feed("OPEN_PALM", [(0.5, 0.5)] * 20)
        self.assertIsNone(self.app.selected_item)
        feed("OPEN_PALM", [(0.5 - i * 0.004, 0.5) for i in range(1, 36)])
        self.assertEqual(self.app.current_index, 1)
        feed("CLOSED_FIST", [(0.36 + i * 0.006, 0.5 + i * 0.005) for i in range(1, 21)])
        self.assertFalse(self.app.menu_open)
        self.assertFalse(controller.menu_open)

    def test_response_waits_until_menu_has_applied_gesture(self):
        connection = self.connection()
        connection.socket.sendall(b"OPEN_PALM\n")
        ready, _, _ = select.select([connection.socket], [], [], 0.05)
        self.assertEqual(ready, [])
        self.assertFalse(self.app.menu_open)
        deadline = time.monotonic() + 3
        while not ready and time.monotonic() < deadline:
            self.root.update()
            ready, _, _ = select.select([connection.socket], [], [], 0.001)
        self.assertTrue(ready)
        response = json.loads(connection.reader.readline())
        self.assertTrue(response["ok"])
        self.assertTrue(response["state"]["menu_open"])
        self.assertTrue(self.app.menu_open)

    def test_status_reports_existing_menu_state_without_changing_it(self):
        self.app.show_menu()
        self.app.select_item("Lemon grilled chicken")
        response = self.request(self.connection(), "STATUS")
        self.assertTrue(response["ok"])
        self.assertTrue(response["state"]["menu_open"])
        self.assertEqual(response["state"]["selected_item"], "Lemon grilled chicken")

    def test_quantity_add_remove_and_undo_keep_the_order_consistent(self):
        self.app.show_menu()
        self.app.select_item("House burger")
        self.app.action(text="Increase quantity").invoke()
        self.app.action(key="add-detail").invoke()
        self.assertEqual(self.app.cart, {"House burger": 2})
        self.app.add_to_order("Fresh orange juice")
        self.assertEqual((self.app.order_count, self.app.order_total), (3, 650))
        self.app.show_order()
        self.app.action(text="Remove House burger").invoke()
        self.assertEqual(self.app.order_total, 90)
        self.app.action(text="Undo").invoke()
        self.assertEqual(self.app.order_total, 650)
        self.app.close_menu()
        self.app.show_menu()
        self.assertEqual(self.app.order_count, 3)

    def test_unavailable_item_cannot_be_added(self):
        self.app.show_menu()
        self.app.action(key="add:Garden fattoush").invoke()
        self.assertFalse(self.app.cart)
        self.app.select_item("Garden fattoush")
        self.app.action(key="add-detail").invoke()
        self.assertFalse(self.app.cart)

    def test_touch_and_camera_switches_are_in_confirmed_state(self):
        self.app.show_menu()
        self.app.action(text="Use touch instead").invoke()
        self.assertFalse(self.app.get_state()["hand_control_enabled"])
        self.assertFalse(self.app.handle_gesture("CLOSED_FIST"))
        self.assertTrue(self.app.menu_open)
        self.app.action(text="Drinks").invoke()
        self.assertEqual(self.app.current_index, 3)
        self.app.action(text="Use hand control").invoke()
        self.app.action(text="Turn camera off").invoke()
        state = self.request(self.connection(), "STATUS")["state"]
        self.assertFalse(state["camera_enabled"])
        self.assertFalse(state["hand_control_enabled"])
        self.app.action(text="Turn camera on").invoke()
        self.assertTrue(self.app.get_state()["camera_enabled"])

    def test_menu_hit_targets_follow_window_resizing(self):
        self.app.show_menu()
        self.root.deiconify()
        for geometry, category in [("1100x740", "Drinks"), ("980x600", "Desserts")]:
            self.root.geometry(geometry)
            self.root.update()
            self.app._resize()
            action = self.app.action(text=category)
            scale, x, y = self.app._transform
            left, top, right, bottom = action.rect
            self.app.menu_canvas.event_generate("<Button-1>",
                x=round(x + (left + right) / 2 * scale),
                y=round(y + (top + bottom) / 2 * scale))
            self.root.update()
            self.assertEqual(self.app.categories[self.app.current_index], category)

    def test_original_figma_assets_fill_the_menu_slots(self):
        self.app.show_menu()
        slots = dict(self.app.renderer.asset_slots)
        for name, expected_x in [("interactive_imgFoodPhotograph.png", 236),
                                 ("interactive_imgFoodPhotograph1.png", 549.333),
                                 ("interactive_imgFoodPhotograph2.png", 862.666)]:
            self.assertAlmostEqual(slots[name][0], expected_x, places=2)
            self.assertEqual(slots[name][1], 322)
        asset_root = Path(__file__).resolve().parents[1] / "assets" / "figma"
        for name, box in self.app.renderer.asset_slots:
            self.assertGreater((asset_root / name).stat().st_size, 0)
            self.assertGreater(box[2] - box[0], 0)
            self.assertGreater(box[3] - box[1], 0)

    def test_mouse_targets_work_after_scrolling(self):
        self.app.show_menu()
        self.root.deiconify()
        self.root.geometry("1000x600")
        self.root.update()
        self.app._resize()
        self.app.menu_canvas.yview_moveto(1)
        self.root.update()
        action = self.app.action(text="Review order")
        scale, x, y = self.app._transform
        left, top, right, bottom = action.rect
        viewport_top = self.app.menu_canvas.canvasy(0)
        self.app.menu_canvas.event_generate("<Button-1>",
            x=round(x + (left + right) / 2 * scale),
            y=round(y + (top + bottom) / 2 * scale - viewport_top))
        self.root.update()
        self.assertEqual(self.app.screen, "order")

    def test_orders_with_more_than_three_dishes_can_be_paged(self):
        self.app.show_menu()
        for name in ["House burger", "Fresh orange juice", "Hibiscus cooler", "Mint lemonade"]:
            self.app.add_to_order(name)
        self.app.show_order()
        self.app.action(text="More items").invoke()
        self.assertEqual(self.app.order_page, 1)
        self.app.action(text="Remove Mint lemonade").invoke()
        self.assertNotIn("Mint lemonade", self.app.cart)

    def test_keyboard_focus_and_arrow_navigation_work(self):
        self.app.show_menu()
        self.root.deiconify()
        self.root.update()
        canvas = self.app.menu_canvas
        canvas.focus_force()
        self.root.update()
        enabled = [action for action in self.app.actions if action.enabled]
        drinks_index = next(index for index, action in enumerate(enabled) if action.text == "Drinks")
        for _ in range(drinks_index + 1):
            canvas.event_generate("<KeyPress-Tab>")
        canvas.event_generate("<KeyPress-Return>")
        self.root.update()
        self.assertEqual(self.app.categories[self.app.current_index], "Drinks")
        canvas.event_generate("<KeyPress-Right>")
        self.root.update()
        self.assertEqual(self.app.categories[self.app.current_index], "Desserts")

    def test_failed_action_does_not_stop_later_gestures(self):
        connection = self.connection()
        self.request(connection, "OPEN_PALM")
        with patch.object(self.app, "handle_gesture", side_effect=RuntimeError("Test failure")):
            with patch("menu_server_gui.traceback.print_exc"):
                response = self.request(connection, "CLOSED_FIST")
        self.assertFalse(response["ok"])
        self.assertTrue(response["state"]["menu_open"])
        response = self.request(connection, "CLOSED_FIST")
        self.assertTrue(response["ok"])
        self.assertFalse(response["state"]["menu_open"])

    def test_expired_request_is_not_applied_later(self):
        request = GestureRequest("OPEN_PALM")
        request.reply.cancel()
        gesture_queue.put(request)
        process_gestures(self.root, self.app)
        self.assertFalse(self.app.menu_open)


if __name__ == "__main__":
    unittest.main()
