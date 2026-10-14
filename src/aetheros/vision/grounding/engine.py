"""
The grounding engine: natural-language target -> ranked visual match.

The engine adds no perception of its own. It reuses an injected
:class:`~aetheros.vision.controller.VisionService` for OCR and object detection
and works on an already-captured image, so it is pure with respect to the
screen and fully testable with recorded blocks/detections. Screen capture and
mouse/keyboard actuation stay in the tool layer.

Flow: parse the request -> read the screen's text and objects -> build scored
candidates -> apply any spatial relation and ordinal -> rank, detect ambiguity
-> map the winner's score onto a confidence band and a safe-to-act gate ->
return a :class:`GroundingResult` carrying the bbox, the click point and the
evidence for the choice.
"""

from __future__ import annotations

from ..controller import VisionService
from ..image import Image
from ..models.detection import Detection
from ..models.text import TextBlock
from . import spatial
from .models import (
    BAND_HIGH,
    BAND_LOW,
    BAND_MEDIUM,
    GroundingCandidate,
    GroundingResult,
    GroundingTarget,
)
from .parser import parse_target
from .scoring import text_match_score, type_match_score

# Minimum OCR confidence for a text block to be considered a candidate at all.
# Blocks the reader is itself unsure of are dropped rather than scaled, keeping
# the match score a clean function of the text alone.
_OCR_FLOOR = 0.30

# A tie between the top two candidates within this score margin is treated as
# ambiguous: the winner's confidence is penalised so an ambiguous match does not
# reach the auto-act band.
_AMBIGUITY_MARGIN = 0.05
_AMBIGUITY_PENALTY = 0.6

# "near" radius as a fraction of the image diagonal when a target is anchored
# with "near"/"next to"/"beside".
_NEAR_FRACTION = 0.15


