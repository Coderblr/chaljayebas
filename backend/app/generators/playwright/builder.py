from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.generators.playwright.constants import (
    CORE_DIR,
    FEATURES_DIR,
    PACKAGE_NAME,
    PAGES_DIR,
    STEPS_DIR,
    SUPPORT_DIR,
)
from app.services.generated_file_store import save_generated_file

TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True)


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
    """Renders the deterministic Playwright/TypeScript/Cucumber.js scaffold to disk and persists
    each file as a generated_files row of type 'framework_asset'."""

    output_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "package_name": PACKAGE_NAME,
        "pages_dir": PAGES_DIR,
        "steps_dir": STEPS_DIR,
        "support_dir": SUPPORT_DIR,
        "features_dir": FEATURES_DIR,
        "base_url": base_url or DEFAULT_BASE_URL,
        "environment": "UAT",
        "transaction_name": analysis.get("transaction_name", "NBC Transaction"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    rendered_files = {
        "package.json": "package.json.j2",
        "tsconfig.json": "tsconfig.json.j2",
        "cucumber.js": "cucumber.js.j2",
        f"{CORE_DIR}/BasePage.ts": "BasePage.ts.j2",
        f"{CORE_DIR}/config.ts": "config.ts.j2",
        f"{SUPPORT_DIR}/world.ts": "world.ts.j2",
        f"{SUPPORT_DIR}/hooks.ts": "hooks.ts.j2",
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
    relative_path = "testdata/test_data.xlsx"
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
    if field_type in ("number", "currency"):
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
    for feature in features:
        path = output_dir / FEATURES_DIR / feature["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(feature["content"], encoding="utf-8")

    for po in page_objects:
        path = output_dir / PAGES_DIR / po["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(po["content"], encoding="utf-8")

    for sd in step_definitions:
        path = output_dir / STEPS_DIR / sd["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sd["content"], encoding="utf-8")
