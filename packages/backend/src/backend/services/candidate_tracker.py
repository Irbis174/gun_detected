from backend.domain.time_detection import TemporaryDetection, DetectionCandidate
from backend.repositories.detection_event_repository import detection_repo
from backend.domain.detection_event import DetectionEvent

class CandidateTracker:
    def __init__(self):
        self.candidate_dict: dict[int, list[DetectionCandidate]] = {}  # По test_run_id

    def comparison_bbox(self, bbox1: tuple[int, int, int, int], bbox2: tuple[int, int, int, int]):
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        center_1 = (x1 + w1 / 2, y1 + h1 / 2)
        center_2 = (x2 + w2 / 2, y2 + h2 / 2)

        dx = center_1[0] - center_2[0]
        dy = center_1[1] - center_2[1]

        distance = (dx**2 + dy**2) ** 0.5

        threshold = max(max(w1, h1), max((w2, h2))) * 0.4

        return distance < threshold


    def add(self, temporary_detection: TemporaryDetection):
        test_run_id = temporary_detection.test_run_id

        candidate_list = self.candidate_dict.setdefault(test_run_id, [])

        matched_candidate = None
        for candidate in candidate_list:
            if candidate.source_id != temporary_detection.source_id:
                continue

            if not self.comparison_bbox(candidate.bbox, temporary_detection.bbox):
                continue

            matched_candidate = candidate
            break

        if matched_candidate is None:
            new_candidate = DetectionCandidate(
                test_run_id=temporary_detection.test_run_id,
                source_id=temporary_detection.source_id,
                bbox=temporary_detection.bbox,
                first_seen_frame=temporary_detection.frame_index,
                last_seen_frame=temporary_detection.frame_index,
                hits=1,
                confirmed=False,
            )
            candidate_list.append(new_candidate)
            return None

        matched_candidate.bbox = temporary_detection.bbox
        matched_candidate.last_seen_frame = temporary_detection.frame_index
        matched_candidate.hits += 1

        if matched_candidate.hits >= 3:
            matched_candidate.confirmed = True
            candidate_list.remove(matched_candidate)
            return matched_candidate

        return None

    def remove(self, detection_candidate: DetectionCandidate):
        if detection_candidate.test_run_id not in self.candidate_dict:
            return
        candidates = self.candidate_dict[detection_candidate.test_run_id]
        candidates.remove(detection_candidate)
        if candidates == []:
            self.candidate_dict.pop(detection_candidate.test_run_id)
