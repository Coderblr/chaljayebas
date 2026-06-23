import os

import requests
import streamlit as st

API_BASE_URL = os.environ.get("NBC_API_BASE_URL", "http://127.0.0.1:8000")


def _headers() -> dict:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _raise_for_status(response: requests.Response) -> None:
    """requests' default raise_for_status() gives you "400 Client Error: Bad Request for url:
    ..." with no indication of *why* - every route on this backend puts the real reason in a
    JSON `detail` field. Surface that instead, everywhere, so the UI is always diagnosable
    without needing to read the backend's console output."""
    if response.ok:
        return
    detail = None
    try:
        body = response.json()
        detail = body.get("detail") if isinstance(body, dict) else None
    except ValueError:
        pass
    if detail:
        raise RuntimeError(f"{response.status_code}: {detail}")
    response.raise_for_status()


def login(username: str, password: str) -> dict:
    response = requests.post(f"{API_BASE_URL}/auth/login", json={"username": username, "password": password})
    _raise_for_status(response)
    return response.json()


def get_me() -> dict:
    response = requests.get(f"{API_BASE_URL}/auth/me", headers=_headers())
    _raise_for_status(response)
    return response.json()


def change_password(current_password: str, new_password: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/auth/change-password", headers=_headers(),
        json={"current_password": current_password, "new_password": new_password},
    )
    _raise_for_status(response)
    return response.json()


def list_projects() -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/projects", headers=_headers())
    _raise_for_status(response)
    return response.json()


def create_project(name: str, description: str, transaction_type: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/projects", headers=_headers(),
        json={"name": name, "description": description, "transaction_type": transaction_type},
    )
    _raise_for_status(response)
    return response.json()


def list_documents(project_id: int) -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/documents/project/{project_id}", headers=_headers())
    _raise_for_status(response)
    return response.json()


def upload_document(project_id: int, doc_type: str, filename: str, file_bytes: bytes) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/documents/upload", headers=_headers(),
        data={"project_id": project_id, "doc_type": doc_type},
        files={"file": (filename, file_bytes)},
    )
    _raise_for_status(response)
    return response.json()


def upload_git_repo(project_id: int, git_url: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/documents/upload-git", headers=_headers(),
        json={"project_id": project_id, "git_url": git_url},
    )
    _raise_for_status(response)
    return response.json()


def upload_local_path(project_id: int, local_path: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/documents/upload-local-path", headers=_headers(),
        json={"project_id": project_id, "local_path": local_path},
    )
    _raise_for_status(response)
    return response.json()


def run_generation(
    project_id: int, document_id: int, framework_type: str = "selenium_java",
    mode: str = "generate_new", framework_document_id: int | None = None,
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/generation/run", headers=_headers(),
        json={
            "project_id": project_id, "document_id": document_id, "framework_type": framework_type,
            "mode": mode, "framework_document_id": framework_document_id,
        },
        timeout=300,
    )
    _raise_for_status(response)
    return response.json()


def get_generation(generation_id: int) -> dict:
    response = requests.get(f"{API_BASE_URL}/generation/{generation_id}", headers=_headers())
    _raise_for_status(response)
    return response.json()


def download_generation(generation_id: int) -> bytes:
    response = requests.get(f"{API_BASE_URL}/generation/{generation_id}/download", headers=_headers())
    _raise_for_status(response)
    return response.content


def list_history(project_id: int | None = None) -> list[dict]:
    params = {"project_id": project_id} if project_id else {}
    response = requests.get(f"{API_BASE_URL}/history", headers=_headers(), params=params)
    _raise_for_status(response)
    return response.json()


def run_execution(generation_id: int) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/execution/run", headers=_headers(),
        json={"generation_id": generation_id}, timeout=900,
    )
    _raise_for_status(response)
    return response.json()


def get_execution(execution_id: int) -> dict:
    response = requests.get(f"{API_BASE_URL}/execution/{execution_id}", headers=_headers())
    _raise_for_status(response)
    return response.json()


