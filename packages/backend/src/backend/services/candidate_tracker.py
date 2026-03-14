from backend.domain.time_detection import TemporaryDetection, DetectionCandidate
from backend.domain.detection_event import DetectionEvent
from backend.domain.test_run import TestRun


class CandidateTracker:
    def __init__(self):
        self.candidate_dict: dict[int: list[DetectionCandidate]] = {} #По test_run_id

    def comparison_bbox(self, temporary_detection: TemporaryDetection):
        x, y, w, h = temporary_detection.bbox
        test_run_id = temporary_detection.test_run_id 
        self.candidate_dict[test_run_id]
        bbox, hits = self.candidate_dict[test_run_id].bbox, self.candidate_dict[test_run_id].hits
        center = (x + w/2, y + h/2)

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
        pass