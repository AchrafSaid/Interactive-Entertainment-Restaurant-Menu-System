"""Interactive OLIVE / TABLE menu, styled from the supplied Figma file."""

import tkinter as tk
from PIL import Image, ImageTk

from menu_data import CATEGORIES, DISHES
from menu_design import MenuRenderer, CANVAS, FOREST


class RestaurantMenuUI:
    def __init__(self, root):
        self.root = root
        root.title("OLIVE / TABLE — Interactive Restaurant Menu")
        width = min(1194, root.winfo_screenwidth() - 100)
        height = min(934, root.winfo_screenheight() - 110)
        root.geometry(f"{width}x{height}")
        root.minsize(960, 560)
        root.resizable(True, True)
        root.configure(bg=CANVAS)
        self.categories = list(CATEGORIES)
        self.current_index = self.categories.index("Main courses")
        self.dishes = DISHES
        self.menu_items = {
            category: [(name, f"EGP {DISHES[name].price}") for name in names]
            for category, names in CATEGORIES.items()
        }
        self.selected_item = None
        self.game_open = False
        self.menu_open = False
        self.screen = "welcome"
        self.quantity = 1
        self.cart = {}
        self.order_page = 0
        self.hand_control_enabled = True
        self.camera_enabled = True
        self.notice = ""
        self.message = ("", "")
        self._undo_cart = None
        self._notice_timer = None
        self._resize_timer = None
        self._focused_action = -1
        self._display = None
        self._image = None
        self._transform = (1, 0, 0)
        self.welcome_frame = tk.Frame(root, bg=CANVAS)
        self.main_frame = tk.Frame(root, bg=CANVAS)
        self.welcome_canvas = self._make_canvas(self.welcome_frame)
        self.menu_canvas = self._make_canvas(self.main_frame)
        self.welcome_frame.pack(fill="both", expand=True)
        self.renderer = MenuRenderer(self)
        self.actions = []
        root.bind("<Configure>", self._on_resize)
        root.bind("<Left>", lambda event: self.previous_category())
        root.bind("<Right>", lambda event: self.next_category())
        root.bind("<Escape>", lambda event: self.show_menu() if self.selected_item else self.close_menu())
        self.render()

    @property
    def visible_items(self):
        return CATEGORIES[self.categories[self.current_index]][:3]

    @property
    def order_count(self):
        return sum(self.cart.values())

    @property
    def order_total(self):
        return sum(self.dishes[name].price * quantity for name, quantity in self.cart.items())

    def _make_canvas(self, parent):
        canvas = tk.Canvas(parent, bg=CANVAS, highlightthickness=0, takefocus=True,
                           yscrollincrement=24)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Button-1>", self._click)
        canvas.bind("<Motion>", self._hover)
        canvas.bind("<Tab>", self._next_focus)
        canvas.bind("<Shift-Tab>", lambda event: self._next_focus(event, -1))
        canvas.bind("<Return>", self._activate_focus)
        canvas.bind("<space>", self._activate_focus)
        canvas.bind("<MouseWheel>", self._scroll)
        canvas.bind("<Button-4>", lambda event: canvas.yview_scroll(-2, "units"))
        canvas.bind("<Button-5>", lambda event: canvas.yview_scroll(2, "units"))
        canvas.bind("<Next>", lambda event: canvas.yview_scroll(1, "pages"))
        canvas.bind("<Prior>", lambda event: canvas.yview_scroll(-1, "pages"))
        return canvas

    def _scroll(self, event):
        if event.delta:
            steps = -int(event.delta / 120) * 3 if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
            event.widget.yview_scroll(steps, "units")
        return "break"

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(60, self._resize)

    def _resize(self):
        self._resize_timer = None
        self._paint()

    def render(self):
        self._image, self.actions = self.renderer.render()
        self._focused_action = -1
        self._paint()
        canvas = self.menu_canvas if self.menu_open else self.welcome_canvas
        canvas.yview_moveto(0)

    def _paint(self):
        if self._image is None:
            return
        canvas = self.menu_canvas if self.menu_open else self.welcome_canvas
        width = canvas.winfo_width() if canvas.winfo_width() > 1 else self.root.winfo_width()
        height = canvas.winfo_height() if canvas.winfo_height() > 1 else self.root.winfo_height()
        if width <= 1 or height <= 1:
            return
        source_width, source_height = self._image.size
        ratio = width / source_width
        size = (max(1, round(source_width * ratio)), max(1, round(source_height * ratio)))
        image = self._image.resize(size, Image.Resampling.LANCZOS)
        self._display = ImageTk.PhotoImage(image, master=self.root)
        offset_x, offset_y = 0, 0
        canvas.delete("all")
        canvas.create_image(offset_x, offset_y, image=self._display, anchor="nw")
        canvas.configure(scrollregion=(0, 0, width, max(height, size[1])))
        self._transform = (ratio * 2, offset_x, offset_y)

    def _hit_test(self, event):
        scale, offset_x, offset_y = self._transform
        x = (event.widget.canvasx(event.x) - offset_x) / scale
        y = (event.widget.canvasy(event.y) - offset_y) / scale
        for action in reversed(self.actions):
            left, top, right, bottom = action.rect
            if action.enabled and left <= x <= right and top <= y <= bottom:
                return action
        return None

    def _click(self, event):
        event.widget.focus_set()
        action = self._hit_test(event)
        if action:
            action.invoke()

    def _hover(self, event):
        event.widget.configure(cursor="hand2" if self._hit_test(event) else "")

    def _next_focus(self, event, direction=1):
        available = [action for action in self.actions if action.enabled]
        if not available:
            return "break"
        self._focused_action = (self._focused_action + direction) % len(available)
        action = available[self._focused_action]
        scale, x, y = self._transform
        event.widget.delete("focus-ring")
        left, top, right, bottom = action.rect
        visible_top = event.widget.canvasy(0)
        visible_bottom = visible_top + event.widget.winfo_height()
        if top * scale < visible_top or bottom * scale > visible_bottom:
            image_height = self._image.height / 2 * scale
            event.widget.yview_moveto(max(0, (top * scale - 30) / image_height))
        event.widget.create_rectangle(x + left * scale, y + top * scale,
                                      x + right * scale, y + bottom * scale,
                                      outline=FOREST, width=3, dash=(4, 3), tags="focus-ring")
        return "break"

    def _activate_focus(self, event):
        available = [action for action in self.actions if action.enabled]
        if 0 <= self._focused_action < len(available):
            available[self._focused_action].invoke()
        return "break"

    def action(self, text=None, key=None):
        return next(action for action in self.actions
                    if (key is not None and action.key == key) or
                    (text is not None and action.text == text))

    def show_menu(self):
        self.menu_open = True
        self.game_open = False
        self.selected_item = None
        self.screen = "menu"
        self.welcome_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.render()

    def close_menu(self):
        self.menu_open = False
        self.game_open = False
        self.selected_item = None
        self.screen = "welcome"
        self.main_frame.pack_forget()
        self.welcome_frame.pack(fill="both", expand=True)
        self.render()

    def select_category(self, index):
        if self.menu_open and 0 <= index < len(self.categories):
            self.current_index = index
            self.show_menu()

    def next_category(self):
        if self.menu_open:
            self.select_category((self.current_index + 1) % len(self.categories))

    def previous_category(self):
        if self.menu_open:
            self.select_category((self.current_index - 1) % len(self.categories))

    def select_current_item(self, index=0):
        if self.menu_open and 0 <= index < len(self.visible_items):
            return self.select_item(self.visible_items[index])
        return False

    def select_current_category(self):
        return self.select_current_item()

    def select_item(self, item):
        if not self.menu_open or item not in self.dishes:
            return False
        self.selected_item = item
        self.quantity = 1
        self.screen = "detail"
        self.game_open = False
        self.render()
        return True

    def change_quantity(self, change):
        self.quantity = max(1, min(20, self.quantity + change))
        self.render()

    def _cart_change(self):
        self._undo_cart = self.cart.copy()

    def add_to_order(self, item, quantity=1):
        if item not in self.dishes or not self.dishes[item].available:
            return False
        self._cart_change()
        self.cart[item] = self.cart.get(item, 0) + max(1, min(20, quantity))
        if self.screen == "detail":
            self.show_menu()
        self._notify(f"{item} added · EGP {self.order_total} total")
        return True

    def adjust_order(self, item, change):
        self._cart_change()
        quantity = self.cart.get(item, 0) + change
        if quantity <= 0:
            self.cart.pop(item, None)
        else:
            self.cart[item] = quantity
        self.render()

    def remove_from_order(self, item):
        self._cart_change()
        self.cart.pop(item, None)
        self._notify(item + " removed")

    def undo(self):
        if self._undo_cart is not None:
            self.cart, self._undo_cart = self._undo_cart, None
            self.notice = ""
            self.render()

    def _notify(self, message):
        self.notice = message
        if self._notice_timer:
            self.root.after_cancel(self._notice_timer)
        self._notice_timer = self.root.after(3500, self._clear_notice)
        self.render()

    def _clear_notice(self):
        self._notice_timer = None
        self.notice = ""
        self.render()

    def show_order(self):
        if not self.menu_open:
            self.show_menu()
        self.screen = "order"
        self.selected_item = None
        self.notice = ""
        self.render()

    def change_order_page(self, change):
        last_page = max(0, (len(self.cart) - 1) // 2)
        self.order_page = max(0, min(last_page, self.order_page + change))
        self.render()

    def _show_message(self, screen, title, body):
        if not self.menu_open:
            self.show_menu()
        self.screen = screen
        self.game_open = screen == "games"
        self.selected_item = None
        self.message = title, body
        self.render()

    def open_game(self):
        self._show_message("games", "A moment of play.",
                           "Table Trivia · A few questions for good company.\n\n"
                           "Olive Match · A quiet matching-game break.\n\n"
                           "Ask your server about the table’s games. Your order stays here while you explore.")
        self.game_open = True

    def show_rewards(self):
        self.game_open = False
        self._show_message("rewards", "A little thank you.",
                           "Good food is even better with something to look forward to.\n\n"
                           "Ask your server about OLIVE / TABLE rewards.\n\n"
                           "You can always browse and order as a guest.")

    def show_help(self):
        self.game_open = False
        self._show_message("help", "Enjoy the table your way.",
                           "Open palm + hold: open the menu or return to browsing.\n"
                           "Palm sweep left / right: browse categories.\n"
                           "One finger + hold in the left, center or right camera zone: view that dish.\n"
                           "Closed fist + hold: close the menu.\n\n"
                           "Every menu action also works by mouse or keyboard.\n"
                           "Need ingredients or allergen information? Please ask a member of staff.")

    def toggle_hand_control(self):
        self.hand_control_enabled = not self.hand_control_enabled
        if self.hand_control_enabled:
            self.camera_enabled = True
        self.render()

    def toggle_camera(self):
        self.camera_enabled = not self.camera_enabled
        self.hand_control_enabled = self.camera_enabled
        self.render()

    def get_state(self):
        return {
            "menu_open": self.menu_open,
            "category": self.categories[self.current_index],
            "selected_item": self.selected_item,
            "hand_control_enabled": self.hand_control_enabled,
            "camera_enabled": self.camera_enabled,
        }

    def handle_gesture(self, gesture):
        if not self.hand_control_enabled:
            return False
        if not self.menu_open and gesture not in ("OPEN_PALM", "CLOSED_FIST"):
            return False
        if gesture == "OPEN_PALM":
            self.show_menu()
        elif gesture == "CLOSED_FIST":
            self.close_menu()
        elif gesture == "SWIPE_RIGHT":
            self.next_category()
        elif gesture == "SWIPE_LEFT":
            self.previous_category()
        elif gesture == "SELECT_PRODUCT":
            return self.select_current_item()
        elif gesture.startswith("SELECT_PRODUCT:"):
            try:
                index = int(gesture.split(":", 1)[1])
            except ValueError:
                return False
            return self.select_current_item(index)
        else:
            return False
        return True


if __name__ == "__main__":
    root = tk.Tk()
    RestaurantMenuUI(root)
    root.mainloop()
