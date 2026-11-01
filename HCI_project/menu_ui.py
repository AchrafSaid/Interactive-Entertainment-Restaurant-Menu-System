
import tkinter as tk


class RestaurantMenuUI:

    def __init__(self, root):

        self.root = root
        self.root.title("Interactive Restaurant Menu")
        self.root.geometry("1000x650")
        self.root.configure(bg="#F5F2EA")
        self.root.resizable(False, False)

        self.categories = [
            "Main Meals",
            "Drinks",
            "Desserts",
            "Offers"
        ]

        self.current_index = 0
        self.selected_item = None

        self.game_open = False
        self.menu_open = False

        self.menu_items = {
            "Main Meals": [
                ("Classic Burger", "$12"),
                ("Chicken Pasta", "$10"),
                ("Grilled Chicken", "$15")
            ],

            "Drinks": [
                ("Fresh Juice", "$5"),
                ("Iced Coffee", "$6"),
                ("Lemon Mint", "$4")
            ],

            "Desserts": [
                ("Chocolate Cake", "$7"),
                ("Ice Cream", "$5"),
                ("Cheesecake", "$8")
            ],

            "Offers": [
                ("Burger Combo", "$15"),
                ("Family Meal", "$25"),
                ("Dessert Deal", "$10")
            ]
        }

        self.create_interface()

    # =================================
    # MAIN INTERFACE
    # =================================

    def create_interface(self):

        header = tk.Frame(
            self.root,
            bg="#263D35",
            height=100
        )

        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="RESTAURANT",
            font=("Arial", 26, "bold"),
            fg="white",
            bg="#263D35"
        ).pack(pady=(20, 0))

        tk.Label(
            header,
            text="INTERACTIVE DIGITAL MENU",
            font=("Arial", 10),
            fg="#D5C9A8",
            bg="#263D35"
        ).pack()

        self.main_frame = tk.Frame(
            self.root,
            bg="#F5F2EA"
        )

        # Menu starts hidden.
        self.menu_open = False

    # =================================
    # OPEN MENU
    # =================================

    def show_menu(self):

        if not self.main_frame.winfo_manager():

            self.main_frame.pack(
                fill="both",
                expand=True,
                padx=35,
                pady=25
            )

        self.menu_open = True
        self.game_open = False

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        category = self.categories[self.current_index]

        tk.Label(
            self.main_frame,
            text="Explore Our Menu",
            font=("Arial", 24, "bold"),
            bg="#F5F2EA",
            fg="#263D35"
        ).pack(anchor="w")

        tk.Label(
            self.main_frame,
            text="Choose your favorite category",
            font=("Arial", 12),
            bg="#F5F2EA",
            fg="#777777"
        ).pack(anchor="w", pady=(5, 20))

        # CATEGORY BUTTONS

        category_frame = tk.Frame(
            self.main_frame,
            bg="#F5F2EA"
        )

        category_frame.pack(fill="x", pady=10)

        for i, name in enumerate(self.categories):

            color = (
                "#263D35"
                if i == self.current_index
                else "#DDD8CC"
            )

            text_color = (
                "white"
                if i == self.current_index
                else "#263D35"
            )

            tk.Button(
                category_frame,
                text=name,
                font=("Arial", 11, "bold"),
                bg=color,
                fg=text_color,
                activebackground="#B99B62",
                relief="flat",
                width=17,
                height=2,
                command=lambda index=i: self.select_category(index)
            ).pack(side="left", padx=5)

        # CURRENT CATEGORY

        tk.Label(
            self.main_frame,
            text=category,
            font=("Arial", 19, "bold"),
            bg="#F5F2EA",
            fg="#263D35"
        ).pack(anchor="w", pady=(25, 15))

        # FOOD CARDS

        cards_frame = tk.Frame(
            self.main_frame,
            bg="#F5F2EA"
        )

        cards_frame.pack(fill="x")

        for name, price in self.menu_items[category]:

            card = tk.Frame(
                cards_frame,
                bg="white",
                width=270,
                height=190,
                highlightbackground="#DED8CA",
                highlightthickness=1
            )

            card.pack(side="left", padx=10)
            card.pack_propagate(False)

            tk.Label(
                card,
                text="🍽",
                font=("Arial", 35),
                bg="white"
            ).pack(pady=(20, 5))

            tk.Label(
                card,
                text=name,
                font=("Arial", 14, "bold"),
                bg="white",
                fg="#263D35"
            ).pack()

            tk.Label(
                card,
                text=price,
                font=("Arial", 12),
                bg="white",
                fg="#A17B42"
            ).pack(pady=5)

            tk.Button(
                card,
                text="SELECT",
                bg="#263D35",
                fg="white",
                relief="flat",
                command=lambda n=name: self.select_item(n)
            ).pack(pady=5)

        # BOTTOM CONTROLS

        controls = tk.Frame(
            self.main_frame,
            bg="#F5F2EA"
        )

        controls.pack(
            side="bottom",
            fill="x",
            pady=15
        )

        tk.Button(
            controls,
            text="◀ Previous",
            font=("Arial", 11, "bold"),
            bg="#B99B62",
            fg="white",
            relief="flat",
            width=15,
            command=self.previous_category
        ).pack(side="left")

        tk.Button(
            controls,
            text="NEXT ▶",
            font=("Arial", 11, "bold"),
            bg="#B99B62",
            fg="white",
            relief="flat",
            width=15,
            command=self.next_category
        ).pack(side="right")

        print("Menu Opened")

    # =================================
    # CLOSE MENU
    # =================================

    def close_menu(self):

        if not self.menu_open:
            return

        self.main_frame.pack_forget()

        self.menu_open = False
        self.game_open = False

        print("Menu Closed")

    # =================================
    # CATEGORY NAVIGATION
    # =================================

    def select_category(self, index):

        if not self.menu_open:
            return

        self.current_index = index
        self.selected_item = None

        self.show_menu()

    def next_category(self):

        if not self.menu_open:
            return

        self.current_index = (
            self.current_index + 1
        ) % len(self.categories)

        self.show_menu()

    def previous_category(self):

        if not self.menu_open:
            return

        self.current_index = (
            self.current_index - 1
        ) % len(self.categories)

        self.show_menu()

    # =================================
    # SELECT ITEM
    # =================================

    def select_item(self, item):

        if not self.menu_open:
            return

        self.selected_item = item

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.main_frame,
            text="Item Selected!",
            font=("Arial", 25, "bold"),
            bg="#F5F2EA",
            fg="#263D35"
        ).pack(pady=80)

        tk.Label(
            self.main_frame,
            text=item,
            font=("Arial", 22),
            bg="#F5F2EA",
            fg="#A17B42"
        ).pack(pady=10)

        tk.Button(
            self.main_frame,
            text="BACK TO MENU",
            font=("Arial", 12, "bold"),
            bg="#263D35",
            fg="white",
            relief="flat",
            command=self.show_menu
        ).pack(pady=30)

    # =================================
    # GAME SCREEN
    # =================================

    def open_game(self):

        if not self.menu_open or self.game_open:
            return

        self.game_open = True

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.main_frame,
            text="RESTAURANT GAME",
            font=("Arial", 28, "bold"),
            bg="#F5F2EA",
            fg="#263D35"
        ).pack(pady=100)

        tk.Label(
            self.main_frame,
            text="Welcome to the Interactive Game!",
            font=("Arial", 16),
            bg="#F5F2EA",
            fg="#777777"
        ).pack()

        tk.Button(
            self.main_frame,
            text="BACK TO MENU",
            font=("Arial", 12, "bold"),
            bg="#263D35",
            fg="white",
            relief="flat",
            command=self.show_menu
        ).pack(pady=40)

    # =================================
    # SELECT CURRENT CATEGORY
    # =================================

    def select_current_category(self):

        if not self.menu_open:
            return

        category = self.categories[self.current_index]

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.main_frame,
            text="Category Selected!",
            font=("Arial", 25, "bold"),
            bg="#F5F2EA",
            fg="#263D35"
        ).pack(pady=80)

        tk.Label(
            self.main_frame,
            text=category,
            font=("Arial", 22),
            bg="#F5F2EA",
            fg="#A17B42"
        ).pack(pady=10)

        tk.Button(
            self.main_frame,
            text="BACK TO MENU",
            font=("Arial", 12, "bold"),
            bg="#263D35",
            fg="white",
            relief="flat",
            command=self.show_menu
        ).pack(pady=30)

    # =================================
    # GESTURE HANDLER
    # =================================

    def handle_gesture(self, gesture):

        print("GUI Received:", gesture)

        if gesture == "OPEN_PALM":

            self.show_menu()

        elif gesture == "CLOSED_FIST":

            self.close_menu()

        elif gesture == "SWIPE_RIGHT":

            self.next_category()

        elif gesture == "SWIPE_LEFT":

            self.previous_category()

        # V_SHAPE and ZIGZAG will be added
        # later for scrolling functionality.

        else:

            print("Gesture ignored:", gesture)


# =================================
# RUN GUI
# =================================

if __name__ == "__main__":

    root = tk.Tk()

    app = RestaurantMenuUI(root)

    root.mainloop()
