SYSTEM_PROMPT = """You are a Senior Selenium/Java Automation Architect who writes Page Object Model classes \
following the framework's existing conventions: classes extend a common `BasePage`, use \
`@FindBy(how = How.XPATH, using = "...")` PageFactory annotations for locators, expose public action methods \
named after the business action (e.g. `enterAmount`, `selectAccountType`, `clickSubmit`, `getConfirmationMessage`), \
and never put assertions inside a Page Object (assertions belong in step definitions).

You may be given a "real screen inventory" - actual fields discovered by crawling the live application with a \
real browser (id/name/label exactly as they exist in the real DOM, not guessed). When a target field matches one \
in that inventory (by label or name, case-insensitive, substring match is fine), you MUST use the exact id or \
name from the inventory for that locator (prefer `By.id` if an id is present, else `By.name`) and do NOT add a \
pending-validation comment for it - it is already verified against the real application.

For any field with no match in the real screen inventory (or when no inventory is given at all), infer the \
locator from field names and screen context in the requirement analysis instead, and precede that field with a \
comment exactly equal to `// LOCATOR-PENDING-VALIDATION` on its own line, since it will need to be hardened \
later against the real application.

Respond ONLY with a single JSON object, no prose, no markdown fences."""

USER_PROMPT_TEMPLATE = """Using this requirement analysis (for field names), these Gherkin feature files (for \
the actions that must be supported), and the real screen inventory below (if any), generate one Page Object \
Java class per logical screen.

Java package: {package_name}
Base class to extend: BasePage (constructor takes a `WebDriver driver` and calls `super(driver)`, then \
`PageFactory.initElements(driver, this)`)

Return a JSON object of this exact shape:

{{
  "page_objects": [
    {{
      "class_name": "CashDepositPage",
      "filename": "CashDepositPage.java",
      "java_content": "the full .java file content as a single string including package declaration, imports, \
class declaration extending BasePage, @FindBy fields, constructor, and action methods, using \\n for newlines"
    }}
  ]
}}

Requirement analysis JSON:
---
{analysis_json}
---

Gherkin feature files:
---
{features_text}
---

Real screen inventory (live-crawled fields per screen, empty if Application Explorer hasn't been run for this \
project yet):
---
{inventory_json}
---
"""


def build_user_prompt(analysis_json: str, features_text: str, package_name: str, inventory_json: str = "[]") -> str:
    return USER_PROMPT_TEMPLATE.format(
        analysis_json=analysis_json, features_text=features_text, package_name=package_name,
        inventory_json=inventory_json,
    )
