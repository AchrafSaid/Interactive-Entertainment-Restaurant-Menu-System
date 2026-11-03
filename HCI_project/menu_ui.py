import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


# =========================
# COLORS & FONTS
# =========================

BG = "#F5F2EA"
CARD = "#FFFDF9"
GREEN = "#173D33"
GREEN_LIGHT = "#E5ECE5"
SAGE = "#A8B8A5"
TEXT = "#263A32"
MUTED = "#78847B"
BORDER = "#E6E2D8"
CREAM = "#F0EBDD"
WARNING = "#B77945"

FONT_TITLE = ("Georgia", 25, "bold")
FONT_HEADING = ("Georgia", 18, "bold")
FONT_BODY = ("Arial", 10)
FONT_SMALL = ("Arial", 9)
FONT_BOLD = ("Arial", 10, "bold")


class RestaurantMenuUI:

    def __init__(self, root):

        self.root = root

        self.root.title("OLIVE / TABLE")
        self.root.geometry("1200x760")
        self.root.minsize(1000, 650)
        self.root.configure(bg=BG)

        # Application state
        self.current_page = "welcome"
        self.current_category = "Main courses"

        self.selected_product = None
        self.quantity = 1

        self.cart = []
        self.order_number = 1

        self.menu_open = False

        # Camera widgets
        self.camera_label = None
        self.camera_status = None
        self.gesture_label = None
        self._camera_photo = None

        # Categories
        self.categories = [
            "Small plates",
            "Main courses",
            "Snacks",
            "Drinks",
            "Desserts"
        ]

        # Products
        self.products = [

            {
                "name": "House burger",
                "description": "Grilled beef, tahini, crisp greens and brioche.",
                "details": (
                    "A juicy grilled beef burger served with "
                    "creamy tahini sauce, fresh greens and "
                    "a soft toasted brioche bun."
                ),
                "ingredients": "Beef, brioche bun, tahini, lettuce, tomato",
                "price": 280,
                "emoji": "🍔",
                "category": "Main courses",
                "color": "#E9DCC9",
                "off": False
            },

            {
                "name": "Garden fattoush",
                "description": "Cucumber, tomato, sumac and toasted pita.",
                "details": (
                    "A fresh garden salad with crunchy vegetables, "
                    "sumac dressing and toasted pita bread."
                ),
                "ingredients": "Cucumber, tomato, lettuce, sumac, pita",
                "price": 150,
                "emoji": "🥗",
                "category": "Small plates",
                "color": "#DDE7D9",
                "off": True
            },

            {
                "name": "Fresh orange juice",
                "description": "Freshly squeezed oranges. Nothing more.",
                "details": (
                    "Fresh orange juice, prepared from "
                    "freshly squeezed oranges."
                ),
                "ingredients": "Fresh oranges",
                "price": 90,
                "emoji": "🍹",
                "category": "Drinks",
                "color": "#F3E1C9",
                "off": False
            }
        ]

        self.show_welcome()

    # =========================
    # GENERAL FUNCTIONS
    # =========================

    def clear_screen(self):

        for widget in self.root.winfo_children():
            widget.destroy()

        # Clear old camera references
        self.camera_label = None
        self.camera_status = None
        self.gesture_label = None
        self._camera_photo = None

    def make_button(
        self,
        parent,
        text,
        command,
        primary=True,
        width=None
    ):

        return tk.Button(
            parent,
            text=text,
            command=command,

            bg=GREEN if primary else CARD,
            fg=CARD if primary else GREEN,

            activebackground=GREEN if primary else GREEN_LIGHT,
            activeforeground=CARD if primary else GREEN,

            relief="flat",
            bd=0,

            highlightthickness=1,
            highlightbackground=GREEN if primary else BORDER,

            font=FONT_BOLD,
            cursor="hand2",

            padx=18,
            pady=10,
            width=width
        )

    def label(
        self,
        parent,
        text,
        font=FONT_BODY,
        color=TEXT,
        bg=CARD,
        **kwargs
    ):

        return tk.Label(
            parent,
            text=text,
            font=font,
            fg=color,
            bg=bg,
            **kwargs
        )

    def build_header(self, parent, show_cart=True):

        header = tk.Frame(parent, bg=BG)

        header.pack(
            fill="x",
            padx=35,
            pady=(18, 12)
        )

        self.label(
            header,
            "OLIVE / TABLE",
            ("Georgia", 17, "bold"),
            GREEN,
            BG
        ).pack(side="left")

        self.label(
            header,
            "A PLACE AT THE TABLE",
            ("Arial", 8, "bold"),
            MUTED,
            BG
        ).pack(side="left", padx=18)

        if show_cart:

            self.make_button(
                header,
                f"Order ({self.cart_count()})",
                self.show_cart,
                False
            ).pack(side="right")

    def cart_count(self):

        return sum(
            item["quantity"]
            for item in self.cart
        )

    def get_total(self):

        return sum(
            item["price"] * item["quantity"]
            for item in self.cart
        )

    # =========================
    # WELCOME PAGE
    # =========================

    def show_welcome(self):

        self.clear_screen()

        self.current_page = "welcome"
        self.menu_open = False

        main = tk.Frame(self.root, bg=BG)

        main.pack(
            fill="both",
            expand=True,
            padx=45,
            pady=30
        )

        self.build_header(main, False)

        content = tk.Frame(main, bg=BG)

        content.pack(
            fill="both",
            expand=True,
            pady=15
        )

        # Left section
        hero = tk.Frame(
            content,
            bg=GREEN,
            width=530
        )

        hero.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 14)
        )

        hero.pack_propagate(False)

        self.label(
            hero,
            "🍽️",
            ("Arial", 65),
            CARD,
            GREEN
        ).pack(pady=(65, 12))

        self.label(
            hero,
            "Good food.\nGood company.",
            ("Georgia", 31, "bold"),
            CARD,
            GREEN,
            justify="center"
        ).pack(pady=8)

        self.label(
            hero,
            "A little moment made around the table.",
            FONT_BODY,
            "#D7E0D8",
            GREEN
        ).pack(pady=8)

        self.label(
            hero,
            "TABLE 08",
            FONT_SMALL,
            "#C5D2C7",
            GREEN
        ).pack(side="bottom", pady=25)

        # Right section
        panel = tk.Frame(
            content,
            bg=CARD,
            padx=38,
            pady=30
        )

        panel.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.label(
            panel,
            "WELCOME",
            FONT_SMALL,
            MUTED
        ).pack(anchor="w", pady=(35, 15))

        self.label(
            panel,
            "A place at\nthe table.",
            ("Georgia", 30, "bold"),
            GREEN,
            justify="left"
        ).pack(anchor="w")

        self.label(
            panel,
            "Explore the menu, discover something new,\nand enjoy your time with us.",
            FONT_BODY,
            MUTED,
            justify="left"
        ).pack(anchor="w", pady=18)

        self.make_button(
            panel,
            "Continue as guest",
            self.show_gate
        ).pack(fill="x", pady=(18, 10))

        self.make_button(
            panel,
            "Sign in",
            lambda: messagebox.showinfo(
                "Sign in",
                "Demo feature."
            ),
            False
        ).pack(fill="x", pady=5)

        self.make_button(
            panel,
            "Create account",
            lambda: messagebox.showinfo(
                "Create account",
                "Demo feature."
            ),
            False
        ).pack(fill="x", pady=5)

        self.label(
            panel,
            "Need help? Ask a member of our staff.",
            FONT_SMALL,
            MUTED
        ).pack(anchor="w", pady=(20, 0))

    # =========================
    # GATE PAGE
    # =========================

    def show_gate(self):

        self.clear_screen()

        self.current_page = "gate"
        self.menu_open = False

        self.build_header(self.root, False)

        body = tk.Frame(self.root, bg=BG)

        body.pack(
            fill="both",
            expand=True,
            padx=55,
            pady=25
        )

        left = tk.Frame(
            body,
            bg=CARD,
            padx=35,
            pady=35
        )

        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 12)
        )

        self.label(
            left,
            "YOUR HANDS,\nYOUR CHOICE.",
            ("Georgia", 27, "bold"),
            GREEN,
            justify="left"
        ).pack(anchor="w", pady=(20, 15))

        self.label(
            left,
            "Use simple hand gestures to explore the menu.\n"
            "You can also continue using the buttons.",
            FONT_BODY,
            MUTED,
            justify="left"
        ).pack(anchor="w", pady=10)

        self.label(
            left,
            "CAMERA CONTROL",
            FONT_BOLD,
            GREEN
        ).pack(anchor="w", pady=(25, 8))

        self.label(
            left,
            "The live camera preview appears in this panel "
            "when the camera starts.",
            FONT_SMALL,
            MUTED,
            wraplength=350,
            justify="left"
        ).pack(anchor="w")

        self.make_button(
            left,
            "Continue to menu",
            self.show_menu
        ).pack(anchor="w", pady=(28, 10))

        self.make_button(
            left,
            "Back",
            self.show_welcome,
            False
        ).pack(anchor="w")

        self.build_camera_panel(body, side=True)

    # =========================
    # CAMERA PANEL
    # =========================

    def build_camera_panel(self, parent, side=False):

        panel = tk.Frame(
            parent,
            bg=GREEN,
            padx=15,
            pady=15,
            width=300 if side else 390
        )

        panel.pack(
            side="right",
            fill="y" if side else "both",
            padx=(12, 0) if side else 0
        )

        panel.pack_propagate(False)

        self.label(
            panel,
            "LIVE CAMERA",
            FONT_BOLD,
            CARD,
            GREEN
        ).pack(anchor="w", pady=(3, 10))

        self.camera_label = tk.Label(
            panel,
            text="Camera preview\nwill appear here",
            bg="#263F36",
            fg="#D7E0D8",
            font=FONT_BODY
        )

        self.camera_label.pack(
            fill="both",
            expand=True
        )

        self.camera_status = self.label(
            panel,
            "Waiting for camera...",
            FONT_SMALL,
            "#D7E0D8",
            GREEN
        )

        self.camera_status.pack(
            anchor="w",
            pady=8
        )

        self.gesture_label = self.label(
            panel,
            "Gesture: Waiting...",
            FONT_BOLD,
            CARD,
            GREEN
        )

        self.gesture_label.pack(anchor="w")

    # =========================
    # MENU PAGE
    # =========================

    def show_menu(self):

        self.clear_screen()

        self.current_page = "menu"
        self.menu_open = True

        self.build_header(self.root)

        top = tk.Frame(self.root, bg=BG)

        top.pack(
            fill="x",
            padx=35,
            pady=(3, 10)
        )

        self.label(
            top,
            "Good to have you here.",
            ("Georgia", 23, "bold"),
            GREEN,
            BG
        ).pack(side="left")

        self.label(
            top,
            "TABLE 08  •  MENU",
            FONT_SMALL,
            MUTED,
            BG
        ).pack(side="right")

        # Navigation
        nav = tk.Frame(self.root, bg=BG)

        nav.pack(
            fill="x",
            padx=35,
            pady=(0, 12)
        )

        for name, command in [
            ("Menu", self.show_menu),
            ("Rewards", self.show_rewards),
            ("Games", self.show_games)
        ]:

            self.make_button(
                nav,
                name,
                command,
                name == "Menu"
            ).pack(side="left", padx=(0, 8))

        content = tk.Frame(self.root, bg=BG)

        content.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(0, 18)
        )

        menu_area = tk.Frame(content, bg=BG)

        menu_area.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 14)
        )

        self.label(
            menu_area,
            "Explore the menu",
            FONT_HEADING,
            GREEN,
            BG
        ).pack(anchor="w", pady=(0, 12))

        categories_frame = tk.Frame(menu_area, bg=BG)

        categories_frame.pack(
            fill="x",
            pady=(0, 15)
        )

        for category in self.categories:

            self.make_button(
                categories_frame,
                category,
                lambda c=category: self.change_category(c),
                category == self.current_category
            ).pack(side="left", padx=(0, 5))

        self.products_frame = tk.Frame(menu_area, bg=BG)

        self.products_frame.pack(
            fill="both",
            expand=True
        )

        self.render_products()

        # Right panel
        side = tk.Frame(
            content,
            bg=CARD,
            width=275,
            padx=15,
            pady=15
        )

        side.pack(
            side="right",
            fill="y"
        )

        side.pack_propagate(False)

        self.label(
            side,
            "YOUR TABLE",
            FONT_BOLD,
            GREEN
        ).pack(anchor="w")

        self.label(
            side,
            "Table 08",
            FONT_SMALL,
            MUTED
        ).pack(anchor="w", pady=(3, 12))

        self.build_camera_panel(side, side=True)

        tk.Frame(
            side,
            bg=BORDER,
            height=1
        ).pack(fill="x", pady=10)

        self.label(
            side,
            "GESTURE GUIDE",
            FONT_BOLD,
            GREEN
        ).pack(anchor="w", pady=(3, 8))

        guide = [
            "✋ Open palm: Open menu",
            "✊ Closed fist: Close menu",
            "☝ Index finger: Select",
            "← → Swipe: Change category"
        ]

        for item in guide:

            self.label(
                side,
                item,
                FONT_SMALL,
                MUTED
            ).pack(anchor="w", pady=3)

        self.make_button(
            side,
            f"Review order ({self.cart_count()})",
            self.show_cart
        ).pack(
            fill="x",
            side="bottom",
            pady=(12, 0)
        )

    def change_category(self, category):

        if category in self.categories:

            self.current_category = category
            self.show_menu()

    def render_products(self):

        for widget in self.products_frame.winfo_children():
            widget.destroy()

        matching = [
            product
            for product in self.products
            if product["category"] == self.current_category
        ]

        if not matching:

            self.label(
                self.products_frame,
                "More dishes coming soon.",
                FONT_BODY,
                MUTED,
                BG
            ).pack(anchor="w", pady=30)

            return

        for product in matching:

            card = tk.Frame(
                self.products_frame,
                bg=CARD,
                highlightthickness=1,
                highlightbackground=BORDER,
                padx=15,
                pady=12
            )

            card.pack(
                fill="x",
                pady=(0, 12)
            )

            visual = tk.Frame(
                card,
                bg=product["color"],
                width=100,
                height=95
            )

            visual.pack(
                side="left",
                padx=(0, 15)
            )

            visual.pack_propagate(False)

            self.label(
                visual,
                product["emoji"],
                ("Arial", 36),
                TEXT,
                product["color"]
            ).pack(expand=True)

            info = tk.Frame(card, bg=CARD)

            info.pack(
                side="left",
                fill="both",
                expand=True
            )

            self.label(
                info,
                product["name"],
                ("Georgia", 14, "bold"),
                GREEN
            ).pack(anchor="w")

            self.label(
                info,
                product["description"],
                FONT_SMALL,
                MUTED,
                wraplength=310,
                justify="left"
            ).pack(anchor="w", pady=5)

            self.label(
                info,
                f"EGP {product['price']}",
                FONT_BOLD,
                TEXT
            ).pack(anchor="w", pady=3)

            if product["off"]:

                self.label(
                    info,
                    "Unavailable today",
                    FONT_SMALL,
                    WARNING
                ).pack(anchor="w")

            else:

                self.make_button(
                    card,
                    "View details",
                    lambda p=product: self.show_product(p),
                    False
                ).pack(side="right", padx=5)

    # =========================
    # PRODUCT DETAILS
    # =========================

    def show_product(self, product):

        if product.get("off"):

            messagebox.showinfo(
                "Unavailable",
                "This item is unavailable today."
            )

            return

        self.selected_product = product
        self.quantity = 1

        self.clear_screen()

        self.current_page = "product"
        self.menu_open = True

        self.build_header(self.root)

        panel = tk.Frame(
            self.root,
            bg=CARD,
            padx=35,
            pady=25
        )

        panel.pack(
            fill="both",
            expand=True,
            padx=80,
            pady=25
        )

        self.label(
            panel,
            product["emoji"],
            ("Arial", 65),
            GREEN,
            product["color"],
            width=8,
            height=2
        ).pack(anchor="w", pady=(0, 18))

        self.label(
            panel,
            product["name"],
            FONT_TITLE,
            GREEN
        ).pack(anchor="w")

        self.label(
            panel,
            product["details"],
            FONT_BODY,
            MUTED,
            wraplength=700,
            justify="left"
        ).pack(anchor="w", pady=10)

        self.label(
            panel,
            "INGREDIENTS",
            FONT_BOLD,
            GREEN
        ).pack(anchor="w", pady=(15, 5))

        self.label(
            panel,
            product["ingredients"],
            FONT_BODY,
            MUTED
        ).pack(anchor="w")

        self.label(
            panel,
            "Please inform our staff about any allergies.",
            FONT_SMALL,
            WARNING
        ).pack(anchor="w", pady=15)

        row = tk.Frame(panel, bg=CARD)

        row.pack(anchor="w", pady=10)

        self.make_button(
            row,
            "−",
            self.decrease_quantity,
            False
        ).pack(side="left")

        self.quantity_label = self.label(
            row,
            str(self.quantity),
            FONT_BOLD,
            GREEN,
            width=5
        )

        self.quantity_label.pack(side="left")

        self.make_button(
            row,
            "+",
            self.increase_quantity,
            False
        ).pack(side="left")

        self.add_button = self.make_button(
            panel,
            f"Add to order • EGP {product['price']}",
            self.add_to_cart
        )

        self.add_button.pack(
            anchor="w",
            pady=15
        )

        self.make_button(
            panel,
            "Back to menu",
            self.show_menu,
            False
        ).pack(anchor="w")

    def refresh_quantity(self):

        if (
            hasattr(self, "quantity_label")
            and self.quantity_label.winfo_exists()
        ):

            self.quantity_label.config(
                text=str(self.quantity)
            )

        if (
            hasattr(self, "add_button")
            and self.add_button.winfo_exists()
            and self.selected_product
        ):

            total = self.selected_product["price"] * self.quantity

            self.add_button.config(
                text=f"Add to order • EGP {total}"
            )

    def increase_quantity(self):

        self.quantity = min(
            20,
            self.quantity + 1
        )

        self.refresh_quantity()

    def decrease_quantity(self):

        self.quantity = max(
            1,
            self.quantity - 1
        )

        self.refresh_quantity()

    def add_to_cart(self):

        if not self.selected_product:
            return

        product = self.selected_product

        existing = next(
            (
                item for item in self.cart
                if item["name"] == product["name"]
            ),
            None
        )

        if existing:

            existing["quantity"] += self.quantity

        else:

            self.cart.append({
                "name": product["name"],
                "price": product["price"],
                "quantity": self.quantity
            })

        messagebox.showinfo(
            "Added to order",
            f"{self.quantity} × {product['name']} added to your order."
        )

        self.show_menu()

    # =========================
    # CART
    # =========================

    def show_cart(self):

        self.clear_screen()

        self.current_page = "cart"
        self.menu_open = True

        self.build_header(self.root)

        panel = tk.Frame(
            self.root,
            bg=CARD,
            padx=35,
            pady=25
        )

        panel.pack(
            fill="both",
            expand=True,
            padx=65,
            pady=25
        )

        self.label(
            panel,
            "Review your order",
            FONT_TITLE,
            GREEN
        ).pack(anchor="w")

        self.label(
            panel,
            "Check everything before placing your order.",
            FONT_BODY,
            MUTED
        ).pack(anchor="w", pady=(5, 20))

        if not self.cart:

            self.label(
                panel,
                "Your order is empty.",
                FONT_BODY,
                MUTED
            ).pack(anchor="w", pady=25)

        else:

            for index, item in enumerate(self.cart):

                row = tk.Frame(
                    panel,
                    bg=BG,
                    padx=15,
                    pady=12
                )

                row.pack(
                    fill="x",
                    pady=5
                )

                self.label(
                    row,
                    f"{item['quantity']} × {item['name']}",
                    FONT_BOLD,
                    TEXT,
                    BG
                ).pack(side="left")

                self.label(
                    row,
                    f"EGP {item['price'] * item['quantity']}",
                    FONT_BOLD,
                    GREEN,
                    BG
                ).pack(side="right")

                tk.Button(
                    row,
                    text="Remove",
                    command=lambda i=index: self.remove_from_cart(i),
                    bg=BG,
                    fg=WARNING,
                    relief="flat",
                    cursor="hand2",
                    font=FONT_SMALL
                ).pack(side="right", padx=15)

        tk.Frame(
            panel,
            bg=BORDER,
            height=1
        ).pack(fill="x", pady=18)

        self.label(
            panel,
            f"Total     EGP {self.get_total()}",
            ("Georgia", 18, "bold"),
            GREEN
        ).pack(anchor="e", pady=8)

        self.label(
            panel,
            "Payment will be handled by a member of staff.",
            FONT_SMALL,
            MUTED
        ).pack(anchor="e", pady=5)

        buttons = tk.Frame(panel, bg=CARD)

        buttons.pack(
            anchor="w",
            pady=20
        )

        self.make_button(
            buttons,
            "Continue browsing",
            self.show_menu,
            False
        ).pack(side="left", padx=(0, 10))

        self.make_button(
            buttons,
            "Place order",
            self.place_order
        ).pack(side="left")

    def remove_from_cart(self, index):

        if 0 <= index < len(self.cart):
            self.cart.pop(index)

        self.show_cart()

    def place_order(self):

        if not self.cart:

            messagebox.showinfo(
                "Empty order",
                "Add an item before placing your order."
            )

            return

        reference = f"T08-{self.order_number:04d}"

        self.order_number += 1

        self.clear_screen()

        self.current_page = "confirmation"
        self.menu_open = False

        panel = tk.Frame(
            self.root,
            bg=CARD,
            padx=45,
            pady=45
        )

        panel.pack(
            fill="both",
            expand=True,
            padx=100,
            pady=70
        )

        self.label(
            panel,
            "✓",
            ("Arial", 35, "bold"),
            GREEN,
            GREEN_LIGHT,
            width=3,
            height=1
        ).pack(anchor="w", pady=10)

        self.label(
            panel,
            "Your order is ready to be sent.",
            ("Georgia", 24, "bold"),
            GREEN
        ).pack(anchor="w", pady=10)

        self.label(
            panel,
            f"Order reference: {reference}",
            FONT_BODY,
            MUTED
        ).pack(anchor="w")

        self.label(
            panel,
            "Project demo only. No real restaurant order is transmitted.",
            FONT_SMALL,
            WARNING
        ).pack(anchor="w", pady=15)

        self.cart.clear()

        self.make_button(
            panel,
            "Back to menu",
            self.show_menu
        ).pack(anchor="w", pady=15)

    # =========================
    # REWARDS & GAMES
    # =========================

    def show_rewards(self):

        self.simple_page(
            "rewards",
            "A little something extra.",
            "Your rewards and points will appear here.",
            "REWARDS"
        )

    def show_games(self):

        self.simple_page(
            "games",
            "Make the table a little more fun.",
            "Play a quick trivia game with the people at your table.",
            "TABLE TRIVIA"
        )

    def simple_page(
        self,
        page,
        title,
        description,
        tag
    ):

        self.clear_screen()

        self.current_page = page
        self.menu_open = True

        self.build_header(self.root)

        panel = tk.Frame(
            self.root,
            bg=CARD,
            padx=45,
            pady=40
        )

        panel.pack(
            fill="both",
            expand=True,
            padx=65,
            pady=35
        )

        self.label(
            panel,
            title,
            FONT_TITLE,
            GREEN
        ).pack(anchor="w")

        self.label(
            panel,
            description,
            FONT_BODY,
            MUTED
        ).pack(anchor="w", pady=12)

        self.label(
            panel,
            tag,
            FONT_BOLD,
            GREEN,
            GREEN_LIGHT,
            padx=18,
            pady=15
        ).pack(anchor="w", pady=20)

        self.make_button(
            panel,
            "Back to menu",
            self.show_menu
        ).pack(anchor="w")

    # =========================
    # CAMERA UPDATE
    # =========================

    def update_camera(self, frame):

        if (
            self.camera_label is None
            or not self.camera_label.winfo_exists()
        ):
            return

        try:

            image = Image.fromarray(frame)

            image.thumbnail((300, 190))

            photo = ImageTk.PhotoImage(image)

            self.camera_label.configure(
                image=photo,
                text=""
            )

            self.camera_label.image = photo
            self._camera_photo = photo

            if (
                self.camera_status is not None
                and self.camera_status.winfo_exists()
            ):

                self.camera_status.config(
                    text="Camera is running"
                )

        except tk.TclError:
            pass

        except Exception:

            if (
                self.camera_status is not None
                and self.camera_status.winfo_exists()
            ):

                self.camera_status.config(
                    text="Camera preview unavailable"
                )

    def update_gesture_status(self, gesture):

        if (
            self.gesture_label is not None
            and self.gesture_label.winfo_exists()
        ):

            try:

                self.gesture_label.config(
                    text=f"Gesture: {gesture}"
                )

            except tk.TclError:
                pass

    # =========================
    # GESTURE HANDLER
    # =========================

    def handle_gesture(self, gesture):

        if gesture == "OPEN_PALM":

            if self.current_page in (
                "welcome",
                "gate",
                "confirmation"
            ):

                self.show_menu()

            elif self.current_page in (
                "product",
                "cart",
                "games",
                "rewards"
            ):

                self.show_menu()

        elif gesture == "CLOSED_FIST":

            if self.current_page in (
                "menu",
                "product",
                "cart",
                "games",
                "rewards"
            ):

                self.show_welcome()

        elif gesture == "SWIPE_RIGHT":

            self.next_category()

        elif gesture == "SWIPE_LEFT":

            self.previous_category()

        elif gesture in (
            "SELECT_PRODUCT",
            "V_SHAPE"
        ):

            if self.current_page == "menu":

                self.select_item()

            elif self.current_page == "product":

                self.add_to_cart()

        elif gesture == "THUMBS_UP":

            if self.current_page == "product":
                self.increase_quantity()

        elif gesture == "THUMBS_DOWN":

            if self.current_page == "product":
                self.decrease_quantity()

        elif gesture == "OK_SIGN":

            if self.current_page in (
                "menu",
                "product"
            ):

                self.show_cart()

    # =========================
    # CATEGORY NAVIGATION
    # =========================

    def next_category(self):

        if self.current_page != "menu":
            return

        index = self.categories.index(
            self.current_category
        )

        next_index = (
            index + 1
        ) % len(self.categories)

        self.change_category(
            self.categories[next_index]
        )

    def previous_category(self):

        if self.current_page != "menu":
            return

        index = self.categories.index(
            self.current_category
        )

        previous_index = (
            index - 1
        ) % len(self.categories)

        self.change_category(
            self.categories[previous_index]
        )

    def select_item(self):

        if self.current_page != "menu":
            return

        available = [
            product
            for product in self.products
            if (
                product["category"] == self.current_category
                and not product["off"]
            )
        ]

        if available:

            self.show_product(available[0])

        else:

            messagebox.showinfo(
                "No available items",
                "There are no available items in this category yet."
            )

    def open_game(self):

        self.show_games()

    def select_current_category(self):

        self.select_item()

    def close_menu(self):

        self.menu_open = False
        self.show_welcome()


# =========================
# RUN UI DIRECTLY
# =========================

if __name__ == "__main__":

    root = tk.Tk()

    app = RestaurantMenuUI(root)

    root.mainloop()