from datetime import datetime, timezone
import os
import re
import secrets
import smtplib
import sqlite3
import threading
import time
import uuid
from email.message import EmailMessage

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

try:
    from .database import create_deployment as save_deployment
    from .database import DATABASE_PATH, create_user, find_deployment, find_user, find_user_by_login, get_connection, username_exists
    from .database import list_deployments as get_user_deployments
    from .database import create_project, list_projects
    from .database import list_users
    from .database import update_deployment_status, update_user_profile
except ImportError:
    from database import create_deployment as save_deployment
    from database import DATABASE_PATH, create_user, find_deployment, find_user, find_user_by_login, get_connection, username_exists
    from database import list_deployments as get_user_deployments
    from database import create_project, list_projects
    from database import list_users
    from database import update_deployment_status, update_user_profile

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=3600,
)
APP_STARTED_AT = time.perf_counter()
REQUEST_METRICS = {"count": 0, "duration_ms_total": 0.0}
REQUEST_METRICS_LOCK = threading.Lock()
LOGIN_USER = os.environ.get("APP_USER", "mugesh")
KNOWN_RELEASES = {
    "8f3a2c1": "v1.4.2",
    "6b91d04": "v1.4.1",
    "4e72a8f": "v1.4.0",
}
DEPLOYMENT_STAGES = ["Source", "Test", "Build", "Deploy"]
SERVICE_LOGS = [
    {"time": "10:42:18", "level": "INFO", "message": "GET /health 200 12ms"},
    {"time": "10:42:16", "level": "INFO", "message": "Deployment v1.4.2 serving traffic"},
    {"time": "10:41:54", "level": "INFO", "message": "ECS task healthy: aws-cicd-webapp"},
    {"time": "10:40:31", "level": "WARN", "message": "Request latency above 200ms threshold"},
    {"time": "10:39:08", "level": "INFO", "message": "GET /api/status 200 18ms"},
    {"time": "10:37:44", "level": "ERROR", "message": "Retrying ECR image metadata request"},
]

@app.before_request
def start_request_timer():
    g.request_started_at = time.perf_counter()


@app.after_request
def record_request_metrics(response):
    started_at = getattr(g, "request_started_at", None)
    if started_at is not None:
        duration_ms = (time.perf_counter() - started_at) * 1000
        with REQUEST_METRICS_LOCK:
            REQUEST_METRICS["count"] += 1
            REQUEST_METRICS["duration_ms_total"] += duration_ms
    return response


