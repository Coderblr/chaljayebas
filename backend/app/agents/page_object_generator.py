import json

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.generators.playwright.constants import PAGES_DIR
from app.generators.selenium.constants import PAGES_PACKAGE
from app.llm.base import LLMError
from app.llm.prompts.page_object_generator import SYSTEM_PROMPT as JAVA_SYSTEM_PROMPT
from app.llm.prompts.page_object_generator import build_user_prompt as build_java_user_prompt
from app.llm.prompts.page_object_generator_ts import SYSTEM_PROMPT as TS_SYSTEM_PROMPT
from app.llm.prompts.page_object_generator_ts import build_user_prompt as build_ts_user_prompt
from app.services.application_inventory_service import get_inventory_summary
from app.services.generated_file_store import save_generated_file


class PageObjectGeneratorAgent(BaseAgent):
    name = "PageObjectGeneratorAgent"

    def run(self, context: AgentContext) -> AgentResult:
        analysis = context.state.get("RequirementAnalyzerAgent", {}).get("analysis")
        features = context.state.get("FeatureGeneratorAgent", {}).get("features", [])
        if not analysis or not features:
            return AgentResult(success=False, error="Missing requirement analysis or feature files")

        features_text = "\n\n".join(f["content"] for f in features)
        framework_type = context.state.get("framework_type", "selenium_java")
        inventory = get_inventory_summary(context.db, context.project_id)
        inventory_json = json.dumps(inventory)

        if framework_type == "playwright_ts":
            return self._run_playwright(context, analysis, features_text, inventory_json, bool(inventory))
        return self._run_selenium(context, analysis, features_text, inventory_json, bool(inventory))

    def _run_selenium(
        self, context: AgentContext, analysis: dict, features_text: str, inventory_json: str, has_real_data: bool
    ) -> AgentResult:
        detected_package = context.state.get("FrameworkAnalyzerAgent", {}).get("inventory", {}).get(
            "detected_pages_package"
        )
        package_name = detected_package or PAGES_PACKAGE

        try:
            result = context.llm.complete_json(
                JAVA_SYSTEM_PROMPT,
                build_java_user_prompt(json.dumps(analysis), features_text, package_name, inventory_json),
            )
        except LLMError as exc:
            return AgentResult(success=False, error=str(exc))

        page_objects = result.get("page_objects", [])
        if not page_objects:
            return AgentResult(success=False, error="LLM returned no page objects")

        package_path = package_name.replace(".", "/")
        saved = []
        for po in page_objects:
            filename = po["filename"]
            content = po["java_content"]
            save_generated_file(
                context.db, context.generation_id, context.project_id, "page_object",
                filename, f"src/test/java/{package_path}/{filename}", content,
            )
            saved.append({"class_name": po["class_name"], "filename": filename, "content": content})

        source = "real Application Explorer data" if has_real_data else "AI-guessed (no Application Explorer data yet)"
        return AgentResult(
            success=True,
            output={"page_objects": saved},
            output_summary=f"Generated {len(saved)} page object(s) using {source}: "
            f"{', '.join(p['class_name'] for p in saved)}",
        )

    def _run_playwright(
        self, context: AgentContext, analysis: dict, features_text: str, inventory_json: str, has_real_data: bool
    ) -> AgentResult:
        try:
            result = context.llm.complete_json(
                TS_SYSTEM_PROMPT, build_ts_user_prompt(json.dumps(analysis), features_text, inventory_json)
            )
        except LLMError as exc:
            return AgentResult(success=False, error=str(exc))

        page_objects = result.get("page_objects", [])
        if not page_objects:
            return AgentResult(success=False, error="LLM returned no page objects")

        saved = []
        for po in page_objects:
            filename = po["filename"]
            content = po["ts_content"]
            save_generated_file(
                context.db, context.generation_id, context.project_id, "page_object",
                filename, f"{PAGES_DIR}/{filename}", content,
            )
            saved.append({"class_name": po["class_name"], "filename": filename, "content": content})

        source = "real Application Explorer data" if has_real_data else "AI-guessed (no Application Explorer data yet)"
        return AgentResult(
            success=True,
            output={"page_objects": saved},
            output_summary=f"Generated {len(saved)} page object(s) using {source}: "
            f"{', '.join(p['class_name'] for p in saved)}",
        )
