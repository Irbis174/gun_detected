from pathlib import Path

import cv2

from backend.config import DETECTION_FRAMES_DIR


class DetectionFrameStore:
    def __init__(self, root_dir: Path = DETECTION_FRAMES_DIR):
        self.root_dir = root_dir

    def save(
        self,
        frame,
        *,
        test_run_id: int,
        detection_id: int,
        frame_index: int,
        bbox: tuple[int, int, int, int],
        label: str,
        score: float,
    ) -> str | None:
        run_dir = self.root_dir / f'test_run_{test_run_id}'

        output_path = run_dir / (
            f'detection_{detection_id}_frame_{frame_index:06d}.jpg'
        )
        annotated_frame = self._annotate_frame(
            frame=frame,
            bbox=bbox,
            label=label,
            score=score,
        )

        ok, encoded = cv2.imencode(
            '.jpg',
            annotated_frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 92],
        )
        if not ok:
            return None

        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(encoded.tobytes())
        except OSError:
            return None

        return str(output_path)

    @staticmethod
    def _annotate_frame(
        *,
        frame,
        bbox: tuple[int, int, int, int],
        label: str,
        score: float,
    ):
        annotated_frame = frame.copy()
        height, width = annotated_frame.shape[:2]
        x, y, box_width, box_height = bbox

        left = max(0, min(int(x), width - 1))
        top = max(0, min(int(y), height - 1))
        right = max(left + 1, min(int(x + box_width), width - 1))
        bottom = max(top + 1, min(int(y + box_height), height - 1))

        color = (0, 0, 255)
        cv2.rectangle(annotated_frame, (left, top), (right, bottom), color, 2)

        caption = f'{label} {score:.2f}'
        text_origin = (left, max(18, top - 8))
        cv2.putText(
            annotated_frame,
            caption,
            text_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )
        return annotated_frame


detection_frame_store = DetectionFrameStore()
