from backend.domain.time_detection import TemporaryDetection
from backend.domain.detection_event import DetectionEvent
from backend.domain.test_run import TestRun


class CandidateTracker:
    def __init__(self):
        self.candidate_dict: dict[int: TemporaryDetection] = {} #По test_run_id

    def comparison_bbox(self, temporary_detection: TemporaryDetection):
        x, y, w, h = temporary_detection.bbox
        test_run_id = temporary_detection.test_run_id 
        self.candidate_dict[test_run_id]
        bbox, hits = self.candidate_dict[test_run_id]
        CandidateTracker.add(temporary_detection)
        center = (x + w/2, y + h/2)
        candidate = self.candidate_dict[test_run_id]

    def add(self, temporary_detection: TemporaryDetection):
        pass
    
    def remove(self):
        pass