class GroundingEngine:
    """Resolve a target phrase to an on-screen element using existing vision."""

    def __init__(
        self,
        vision: VisionService,
        *,
        high_threshold: float,
        medium_threshold: float,
    ) -> None:
        self._vision = vision
        self._high = high_threshold
        self._medium = medium_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ground(self, query: str, image: Image) -> GroundingResult:
        target = parse_target(query)

        if not self._vision.has_ocr and not self._vision.has_detector:
            return GroundingResult.failure(
                query=query,
                reason=(
                    "No perception available: neither OCR nor object detection "
                    "is configured, so nothing on screen can be grounded."
                ),
                target=target.to_dict(),
            )

        blocks = await self._read_text(image)
        detections = await self._detect(image)

        candidates = self._build_candidates(target, blocks, detections)

        # Nothing matched by label: if the request selects by position or by a
        # spatial relation, fall back to ranking every element geometrically.
        if not candidates and (
            target.ordinal or (target.relation and target.anchor)
        ):
            candidates = self._positional_candidates(blocks, detections)

        if not candidates:
            return GroundingResult.failure(
                query=query,
                reason=self._no_candidate_reason(target, blocks, detections),
                candidates_considered=len(blocks) + len(detections),
                target=target.to_dict(),
            )

        if target.relation and target.anchor:
            candidates, anchor_err = self._apply_relation(
                target, candidates, blocks
            )
            if anchor_err is not None:
                return GroundingResult.failure(
                    query=query,
                    reason=anchor_err,
                    candidates_considered=len(blocks) + len(detections),
                    target=target.to_dict(),
                )

        if not candidates:
            return GroundingResult.failure(
                query=query,
                reason=(
                    f"No element satisfied the spatial relation "
                    f"'{target.relation}' to '{target.anchor}'."
                ),
                candidates_considered=len(blocks) + len(detections),
                target=target.to_dict(),
            )

        return self._select(target, query, candidates, blocks, detections)

    # ------------------------------------------------------------------
    # Perception (reused from VisionService)
    # ------------------------------------------------------------------

    async def _read_text(self, image: Image) -> list[TextBlock]:
        if not self._vision.has_ocr:
            return []
        try:
            return await self._vision.read_text(image)
        except Exception:
            # An OCR failure is not fatal on its own: detection may still
            # ground the target, and if nothing does the caller gets a
            # structured "not found" rather than an exception.
            return []

    async def _detect(self, image: Image) -> list[Detection]:
        if not self._vision.has_detector:
            return []
        try:
            return await self._vision.detect_objects(image)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Candidate construction
    # ------------------------------------------------------------------

    def _build_candidates(
        self,
        target: GroundingTarget,
        blocks: list[TextBlock],
        detections: list[Detection],
    ) -> list[GroundingCandidate]:
        """Score readable elements against the target by text and by type.

        OCR blocks are scored by text; detections by element type (they carry a
        class label, not readable text). Only elements that actually match are
        returned -- positional selection (ordinal / spatial relation) falls back
        to :meth:`_positional_candidates` when this finds nothing to match on.
        """

        candidates: list[GroundingCandidate] = []

        for block in blocks:
            if block.confidence < _OCR_FLOOR:
                continue
            score = text_match_score(target.text, block.text)
            if score <= 0.0:
                continue
            candidates.append(
                GroundingCandidate(
                    text=block.text,
                    left=block.left,
                    top=block.top,
                    right=block.right,
                    bottom=block.bottom,
                    score=score,
                    source="ocr",
                    element_type=None,
                    reason=(
                        f"OCR text '{block.text}' scored {score:.2f} "
                        f"against '{target.text}'."
                    ),
                )
            )

        for det in detections:
            type_score = type_match_score(target.element_type, det.label)
            text_score = text_match_score(target.text, det.label)
            score = max(type_score, text_score)
            if score <= 0.0:
                continue
            candidates.append(
                GroundingCandidate(
                    text=det.label,
                    left=det.left,
                    top=det.top,
                    right=det.right,
                    bottom=det.bottom,
                    score=score,
                    source="detection",
                    element_type=det.label,
                    reason=(
                        f"Detected '{det.label}' "
                        f"(conf {det.confidence:.2f}) scored {score:.2f}."
                    ),
                )
            )

        return candidates

    def _positional_candidates(
        self,
        blocks: list[TextBlock],
        detections: list[Detection],
    ) -> list[GroundingCandidate]:
        """Every element as a neutral candidate, for ordinal/spatial selection.

        Used only when the target names no text that matches (e.g. "the leftmost
        result", "the button below Login"): position or relation, not a label,
        decides the winner, so each element starts at a middling score that
        keeps the result out of the auto-act band unless the geometry is a
        strong, unambiguous fit.
        """

        candidates: list[GroundingCandidate] = []
        for block in blocks:
            if block.confidence < _OCR_FLOOR:
                continue
            candidates.append(
                GroundingCandidate(
                    text=block.text,
                    left=block.left,
                    top=block.top,
                    right=block.right,
                    bottom=block.bottom,
                    score=0.5,
                    source="ocr",
                    element_type=None,
                    reason=f"Positional candidate '{block.text}'.",
                )
            )
        for det in detections:
            candidates.append(
                GroundingCandidate(
                    text=det.label,
                    left=det.left,
                    top=det.top,
                    right=det.right,
                    bottom=det.bottom,
                    score=0.5,
                    source="detection",
                    element_type=det.label,
                    reason=f"Positional candidate '{det.label}'.",
                )
            )
        return candidates


    # ------------------------------------------------------------------
    # Spatial relation
    # ------------------------------------------------------------------

    def _apply_relation(
        self,
        target: GroundingTarget,
        candidates: list[GroundingCandidate],
        blocks: list[TextBlock],
    ) -> tuple[list[GroundingCandidate], str | None]:
        """Keep only candidates standing in the requested relation to the anchor.

        The anchor is found by text among the OCR blocks. If it is not on the
        screen the whole request fails with that reason -- grounding "the button
        below Login" is meaningless if "Login" is not visible.
        """

        anchor_block = self._best_anchor(target.anchor or "", blocks)
        if anchor_block is None:
            return [], (
                f"Spatial anchor '{target.anchor}' was not found on screen, "
                f"so the relation '{target.relation}' cannot be resolved."
            )

        near_radius = 4.0 * max(anchor_block.width, anchor_block.height, 1)
        anchor_bbox = anchor_block.bbox

        kept: list[GroundingCandidate] = []
        for cand in candidates:
            if cand.bbox == anchor_bbox:
                continue  # the anchor is not its own relative target
            if spatial.satisfies(
                target.relation or "",
                cand,
                anchor_block,
                near_radius=near_radius,
            ):
                # Closer to the anchor is a better spatial match; fold proximity
                # into the score without letting it dominate the text score.
                dist = spatial.distance(cand, anchor_block)
                proximity = max(0.0, 1.0 - dist / (near_radius * 2 or 1.0))
                cand.score = 0.7 * cand.score + 0.3 * proximity
                cand.reason += (
                    f" Satisfies '{target.relation}' to anchor "
                    f"'{anchor_block.text}' (dist {dist:.0f}px)."
                )
                kept.append(cand)

        return kept, None

    def _best_anchor(
        self, anchor: str, blocks: list[TextBlock]
    ) -> TextBlock | None:
        best: TextBlock | None = None
        best_score = 0.0
        for block in blocks:
            score = text_match_score(anchor, block.text)
            if score >= 0.7 and (
                score > best_score
                or (score == best_score and best is not None and block.area > best.area)
            ):
                best, best_score = block, score
        return best

    # ------------------------------------------------------------------
    # Selection, ambiguity and confidence
    # ------------------------------------------------------------------

    def _select(
        self,
        target: GroundingTarget,
        query: str,
        candidates: list[GroundingCandidate],
        blocks: list[TextBlock],
        detections: list[Detection],
    ) -> GroundingResult:
        considered = len(blocks) + len(detections)

        if target.ordinal:
            winner = self._ordinal_pick(target.ordinal, candidates)
            confidence = winner.score
            band = self._band(confidence)
            reason = (
                f"Selected the {target.ordinal} of {len(candidates)} "
                f"matching element(s): '{winner.text}'."
            )
            return GroundingResult.from_candidate(
                winner,
                query=query,
                confidence=confidence,
                band=band,
                safe_to_act=band == BAND_HIGH,
                reason=reason,
                candidates_considered=considered,
                target=target.to_dict(),
            )

        ordered = sorted(candidates, key=lambda c: c.score, reverse=True)
        winner = ordered[0]
        confidence = winner.score
        ambiguous = (
            len(ordered) > 1
            and winner.score > 0.0
            and (winner.score - ordered[1].score) <= _AMBIGUITY_MARGIN
        )

        reason = winner.reason
        if ambiguous:
            confidence *= _AMBIGUITY_PENALTY
            reason += (
                f" Ambiguous: '{ordered[1].text}' scored nearly as high, so "
                f"confidence was reduced and auto-action withheld."
            )

        band = self._band(confidence)
        safe = band == BAND_HIGH and not ambiguous

        return GroundingResult.from_candidate(
            winner,
            query=query,
            confidence=confidence,
            band=band,
            safe_to_act=safe,
            reason=reason,
            candidates_considered=considered,
            target=target.to_dict(),
        )

    def _ordinal_pick(
        self, ordinal: str, candidates: list[GroundingCandidate]
    ) -> GroundingCandidate:
        if ordinal == "leftmost":
            return min(candidates, key=lambda c: c.center[0])
        if ordinal == "rightmost":
            return max(candidates, key=lambda c: c.center[0])
        if ordinal == "topmost":
            return min(candidates, key=lambda c: c.center[1])
        if ordinal == "bottommost":
            return max(candidates, key=lambda c: c.center[1])
        if ordinal == "first":
            return min(candidates, key=lambda c: (c.top, c.left))
        if ordinal == "last":
            return max(candidates, key=lambda c: (c.top, c.left))
        return max(candidates, key=lambda c: c.score)

    def _band(self, confidence: float) -> str:
        if confidence >= self._high:
            return BAND_HIGH
        if confidence >= self._medium:
            return BAND_MEDIUM
        return BAND_LOW

    def _no_candidate_reason(
        self,
        target: GroundingTarget,
        blocks: list[TextBlock],
        detections: list[Detection],
    ) -> str:
        if not blocks and not detections:
            return (
                "Nothing was read from the screen: OCR returned no text and no "
                "objects were detected."
            )
        parts = [f"No element matched '{target.text or target.raw}'."]
        if blocks:
            parts.append(f"{len(blocks)} text block(s) were read but none matched.")
        if detections:
            parts.append(
                f"{len(detections)} object(s) were detected but none matched "
                f"the requested type '{target.element_type}'."
            )
        return " ".join(parts)


__all__ = ["GroundingEngine"]




