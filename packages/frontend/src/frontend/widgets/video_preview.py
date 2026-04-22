from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from frontend.i18n import translate_detection_label


class VideoPreviewLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame: QImage | None = None
        self._overlay: dict | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            """
            QLabel {
                background: #101317;
                border: 1px solid #2c3440;
                border-radius: 12px;
                color: #aab4c3;
                padding: 0px;
            }
            """
        )
        self.setText('Превью недоступно')

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        ratio = self._frame_aspect_ratio()
        if ratio <= 0:
            return max(220, width // 2)
        return max(220, int(width / ratio))

    def sizeHint(self) -> QSize:
        return QSize(520, self.heightForWidth(520))

    def set_frame(self, frame: QImage) -> None:
        self._frame = frame
        self.updateGeometry()
        self.update()

    def clear_frame(self) -> None:
        self._frame = None
        self.updateGeometry()
        self.update()

    def set_overlay(self, overlay: dict | None) -> None:
        self._overlay = overlay
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        panel_rect = QRectF(self.rect())
        self._draw_background(painter, panel_rect)

        if self._frame is None:
            painter.setPen(QColor('#aab4c3'))
            painter.drawText(
                panel_rect.adjusted(16.0, 16.0, -16.0, -16.0),
                Qt.AlignmentFlag.AlignCenter,
                self.text(),
            )
            painter.end()
            return

        target_rect = panel_rect.adjusted(8.0, 8.0, -8.0, -8.0)
        pixmap = QPixmap.fromImage(self._frame)
        source_rect = self._source_crop_rect(target_rect=target_rect)

        clip_path = QPainterPath()
        clip_path.addRoundedRect(target_rect, 10.0, 10.0)
        painter.setClipPath(clip_path)
        painter.drawPixmap(target_rect, pixmap, source_rect)
        painter.setClipping(False)

        self._draw_overlay(
            painter=painter,
            target_rect=target_rect,
            source_rect=source_rect,
        )
        painter.end()

    def _draw_background(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor('#101317'))

    def _draw_overlay(
        self,
        *,
        painter: QPainter,
        target_rect: QRectF,
        source_rect: QRectF,
    ) -> None:
        overlay = self._overlay or {}
        bbox = overlay.get('bbox')
        if not bbox or len(bbox) != 4:
            return

        try:
            bbox_x, bbox_y, bbox_w, bbox_h = [float(value) for value in bbox]
        except (TypeError, ValueError):
            return

        if source_rect.width() <= 0 or source_rect.height() <= 0:
            return

        scale_x = target_rect.width() / source_rect.width()
        scale_y = target_rect.height() / source_rect.height()

        rect = QRectF(
            target_rect.left() + (bbox_x - source_rect.left()) * scale_x,
            target_rect.top() + (bbox_y - source_rect.top()) * scale_y,
            bbox_w * scale_x,
            bbox_h * scale_y,
        )

        if rect.width() <= 2 or rect.height() <= 2:
            return

        painter.setPen(QPen(QColor('#ff5d5d'), 3.0))
        painter.drawRoundedRect(rect, 4.0, 4.0)

        label = translate_detection_label(str(overlay.get('label') or ''))
        score = overlay.get('score')
        score_text = ''
        if isinstance(score, (float, int)):
            score_text = f' {float(score):.2f}'
        badge_text = (label + score_text).strip()
        if not badge_text:
            return

        metrics = QFontMetrics(painter.font())
        badge_width = metrics.horizontalAdvance(badge_text) + 16
        badge_height = metrics.height() + 8
        badge_top = rect.top() - badge_height - 6
        if badge_top < target_rect.top():
            badge_top = rect.top() + 6

        badge_rect = QRectF(
            max(target_rect.left(), rect.left()),
            badge_top,
            min(badge_width, target_rect.width() - 8),
            badge_height,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(12, 15, 18, 220))
        painter.drawRoundedRect(badge_rect, 6.0, 6.0)
        painter.setPen(QColor('#f4f7fb'))
        painter.drawText(
            badge_rect.adjusted(8.0, 0.0, -8.0, 0.0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            badge_text,
        )

    def _frame_aspect_ratio(self) -> float:
        if self._frame is None or self._frame.height() <= 0:
            return 16.0 / 9.0
        return self._frame.width() / self._frame.height()

    def _source_crop_rect(self, *, target_rect: QRectF) -> QRectF:
        if self._frame is None or self._frame.width() <= 0 or self._frame.height() <= 0:
            return QRectF()

        frame_width = float(self._frame.width())
        frame_height = float(self._frame.height())
        target_ratio = target_rect.width() / max(1.0, target_rect.height())
        frame_ratio = frame_width / frame_height

        if frame_ratio > target_ratio:
            crop_width = frame_height * target_ratio
            crop_x = (frame_width - crop_width) / 2.0
            return QRectF(crop_x, 0.0, crop_width, frame_height)

        crop_height = frame_width / target_ratio
        crop_y = (frame_height - crop_height) / 2.0
        return QRectF(0.0, crop_y, frame_width, crop_height)
