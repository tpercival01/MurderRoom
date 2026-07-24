from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from app.models import (
    ClueDraft,
    ClueKind,
    CoreTruthDraft,
    DeductionDraft,
    DeductionKind,
    Difficulty,
    EvidenceBoardDraft,
    NarrativeSeedAI,
    SuspectCastDraft,
    SuspectDraft,
    SuspectKey,
    SuspectReferenceKey,
)


class ObjectFamily(str, Enum):
    sharp = "sharp"
    flexible = "flexible"
    soft = "soft"
    fabric = "fabric"
    container = "container"
    light = "light"
    seat = "seat"
    readable = "readable"
    furniture = "furniture"
    electronic = "electronic"
    reflective = "reflective"
    decorative = "decorative"
    rigid = "rigid"
    general = "general"


class MethodStyle(str, Enum):
    sharp = "sharp"
    ligature = "ligature"
    smothering = "smothering"
    poisoning = "poisoning"
    blunt = "blunt"


@dataclass(frozen=True)
class ObjectProfile:
    index: int
    name: str
    tokens: frozenset[str]
    families: frozenset[ObjectFamily]
    method_score: int
    timeline_score: int
    identity_score: int


@dataclass(frozen=True)
class Signature:
    item: str
    trace_plural: str
    damage: str
    pattern: str


@dataclass(frozen=True)
class IdentityMarker:
    item: str
    fragment: str
    damage: str
    colour: str


@dataclass(frozen=True)
class CasePlan:
    room_objects: tuple[str, str, str, str]
    profiles: tuple[ObjectProfile, ObjectProfile, ObjectProfile, ObjectProfile]
    killer_key: SuspectKey
    method_index: int
    timeline_index: int
    identity_index: int
    red_herring_index: int
    method_style: MethodStyle
    signature: Signature
    identity_marker: IdentityMarker
    departure_time: str
    claimed_exit_time: str
    discovery_time: str
    seed: int
    difficulty: Difficulty


_WORD_RE = re.compile(r"[a-z0-9]+")

_FAMILY_TERMS: dict[ObjectFamily, set[str]] = {
    ObjectFamily.sharp: {
        "knife", "knives", "scissors", "blade", "razor", "sword",
        "dagger", "opener", "screwdriver", "skewer", "needle",
    },
    ObjectFamily.flexible: {
        "cord", "cable", "rope", "belt", "scarf", "tie", "wire",
        "chain", "curtain", "drape", "lace", "lead", "strap",
    },
    ObjectFamily.soft: {
        "pillow", "cushion", "blanket", "duvet", "towel",
    },
    ObjectFamily.fabric: {
        "pillow", "cushion", "blanket", "duvet", "cloth", "towel",
        "curtain", "drape", "coat", "jacket", "fabric", "rug", "carpet",
    },
    ObjectFamily.container: {
        "cup", "mug", "glass", "bottle", "decanter", "jar", "bowl",
        "plate", "vase", "kettle", "can", "jug", "flask", "goblet",
    },
    ObjectFamily.light: {
        "lamp", "light", "lantern", "candle", "candlestick", "torch",
    },
    ObjectFamily.seat: {
        "chair", "armchair", "stool", "sofa", "couch", "bench",
    },
    ObjectFamily.readable: {
        "book", "notebook", "magazine", "newspaper", "letter", "paper",
        "folder", "file", "journal", "diary", "document",
    },
    ObjectFamily.furniture: {
        "chair", "armchair", "stool", "sofa", "couch", "bench", "table",
        "desk", "shelf", "cabinet", "drawer", "wardrobe", "bed",
        "nightstand", "stand", "dresser", "bookcase",
    },
    ObjectFamily.electronic: {
        "phone", "telephone", "mobile", "laptop", "tablet", "television",
        "tv", "radio", "computer", "monitor", "speaker", "remote", "clock",
    },
    ObjectFamily.reflective: {
        "mirror", "window", "glass", "screen",
    },
    ObjectFamily.decorative: {
        "vase", "statue", "figurine", "trophy", "ornament", "frame",
        "picture", "painting", "plant", "pot", "clock", "candlestick",
    },
    ObjectFamily.rigid: {
        "lamp", "lantern", "vase", "statue", "figurine", "trophy",
        "clock", "book", "bottle", "decanter", "mug", "cup", "chair",
        "stool", "ashtray", "ornament", "paperweight", "remote", "phone",
        "tablet", "laptop", "monitor", "kettle", "pan", "pot", "jar", "bowl",
        "plate", "frame", "mirror", "rock", "brick", "hammer", "wrench",
        "tool", "candlestick", "desk", "table",
    },
}

