from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MergeReport(Base):
    """Populated by the Code Merge Agent (Phase 2+, Mode 2). Empty in Phase 1."""

    __tablename__ = "merge_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("generation_history.id"), nullable=True)
    conflicts_detected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duplicates_detected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WorkflowInventory(Base):
    """Populated by the Workflow Discovery Agent (Phase 3+). Empty in Phase 1."""

    __tablename__ = "workflow_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    workflow_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    steps_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApplicationInventory(Base):
    """Populated by the Application Explorer Agent. Consumed by PageObjectGeneratorAgent and the
    framework builders to ground generated locators / base.url in real, live-crawled data instead
    of AI guesses from the requirement document alone."""

    __tablename__ = "application_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    screen_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Report(Base):
    """Populated by the Reporting Agent once live execution exists (Phase 2+). Empty in Phase 1."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("executions.id"), nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    execution: Mapped["Execution"] = relationship(back_populates="report")


class SettingKV(Base):
    """Non-secret runtime settings (e.g. LLM model name, temperature) editable from the Settings page."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
