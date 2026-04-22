import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class InputSourceModel(Base):
    __tablename__ = 'input_sources'

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    test_runs: Mapped[list['TestRunModel']] = relationship(
        back_populates='source_rel',
        cascade='all, delete-orphan',
    )


class TestRunModel(Base):
    __tablename__ = 'test_runs'

    test_run_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey('input_sources.source_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_frames: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detections_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_rel: Mapped[InputSourceModel] = relationship(back_populates='test_runs')
    detections: Mapped[list['DetectionModel']] = relationship(
        back_populates='test_run',
        cascade='all, delete-orphan',
    )
    tracking_updates: Mapped[list['TrackingUpdateModel']] = relationship(
        back_populates='test_run',
        cascade='all, delete-orphan',
    )


class DetectionModel(Base):
    __tablename__ = 'detections'

    detection_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_run_id: Mapped[int] = mapped_column(
        ForeignKey('test_runs.test_run_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey('input_sources.source_id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_ts: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_w: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_h: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_ms: Mapped[float] = mapped_column(Float, nullable=False)
    frame_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    test_run: Mapped[TestRunModel] = relationship(back_populates='detections')
    tracking_updates: Mapped[list['TrackingUpdateModel']] = relationship(
        back_populates='detection',
        cascade='all, delete-orphan',
    )


class TrackingUpdateModel(Base):
    __tablename__ = 'tracking_updates'

    update_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_run_id: Mapped[int] = mapped_column(
        ForeignKey('test_runs.test_run_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    detection_id: Mapped[int] = mapped_column(
        ForeignKey('detections.detection_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    frame_ts: Mapped[float] = mapped_column(Float, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_w: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_h: Mapped[int] = mapped_column(Integer, nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    test_run: Mapped[TestRunModel] = relationship(back_populates='tracking_updates')
    detection: Mapped[DetectionModel] = relationship(back_populates='tracking_updates')
