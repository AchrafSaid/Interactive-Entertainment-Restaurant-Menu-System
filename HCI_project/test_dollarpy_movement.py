"""DollarPy movement classification: accuracy, direction, rejection and wiring."""
import random
import unittest

from hand_input import HandInput
from movement_dollarpy import MovementClassifier, encode, load_templates, synthetic_trail


def noisy(direction, rng):
    trail = synthetic_trail(direction, samples=rng.randint(6, 20), duration=rng.uniform(.2, .7),
                            drift=rng.uniform(-.3, .3), curve=rng.uniform(-.25, .25),
                            easing=rng.choice(["linear", "ease", "fast_start"]), distance=rng.uniform(.1, .4))
    return [(t, x + rng.gauss(0, .006), y + rng.gauss(0, .006)) for t, x, y in trail]


class DollarPyClassifierTests(unittest.TestCase):
    def test_templates_exist_for_every_direction(self):
        names = load_templates()
        for direction in ("LEFT", "RIGHT", "UP", "DOWN"):
            self.assertTrue(any(n.startswith(f"SWIPE_{direction}") for n in names), direction)

    def test_dollarpy_classifies_noisy_movements_in_all_four_directions(self):
        rng, classifier = random.Random(7), MovementClassifier()
        for direction in ("left", "right", "up", "down"):
            results = [classifier.classify(noisy(direction, rng))[0] for _ in range(25)]
            self.assertGreaterEqual(results.count(direction), 24, (direction, results))

    def test_opposite_directions_are_different_shapes_for_dollarpy(self):
        # $P ignores point order, so the encoding must make left and right differ.
        left, right = encode(synthetic_trail("left")), encode(synthetic_trail("right"))
        self.assertNotEqual(sorted(map(tuple, left)), sorted(map(tuple, right)))
        self.assertEqual(MovementClassifier().classify(synthetic_trail("left"))[1], "SWIPE_LEFT")

    def test_templates_do_not_grow_when_recognising(self):
        # dollarpy inserts points into the lists it receives; ours must stay intact.
        classifier = MovementClassifier()
        sizes = {name: len(points) for name, points in classifier.templates.items()}
        for _ in range(5):
            classifier.classify(synthetic_trail("up"))
        self.assertEqual(sizes, {name: len(points) for name, points in classifier.templates.items()})

    def test_still_hand_and_too_short_trails_are_rejected(self):
        classifier = MovementClassifier()
        self.assertIsNone(classifier.classify([(0, .5, .5), (.1, .5, .5)])[0])
        rng = random.Random(3)
        still = [(i / 30, .5 + rng.gauss(0, .004), .5 + rng.gauss(0, .004)) for i in range(12)]
        self.assertIsNone(classifier.classify(still)[0])


class FixedClassifier:
    """Stand-in that proves HandInput uses the classifier's answer."""
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def classify(self, trail):
        self.calls += 1
        return (self.answer, f"SWIPE_{self.answer.upper()}", .9) if self.answer else (None, "SWIPE_UP", .3)


class HandInputUsesDollarPyTests(unittest.TestCase):
    def swipe_right(self, hand):
        return [hand.step("menu", .3 + .4 * n / 6, .5, n / 30) for n in range(7)]

    def test_direction_comes_from_dollarpy_not_from_geometry(self):
        events = self.swipe_right(HandInput(FixedClassifier("left")))
        swipes = [e for e in events if e["action"] == "swipe"]
        self.assertEqual([e["direction"] for e in swipes], ["left"])
        self.assertEqual(swipes[0]["classifier"], "dollarpy")
        self.assertEqual(swipes[0]["gesture"], "SWIPE_LEFT")

    def test_rejected_movement_does_not_move_and_is_not_retried_every_frame(self):
        classifier = FixedClassifier(None)
        events = self.swipe_right(HandInput(classifier))
        self.assertFalse(any(e["action"] == "swipe" for e in events))
        self.assertLess(classifier.calls, 4)

    def test_real_dollarpy_swipe_event_reports_its_score(self):
        events = self.swipe_right(HandInput())
        swipe = next(e for e in events if e["action"] == "swipe")
        self.assertEqual((swipe["direction"], swipe["gesture"]), ("right", "SWIPE_RIGHT"))
        self.assertGreaterEqual(swipe["score"], .7)


if __name__ == "__main__":
    unittest.main()
