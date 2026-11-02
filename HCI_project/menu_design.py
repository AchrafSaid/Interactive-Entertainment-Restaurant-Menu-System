"""Tkinter-compatible rendering of the OLIVE / TABLE Figma design.

The design is drawn from live application data, original assets and bundled
fonts. Hit targets remain interactive at every window size; no Figma screen
capture is used as a UI background.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = Path(__file__).resolve().parent / "assets"
CANVAS = "#F7F4ED"
SURFACE = "#FFFEFA"
FOREST = "#173E32"
SAGE = "#E4EBE3"
CHARCOAL = "#252B27"
SECONDARY = "#626B63"
DIVIDER = "#D8DCD3"
TERRACOTTA = "#A54C35"
SCALE = 2


@dataclass
class Action:
    text: str
    rect: tuple
    command: object
    enabled: bool = True
    key: str = ""

    def invoke(self):
        if self.enabled:
            return self.command()

    def cget(self, name):
        return self.text if name == "text" else ("normal" if self.enabled else "disabled")


@lru_cache(maxsize=128)
def font(size, family="Inter", bold=False):
    name = "Lora-Regular.ttf" if family == "Lora" else ("Inter-SemiBold.ttf" if bold else "Inter-Regular.ttf")
    return ImageFont.truetype(str(ASSETS / "fonts" / name), round(size * SCALE))


@lru_cache(maxsize=128)
def picture(name, width, height, radius=0, fit=True):
    source = Image.open(ASSETS / "figma" / name).convert("RGBA")
    size = (round(width * SCALE), round(height * SCALE))
    if fit:
        source = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
    else:
        source = source.resize(size, Image.Resampling.LANCZOS)
    if radius:
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *size), radius=radius * SCALE, fill=255)
        source.putalpha(mask)
    return source


class MenuRenderer:
    width = 1194

    def __init__(self, app):
        self.app = app
        self.actions = []
        self.asset_slots = []

    def rect(self, box, fill=SURFACE, radius=16, outline=None, stroke=1):
        self.draw.rounded_rectangle(tuple(round(v * SCALE) for v in box),
                                    radius=round(radius * SCALE), fill=fill,
                                    outline=outline, width=round(stroke * SCALE))

    def line(self, x1, y1, x2, y2, color=DIVIDER):
        self.draw.line(tuple(round(v * SCALE) for v in (x1, y1, x2, y2)), fill=color, width=SCALE)

    def text(self, x, y, text, size=15, color=CHARCOAL, family="Inter", bold=False,
             width=None, line_height=None, align="left", tracking=0):
        face = font(size, family, bold)
        lines = []
        for paragraph in str(text).split("\n"):
            if width is None:
                lines.append(paragraph)
                continue
            line = ""
            for word in paragraph.split():
                candidate = (line + " " + word).strip()
                if line and self.draw.textlength(candidate, font=face) > width * SCALE:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        step = line_height or size * 1.45
        for index, line in enumerate(lines):
            dx = 0
            measured = self.draw.textlength(line, font=face) / SCALE
            if width and align == "center":
                dx = (width - measured) / 2
            elif width and align == "right":
                dx = width - measured
            if tracking:
                cursor = (x + dx) * SCALE
                for character in line:
                    self.draw.text((round(cursor), round((y + index * step) * SCALE)),
                                   character, fill=color, font=face, anchor="lt")
                    cursor += self.draw.textlength(character, font=face) + tracking * SCALE
            else:
                self.draw.text((round((x + dx) * SCALE), round((y + index * step) * SCALE)),
                               line, fill=color, font=face, anchor="lt")
        return len(lines) * step

    def photo(self, name, box, radius=12, fit=True):
        x, y, right, bottom = box
        self.image.paste(picture(name, right - x, bottom - y, radius, fit),
                         (round(x * SCALE), round(y * SCALE)),
                         picture(name, right - x, bottom - y, radius, fit))
        self.asset_slots.append((name, box))

    def icon(self, name, x, y, size=24):
        self.photo(name, (x, y, x + size, y + size), radius=0, fit=False)

    def target(self, text, box, command, key="", enabled=True):
        action = Action(text, box, command, enabled, key)
        self.actions.append(action)
        return action

    def button(self, text, box, command, kind="secondary", icon=None, enabled=True, key=""):
        x, y, right, bottom = box
        fill = FOREST if kind == "primary" else SAGE if kind == "selected" else SURFACE
        color = SURFACE if kind == "primary" else FOREST
        outline = FOREST if kind == "secondary" else None
        if not enabled:
            fill, color, outline = "#E7E8E2", "#858B84", None
        if kind == "tertiary":
            fill, outline = CANVAS, None
        self.rect(box, fill, 12, outline)
        face = font(16, bold=True)
        total = self.draw.textlength(text, font=face) / SCALE + (28 if icon else 0)
        start = x + (right - x - total) / 2
        if icon:
            self.icon(icon, start, y + (bottom - y - 20) / 2, 20)
            start += 28
        self.text(start, y + (bottom - y - 16) / 2 - 1, text, 16, color, bold=True)
        return self.target(text, box, command, key, enabled)

    def chip(self, label, box, icon=None, fill=SAGE, color=FOREST):
        self.rect(box, fill, 8)
        x, y, _, bottom = box
        if icon:
            self.icon(icon, x + 12, y + (bottom - y - 16) / 2, 16)
            x += 24
        self.text(x + 12, y + (bottom - y - 12) / 2, label, 12, color, bold=True)

    def header(self, selected="Menu"):
        app = self.app
        self.rect((0, 0, 1194, 104), SURFACE, 16, DIVIDER)
        self.text(24, 47, "OLIVE / TABLE", 20, FOREST, bold=True, tracking=2)
        for label, x, width, icon, action in [
            ("Menu", 372, 120, "interactive_imgUtensils.png", app.show_menu),
            ("Rewards", 500, 140, "interactive_imgGift.png", app.show_rewards),
            ("Games", 648, 130, "interactive_imgGamepad2.png", app.open_game),
        ]:
            if label == selected:
                self.rect((x, 29, x + width, 85), SAGE, 12)
            self.icon(icon, x + 20, 45, 24)
            self.text(x + 52, 48, label, 17, FOREST, bold=label == selected)
            self.target(label, (x, 29, x + width, 85), action)
        self.button(f"Order · {app.order_count} · EGP {app.order_total}",
                    (970, 29, 1166, 85), app.show_order, "primary")
        self.line(0, 170, 1194, 170)
        self.text(48, 133, "Table 08    /    Welcome, guest", 14, FOREST, bold=True)
        status = "Camera off" if not app.camera_enabled else (
            "Camera on · Hand control" if app.hand_control_enabled else "Camera on · Touch control")
        self.text(535, 133, status, 13, SECONDARY)
        self.target("Help / Call staff", (988, 104, 1146, 170), app.show_help)
        self.text(998, 132, "Help / Call staff", 16, FOREST, bold=True)

    def welcome(self):
        app = self.app
        self.photo("welcome_imgSharedMediterraneanTable.png", (0, 0, 620, 834), 0)
        self.text(48, 53, "OLIVE / TABLE", 22, SURFACE, bold=True, tracking=3)
        overlay = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle((48*SCALE, 612*SCALE, 572*SCALE, 786*SCALE),
                                                 16*SCALE, fill=(23, 62, 50, 232))
        self.image = Image.alpha_composite(self.image, overlay)
        self.draw = ImageDraw.Draw(self.image)
        self.text(72, 636, "Good food.\nGood company.", 40, SURFACE, "Lora", line_height=44)
        self.text(72, 736, "A little of the Mediterranean, a warm Egyptian welcome.", 16, SURFACE, width=476)
        self.chip("Table 08", (668, 48, 767, 80), "welcome_imgCircleCheck.png")
        self.text(1045, 72, "English", 16, FOREST, bold=True)
        self.text(668, 154, "A place at\nthe table.", 56, FOREST, "Lora", line_height=60)
        self.text(668, 300, "Settle in. Explore our menu and make yourself at home.",
                  17, SECONDARY, width=478)
        self.button("Continue as guest", (673, 347, 1141, 403), app.show_menu, "primary")
        self.text(668, 437, "No account or personal details needed to browse.", 13, SECONDARY)
        self.line(668, 474, 1146, 474)
        self.button("How hand control works", (673, 503, 1141, 559), app.show_help)
        self.button("Open palm to open the menu", (673, 594, 1141, 650), app.show_menu, "tertiary")
        self.button("Help / Call staff · Table 08", (673, 698, 1141, 754), app.show_help, "tertiary")
        self.text(668, 780, "Hand control is always optional · Buttons work too", 13,
                  SECONDARY, width=478, align="center")

    def categories(self, top=312):
        app = self.app
        for index, category in enumerate(app.categories):
            y = top + index * 74
            selected = index == app.current_index
            self.rect((54, y, 198, y + 56), FOREST if selected else SURFACE, 12, DIVIDER)
            self.text(54, y + 20, category, 15, SURFACE if selected else FOREST,
                      bold=selected, width=144, align="center")
            self.target(category, (54, y, 198, y + 56),
                        lambda i=index: app.select_category(i), f"category:{category}")

    def card(self, dish, box, index, photo=None):
        app = self.app
        x, y, right, bottom = box
        width = right - x
        self.rect(box, SURFACE, 16, DIVIDER)
        if photo or dish.photo:
            self.photo(photo or dish.photo, (x + 16, y + 16, right - 16, y + 192))
        else:
            self.rect((x + 16, y + 16, right - 16, y + 192), SAGE, 12)
            self.text(x + 30, y + 76, "Something sweet.", 25, FOREST, "Lora", width=width - 60)
        self.text(x + 16, y + 216, dish.name, 25, CHARCOAL, "Lora", width=width - 32, line_height=30)
        self.text(x + 16, y + 254, dish.description, 15, SECONDARY, width=width - 32, line_height=21.75)
        self.text(x + 16, y + 338, f"EGP {dish.price}", 17, FOREST, bold=True)
        self.button("Add" if dish.available else "Unavailable", (right - 168, y + 316, right - 20, y + 372),
                    lambda n=dish.name: app.add_to_order(n), enabled=dish.available,
                    icon="interactive_imgPlus.png" if dish.available else None, key=f"add:{dish.name}")
        if not dish.available:
            self.chip("Not available today", (x + 28, y + 28, x + 220, y + 64),
                      "interactive_imgBan.png", "#EFECE4", SECONDARY)
        elif app.cart.get(dish.name):
            self.chip("Added · Undo available", (x + 28, y + 28, x + 228, y + 64), "interactive_imgCheck.png")
        self.target(dish.name, (x, y, right, y + 310),
                    lambda n=dish.name: app.select_item(n), f"select:{index}")

    def menu(self):
        app = self.app
        self.header()
        self.text(48, 200, "A new way to\nbrowse.", 40, FOREST, "Lora", width=300, line_height=44)
        self.rect((408, 216, 648, 260), SAGE, 12)
        self.icon("interactive_imgHand.png", 420, 228, 20)
        self.text(448, 231, "Hand control active" if app.hand_control_enabled else "Touch control active",
                  14, CHARCOAL, bold=True)
        self.chip("Camera on" if app.camera_enabled else "Camera off", (664, 220, 774, 254),
                  "interactive_imgCircleCheck.png")
        self.button("Turn camera off" if app.camera_enabled else "Turn camera on",
                    (790, 210, 950, 266), app.toggle_camera, "tertiary")
        self.button("Use touch instead" if app.hand_control_enabled else "Use hand control",
                    (972, 210, 1142, 266), app.toggle_hand_control)
        self.categories()
        for index, name in enumerate(app.visible_items):
            x = 220 + index * (297.333 + 16)
            self.card(app.dishes[name], (x, 306, x + 297.333, 754), index)
        self.rect((48, 790, 388, 902), SURFACE, 16, DIVIDER)
        self.icon("interactive_imgCursorTarget.png", 72, 798, 96)
        self.text(184, 805, "Point to choose\na dish", 15, CHARCOAL, bold=True, line_height=21)
        self.text(184, 857, "Left · center · right", 13, SECONDARY)
        self.text(404, 816, "One finger + hold to view a dish", 13, SECONDARY)
        self.text(404, 843, "Palm sweep to browse · Fist hold to close", 13, SECONDARY)
        self.text(404, 870, "Open palm to go back · Buttons work too", 13, SECONDARY)
        self.rect((886, 790, 1146, 902), FOREST, 16)
        self.text(906, 820, f"Review order · {app.order_count} items", 20, SURFACE, bold=True)
        self.text(906, 856, f"EGP {app.order_total} · Table 08", 17, SURFACE)
        self.target("Review order", (886, 790, 1146, 902), app.show_order)

    def catalogue_background(self):
        """The two-column catalogue visible behind the Figma dish sheet."""
        app = self.app
        self.header()
        self.text(48, 194, "From our kitchen.", 40, FOREST, "Lora")
        self.text(48, 246, "Familiar flavours, generously made.", 17, SECONDARY)
        self.categories(296)
        for index, (name, photo) in enumerate([
            ("House burger", "detail_imgFoodPhotograph.png"),
            ("Garden fattoush", "detail_imgFoodPhotograph1.png"),
            ("Lemon grilled chicken", "detail_imgFoodPhotograph2.png"),
            ("Roasted aubergine", "detail_imgFoodPhotograph3.png"),
        ]):
            x, y = 228 + (index % 2) * 324, 291 + (index // 2) * 432
            self.card(app.dishes[name], (x, y, x + 300, y + 408), index, photo)
        self.rect((876, 291, 1146, 730), SURFACE, 16)
        self.text(900, 315, "Your order", 32, FOREST, "Lora")
        self.text(900, 365, f"Table 08 · {app.order_count} items", 13, SECONDARY)
        self.line(900, 395, 1122, 395)
        for index, (name, quantity) in enumerate(list(app.cart.items())[:2]):
            self.text(900, 418 + index * 64, f"{quantity} × {name}", 16, SECONDARY, bold=True, width=222)
            self.text(900, 447 + index * 64, f"EGP {app.dishes[name].price * quantity}", 13, SECONDARY)
        self.line(900, 556, 1122, 556)
        self.text(900, 578, "Total", 16, CHARCOAL, bold=True)
        self.text(1002, 576, f"EGP {app.order_total}", 20, FOREST, bold=True)
        self.text(900, 747, "Ask staff about allergens.", 13, SECONDARY)

    def detail(self):
        app = self.app
        dish = app.dishes[app.selected_item]
        self.catalogue_background()
        self.actions.clear()
        shade = Image.new("RGBA", self.image.size, (16, 37, 29, 135))
        self.image = Image.alpha_composite(self.image, shade)
        self.draw = ImageDraw.Draw(self.image)
        self.rect((40, 140, 1154, 699), SURFACE, 24, DIVIDER)
        if dish.detail_photo or dish.photo:
            self.photo(dish.detail_photo or dish.photo, (72, 172, 552, 602))
        else:
            self.rect((72, 172, 552, 602), SAGE, 12)
        self.chip("HOUSE FAVOURITE" if dish.name == "House burger" else app.categories[app.current_index].upper(),
                  (592, 180, 724, 210), fill="#F5E8E1", color=TERRACOTTA)
        self.rect((1078, 172, 1122, 216), "#EFECE4", 22)
        self.icon("detail_imgX.png", 1088, 182, 24)
        self.target("BACK TO MENU", (1078, 172, 1122, 216), app.show_menu)
        self.text(592, 244, dish.name, 40, CHARCOAL, "Lora", width=530, line_height=44)
        description = ("Flame-grilled beef, melted cheese and our house tahini sauce, layered with crisp greens in a toasted brioche bun."
                       if dish.name == "House burger" else dish.description)
        self.text(592, 308, description, 17, SECONDARY, width=530, line_height=24.65)
        self.text(592, 378, "Ingredients", 15, CHARCOAL, bold=True)
        self.text(592, 406, dish.ingredients, 15, SECONDARY, width=530)
        self.icon("detail_imgInfo.png", 592, 454, 20)
        self.text(620, 458, "Ask staff about allergens", 15, FOREST)
        self.target("Ask staff about allergens", (592, 450, 950, 486), app.show_help)
        self.line(592, 504, 1122, 504)
        self.text(592, 543, f"EGP {dish.price}", 24, FOREST, bold=True)
        self.rect((976, 525, 1122, 581), "#EFECE4", 12)
        self.icon("detail_imgMinus.png", 992, 543, 20)
        self.text(1044, 545, str(app.quantity), 16, CHARCOAL, bold=True)
        self.icon("detail_imgPlus.png", 1088, 543, 20)
        self.target("Decrease quantity", (976, 525, 1024, 581), lambda: app.change_quantity(-1))
        self.target("Increase quantity", (1074, 525, 1122, 581), lambda: app.change_quantity(1))
        self.button(f"Add to order · EGP {dish.price * app.quantity}" if dish.available else "Not available today",
                    (597, 607, 1117, 663), lambda: app.add_to_order(dish.name, app.quantity), "primary",
                    "detail_imgPlus1.png", dish.available, "add-detail")
        self.text(40, 725, f"Your order is preserved · {app.order_count} items · EGP {app.order_total}",
                  17, SURFACE, width=1114, align="center")

    def order(self):
        app = self.app
        self.header()
        self.text(48, 200, "A little of what you love.", 40, FOREST, "Lora")
        self.text(48, 252, "Your order · Table 08", 17, SECONDARY)
        self.button("Browse more", (972, 205, 1142, 261), app.show_menu)
        app.order_page = min(app.order_page, max(0, (len(app.cart) - 1) // 2))
        page_items = list(app.cart.items())[app.order_page * 2:app.order_page * 2 + 2]
        self.rect((48, 296, 764, 772), SURFACE, 16)
        if not app.cart:
            self.text(80, 336, "Your table is waiting.", 32, FOREST, "Lora")
            self.text(80, 397, "Choose something delicious from the menu to begin.", 17, SECONDARY, width=620)
            self.button("Explore the menu", (80, 466, 342, 522), app.show_menu, "primary")
        for index, (name, quantity) in enumerate(page_items):
            dish = app.dishes[name]
            y = 320 + index * 214
            photo = ("order_imgFoodPhotograph.png" if name == "House burger" else
                     "order_imgFoodPhotograph1.png" if name == "Fresh orange juice" else dish.photo)
            if photo:
                self.photo(photo, (72, y, 164, y + 92), 12)
            self.text(184, y + 21, name, 25, CHARCOAL, "Lora", width=390)
            self.text(184, y + 57, f"{quantity} × EGP {dish.price}", 15, SECONDARY)
            self.text(634, y + 36, f"EGP {dish.price * quantity}", 18, FOREST, bold=True)
            self.rect((72, y + 112, 218, y + 168), "#EFECE4", 12)
            self.icon("order_imgMinus.png", 88, y + 130, 20)
            self.text(140, y + 132, str(quantity), 17, bold=True)
            self.icon("order_imgPlus.png", 184, y + 130, 20)
            self.target("Decrease " + name, (72, y + 112, 120, y + 168), lambda n=name: app.adjust_order(n, -1))
            self.target("Increase " + name, (170, y + 112, 218, y + 168), lambda n=name: app.adjust_order(n, 1))
            self.icon("order_imgTrash2.png", 624, y + 130, 20)
            self.text(652, y + 132, "Remove", 16, FOREST, bold=True)
            self.target("Remove " + name, (616, y + 112, 740, y + 168), lambda n=name: app.remove_from_order(n))
            if index < len(page_items) - 1:
                self.line(72, y + 191, 740, y + 191)
        if app.cart:
            self.text(72, 734, "Use Remove to take an item out. Undo will be available.", 13, SECONDARY)
        self.rect((796, 296, 1146, 672), SURFACE, 16, DIVIDER)
        self.text(820, 328, "Your order", 32, FOREST, "Lora")
        self.text(820, 388, f"{app.order_count} items", 17, SECONDARY)
        self.text(1010, 388, f"EGP {app.order_total}", 17, CHARCOAL)
        self.line(820, 422, 1122, 422)
        self.text(820, 448, "Total", 20, CHARCOAL, bold=True)
        self.text(982, 448, f"EGP {app.order_total}", 28, FOREST, bold=True)
        self.button("Back to menu", (825, 500, 1117, 556), app.show_menu, "primary")
        self.text(820, 584, "Payment is handled by staff. Ask your server when you’re ready.",
                  15, SECONDARY, width=300)
        self.text(796, 696, "All displayed taxes and service are included. No hidden charges.",
                  13, SECONDARY, width=350)
        self.button("Rewards & guest dining", (801, 752, 1141, 808), app.show_rewards)
        self.text(796, 837, "Guest dining is always available. Payment is handled by staff, outside this app.",
                  13, SECONDARY, width=350)
        if len(app.cart) > 2:
            self.button("Previous items", (72, 790, 260, 846), lambda: app.change_order_page(-1),
                        enabled=app.order_page > 0)
            self.text(310, 810, f"Page {app.order_page + 1} of {(len(app.cart) + 1) // 2}", 15, SECONDARY)
            self.button("More items", (552, 790, 740, 846), lambda: app.change_order_page(1),
                        enabled=(app.order_page + 1) * 2 < len(app.cart))

    def message(self):
        app = self.app
        self.header("Games" if app.game_open else "Rewards" if app.screen == "rewards" else "Menu")
        title, body = app.message
        self.text(48, 206, title, 40, FOREST, "Lora", width=1098)
        self.rect((48, 296, 1146, 660), SURFACE, 16, DIVIDER)
        self.text(80, 330, body, 19, SECONDARY, width=1010, line_height=32)
        self.button("Back to menu", (80, 558, 360, 614), app.show_menu, "primary")

    def render(self):
        app = self.app
        self.actions = []
        self.asset_slots = []
        height = 834 if not app.menu_open else 934 if app.screen == "menu" else 843 if app.screen == "detail" else 901
        self.image = Image.new("RGBA", (self.width * SCALE, height * SCALE), CANVAS)
        self.draw = ImageDraw.Draw(self.image)
        if not app.menu_open:
            self.welcome()
        elif app.screen == "detail":
            self.detail()
        elif app.screen == "order":
            self.order()
        elif app.screen == "menu":
            self.menu()
        else:
            self.message()
        if app.notice and app.menu_open and app.screen != "detail":
            self.rect((228, height - 100, 966, height - 20), FOREST, 16)
            self.text(252, height - 74, app.notice, 17, SURFACE, bold=True, width=580)
            self.text(890, height - 71, "Undo", 17, SURFACE, bold=True)
            self.target("Undo", (864, height - 100, 966, height - 20), app.undo)
        return self.image, self.actions
