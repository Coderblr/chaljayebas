from pathlib import Path

from app.models.document import Document, DocumentVersion
from app.models.project import Project
from app.models.user import User
from app.services import execution_service, generation_service
from tests.test_pipeline_mocked_llm import CANNED_RESPONSES, SAMPLE_DOCUMENT_TEXT, FakeLLMClient


def test_execution_pipeline_runs_real_mvn_test_against_generated_framework(db_session, monkeypatch):
    """Generates a real Selenium framework with a mocked LLM (same fixture as
    test_pipeline_mocked_llm.py, whose CashDepositSteps fully implements every step), then runs
    the Execution Agent for real - actually shelling out to `mvn test`, launching a real
    ChromeDriver, and parsing the real Cucumber JSON report - to prove the execution/reporting
    wiring works end to end, not just the generation side."""

    user = db_session.query(User).filter(User.username == "testadmin").first()
    project = Project(name="Execution Pilot", description="execution test", created_by=user.id)
    db_session.add(project)
    db_session.commit()

    document = Document(project_id=project.id, doc_type="requirement", filename="cash_deposit.docx", file_path="x", uploaded_by=user.id)
    db_session.add(document)
    db_session.commit()
    db_session.add(DocumentVersion(
        document_id=document.id, version_number=1, file_path="x",
        extracted_text=SAMPLE_DOCUMENT_TEXT, uploaded_by=user.id,
    ))
    db_session.commit()

    generation_fake_client = FakeLLMClient(CANNED_RESPONSES)
    monkeypatch.setattr(generation_service, "get_llm_client", lambda db=None: generation_fake_client)

    generation = generation_service.run_generation(db_session, project.id, document.id, "selenium_java", user.id)
    assert generation.status == "success", generation.change_summary

    # Hooks.java now actually navigates to base.url on every scenario (previously it was rendered
    # into config.properties but never read by anything - a real gap, now fixed). The generated
    # default is an illustrative placeholder host that doesn't resolve, which would correctly fail
    # navigation - swap it for a URL that always resolves so this test still proves the full,
    # now-more-complete chain (driver launch -> real navigation -> step execution) passes green.
    output_dir = Path(generation.zip_path).with_suffix("")
    config_path = output_dir / "src/test/resources/config.properties"
    config_path.write_text(
        config_path.read_text().replace("base.url=https://nbc-uat.example-bank.internal", "base.url=about:blank"),
        encoding="utf-8",
    )

    # No failures are expected (the fixture's steps are fully implemented), so the
    # FailureAnalysisAgent/SelfHealingAgent should never need to call the LLM in this run -
    # an empty response list proves that if it were called unexpectedly, the test would fail loudly.
    execution_fake_client = FakeLLMClient([])
    monkeypatch.setattr(execution_service, "get_llm_client", lambda db=None: execution_fake_client)

    execution = execution_service.run_execution(db_session, generation.id, user.id)

    assert execution.status == "success", [r.error_message for r in execution.results]
    assert len(execution.results) == 1
    assert execution.results[0].status == "passed"
    assert execution.report is not None
    assert execution.report.report_type == "selenium_java"
    assert execution_fake_client.calls == 0
