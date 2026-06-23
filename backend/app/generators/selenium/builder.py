from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.generators.selenium.constants import (
    ARTIFACT_ID,
    BASE_PACKAGE,
    CORE_PACKAGE,
    GROUP_ID,
    JAVA_VERSION,
    PAGES_PACKAGE,
    STEPS_PACKAGE,
    UTILS_PACKAGE,
)
from app.services.generated_file_store import save_generated_file

TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True)


def _pkg_path(package: str) -> str:
    return package.replace(".", "/")


DEFAULT_BASE_URL = "https://nbc-uat.example-bank.internal"


def build_framework_project(
    db: Session,
    generation_id: int,
    project_id: int,
    output_dir: Path,
    analysis: dict,
    fields: list[dict],
    test_data_rows: list[dict] | None = None,
    base_url: str | None = None,
) -> Path:
    """Renders the deterministic Maven scaffold to disk and persists each file as a
    generated_files row of type 'framework_asset'. Returns the project root directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    core_path = _pkg_path(CORE_PACKAGE)
    pages_path = _pkg_path(PAGES_PACKAGE)
    steps_path = _pkg_path(STEPS_PACKAGE)
    utils_path = _pkg_path(UTILS_PACKAGE)

    context = {
        "group_id": GROUP_ID,
        "artifact_id": ARTIFACT_ID,
        "java_version": JAVA_VERSION,
        "base_package": BASE_PACKAGE,
        "core_package": CORE_PACKAGE,
        "pages_package": PAGES_PACKAGE,
        "steps_package": STEPS_PACKAGE,
        "utils_package": UTILS_PACKAGE,
        "core_package_path": core_path,
        "pages_package_path": pages_path,
        "steps_package_path": steps_path,
        "base_url": base_url or DEFAULT_BASE_URL,
        "environment": "UAT",
        "transaction_name": analysis.get("transaction_name", "NBC Transaction"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    rendered_files = {
        "pom.xml": "pom.xml.j2",
        f"src/main/java/{core_path}/DriverFactory.java": "DriverFactory.java.j2",
        f"src/main/java/{core_path}/ConfigReader.java": "ConfigReader.java.j2",
        f"src/main/java/{core_path}/BasePage.java": "BasePage.java.j2",
        f"src/main/java/{core_path}/BaseTest.java": "BaseTest.java.j2",
        f"src/main/java/{core_path}/Hooks.java": "Hooks.java.j2",
        f"src/main/java/{utils_path}/TestDataReader.java": "TestDataReader.java.j2",
        f"src/test/java/{_pkg_path(BASE_PACKAGE)}/TestRunner.java": "TestRunner.java.j2",
        "src/test/resources/testng.xml": "testng.xml.j2",
        "src/test/resources/config.properties": "config.properties.j2",
        "src/test/resources/log4j2.xml": "log4j2.xml.j2",
        "README.md": "README.md.j2",
        ".gitignore": "gitignore.j2",
    }

    for relative_path, template_name in rendered_files.items():
        content = _env.get_template(template_name).render(**context)
        full_path = output_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        save_generated_file(
            db, generation_id, project_id, "framework_asset", full_path.name, relative_path, content
        )

    _write_test_data(db, generation_id, project_id, output_dir, fields, test_data_rows)

    return output_dir


def _write_test_data(
    db: Session, generation_id: int, project_id: int, output_dir: Path, fields: list[dict],
    test_data_rows: list[dict] | None,
) -> None:
    relative_path = "src/test/resources/testdata/test_data.xlsx"
    full_path = output_dir / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "TestData"

    headers = [f["name"] for f in fields] if fields else ["Field1", "Field2"]
    sheet.append(["row_type", *headers] if test_data_rows else headers)

    if test_data_rows:
        for row in test_data_rows:
            values = row.get("values", {})
            sheet.append([row.get("row_type", "")] + [values.get(h, "") for h in headers])
    else:
        sample_row = [_sample_value(f) for f in fields] if fields else ["SampleValue1", "SampleValue2"]
        sheet.append(sample_row)

    workbook.save(full_path)

    save_generated_file(
        db, generation_id, project_id, "test_data", "test_data.xlsx", relative_path,
        f"[binary XLSX, {len(test_data_rows) if test_data_rows else 1} row(s), columns: {', '.join(headers)}]",
    )


def _sample_value(field: dict) -> str:
    field_type = (field.get("type") or "text").lower()
    if field_type == "number" or field_type == "currency":
        return "1000"
    if field_type == "date":
        return "2026-06-21"
    return f"Sample{field.get('name', 'Value').replace(' ', '')}"


def write_generated_artifacts(
    output_dir: Path,
    features: list[dict],
    page_objects: list[dict],
    step_definitions: list[dict],
) -> None:
    """Writes the LLM-generated feature/page-object/step-definition files (already persisted to
    the DB by their respective agents) onto disk at the same relative paths used in the DB."""

    pages_path = _pkg_path(PAGES_PACKAGE)
    steps_path = _pkg_path(STEPS_PACKAGE)

    for feature in features:
        path = output_dir / "src/test/resources/features" / feature["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(feature["content"], encoding="utf-8")

    for po in page_objects:
        path = output_dir / "src/test/java" / pages_path / po["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(po["content"], encoding="utf-8")

    for sd in step_definitions:
        path = output_dir / "src/test/java" / steps_path / sd["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sd["content"], encoding="utf-8")
