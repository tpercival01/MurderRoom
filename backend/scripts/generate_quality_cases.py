import json
import time
from pathlib import Path

import httpx


BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("quality_tests/baseline")

OBJECT_SETS = {
    "set-a": ["lamp", "book", "mug", "chair"],
    "set-b": ["mirror", "clock", "candle", "photograph"],
    "set-c": ["shoe", "remote control", "water bottle", "backpack"],
    "set-d": ["glass", "bottle", "plate", "knife"],
}

SEEDS = [1001, 1002, 1003]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=180.0) as client:
        for set_name, room_objects in OBJECT_SETS.items():
            for seed in SEEDS:
                filename = OUTPUT_DIR / f"{set_name}-seed-{seed}.json"
                error_filename = OUTPUT_DIR / f"{set_name}-seed-{seed}-error.json"

                print(f"Generating {filename.name}...")

                started_at = time.perf_counter()

                response = client.post(
                    f"{BASE_URL}/generate-case",
                    json={
                        "room_objects": room_objects,
                        "difficulty": "standard",
                        "seed": seed,
                    },
                )

                duration = time.perf_counter() - started_at

                if response.is_error:
                    filename.unlink(missing_ok=True)
                    error_filename.write_text(
                        json.dumps(
                            {
                                "status_code": response.status_code,
                                "response": response.text,
                                "duration_seconds": round(duration, 1),
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )

                    print(
                        f"FAILED {error_filename.name} "
                        f"({duration:.1f} seconds, HTTP {response.status_code})"
                    )
                    continue

                filename.write_text(
                    json.dumps(response.json(), indent=2),
                    encoding="utf-8",
                )
                error_filename.unlink(missing_ok=True)

                print(
                    f"Saved {filename.name} "
                    f"({duration:.1f} seconds, HTTP {response.status_code})"
                )


if __name__ == "__main__":
    main()