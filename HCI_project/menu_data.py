"""Local restaurant catalogue and the corresponding original Figma imagery."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dish:
    name: str
    price: int
    description: str
    photo: str | None
    ingredients: str = "Ask a member of staff for ingredients and allergen information."
    available: bool = True
    detail_photo: str | None = None


DISHES = {
    "House burger": Dish(
        "House burger", 280,
        "Grilled beef, tahini sauce, crisp greens and a toasted brioche bun.",
        "interactive_imgFoodPhotograph.png",
        "Beef, brioche, cheese, lettuce, tomato, pickles, tahini sauce.",
        detail_photo="detail_imgFoodPhotograph4.png",
    ),
    "Garden fattoush": Dish(
        "Garden fattoush", 150,
        "Cucumber, tomato, sumac and toasted pita. Bright, fresh, generous.",
        "interactive_imgFoodPhotograph1.png", available=False,
    ),
    "Fresh orange juice": Dish(
        "Fresh orange juice", 90,
        "Freshly squeezed oranges. Nothing added, just sunshine in a glass.",
        "interactive_imgFoodPhotograph2.png", "Fresh oranges.",
    ),
    "Lemon grilled chicken": Dish(
        "Lemon grilled chicken", 320,
        "Chargrilled chicken, lemon, herbs and warm flatbread.",
        "detail_imgFoodPhotograph2.png",
    ),
    "Roasted aubergine": Dish(
        "Roasted aubergine", 220,
        "Roasted aubergine with tahini, herbs and pomegranate.",
        "detail_imgFoodPhotograph3.png",
    ),
    "Hibiscus cooler": Dish(
        "Hibiscus cooler", 80, "Chilled hibiscus with citrus and ice.",
        "drinks_imgFoodPhotograph1.png",
    ),
    "Mint lemonade": Dish(
        "Mint lemonade", 95, "Fresh lemon, mint and a bright little lift.",
        "drinks_imgFoodPhotograph2.png",
    ),
    "Chocolate cake": Dish("Chocolate cake", 120, "A little chocolate indulgence, made to share.", None),
    "Ice cream": Dish("Ice cream", 100, "A cool, creamy finish to your meal.", None),
    "Cheesecake": Dish("Cheesecake", 140, "Our daily cheesecake. Ask staff for today’s flavour.", None),
}

CATEGORIES = {
    "Small plates": ["Garden fattoush", "Roasted aubergine", "Lemon grilled chicken"],
    "Main courses": ["House burger", "Garden fattoush", "Fresh orange juice"],
    "Snacks": ["Roasted aubergine", "Lemon grilled chicken", "House burger"],
    "Drinks": ["Fresh orange juice", "Hibiscus cooler", "Mint lemonade"],
    "Desserts": ["Chocolate cake", "Ice cream", "Cheesecake"],
}
