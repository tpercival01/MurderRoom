import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


INPUT_DIR = Path("quality_tests/baseline")
OUTPUT_FILE = INPUT_DIR / "quality_summary.csv"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_run_name(path: Path) -> tuple[str, str]:
    match = re.match(r"(set-[a-z])-seed-(\d+)", path.stem)

    if not match:
        return path.stem, ""

    return match.group(1), match.group(2)


def normalise_titles(titles: list[str]) -> str:
    return " | ".join(title.strip().lower() for title in titles)


def build_success_row(path: Path, case: dict[str, Any]) -> dict[str, Any]:
    object_set, seed = parse_run_name(path)

    suspects = case.get("suspects", [])
    clues = case.get("clues", [])
    solution = case.get("solution", {})

    killer_id = solution.get("killerID", "")
    killer_name = next(
        (
            suspect.get("name", "")
            for suspect in suspects
            if suspect.get("id") == killer_id
        ),
        "",
    )

    clue_titles = [clue.get("title", "") for clue in clues]

    direct_killer_clues = 0
    corroborated_non_killers: set[str] = set()

    for clue in clues:
        for deduction in clue.get("deductions", []):
            related_id = deduction.get("relatedSuspectID")
            deduction_kind = deduction.get("kind")

            if (
                related_id == killer_id
                and deduction_kind
                in {
                    "supportsSuspect",
                    "contradictsStatement",
                    "establishesOpportunity",
                }
            ):
                direct_killer_clues += 1

            if (
                related_id
                and related_id != killer_id
                and deduction_kind == "corroboratesAlibi"
            ):
                corroborated_non_killers.add(related_id)

    motive = solution.get("motive", "")
    motive_lower = motive.lower().strip()

    malformed_motive = (
        motive_lower.endswith("because")
        or motive_lower.endswith("because.")
        or motive_lower.count(" because ") > 1
    )

    likely_obvious_killer = (
        len(suspects) == 3
        and len(corroborated_non_killers) == 2
        and direct_killer_clues >= 2
    )

    red_herring_count = sum(
        1 for clue in clues if clue.get("kind") == "redHerring"
    )

    used_object_ids = {
        clue.get("roomObjectID")
        for clue in clues
        if clue.get("roomObjectID")
    }

    return {
        "run_id": f"{object_set}-{seed}",
        "object_set": object_set,
        "seed": seed,
        "status": "success",
        "http_status": 200,
        "title": case.get("title", ""),
        "victim": case.get("victim", {}).get("name", ""),
        "killer": killer_name,
        "motive": motive,
        "method": solution.get("method", ""),
        "time_of_death": solution.get("timeOfDeath", ""),
        "clue_titles": " | ".join(clue_titles),
        "clue_pattern": normalise_titles(clue_titles),
        "direct_killer_clue_count": direct_killer_clues,
        "corroborated_non_killer_count": len(corroborated_non_killers),
        "red_herring_count": red_herring_count,
        "objects_used_in_clues": len(used_object_ids),
        "malformed_motive": malformed_motive,
        "likely_obvious_killer": likely_obvious_killer,
        "duplicate_title_count": 0,
        "duplicate_clue_pattern_count": 0,
        "automatic_flags": "",
        "manual_notes": "",
        "would_ship": "",
        "source_file": str(path),
    }


def build_error_row(path: Path, error: dict[str, Any]) -> dict[str, Any]:
    object_set, seed = parse_run_name(path)

    return {
        "run_id": f"{object_set}-{seed}",
        "object_set": object_set,
        "seed": seed,
        "status": "error",
        "http_status": error.get("status_code", ""),
        "title": "",
        "victim": "",
        "killer": "",
        "motive": "",
        "method": "",
        "time_of_death": "",
        "clue_titles": "",
        "clue_pattern": "",
        "direct_killer_clue_count": "",
        "corroborated_non_killer_count": "",
        "red_herring_count": "",
        "objects_used_in_clues": "",
        "malformed_motive": "",
        "likely_obvious_killer": "",
        "duplicate_title_count": "",
        "duplicate_clue_pattern_count": "",
        "automatic_flags": f"Generation failed: {error.get('response', '')}",
        "manual_notes": "",
        "would_ship": "No",
        "source_file": str(path),
    }


def main() -> None:
    rows: list[dict[str, Any]] = []

    for path in sorted(INPUT_DIR.glob("*.json")):
        data = load_json(path)

        if path.name.endswith("-error.json"):
            rows.append(build_error_row(path, data))
        else:
            rows.append(build_success_row(path, data))

    successful_rows = [
        row for row in rows if row["status"] == "success"
    ]

    title_counts = Counter(
        row["title"] for row in successful_rows if row["title"]
    )

    clue_pattern_counts = Counter(
        row["clue_pattern"]
        for row in successful_rows
        if row["clue_pattern"]
    )

    for row in successful_rows:
        row["duplicate_title_count"] = title_counts[row["title"]]
        row["duplicate_clue_pattern_count"] = clue_pattern_counts[
            row["clue_pattern"]
        ]

        flags: list[str] = []

        if row["malformed_motive"]:
            flags.append("Malformed motive")

        if row["likely_obvious_killer"]:
            flags.append("Likely obvious killer")

        if row["duplicate_title_count"] > 1:
            flags.append("Repeated title")

        if row["duplicate_clue_pattern_count"] > 1:
            flags.append("Repeated clue structure")

        if row["objects_used_in_clues"] < 4:
            flags.append("Not all room objects used")

        row["automatic_flags"] = " | ".join(flags)

    fieldnames = [
        "run_id",
        "object_set",
        "seed",
        "status",
        "http_status",
        "title",
        "victim",
        "killer",
        "motive",
        "method",
        "time_of_death",
        "clue_titles",
        "clue_pattern",
        "direct_killer_clue_count",
        "corroborated_non_killer_count",
        "red_herring_count",
        "objects_used_in_clues",
        "malformed_motive",
        "likely_obvious_killer",
        "duplicate_title_count",
        "duplicate_clue_pattern_count",
        "automatic_flags",
        "manual_notes",
        "would_ship",
        "source_file",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created {OUTPUT_FILE} with {len(rows)} rows.")


if __name__ == "__main__":
    main()