_METHOD_BONUS = {
    "knife": 60,
    "scissors": 55,
    "blade": 60,
    "candlestick": 45,
    "hammer": 55,
    "lamp": 60,
    "statue": 40,
    "trophy": 38,
    "vase": 35,
    "bottle": 32,
    "chair": 28,
    "clock": 26,
    "monitor": 34,
    "book": 18,
    "cup": 5,
    "mug": 5,
    "pillow": 35,
    "cushion": 30,
    "cord": 42,
    "rope": 45,
    "belt": 38,
}

_SIGNATURES = (
    Signature(
        item="burgundy herringbone scarf",
        trace_plural="burgundy wool fibres",
        damage="a fresh pulled thread",
        pattern="the same distinctive burgundy-and-black herringbone weave",
    ),
    Signature(
        item="teal tweed jacket cuff",
        trace_plural="teal-and-cream tweed fibres",
        damage="a newly frayed cuff edge",
        pattern="the same unusual teal-and-cream check",
    ),
    Signature(
        item="copper silk pocket square",
        trace_plural="fine copper-coloured silk threads",
        damage="a fresh narrow tear",
        pattern="the same alternating copper and navy stripe",
    ),
    Signature(
        item="violet knitted glove",
        trace_plural="violet knitted fibres",
        damage="a fresh snag across one fingertip",
        pattern="the same violet yarn with a single silver strand",
    ),
)

_IDENTITY_MARKERS = (
    IdentityMarker(
        item="cobalt enamel coat button",
        fragment="a crescent-shaped cobalt enamel chip",
        damage="a fresh crescent missing from its rim",
        colour="cobalt blue",
    ),
    IdentityMarker(
        item="green lacquered watch clasp",
        fragment="a narrow flake of green lacquer",
        damage="a fresh bare strip along one edge",
        colour="dark green",
    ),
    IdentityMarker(
        item="amber resin bag clasp",
        fragment="a triangular amber resin fragment",
        damage="a fresh triangular notch",
        colour="amber",
    ),
    IdentityMarker(
        item="black-and-gold fountain-pen cap",
        fragment="a curved black lacquer chip edged in gold",
        damage="a fresh curved gap in the lacquer",
        colour="black and gold",
    ),
)


_GENERIC_TITLES = {
    "mansion murder",
    "the mansion murder",
    "murder mystery",
    "the murder",
    "a murder mystery",
    "death in the mansion",
    "the mysterious death",
    "the mysterious murder",
    "the mysterious office death",
    "the office murder",
    "the office death",
}

_GENERIC_NAMES = {
    "john smith",
    "jane doe",
    "emily wilson",
    "james davis",
    "sarah taylor",
    "richard langley",
}

class PlanError(ValueError):
    pass


def _tokens(name: str) -> frozenset[str]:
    values = set(_WORD_RE.findall(name.casefold()))
    expanded = set(values)
    for value in values:
        if len(value) > 3 and value.endswith("s"):
            expanded.add(value[:-1])
    return frozenset(expanded)


def _families(tokens: frozenset[str]) -> frozenset[ObjectFamily]:
    matched = {
        family
        for family, terms in _FAMILY_TERMS.items()
        if tokens & terms
    }
    if not matched:
        matched.add(ObjectFamily.general)
    return frozenset(matched)


