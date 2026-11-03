"""Generate the default DollarPy swipe templates (swipe_templates.json).

Each direction gets several variants (speed profile, slight drift, slight arc)
so DollarPy can match natural, imperfect hand movements. Recorded templates
from tools/record_swipe_templates.py are kept: only SWIPE_*_GEN_* entries are
replaced.

    python tools/make_swipe_templates.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from movement_dollarpy import TEMPLATES_FILE, encode, synthetic_trail  # noqa: E402

VARIANTS = [
    {"easing": "linear"},
    {"easing": "ease"},
    {"easing": "fast_start"},
    {"easing": "ease", "drift": 0.25},
    {"easing": "ease", "drift": -0.25},
    {"easing": "linear", "curve": 0.2},
    {"easing": "linear", "curve": -0.2},
]


def main():
    existing = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8")) if TEMPLATES_FILE.exists() else {}
    templates = {k: v for k, v in existing.items() if "_GEN_" not in k}
    for direction in ("left", "right", "up", "down"):
        for i, variant in enumerate(VARIANTS, 1):
            points = encode(synthetic_trail(direction, **variant))
            templates[f"SWIPE_{direction.upper()}_GEN_{i}"] = [[round(x, 4), round(y, 4)] for x, y in points]
    TEMPLATES_FILE.write_text(json.dumps(templates, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(templates)} templates to {TEMPLATES_FILE.name}")


if __name__ == "__main__":
    main()
