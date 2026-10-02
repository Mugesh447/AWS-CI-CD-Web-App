import sys
import os
import uuid

# Project root directory-ஐ Python path-ல் add செய்கிறது
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

from app.app import app
from app.database import find_user


def authenticated_client():
    client = app.test_client()
    client.post("/login", data={"username": "mugesh", "password": "change-me"})
    return client


def test_home_page():
    """Test whether the home page is working."""

    client = authenticated_client()

    response = client.get("/")

    assert response.status_code == 200

    assert b"AWS CI/CD Web Application" in response.data


def test_health_check():
    """Test whether the health endpoint is working."""

    client = authenticated_client()

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json["status"] == "healthy"


def test_status_api():
    """Return the deployment details used by the dashboard refresh action."""

    response = authenticated_client().get("/api/status")

    assert response.status_code == 200
    assert response.json["service"] == "aws-cicd-webapp"
    assert response.json["status"] == "operational"


def test_dashboard_requires_login():
    response = app.test_client().get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_new_deployment_requires_authentication():
    response = app.test_client().post(
        "/api/deployments",
        json={"version": "v1.5.0", "branch": "main", "image_tag": "release-1.5.0"},
    )

    assert response.status_code == 401


def test_new_deployment_is_queued():
    response = authenticated_client().post(
        "/api/deployments",
        json={"version": "v1.5.0", "branch": "main", "image_tag": "release-1.5.0"},
    )

    assert response.status_code == 202
    assert response.json["deployment"]["status"] == "Queued"

    deployment_id = response.json["deployment"]["id"]
    progress = authenticated_client().get(f"/api/deployments/{deployment_id}")
    assert progress.status_code == 200
    assert progress.json["progress"] >= 0
    assert progress.json["stage"] in {"Source", "Test", "Build", "Deploy"}


def test_logs_api_returns_service_events():
    response = authenticated_client().get("/api/logs")

    assert response.status_code == 200
    assert response.json["total"] >= 1
    assert response.json["logs"][0]["level"] in {"INFO", "WARN", "ERROR"}


def test_deployment_progress_includes_timeline():
    client = authenticated_client()
    deployment = client.post(
        "/api/deployments",
        json={"version": "v1.8.0", "branch": "main", "image_tag": "release-1.8.0"},
    ).json["deployment"]

    response = client.get(f"/api/deployments/{deployment['id']}")

    assert response.status_code == 200
    assert response.json["status"] in {"Running", "Completed"}
    assert len(response.json["timeline"]) == 4
    assert [stage["name"] for stage in response.json["timeline"]] == ["Source", "Test", "Build", "Deploy"]


def test_costs_api_returns_budget_data():
    response = authenticated_client().get("/api/costs")

    assert response.status_code == 200
    assert response.json["current_month"] < response.json["budget"]
    assert response.json["currency"] == "INR"
    assert "ECS Fargate" in response.json["services"]


def test_known_release_can_be_rolled_back():
    response = authenticated_client().post("/api/deployments/8f3a2c1/rollback")

    assert response.status_code == 202
    assert response.json["target_version"] == "v1.4.1"


def test_diagnostics_api_returns_all_checks():
    response = authenticated_client().get("/api/diagnostics")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"
    assert len(response.json["checks"]) == 4


def test_settings_page_requires_login():
    response = app.test_client().get("/settings", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_settings_updates_profile():
    client = authenticated_client()
    response = client.post(
        "/settings",
        data={"name": "Mugesh Kumar Updated", "email": "updated@example.com"},
    )

    assert response.status_code == 200
    assert b"Profile updated successfully" in response.data
    assert client.get("/").status_code == 200
    client.post(
        "/settings",
        data={"name": "Mugesh Kumar", "email": "mugesh@example.com"},
    )


def test_admin_dashboard_lists_multiple_users():
    client = authenticated_client()
    response = client.get("/admin")

    assert response.status_code == 200
    assert b"Team overview" in response.data
    assert client.get("/api/admin/users").status_code == 200


def test_admin_users_api_requires_login():
    response = app.test_client().get("/api/admin/users")

    assert response.status_code == 401


def test_email_notification_is_queued_for_deployment():
    client = authenticated_client()
    deployment = client.post(
        "/api/deployments",
        json={"version": "v1.6.0", "branch": "main", "image_tag": "release-1.6.0"},
    ).json["deployment"]

    response = client.post(
        "/api/notifications/email",
        json={"deployment_id": deployment["id"]},
    )

    assert response.status_code == 202
    assert response.json["message"] == "Email notification queued."


def test_deployment_list_returns_saved_deployments():
    client = authenticated_client()
    client.post(
        "/api/deployments",
        json={"version": "v1.7.0", "branch": "main", "image_tag": "release-1.7.0"},
    )

    response = client.get("/api/deployments")

    assert response.status_code == 200
    assert any(item["version"] == "v1.7.0" for item in response.json["deployments"])


def test_projects_are_listed_and_linked():
    client = authenticated_client()
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert any(project["name"] == "frontend-dashboard" for project in response.json["projects"])

    linked = client.post(
        "/api/projects",
        json={"name": f"api-service-{uuid.uuid4().hex[:6]}", "description": "API companion"},
    )
    assert linked.status_code == 201
    assert linked.json["message"] == "Project linked successfully."


def test_deployment_requires_approval_when_requested():
    client = authenticated_client()
    deployment = client.post(
        "/api/deployments",
        json={"version": "v1.9.0", "branch": "main", "image_tag": "release-1.9.0", "requires_approval": True},
    )

    assert deployment.status_code == 202
    assert deployment.json["deployment"]["status"] == "Pending approval"

    approval = client.post(f"/api/deployments/{deployment.json['deployment']['id']}/approve")

    assert approval.status_code == 200
    assert approval.json["status"] == "Queued"


def test_github_webhook_queue_deployment():
    client = app.test_client()
    response = client.post(
        "/api/github/webhook",
        json={
            "ref": "refs/heads/main",
            "head_commit": {
                "id": "abc123def456",
                "message": "Deploy v1.10.0",
            },
        },
    )

    assert response.status_code == 202
    assert response.json["deployment"]["version"] == "v1.10.0"


def test_create_account_signs_user_in():
    client = app.test_client()
    username = f"demo-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/register",
        data={
            "name": "Demo Developer",
            "username": username,
            "email": "demo@example.com",
            "password": "secure-pass",
            "confirm_password": "secure-pass",
        },
    )

    assert response.status_code == 302
    assert "/login?registered=1&username=" in response.headers["Location"]
    login_page = client.get(response.headers["Location"])
    assert b"Account created successfully" in login_page.data
    assert client.post("/login", data={"username": username, "password": "secure-pass"}).status_code == 302


def test_password_is_hashed_and_session_is_secure():
    client = app.test_client()
    response = client.post(
        "/login",
        data={"username": "MUGESH", "password": "change-me"},
        follow_redirects=False,
    )

    stored_user = find_user("mugesh")
    cookie = response.headers["Set-Cookie"]
    assert response.status_code == 302
    assert stored_user["password_hash"] != "change-me"
    assert stored_user["email"] == "mugesh@example.com"
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_logout_clears_dashboard_session():
    client = authenticated_client()
    assert client.get("/").status_code == 200

    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert client.get("/", follow_redirects=False).status_code == 302