@app.route("/")
def home():
    current_hour = datetime.now().hour
    if "user" not in session:
        return redirect(url_for("login"))

    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 17:
        greeting = "Good afternoon"
    elif current_hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Good night"

    return render_template(
        "index.html",
        greeting=greeting,
        user_name=session.get("display_name", "CloudEngineeer"),
        user_email=session.get("user_email", ""),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = find_user_by_login(login)
        if user and check_password_hash(user["password_hash"], password):
            session["user"] = user["username"]
            session["display_name"] = user["name"]
            session["user_email"] = user["email"]
            session["role"] = user["role"]
            session.permanent = request.form.get("remember") == "on"
            return redirect(url_for("home"))
        return render_template(
            "login.html",
            error="Username or password is incorrect. Try again or create a new account.",
            mode="login",
            registered_username=login,
        ), 401

    return render_template(
        "login.html",
        mode="login",
        registered=request.args.get("registered") == "1",
        registered_username=request.args.get("username", ""),
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not username or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(password) < 6:
            error = "Enter your name, valid email, username, and a password with 6+ characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif username_exists(username):
            error = "That username already exists."
        else:
            create_user(name, username, email, password)
            return redirect(url_for("login", registered="1", username=username))
        return render_template("login.html", error=error, mode="register"), 400

    return render_template("login.html", mode="register")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user" not in session:
        return redirect(url_for("login"))
    user = find_user(session["user"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return render_template("settings.html", user=user, error="Enter a valid name and email."), 400
        if new_password and (len(new_password) < 6 or new_password != confirm_password):
            return render_template("settings.html", user=user, error="Passwords must match and contain 6+ characters."), 400
        update_user_profile(session["user"], name, email, new_password or None)
        session["display_name"] = name
        session["user_email"] = email
        user = find_user(session["user"])
        return render_template("settings.html", user=user, saved=True)
    return render_template("settings.html", user=user)


@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "admin":
        return render_template("forbidden.html"), 403
    return render_template("admin.html", users=list_users())


@app.route("/api/admin/users")
def admin_users():
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    if session.get("role") != "admin":
        return jsonify(error="admin access required"), 403
    return jsonify(users=[dict(user) for user in list_users()]), 200


@app.route("/health")
def health():
    return {
        "status": "healthy",
        "message": "AWS CI/CD Web App is running"
    }, 200


@app.route("/api/status")
def status():
    if "user" not in session:
        return jsonify(error="authentication required"), 401

    return jsonify(
        service="aws-cicd-webapp",
        environment="production",
        version="v1.4.2",
        region="us-east-1",
        status="operational",
        updated_at=datetime.now(timezone.utc).isoformat(),
    ), 200


@app.route("/api/deployments", methods=["POST"])
def create_deployment():
    if "user" not in session:
        return jsonify(error="authentication required"), 401

    payload = request.get_json(silent=True) or {}
    version = payload.get("version", "").strip()
    branch = payload.get("branch", "").strip()
    image_tag = payload.get("image_tag", "").strip()
    requires_approval = payload.get("requires_approval", False) is True
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        return jsonify(error="Version must use format v1.2.3."), 400
    if not branch or not image_tag:
        return jsonify(error="Branch and image tag are required."), 400

    deployment_id = uuid.uuid4().hex[:10]
    notes = payload.get("notes", "").strip()
    initial_status = "Pending approval" if requires_approval else "Queued"
    save_deployment(
        deployment_id,
        session["user"],
        version,
        branch,
        image_tag,
        notes,
        time.time(),
        status=initial_status,
    )
    return jsonify(
        message="Deployment queued successfully." if not requires_approval else "Deployment submitted for approval.",
        deployment={
            "id": deployment_id,
            "version": version,
            "branch": branch,
            "image_tag": image_tag,
            "status": initial_status,
        },
    ), 202


@app.route("/api/deployments")
def list_deployments():
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    deployments = get_user_deployments(session["user"])
    return jsonify(deployments=[
        {"id": deployment["id"], "version": deployment["version"], "commit": deployment["image_tag"], "status": deployment["status"], "time": "Just now", "triggered_by": session.get("display_name", session["user"])}
        for deployment in deployments
    ]), 200


def build_deployment_timeline(progress):
    timeline = []
    current_stage = min(3, int(progress / 25))

    for index, stage in enumerate(DEPLOYMENT_STAGES):
        if progress >= 100:
            stage_status = "Completed"
        elif index < current_stage:
            stage_status = "Completed"
        elif index == current_stage:
            stage_status = "In progress"
        else:
            stage_status = "Queued"

        timeline.append(
            {
                "name": stage,
                "status": stage_status,
                "progress": min(100, max(0, progress - (index * 25))),
            }
        )

    return timeline


@app.route("/api/deployments/<deployment_id>")
def deployment_progress(deployment_id):
    if "user" not in session:
        return jsonify(error="authentication required"), 401

    deployment = find_deployment(deployment_id, session["user"])
    if not deployment:
        return jsonify(error="deployment not found"), 404

    elapsed = time.time() - deployment["created_at"]
    progress = min(100, int(elapsed / 2 * 100))
    current_stage_index = min(3, int(progress / 25))
    status = "Completed" if progress == 100 else "Running"

    return jsonify(
        id=deployment_id,
        version=deployment["version"],
        progress=progress,
        stage=DEPLOYMENT_STAGES[current_stage_index],
        status=status,
        timeline=build_deployment_timeline(progress),
    ), 200


@app.route("/api/deployments/<deployment_id>/approve", methods=["POST"])
def approve_deployment(deployment_id):
    if "user" not in session:
        return jsonify(error="authentication required"), 401

    deployment = find_deployment(deployment_id, session["user"])
    if not deployment:
        return jsonify(error="deployment not found"), 404
    if deployment["status"] != "Pending approval":
        return jsonify(error="deployment is not pending approval", status=deployment["status"]), 400

    update_deployment_status(deployment_id, session["user"], "Queued")
    return jsonify(
        message=f"Deployment {deployment['version']} approved.",
        status="Queued",
    ), 200


@app.route("/api/deployments/<deployment_id>/rollback", methods=["POST"])
def rollback_deployment(deployment_id):
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    deployment = find_deployment(deployment_id, session["user"])
    version = deployment["version"] if deployment else KNOWN_RELEASES.get(deployment_id)
    if not version:
        return jsonify(error="deployment not found"), 404
    return jsonify(
        message=f"Rollback for {version} has been queued.",
        status="Rollback queued",
        target_version="v1.4.1",
    ), 202


@app.route("/api/notifications/email", methods=["POST"])
def email_notification():
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    payload = request.get_json(silent=True) or {}
    deployment = find_deployment(payload.get("deployment_id", ""), session["user"])
    if not deployment:
        return jsonify(error="deployment not found"), 404
    recipient = session.get("user_email", "")
    smtp_host = os.environ.get("SMTP_HOST")
    if smtp_host and recipient:
        message = EmailMessage()
        message["Subject"] = f"Deployment {deployment['version']} completed"
        message["From"] = os.environ.get("SMTP_FROM", "noreply@example.com")
        message["To"] = recipient
        message.set_content(f"Deployment {deployment['version']} is live in production.")
        with smtplib.SMTP(smtp_host, int(os.environ.get("SMTP_PORT", "587"))) as smtp:
            smtp.starttls()
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(message)
        return jsonify(message="Email notification sent.", recipient=recipient), 200
    SERVICE_LOGS.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "level": "INFO", "message": f"Email notification queued for {recipient or 'account email'}"})
    return jsonify(message="Email notification queued.", recipient=recipient), 202


@app.route("/api/logs")
def logs():
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    return jsonify(logs=SERVICE_LOGS, total=len(SERVICE_LOGS)), 200


@app.route("/api/costs")
def costs():
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    trend = [
        {"month": "Jan", "amount": 3200.00},
        {"month": "Feb", "amount": 3450.00},
        {"month": "Mar", "amount": 3380.00},
        {"month": "Apr", "amount": 3520.00},
        {"month": "May", "amount": 3890.00},
        {"month": "Jun", "amount": 3563.78},
    ]
    return jsonify(
        current_month=3563.78,
        forecast=4876.40,
        budget=8350.00,
        currency="INR",
        change_percent=-8.4,
        services={"ECS Fargate": 2029.05, "ECR": 680.53, "CloudWatch": 511.02, "Other": 343.18},
        trend=trend,
    ), 200


@app.route("/api/diagnostics")
def diagnostics():
    if "user" not in session:
        return jsonify(error="authentication required"), 401

    database_ok = False
    seed_user = None
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        seed_user = find_user(LOGIN_USER)
        database_ok = DATABASE_PATH.exists()
    except sqlite3.Error:
        app.logger.exception("Database diagnostics check failed")

    configured_secret = os.environ.get("FLASK_SECRET_KEY", "")
    secret_configured = bool(
        len(configured_secret) >= 32
        and configured_secret not in {"local-development-secret", "change-me"}
    )
    secure_cookie_enabled = app.config["SESSION_COOKIE_SECURE"]
    default_password_in_use = seed_user is None or check_password_hash(
        seed_user["password_hash"], "change-me"
    )
    checks = [
        {
            "name": "Application service",
            "category": "runtime",
            "status": "Operational",
            "detail": "Flask request handler is responding.",
        },
        {
            "name": "SQLite database",
            "category": "runtime",
            "status": "Operational" if database_ok else "Failed",
            "detail": "Database connection and read query succeeded." if database_ok else "Database connection or read query failed.",
        },
        {
            "name": "Debug mode",
            "category": "security",
            "status": "Warning" if app.debug else "Operational",
            "detail": "Disable debug mode before deployment." if app.debug else "Debug mode is disabled.",
        },
        {
            "name": "Session signing key",
            "category": "security",
            "status": "Operational" if secret_configured else "Warning",
            "detail": "A non-default signing key with at least 32 characters is configured." if secret_configured else "Set a stable, non-default FLASK_SECRET_KEY with at least 32 characters.",
        },
        {
            "name": "HTTPS-only session cookie",
            "category": "security",
            "status": "Operational" if secure_cookie_enabled else "Warning",
            "detail": "Session cookies are restricted to HTTPS." if secure_cookie_enabled else "Enable COOKIE_SECURE=true when serving over HTTPS.",
        },
        {
            "name": "Default account password",
            "category": "security",
            "status": "Warning" if default_password_in_use else "Operational",
            "detail": "Replace the default seed account password before deployment." if default_password_in_use else "The seed account password is not the development default.",
        },
    ]
    has_failure = any(check["status"] == "Failed" for check in checks)
    has_warning = any(check["status"] == "Warning" for check in checks)
    security_status = "needs_attention" if any(
        check["category"] == "security" and check["status"] != "Operational"
        for check in checks
    ) else "passed"
    overall_status = "degraded" if has_failure else "attention" if has_warning else "healthy"
    return jsonify(
        status=overall_status,
        security_status=security_status,
        checks=checks,
        checked_at=datetime.now(timezone.utc).isoformat(),
    ), 200


@app.route("/api/monitoring")
def monitoring():
    if "user" not in session:
        return jsonify(error="authentication required"), 401

    with REQUEST_METRICS_LOCK:
        request_count = REQUEST_METRICS["count"]
        duration_ms_total = REQUEST_METRICS["duration_ms_total"]

    return jsonify(
        scope="this application worker process",
        uptime_seconds=round(time.perf_counter() - APP_STARTED_AT, 1),
        request_count=request_count,
        average_response_ms=round(duration_ms_total / request_count, 2) if request_count else 0,
        sampled_at=datetime.now(timezone.utc).isoformat(),
    ), 200


@app.route("/api/github/webhook", methods=["POST"])
def github_webhook():
    payload = request.get_json(silent=True) or {}

    if not payload:
        return jsonify(error="invalid webhook payload"), 400

    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref else "main"
    head_commit = payload.get("head_commit", {}) or {}
    message = head_commit.get("message", "")
    version_match = re.search(r"v\d+\.\d+\.\d+", message)
    version = version_match.group(0) if version_match else "v1.0.0"
    image_tag = (head_commit.get("id") or payload.get("after", "") or "manual").strip()[:12]

    deployment_id = uuid.uuid4().hex[:10]
    save_deployment(
        deployment_id,
        os.environ.get("APP_USER", "mugesh"),
        version,
        branch,
        image_tag,
        message or "GitHub webhook deployment",
        time.time(),
        status="Queued",
    )

    return jsonify(
        message="Deployment queued from GitHub webhook.",
        deployment={
            "id": deployment_id,
            "version": version,
            "branch": branch,
            "image_tag": image_tag,
            "status": "Queued",
        },
    ), 202


@app.route("/api/projects", methods=["GET", "POST"])
def projects():
    if "user" not in session:
        return jsonify(error="authentication required"), 401
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        name = payload.get("name", "").strip().lower()
        description = payload.get("description", "").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,49}", name):
            return jsonify(error="Use 3-50 lowercase letters, numbers, or hyphens."), 400
        try:
            create_project(name, description, "aws-cicd-webapp")
        except Exception:
            return jsonify(error="That project already exists."), 409
        return jsonify(message="Project linked successfully.", project=name), 201
    return jsonify(projects=[dict(project) for project in list_projects()]), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False
    )