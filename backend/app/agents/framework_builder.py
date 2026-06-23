from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.config import settings
from app.generators.selenium.builder import build_framework_project, write_generated_artifacts
from app.generators.zipper import zip_directory
from app.services.application_inventory_service import get_discovered_base_url


class FrameworkBuilderAgent(BaseAgent):
    """Deterministic, template-based agent (no LLM call) that assembles the complete Maven
    project from the deterministic scaffold + the artifacts produced by the upstream
    AI generation agents, then zips it for download."""

    name = "FrameworkBuilderAgent"

    def run(self, context: AgentContext) -> AgentResult:
        analysis = context.state.get("RequirementAnalyzerAgent", {}).get("analysis", {})
        features = context.state.get("FeatureGeneratorAgent", {}).get("features", [])
        page_objects = context.state.get("PageObjectGeneratorAgent", {}).get("page_objects", [])
        step_definitions = context.state.get("StepDefinitionGeneratorAgent", {}).get("step_definitions", [])

        if not (features and page_objects and step_definitions):
            return AgentResult(success=False, error="Missing upstream artifacts to assemble the framework")

        generated_root = settings.resolved_path(settings.generated_dir)
        output_dir = generated_root / str(context.project_id) / str(context.generation_id) / "selenium-framework"
        test_data_rows = context.state.get("TestDataAgent", {}).get("rows")
        base_url = get_discovered_base_url(context.db, context.project_id)

        try:
            build_framework_project(
                context.db,
                context.generation_id,
                context.project_id,
                output_dir,
                analysis,
                analysis.get("fields", []),
                test_data_rows,
                base_url,
            )
            write_generated_artifacts(output_dir, features, page_objects, step_definitions)

            zip_path = output_dir.parent / "selenium-framework.zip"
            zip_directory(output_dir, zip_path)
        except OSError as exc:
            return AgentResult(success=False, error=f"Failed to assemble framework project: {exc}")

        return AgentResult(
            success=True,
            output={"output_dir": str(output_dir), "zip_path": str(zip_path)},
            output_summary=f"Assembled Maven project at {output_dir} and zipped to {zip_path.name}",
        )
