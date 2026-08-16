"""Add server-owned registered-action jobs.
Revision ID: 0054_automation_jobs
Revises: 0053_core_ephemeral_state
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
revision="0054_automation_jobs"; down_revision="0053_core_ephemeral_state"; branch_labels=None; depends_on=None
ID=sa.String(length=64);STR=sa.String(length=191)
def upgrade():
    if "automation_jobs" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("automation_jobs",
      sa.Column("id",ID,primary_key=True),sa.Column("campaign_id",ID,sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),
      sa.Column("package_id",ID,nullable=False),sa.Column("action_id",STR,nullable=False),sa.Column("action_version",sa.Integer(),nullable=False),
      sa.Column("input_json",sa.Text(),nullable=False),sa.Column("principal_user_id",ID,sa.ForeignKey("users.id",ondelete="SET NULL"),nullable=True),
      sa.Column("run_at_utc",sa.Integer(),nullable=False),sa.Column("idempotency_key",STR,nullable=False),sa.Column("status",STR,nullable=False),
      sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"),sa.Column("lease_owner",STR,nullable=True),sa.Column("lease_expires_at",sa.Integer(),nullable=True),
      sa.Column("error_code",STR,nullable=True),sa.Column("origin_execution_id",ID,nullable=True),sa.Column("origin_job_id",ID,nullable=True),
      sa.Column("causal_depth",sa.Integer(),nullable=False,server_default="0"),sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False),
      sa.CheckConstraint("status IN ('pending','running','succeeded','failed','rejected','cancelled')",name=op.f("ck_automation_jobs_status")),
      sa.UniqueConstraint("campaign_id","package_id","idempotency_key"))
    op.create_index("idx_automation_jobs_due","automation_jobs",["status","run_at_utc","lease_expires_at"])
def downgrade():
    if "automation_jobs" in sa.inspect(op.get_bind()).get_table_names(): op.drop_table("automation_jobs")