def profile_room_objects(room_objects: list[str]) -> tuple[ObjectProfile, ...]:
    profiles: list[ObjectProfile] = []
    for index, name in enumerate(room_objects):
        tokens = _tokens(name)
        families = _families(tokens)

        method_score = 5
        if ObjectFamily.sharp in families:
            method_score += 100
        if ObjectFamily.flexible in families:
            method_score += 82
        if ObjectFamily.soft in families:
            method_score += 65
        if ObjectFamily.rigid in families:
            method_score += 50
        if ObjectFamily.container in families:
            method_score += 5
        method_score += max((_METHOD_BONUS.get(token, 0) for token in tokens), default=0)

        timeline_score = 20
        if ObjectFamily.seat in families:
            timeline_score += 100
        if ObjectFamily.furniture in families:
            timeline_score += 70
        if ObjectFamily.readable in families:
            timeline_score += 65
        if ObjectFamily.container in families:
            timeline_score += 55
        if ObjectFamily.light in families:
            timeline_score += 45

        identity_score = 20
        if ObjectFamily.readable in families:
            identity_score += 100
        if ObjectFamily.seat in families:
            identity_score += 85
        if ObjectFamily.furniture in families:
            identity_score += 70
        if ObjectFamily.light in families:
            identity_score += 60
        if ObjectFamily.container in families:
            identity_score += 50

        profiles.append(
            ObjectProfile(
                index=index,
                name=name,
                tokens=tokens,
                families=families,
                method_score=method_score,
                timeline_score=timeline_score,
                identity_score=identity_score,
            )
        )
    return tuple(profiles)


def _pick_ranked(
    candidates: list[ObjectProfile],
    score_name: str,
    rng: random.Random,
) -> ObjectProfile:
    ranked = sorted(
        candidates,
        key=lambda item: (getattr(item, score_name), rng.random()),
        reverse=True,
    )
    return ranked[0]


def _method_style(profile: ObjectProfile) -> MethodStyle:
    if ObjectFamily.sharp in profile.families:
        return MethodStyle.sharp
    if ObjectFamily.flexible in profile.families:
        return MethodStyle.ligature
    if ObjectFamily.soft in profile.families:
        return MethodStyle.smothering
    if ObjectFamily.container in profile.families:
        return MethodStyle.poisoning
    if ObjectFamily.rigid in profile.families:
        return MethodStyle.blunt
    return MethodStyle.blunt



