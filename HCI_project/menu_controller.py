
class MenuController:

    def __init__(self):
        self.categories = [
            "Main Meals",
            "Drinks",
            "Desserts",
            "Offers"
        ]

        self.current_index = 0
        self.selected_item = None
        self.game_open = False

        print("Menu Controller Initialized!")
        self.show_menu()

    def show_menu(self):
        print("\n========== RESTAURANT MENU ==========")
        print("Current Category:", self.categories[self.current_index])
        print("====================================")

    def handle_gesture(self, gesture):

        print("\nReceived Gesture:", gesture)

        if gesture == "SWIPE_LEFT":
            self.previous_category()

        elif gesture == "SWIPE_RIGHT":
            self.next_category()

        elif gesture == "V_SHAPE":
            self.select_item()

        elif gesture == "ZIGZAG":
            self.open_game()

        elif gesture == "OPEN_PALM":
            self.go_back()

        else:
            print("Unknown Gesture!")

    def next_category(self):
        self.current_index = (
            self.current_index + 1
        ) % len(self.categories)

        print("Action: Next Category")
        self.show_menu()

    def previous_category(self):
        self.current_index = (
            self.current_index - 1
        ) % len(self.categories)

        print("Action: Previous Category")
        self.show_menu()

    def select_item(self):
        self.selected_item = self.categories[self.current_index]

        print("Action: Select Item")
        print("Selected:", self.selected_item)

    def open_game(self):

        if self.game_open:
            print("Game is already open!")
            return

        self.game_open = True

        print("Action: Open Game")
        print("Restaurant Game is now open!")

    def go_back(self):
        if self.game_open:
            self.game_open = False
            print("Action: Close Game")
        else:
            self.selected_item = None
            print("Action: Back to Menu")
            self.show_menu()