import json
import zipfile
from datetime import datetime, timedelta, timezone

from app.llm.base import BaseLLMClient
from app.models.document import Document, DocumentVersion
from app.models.misc import ApplicationInventory
from app.models.project import Project
from app.models.user import User
from app.services import generation_service
from app.services.application_inventory_service import get_discovered_base_url, get_inventory_summary
from tests.test_pipeline_mocked_llm import SAMPLE_DOCUMENT_TEXT

ANALYSIS_RESPONSE = {
    "transaction_name": "Cash Deposit",
    "summary": "Teller deposits cash.",
    "actors": ["Teller"],
    "preconditions": [],
    "fields": [{"name": "Deposit Amount", "type": "currency", "required": True, "validation_rules": "> 0"}],
    "functional_requirements": ["System shall validate deposit amount"],
    "business_rules": [],
    "postconditions": [],
    "negative_scenarios": [],
}

TEST_PLAN_RESPONSE = {
    "transaction_name": "Cash Deposit",
    "test_scenarios": [
        {
            "id": "TC_001", "title": "Successful cash deposit", "type": "positive", "priority": "High",
            "preconditions": [], "steps": ["Enter deposit amount", "Submit"],
            "expected_result": "Deposit posted", "related_business_rules": [],
        }
    ],
}

TEST_DATA_RESPONSE = {"rows": [{"row_type": "positive", "values": {"Deposit Amount": "5000"}}]}

FEATURE_RESPONSE = {
    "features": [{
        "feature_filename": "cash-deposit.feature",
        "feature_title": "Feature: Cash Deposit",
        "gherkin_content": (
            "Feature: Cash Deposit\n\n"
            "  Scenario: Successful cash deposit\n"
            "    Given the teller is on the cash deposit screen\n"
            "    Then the deposit should be posted successfully\n"
        ),
    }]
}

# The page object response deliberately uses the REAL id from the inventory below
# ("realDepositAmount"), proving the agent's prompt successfully carried that real data through -
# a mocked LLM can't invent that exact id on its own, it has to have been told it.
PAGE_OBJECT_RESPONSE = {
    "page_objects": [{
        "class_name": "CashDepositPage", "filename": "CashDepositPage.java",
        "java_content": (
            "package com.nbc.automation.pages;\n\n"
            "import org.openqa.selenium.WebElement;\n"
            "import org.openqa.selenium.support.FindBy;\n"
            "import org.openqa.selenium.support.How;\n"
            "import org.openqa.selenium.WebDriver;\n"
            "import com.nbc.automation.core.BasePage;\n\n"
            "public class CashDepositPage extends BasePage {\n"
            "    @FindBy(how = How.ID, using = \"realDepositAmount\")\n"
            "    private WebElement depositAmountField;\n\n"
            "    public CashDepositPage(WebDriver driver) {\n"
            "        super(driver);\n"
            "    }\n"
            "}\n"
        ),
    }]
}

STEP_DEFINITION_RESPONSE = {
    "step_definitions": [{
        "class_name": "CashDepositSteps", "filename": "CashDepositSteps.java",
        "java_content": (
            "package com.nbc.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n"
            "import com.nbc.automation.pages.CashDepositPage;\n"
            "import com.nbc.automation.core.BaseTest;\n\n"
            "public class CashDepositSteps extends BaseTest {\n"
            "    @Given(\"the teller is on the cash deposit screen\")\n"
            "    public void theTellerIsOnTheCashDepositScreen() {\n"
            "        new CashDepositPage(driver);\n"
            "    }\n"
            "}\n"
        ),
    }]
}


class RecordingFakeLLMClient(BaseLLMClient):
    """Like the other tests' FakeLLMClient, but also records every user_prompt it was called
    with, so the test can assert the real inventory data actually made it into the prompt."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0
        self.user_prompts: list[str] = []

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        self.user_prompts.append(user_prompt)
        response = self._responses[self.calls]
        self.calls += 1
        return response


def test_application_inventory_grounds_locators_and_base_url(db_session, monkeypatch):
    user = db_session.query(User).filter(User.username == "testadmin").first()
    project = Project(name="Inventory-Grounded Pilot", description="test", created_by=user.id)
    db_session.add(project)
    db_session.commit()

    # Simulate Application Explorer having already run against the real app for this project -
    # Login discovered first, same as a real crawl starting at the login screen.
    now = datetime.now(timezone.utc)
    db_session.add(ApplicationInventory(
        project_id=project.id, screen_name="Login", url="https://real-nbc-app.internal:6006/login",
        fields_json=json.dumps([{"tag": "input", "type": "password", "name": "password", "id": "pwd", "label": "Password"}]),
        discovered_at=now,
    ))
    db_session.add(ApplicationInventory(
        project_id=project.id, screen_name="Cash Deposit", url="https://real-nbc-app.internal:6006/deposit",
        fields_json=json.dumps([
            {"tag": "input", "type": "number", "name": "amount", "id": "realDepositAmount", "label": "Deposit Amount"},
        ]),
        discovered_at=now + timedelta(seconds=5),
    ))
    db_session.commit()

    discovered_base_url = get_discovered_base_url(db_session, project.id)
    assert discovered_base_url == "https://real-nbc-app.internal:6006"

    inventory_summary = get_inventory_summary(db_session, project.id)
    assert len(inventory_summary) == 2
    assert any(f["id"] == "realDepositAmount" for screen in inventory_summary for f in screen["fields"])

    document = Document(project_id=project.id, doc_type="requirement", filename="cash_deposit.docx", file_path="x", uploaded_by=user.id)
    db_session.add(document)
    db_session.commit()
    db_session.add(DocumentVersion(
        document_id=document.id, version_number=1, file_path="x",
        extracted_text=SAMPLE_DOCUMENT_TEXT, uploaded_by=user.id,
    ))
    db_session.commit()

    fake_client = RecordingFakeLLMClient([
        ANALYSIS_RESPONSE, TEST_PLAN_RESPONSE, TEST_DATA_RESPONSE, FEATURE_RESPONSE,
        PAGE_OBJECT_RESPONSE, STEP_DEFINITION_RESPONSE,
    ])
    monkeypatch.setattr(generation_service, "get_llm_client", lambda db=None: fake_client)

    generation = generation_service.run_generation(db_session, project.id, document.id, "selenium_java", user.id)
    assert generation.status == "success", generation.change_summary

    # The Page Object Generator's prompt (5th call: analysis, test_plan, test_data, features, page_objects)
    # must have included the real discovered field data.
    page_object_prompt = fake_client.user_prompts[4]
    assert "realDepositAmount" in page_object_prompt
    assert "real-nbc-app.internal" in page_object_prompt

    # And the rendered config.properties must use the discovered base_url, not the generic placeholder.
    with zipfile.ZipFile(generation.zip_path) as zf:
        config_content = zf.read("src/test/resources/config.properties").decode()
    assert "base.url=https://real-nbc-app.internal:6006" in config_content
    assert "nbc-uat.example-bank.internal" not in config_content

    # And the generated Page Object actually used the real id, exactly as instructed.
    with zipfile.ZipFile(generation.zip_path) as zf:
        page_object_content = zf.read("src/test/java/com/nbc/automation/pages/CashDepositPage.java").decode()
    assert "realDepositAmount" in page_object_content
