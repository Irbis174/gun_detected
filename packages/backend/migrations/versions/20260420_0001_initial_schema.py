"""initial schema

Revision ID: 20260420_0001
Revises:
Create Date: 2026-04-20 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '20260420_0001'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'input_sources',
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('connected', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('source_id'),
    )

    op.create_table(
        'test_runs',
        sa.Column('test_run_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_frames', sa.Integer(), nullable=False),
        sa.Column('detections_count', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['input_sources.source_id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('test_run_id'),
    )
    op.create_index('ix_test_runs_source_id', 'test_runs', ['source_id'])

    op.create_table(
        'detections',
        sa.Column('detection_id', sa.Integer(), nullable=False),
        sa.Column('test_run_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('frame_index', sa.Integer(), nullable=True),
        sa.Column('frame_ts', sa.Float(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('bbox_x', sa.Integer(), nullable=False),
        sa.Column('bbox_y', sa.Integer(), nullable=False),
        sa.Column('bbox_w', sa.Integer(), nullable=False),
        sa.Column('bbox_h', sa.Integer(), nullable=False),
        sa.Column('processing_ms', sa.Float(), nullable=False),
        sa.Column('frame_path', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['source_id'],
            ['input_sources.source_id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['test_run_id'],
            ['test_runs.test_run_id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('detection_id'),
    )
    op.create_index('ix_detections_source_id', 'detections', ['source_id'])
    op.create_index('ix_detections_test_run_id', 'detections', ['test_run_id'])

    op.create_table(
        'tracking_updates',
        sa.Column('update_id', sa.Integer(), nullable=False),
        sa.Column('test_run_id', sa.Integer(), nullable=False),
        sa.Column('detection_id', sa.Integer(), nullable=False),
        sa.Column('frame_index', sa.Integer(), nullable=False),
        sa.Column('frame_ts', sa.Float(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('bbox_x', sa.Integer(), nullable=False),
        sa.Column('bbox_y', sa.Integer(), nullable=False),
        sa.Column('bbox_w', sa.Integer(), nullable=False),
        sa.Column('bbox_h', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['detection_id'],
            ['detections.detection_id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['test_run_id'],
            ['test_runs.test_run_id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('update_id'),
    )
    op.create_index(
        'ix_tracking_updates_detection_id',
        'tracking_updates',
        ['detection_id'],
    )
    op.create_index(
        'ix_tracking_updates_test_run_id',
        'tracking_updates',
        ['test_run_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_tracking_updates_test_run_id', table_name='tracking_updates')
    op.drop_index('ix_tracking_updates_detection_id', table_name='tracking_updates')
    op.drop_table('tracking_updates')
    op.drop_index('ix_detections_test_run_id', table_name='detections')
    op.drop_index('ix_detections_source_id', table_name='detections')
    op.drop_table('detections')
    op.drop_index('ix_test_runs_source_id', table_name='test_runs')
    op.drop_table('test_runs')
    op.drop_table('input_sources')