def list_executions(project_id: int) -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/execution/project/{project_id}/list", headers=_headers())
    _raise_for_status(response)
    return response.json()


def report_url(execution_id: int) -> str:
    return f"{API_BASE_URL}/execution/{execution_id}/report"


def download_report_zip(execution_id: int) -> bytes:
    response = requests.get(f"{API_BASE_URL}/execution/{execution_id}/report-zip", headers=_headers())
    _raise_for_status(response)
    return response.content


def list_versions(project_id: int, framework_type: str | None = None) -> list[dict]:
    params = {"project_id": project_id}
    if framework_type:
        params["framework_type"] = framework_type
    response = requests.get(f"{API_BASE_URL}/generation/versions", headers=_headers(), params=params)
    _raise_for_status(response)
    return response.json()


def compare_versions(generation_id_a: int, generation_id_b: int) -> dict:
    response = requests.get(
        f"{API_BASE_URL}/generation/compare", headers=_headers(),
        params={"generation_id_a": generation_id_a, "generation_id_b": generation_id_b},
    )
    _raise_for_status(response)
    return response.json()


def restore_version(generation_id: int) -> dict:
    response = requests.post(f"{API_BASE_URL}/generation/{generation_id}/restore", headers=_headers())
    _raise_for_status(response)
    return response.json()


def reuse_version(generation_id: int) -> dict:
    response = requests.post(f"{API_BASE_URL}/generation/{generation_id}/reuse", headers=_headers())
    _raise_for_status(response)
    return response.json()


def run_exploration(
    project_id: int, base_url: str, max_pages: int = 10, max_depth: int = 2,
    username: str | None = None, password: str | None = None,
    transaction_number: str | None = None, form_values: dict | None = None,
    headless: bool = False, browser: str = "chrome",
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/exploration/run", headers=_headers(),
        json={
            "project_id": project_id, "base_url": base_url, "max_pages": max_pages, "max_depth": max_depth,
            "username": username, "password": password, "transaction_number": transaction_number,
            "form_values": form_values, "headless": headless, "browser": browser,
        },
        timeout=300,
    )
    _raise_for_status(response)
    return response.json()


def run_coverage(project_id: int) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/coverage/run", headers=_headers(), json={"project_id": project_id},
    )
    _raise_for_status(response)
    return response.json()


def run_business_rules(generation_id: int) -> list[dict]:
    response = requests.post(
        f"{API_BASE_URL}/business-rules/run", headers=_headers(), json={"generation_id": generation_id},
    )
    _raise_for_status(response)
    return response.json()


def list_kb_collections() -> list[str]:
    response = requests.get(f"{API_BASE_URL}/knowledge-base/collections", headers=_headers())
    _raise_for_status(response)
    return response.json()


def browse_kb_collection(collection_name: str, project_id: int) -> list[dict]:
    response = requests.get(
        f"{API_BASE_URL}/knowledge-base/{collection_name}", headers=_headers(), params={"project_id": project_id}
    )
    _raise_for_status(response)
    return response.json()


def list_roles() -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/admin/roles", headers=_headers())
    _raise_for_status(response)
    return response.json()


def list_users() -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/admin/users", headers=_headers())
    _raise_for_status(response)
    return response.json()


def create_user(username: str, email: str, password: str, role_name: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/admin/users", headers=_headers(),
        json={"username": username, "email": email, "password": password, "role_name": role_name},
    )
    _raise_for_status(response)
    return response.json()


def set_user_active(user_id: int, active: bool) -> dict:
    action = "activate" if active else "deactivate"
    response = requests.post(f"{API_BASE_URL}/admin/users/{user_id}/{action}", headers=_headers())
    _raise_for_status(response)
    return response.json()


def get_llm_settings() -> dict:
    response = requests.get(f"{API_BASE_URL}/settings/llm", headers=_headers())
    _raise_for_status(response)
    return response.json()


def update_llm_settings(model: str) -> dict:
    response = requests.put(f"{API_BASE_URL}/settings/llm", headers=_headers(), json={"model": model})
    _raise_for_status(response)
    return response.json()