def _format_time(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{value.strftime('%M')} {value.strftime('%p').lower()}"


def build_case_plan(
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
    seed: int | None = None,
) -> CasePlan:
    if len(room_objects) != 4 or len({value.casefold() for value in room_objects}) != 4:
        raise PlanError("The proof planner requires four distinct room objects.")

    actual_seed = seed if seed is not None else random.SystemRandom().randrange(0, 2_147_483_647)
    rng = random.Random(actual_seed)
    profiles = profile_room_objects(room_objects)

    method = _pick_ranked(list(profiles), "method_score", rng)
    remaining = [profile for profile in profiles if profile.index != method.index]
    timeline = _pick_ranked(remaining, "timeline_score", rng)
    remaining = [profile for profile in remaining if profile.index != timeline.index]
    identity = _pick_ranked(remaining, "identity_score", rng)
    red_herring = next(profile for profile in profiles if profile.index not in {
        method.index,
        timeline.index,
        identity.index,
    })

    killer_key = list(SuspectKey)[actual_seed % len(SuspectKey)]
    signature = _SIGNATURES[(actual_seed // 3) % len(_SIGNATURES)]
    identity_marker = _IDENTITY_MARKERS[(actual_seed // 7) % len(_IDENTITY_MARKERS)]

    base_hour = 19 + ((actual_seed // 11) % 3)
    base_minute = (10, 20, 35, 45)[(actual_seed // 17) % 4]
    departure_dt = datetime(2026, 1, 1, base_hour, base_minute)
    discovery_dt = departure_dt + timedelta(minutes=10)
    claimed_exit_dt = departure_dt - timedelta(minutes=5)

    return CasePlan(
        room_objects=tuple(room_objects),
        profiles=profiles,  # type: ignore[arg-type]
        killer_key=killer_key,
        method_index=method.index,
        timeline_index=timeline.index,
        identity_index=identity.index,
        red_herring_index=red_herring.index,
        method_style=_method_style(method),
        signature=signature,
        identity_marker=identity_marker,
        departure_time=_format_time(departure_dt),
        claimed_exit_time=_format_time(claimed_exit_dt),
        discovery_time=_format_time(discovery_dt),
        seed=actual_seed,
        difficulty=difficulty,
    )


def narrative_seed_issues(seed: NarrativeSeedAI) -> list[str]:
    issues: list[str] = []
    all_text = " ".join(
        [
            seed.title,
            seed.setting_description,
            seed.victim_name,
            seed.victim_role,
            seed.motive_detail,
            *(
                part
                for suspect in seed.suspects
                for part in (suspect.name, suspect.relationship_to_victim)
            ),
        ]
    ).casefold()

    title_text = seed.title.casefold().strip()
    if (
        title_text in _GENERIC_TITLES
        or re.fullmatch(
            r"(?:the\s+)?mysterious\s+(?:office\s+)?(?:death|murder)",
            title_text,
        )
    ):
        issues.append("The title is generic. Create a specific, evocative title.")
    if "suspect_" in all_text or "suspect 1" in all_text or "suspect 2" in all_text:
        issues.append("Narrative text may not expose internal suspect keys.")
    if any(term in seed.title.casefold() for term in ("murder mystery", "mansion murder")):
        issues.append("The title may not use placeholder murder-title phrasing.")
    generated_names = {seed.victim_name.casefold().strip()} | {
        suspect.name.casefold().strip() for suspect in seed.suspects
    }
    generic_names = generated_names & _GENERIC_NAMES
    if generic_names:
        issues.append(
            "Replace generic example names: " + ", ".join(sorted(generic_names))
        )

    motive_text = seed.motive_detail.casefold().strip()
    if motive_text.startswith("because "):
        issues.append(
            "motive_detail must not begin with 'because'; Python adds that word."
        )
    if re.search(r"\bbecause[.!?]?$", motive_text):
        issues.append(
            "motive_detail must not end with 'because'."
        )
    if re.search(r"\bbecause\b", motive_text):
        issues.append(
            "motive_detail must not contain 'because'; Python adds that word."
        )
    if any(
        phrase in motive_text
        for phrase in (
            "deep dark secret",
            "deep, dark secret",
            "dispute over a project",
            "professional rivalry",
            "future prospects",
        )
    ):
        issues.append(
            "The motive is generic. Name the concrete secret, loss, betrayal or threat."
        )
    return issues


def _profile(plan: CasePlan, index: int) -> ObjectProfile:
    return plan.profiles[index]


def _display(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split())


def _object_phrase(name: str) -> str:
    lowered = name.casefold().strip()
    if lowered.startswith(("the ", "a ", "an ")):
        return name
    return f"the {name}"


def _location_phrase(profile: ObjectProfile) -> str:
    families = profile.families
    if ObjectFamily.readable in families:
        return f"between the cover and first page of {_object_phrase(profile.name)}"
    if ObjectFamily.fabric in families:
        return f"among the fibres along one edge of {_object_phrase(profile.name)}"
    if ObjectFamily.seat in families:
        return f"inside a narrow seam beneath {_object_phrase(profile.name)}"
    if ObjectFamily.container in families:
        return f"inside the handle joint of {_object_phrase(profile.name)}"
    if ObjectFamily.light in families:
        return f"beneath the base of {_object_phrase(profile.name)}"
    if ObjectFamily.furniture in families:
        return f"inside a narrow joint of {_object_phrase(profile.name)}"
    return f"in a narrow edge of {_object_phrase(profile.name)}"


def _contact_location(profile: ObjectProfile) -> str:
    families = profile.families
    if ObjectFamily.sharp in families:
        return f"around the handle of {_object_phrase(profile.name)}"
    if ObjectFamily.flexible in families:
        return f"inside a newly stretched section of {_object_phrase(profile.name)}"
    if ObjectFamily.soft in families:
        return f"inside a fresh torn seam on {_object_phrase(profile.name)}"
    if ObjectFamily.container in families:
        return f"around the handle and rim of {_object_phrase(profile.name)}"
    if ObjectFamily.light in families:
        return f"inside a fresh split beneath the base of {_object_phrase(profile.name)}"
    return f"inside a fresh split on {_object_phrase(profile.name)}"


def _method_content(
    plan: CasePlan,
    victim_name: str,
) -> tuple[str, str, str]:
    profile = _profile(plan, plan.method_index)
    obj = _object_phrase(profile.name)

    if plan.method_style == MethodStyle.sharp:
        method = f"{victim_name} was fatally stabbed with {obj}."
        detail = (
            f"A fresh line of blood runs along one edge of {obj}, and its point "
            f"has a new bend. {victim_name} has a narrow wound consistent with "
            "that edge."
        )
        title = f"The Edge of {_display(profile.name)}"
    elif plan.method_style == MethodStyle.ligature:
        method = f"{victim_name} was strangled with {obj}."
        detail = (
            f"One section of {obj} is freshly stretched and carries a narrow "
            f"blood transfer. {victim_name} has a pressure mark of the same width."
        )
        title = f"The Stretched {_display(profile.name)}"
    elif plan.method_style == MethodStyle.smothering:
        method = f"{victim_name} was smothered with {obj}."
        detail = (
            f"{_object_phrase(profile.name).capitalize()} has fresh compression "
            f"creases and a small blood transfer. Matching fibres are visible "
            f"around {victim_name}'s mouth."
        )
        title = f"Compression on {_display(profile.name)}"
    elif plan.method_style == MethodStyle.poisoning:
        method = f"A fatal crushed dose was dissolved in {obj} before {victim_name} drank."
        detail = (
            f"Undissolved blue granules cling below the liquid line inside {obj}. "
            f"The same blue residue is visible at {victim_name}'s lips and in the "
            "remaining drink."
        )
        title = f"Granules in {_display(profile.name)}"
    else:
        method = f"{victim_name} was killed by a heavy blow from {obj}."
        if ObjectFamily.light in profile.families or ObjectFamily.electronic in profile.families:
            impact_mark = "a new impact dent"
            title = f"The Dented {_display(profile.name)}"
        elif ObjectFamily.decorative in profile.families or ObjectFamily.container in profile.families:
            impact_mark = "a fresh impact chip along its heaviest edge"
            title = f"The Chipped {_display(profile.name)}"
        elif ObjectFamily.readable in profile.families:
            impact_mark = "a newly crushed corner and split spine"
            title = f"The Crushed {_display(profile.name)}"
        elif ObjectFamily.seat in profile.families or ObjectFamily.furniture in profile.families:
            impact_mark = "a fresh splintered edge"
            title = f"The Splintered {_display(profile.name)}"
        else:
            impact_mark = "a fresh impact mark"
            title = f"Impact on {_display(profile.name)}"
        detail = (
            f"A fresh blood smear and {impact_mark} mark {obj}. "
            f"{victim_name} has a fresh blunt wound to the head."
        )

    return method, title, detail


def _timeline_action(profile: ObjectProfile) -> tuple[str, str, str, str]:
    obj = _object_phrase(profile.name)
    display = _display(profile.name)
    families = profile.families

    if ObjectFamily.seat in families:
        return (
            f"move {obj} clear of the doorway",
            f"moved {obj} clear of the doorway",
            f"a fresh floor scrape made by {obj}",
            f"Movement of {display}",
        )
    if ObjectFamily.readable in families:
        return (
            f"return {obj} squarely to its place",
            f"returned {obj} squarely to its place",
            f"a clean rectangular outline left when {obj} was moved",
            f"Position of {display}",
        )
    if ObjectFamily.container in families:
        return (
            f"set {obj} down on the side table",
            f"set {obj} down on the side table",
            f"the fresh circular ring beneath {obj}",
            f"Ring beneath {display}",
        )
    if ObjectFamily.light in families:
        return (
            f"shift {obj} to light the victim's papers",
            f"shifted {obj} to light the victim's papers",
            f"the clean outline beneath the shifted base of {obj}",
            f"Outline beneath {display}",
        )
    if ObjectFamily.furniture in families:
        return (
            f"move {obj} away from the centre of the room",
            f"moved {obj} away from the centre of the room",
            f"a fresh floor line made by {obj}",
            f"Movement of {display}",
        )
    return (
        f"move {obj} aside",
        f"moved {obj} aside",
        f"the fresh contact mark left by {obj}",
        f"Position of {display}",
    )


def _red_herring_detail(profile: ObjectProfile) -> tuple[str, str]:
    """Return a suspicious observation without telling the player its resolution."""
    obj = _object_phrase(profile.name)
    display = _display(profile.name)
    families = profile.families

    if ObjectFamily.container in families:
        return (
            f"Crack in {display}",
            f"A crack runs across {obj}. A continuous yellowed glue line is visible "
            "deep inside the break.",
        )
    if ObjectFamily.fabric in families:
        return (
            f"Tear in {display}",
            f"A torn section marks {obj}. Faded, evenly spaced stitching is visible "
            "beneath the folded edge.",
        )
    if ObjectFamily.light in families or ObjectFamily.electronic in families:
        return (
            f"Frayed Lead on {display}",
            f"A section of the power lead attached to {obj} is frayed beneath two "
            "overlapping layers of yellowed repair tape.",
        )
    if ObjectFamily.readable in families:
        return (
            f"Torn Corner of {display}",
            f"A corner of {obj} is torn. An old printed stamp continues across both "
            "sides of the tear.",
        )
    if ObjectFamily.seat in families or ObjectFamily.furniture in families:
        return (
            f"Gouge on {display}",
            f"A dark gouge marks {obj}. Hardened varnish covers the groove as well "
            "as the surrounding surface.",
        )
    if ObjectFamily.reflective in families:
        return (
            f"Crack in {display}",
            f"A star-shaped crack marks {obj}. Clear repair film is visible beneath "
            "the surface finish.",
        )
    return (
        f"Mark on {display}",
        f"A dark mark crosses {obj}. The same intact factory finish continues over "
        "the marked area.",
    )


def _ref(key: SuspectKey) -> SuspectReferenceKey:
    return SuspectReferenceKey(key.value)


def compile_case(
    narrative: NarrativeSeedAI,
    plan: CasePlan,
) -> tuple[CoreTruthDraft, SuspectCastDraft, EvidenceBoardDraft]:
    issues = narrative_seed_issues(narrative)
    if issues:
        raise PlanError("; ".join(issues))

    suspects_by_key = {suspect.key: suspect for suspect in narrative.suspects}
    killer = suspects_by_key[plan.killer_key]
    innocent_keys = [key for key in SuspectKey if key != plan.killer_key]
    innocent_1 = suspects_by_key[innocent_keys[0]]
    innocent_2 = suspects_by_key[innocent_keys[1]]

    method_profile = _profile(plan, plan.method_index)
    timeline_profile = _profile(plan, plan.timeline_index)
    identity_profile = _profile(plan, plan.identity_index)
    red_profile = _profile(plan, plan.red_herring_index)

    method, method_title, method_detail = _method_content(plan, narrative.victim_name)
    timeline_action_base, timeline_action_past, timeline_trace, timeline_title = _timeline_action(timeline_profile)
    if plan.method_style == MethodStyle.poisoning:
        attack_trace = "a narrow blue droplet from the spilled poisoned drink"
        attack_trace_short = "blue drink residue"
    else:
        attack_trace = "a narrow blood droplet from the attack"
        attack_trace_short = "blood"

    killer_denial = (
        f"I left at {plan.claimed_exit_time}. I never touched "
        f"{_object_phrase(method_profile.name)} and did not go near "
        f"{_object_phrase(identity_profile.name)}."
    )
    killer_alibi = (
        f"I had already left the room by {plan.claimed_exit_time} and did not return."
    )

    innocent_1_statement = (
        f"At {plan.departure_time}, {innocent_2.name} helped me {timeline_action_base}. "
        f"We left the room together immediately afterwards. {killer.name} and "
        f"{narrative.victim_name} were still inside."
    )
    innocent_2_statement = (
        f"At {plan.departure_time}, I helped {innocent_1.name} {timeline_action_base}. "
        f"We then left together and remained together until the body was found at "
        f"{plan.discovery_time}."
    )
    innocent_1_alibi = (
        f"{innocent_2.name} and I were together outside the room from "
        f"{plan.departure_time} until the discovery at {plan.discovery_time}."
    )
    innocent_2_alibi = (
        f"{innocent_1.name} and I were together outside the room from "
        f"{plan.departure_time} until the discovery at {plan.discovery_time}."
    )

    signature = plan.signature
    contradiction_detail = (
        f"{signature.trace_plural.capitalize()} are caught "
        f"{_contact_location(method_profile)}. {killer.name}'s "
        f"{signature.item} has {signature.damage}, exposing {signature.pattern}."
    )

    marker = plan.identity_marker
    identity_detail = (
        f"{marker.fragment.capitalize()} is lodged {_location_phrase(identity_profile)} "
        f"on top of {attack_trace}. The {marker.item} worn by {killer.name} has "
        f"{marker.damage}; the exposed edges visibly fit the fragment."
    )

    timeline_detail = (
        f"{timeline_trace.capitalize()} is crossed by {attack_trace} whose edge "
        f"remains unbroken. {innocent_1.name} and {innocent_2.name} both state that "
        f"they {timeline_action_past} at {plan.departure_time} before leaving together."
    )

    opportunity = (
        f"{killer.name} claimed to have left at {plan.claimed_exit_time}. The "
        f"timeline evidence places the attack after {innocent_1.name} and "
        f"{innocent_2.name} left together at {plan.departure_time}; the "
        f"{signature.trace_plural} on {_object_phrase(method_profile.name)} and "
        f"the {marker.colour} fragment recovered from {_object_phrase(identity_profile.name)} "
        f"place {killer.name} inside afterwards. {killer.name} therefore had the "
        f"only evidenced opportunity to be alone with {narrative.victim_name} and "
        f"reach {_object_phrase(method_profile.name)} during the murder window."
    )

    motive_clause = narrative.motive_detail.strip().rstrip(".")
    motive_clause = re.sub(
        r"^(?:because\s+)+",
        "",
        motive_clause,
        flags=re.IGNORECASE,
    )
    motive_clause = re.sub(
        r"\bthe killer's\b",
        f"{killer.name}'s",
        motive_clause,
        flags=re.IGNORECASE,
    )
    motive_clause = re.sub(
        r"\bthe killer\b",
        killer.name,
        motive_clause,
        flags=re.IGNORECASE,
    )
    motive = (
        f"{killer.name} killed {narrative.victim_name} because {motive_clause}."
    )
    time_of_death = (
        f"After {plan.departure_time} and before discovery at {plan.discovery_time}"
    )

    setting = narrative.setting_description.strip().rstrip(".")
    if setting.startswith("A "):
        setting = "a " + setting[2:]
    elif setting.startswith("An "):
        setting = "an " + setting[3:]
    elif setting.startswith("The "):
        setting = "the " + setting[4:]

    opening = (
        f"At {plan.discovery_time}, {narrative.victim_name}, "
        f"{narrative.victim_role}, was found dead in {setting}. Three people had "
        "been present during the final minutes, and each gave a different account. "
        "Nothing outside the room is needed to identify the killer."
    )

    core = CoreTruthDraft(
        title=narrative.title.strip(),
        opening_incident=opening,
        victim_name=narrative.victim_name.strip(),
        killer_key=plan.killer_key,
        motive=motive,
        method=method,
        method_evidence=method_detail,
        time_of_death=time_of_death,
        killer_denial=killer_denial,
        hidden_detail=contradiction_detail,
        killer_revealed_detail=(
            f"The visible damage to {killer.name}'s {signature.item} matches the "
            f"{signature.trace_plural} on {_object_phrase(method_profile.name)}."
        ),
        killer_alibi=killer_alibi,
        killer_alibi_flaw=(
            f"Two independent physical traces place {killer.name} in the room after "
            f"the claimed exit: {signature.trace_plural} on "
            f"{_object_phrase(method_profile.name)} and {marker.fragment} at "
            f"{_object_phrase(identity_profile.name)}."
        ),
        primary_room_object_index=plan.method_index,
        contradiction_room_object_index=plan.method_index,
    )

    suspect_drafts: list[SuspectDraft] = []
    for key in SuspectKey:
        source = suspects_by_key[key]
        if key == plan.killer_key:
            statement = killer_denial
            alibi = killer_alibi
            evidence_index = plan.method_index
            evidence_fact = contradiction_detail
        elif key == innocent_keys[0]:
            statement = innocent_1_statement
            alibi = innocent_1_alibi
            evidence_index = plan.timeline_index
            evidence_fact = timeline_detail
        else:
            statement = innocent_2_statement
            alibi = innocent_2_alibi
            evidence_index = plan.timeline_index
            evidence_fact = timeline_detail

        relationship = re.sub(
            r"^(?:his|her|their|the victim's)\s+",
            "",
            source.relationship_to_victim.strip(),
            flags=re.IGNORECASE,
        )
        suspect_drafts.append(
            SuspectDraft(
                key=key,
                name=source.name,
                relationship_to_victim=relationship,
                statement=statement,
                alibi_claim=alibi,
                alibi_room_object_index=evidence_index,
                alibi_evidence_fact=evidence_fact,
            )
        )

    cast = SuspectCastDraft(suspects=suspect_drafts)

    innocent_1_ref = _ref(innocent_keys[0])
    innocent_2_ref = _ref(innocent_keys[1])
    killer_ref = _ref(plan.killer_key)
    red_title, red_detail = _red_herring_detail(red_profile)

    board = EvidenceBoardDraft(
        opportunity=opportunity,
        clue_1=ClueDraft(
            title=method_title,
            detail=method_detail,
            room_object_index=plan.method_index,
            kind=ClueKind.evidence,
            deductions=[
                DeductionDraft(
                    kind=DeductionKind.establishes_method,
                    related_suspect_key=SuspectReferenceKey.none,
                )
            ],
        ),
        clue_2=ClueDraft(
            title=timeline_title,
            detail=timeline_detail,
            room_object_index=plan.timeline_index,
            kind=ClueKind.evidence,
            deductions=[
                DeductionDraft(
                    kind=DeductionKind.establishes_timeline,
                    related_suspect_key=SuspectReferenceKey.none,
                ),
                DeductionDraft(
                    kind=DeductionKind.corroborates_alibi,
                    related_suspect_key=innocent_1_ref,
                ),
                DeductionDraft(
                    kind=DeductionKind.corroborates_alibi,
                    related_suspect_key=innocent_2_ref,
                ),
            ],
        ),
        clue_3=ClueDraft(
            title=f"Fibres on {_display(method_profile.name)}",
            detail=contradiction_detail,
            room_object_index=plan.method_index,
            kind=ClueKind.evidence,
            deductions=[
                DeductionDraft(
                    kind=DeductionKind.contradicts_statement,
                    related_suspect_key=killer_ref,
                ),
                DeductionDraft(
                    kind=DeductionKind.establishes_opportunity,
                    related_suspect_key=killer_ref,
                ),
                DeductionDraft(
                    kind=DeductionKind.supports_suspect,
                    related_suspect_key=killer_ref,
                ),
            ],
        ),
        clue_4=ClueDraft(
            title=f"Fragment at {_display(identity_profile.name)}",
            detail=identity_detail,
            room_object_index=plan.identity_index,
            kind=ClueKind.evidence,
            deductions=[
                DeductionDraft(
                    kind=DeductionKind.supports_suspect,
                    related_suspect_key=killer_ref,
                )
            ],
        ),
        clue_5=ClueDraft(
            title=red_title,
            detail=red_detail,
            room_object_index=plan.red_herring_index,
            kind=ClueKind.red_herring,
            deductions=[],
        ),
    )

    return core, cast, board
