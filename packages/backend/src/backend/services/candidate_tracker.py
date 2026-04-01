from backend.domain.detection_event import DetectionEvent
from backend.domain.time_detection import DetectionCandidate, TemporaryDetection
from backend.repositories.detection_event_repository import detection_repo


class CandidateTracker:
    def __init__(self, confirm_hits: int = 3, max_gap: int = 5):
        self.confirm_hits = confirm_hits
        self.max_gap = max_gap
        self.candidate_dict: dict[int, list[DetectionCandidate]] = {}

    def comparison_bbox(
        self,
        bbox1: tuple[int, int, int, int],
        bbox2: tuple[int, int, int, int],
    ) -> bool:
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        center_1 = (x1 + w1 / 2, y1 + h1 / 2)
        center_2 = (x2 + w2 / 2, y2 + h2 / 2)

        dx = center_1[0] - center_2[0]
        dy = center_1[1] - center_2[1]

        distance = (dx**2 + dy**2) ** 0.5
        threshold = max(max(w1, h1), max(w2, h2)) * 0.4

        return distance < threshold

    def add(self, temporary_detection: TemporaryDetection) -> DetectionEvent | None:
        test_run_id = temporary_detection.test_run_id
        candidate_list = self.candidate_dict.setdefault(test_run_id, [])

        matched_candidate = None
        for candidate in candidate_list:
            if candidate.source_id != temporary_detection.source_id:
                continue

            if candidate.label != temporary_detection.label:
                continue

            if not self.comparison_bbox(candidate.bbox, temporary_detection.bbox):
                continue

            matched_candidate = candidate
            break

        if matched_candidate is None:
            candidate_list.append(
                DetectionCandidate(
                    test_run_id=temporary_detection.test_run_id,
                    source_id=temporary_detection.source_id,
                    label=temporary_detection.label,
                    bbox=temporary_detection.bbox,
                    first_seen_frame=temporary_detection.frame_index,
                    last_seen_frame=temporary_detection.frame_index,
                    first_seen_ts=temporary_detection.frame_ts,
                    last_seen_ts=temporary_detection.frame_ts,
                    hits=1,
                    best_score=temporary_detection.score,
                    last_processing_ms=temporary_detection.processing_ms,
                )
            )
            return None

        matched_candidate.bbox = temporary_detection.bbox
        matched_candidate.last_seen_frame = temporary_detection.frame_index
        matched_candidate.last_seen_ts = temporary_detection.frame_ts
        matched_candidate.hits += 1
        matched_candidate.best_score = max(
            matched_candidate.best_score,
            temporary_detection.score,
        )
        matched_candidate.last_processing_ms = temporary_detection.processing_ms

        if matched_candidate.confirmed:
            return None

        if matched_candidate.hits >= self.confirm_hits:
            matched_candidate.confirmed = True
            event = DetectionEvent(
                detection_id=0,
                test_run_id=temporary_detection.test_run_id,
                frame_ts=temporary_detection.frame_ts,
                label=temporary_detection.label,
                score=matched_candidate.best_score,
                bbox=temporary_detection.bbox,
                processing_ms=temporary_detection.processing_ms,
            )
            detection_repo.add(event)
            return event

        return None

    def remove(self, detection_candidate: DetectionCandidate) -> None:
        candidates = self.candidate_dict.get(detection_candidate.test_run_id)
        if candidates is None:
            return

        if detection_candidate in candidates:
            candidates.remove(detection_candidate)

        if not candidates:
            self.candidate_dict.pop(detection_candidate.test_run_id)

    def prune_stale_candidates(self, test_run_id: int, current_frame: int) -> None:
        candidates = self.candidate_dict.get(test_run_id)
        if not candidates:
            return

        for candidate in candidates.copy():
            if current_frame - candidate.last_seen_frame > self.max_gap:
                self.remove(candidate)
