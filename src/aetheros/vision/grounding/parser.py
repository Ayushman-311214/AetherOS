"""
Parse a natural-language target into a :class:`GroundingTarget`.

Deterministic, keyword-driven, and dependency-free so it is trivially testable:
the same phrase always yields the same structured intent. It recognises a small
vocabulary that covers the spec's cases -- an element kind ("button", "icon",
"link", "field"), a spatial relation to an anchor ("below Login", "left of
Search"), and an ordinal ("leftmost", "first"). Anything it does not recognise
falls through as plain match text, which the engine still grounds by OCR.

No LLM and no chain-of-thought here: this is lexical normalisation, not
reasoning. The engine does the perception and ranking.
"""

from __future__ import annotations

import re

from .models import GroundingTarget

# Element-kind words the UI vocabulary uses. Mapped to a canonical type so
# "textbox"/"input"/"field" all read as "field". Order does not matter; the
# longest matching phrase wins during extraction.
_ELEMENT_TYPES: dict[str, str] = {
    "button": "button",
    "btn": "button",
    "icon": "icon",
    "link": "link",
    "hyperlink": "link",
    "field": "field",
    "input": "field",
    "textbox": "field",
    "text box": "field",
    "text field": "field",
    "checkbox": "checkbox",
    "check box": "checkbox",
    "radio": "radio",
    "menu": "menu",
    "tab": "tab",
    "label": "label",
    "image": "image",
    "toggle": "toggle",
    "dropdown": "dropdown",
    "drop down": "dropdown",
}

# Spatial relations -> canonical relation. Multi-word phrases are checked before
# single words so "to the left of" is not shadowed by a bare "left".
_RELATIONS: list[tuple[str, str]] = [
    ("to the left of", "left_of"),
    ("to the right of", "right_of"),
    ("left of", "left_of"),
    ("right of", "right_of"),
    ("next to", "near"),
    ("beside", "near"),
    ("near", "near"),
    ("inside", "inside"),
    ("within", "inside"),
    ("below", "below"),
    ("beneath", "below"),
    ("under", "below"),
    ("underneath", "below"),
    ("above", "above"),
    ("over", "above"),
    ("on top of", "above"),
]

# Ordinal / positional selectors -> canonical ordinal.
_ORDINALS: dict[str, str] = {
    "leftmost": "leftmost",
    "left-most": "leftmost",
    "rightmost": "rightmost",
    "right-most": "rightmost",
    "topmost": "topmost",
    "top-most": "topmost",
    "bottommost": "bottommost",
    "bottom-most": "bottommost",
    "first": "first",
    "last": "last",
}

# Filler words stripped from the residual match text.
_FILLERS = {"the", "a", "an", "please", "click", "on", "press", "select"}


def _clean(text: str) -> str:
    """Strip filler words and surrounding punctuation from residual text."""

    tokens = re.findall(r"[\w'-]+", text)
    kept = [t for t in tokens if t.lower() not in _FILLERS]
    return " ".join(kept).strip()


def _find_relation(low: str) -> tuple[str, str] | None:
    """Return (phrase, canonical_relation) for the first relation present."""

    for phrase, canonical in _RELATIONS:
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return phrase, canonical
    return None


def _find_element_type(low: str) -> str | None:
    """Return the canonical element type mentioned, longest phrase first."""

    for phrase in sorted(_ELEMENT_TYPES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return _ELEMENT_TYPES[phrase]
    return None


def _find_ordinal(low: str) -> str | None:
    for word, canonical in _ORDINALS.items():
        if re.search(rf"\b{re.escape(word)}\b", low):
            return canonical
    return None


def parse_target(query: str) -> GroundingTarget:
    """Parse ``query`` into a structured :class:`GroundingTarget`.

    The residual text (what remains after pulling out the element kind, the
    relation + anchor, and any ordinal) becomes the label the engine matches
    against OCR. Any recognised piece is optional: a bare "Search" grounds by
    text alone, "leftmost result" grounds by ordinal, and "button below Login"
    grounds a button spatially relative to the "Login" anchor.
    """

    raw = (query or "").strip()
    low = raw.lower()

    element_type = _find_element_type(low)
    ordinal = _find_ordinal(low)

    relation: str | None = None
    anchor: str | None = None

    found = _find_relation(low)
    if found is not None:
        phrase, relation = found
        # Everything after the relation phrase is the anchor; everything before
        # it is the thing we are locating.
        head, _, tail = low.partition(phrase)
        anchor = _clean(tail) or None
        low = head  # residual match text comes from the head only

    # Remove the element-type and ordinal words from the residual so the match
    # text is just the label, e.g. "search" from "the search button".
    residual = low
    if element_type is not None:
        for phrase, canonical in _ELEMENT_TYPES.items():
            if canonical == element_type:
                residual = re.sub(
                    rf"\b{re.escape(phrase)}\b", " ", residual
                )
    for word in _ORDINALS:
        residual = re.sub(rf"\b{re.escape(word)}\b", " ", residual)

    text = _clean(residual)

    return GroundingTarget(
        raw=raw,
        text=text,
        element_type=element_type,
        relation=relation,
        anchor=anchor,
        ordinal=ordinal,
    )


__all__ = ["parse_target"]
