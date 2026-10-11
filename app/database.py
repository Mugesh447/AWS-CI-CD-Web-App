import os
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "app.db"))


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'developer',
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                version TEXT NOT NULL,
                branch TEXT NOT NULL,
                image_tag TEXT NOT NULL,
                notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Queued',
                created_at REAL NOT NULL
            );
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                linked_project TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "email" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'developer'")
        seed_username = os.environ.get("APP_USER", "mugesh")
        seed_name = os.environ.get("APP_NAME", "CloudEngineer")
        seed_email = os.environ.get("APP_EMAIL", "mugesh@example.com")
        seed_password = os.environ.get("APP_PASSWORD", "change-me")
        existing_user = connection.execute(
            "SELECT id FROM users WHERE username = ?", (seed_username,)
        ).fetchone()
        if not existing_user:
            connection.execute(
                "INSERT INTO users (name, username, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
                (seed_name, seed_username, seed_email, "admin", generate_password_hash(seed_password)),
            )
        else:
            connection.execute(
                "UPDATE users SET email = ? WHERE username = ? AND email = ''",
                (seed_email, seed_username),
            )
            connection.execute("UPDATE users SET role = 'admin' WHERE username = ?", (seed_username,))
            connection.execute(
                "INSERT OR IGNORE INTO projects (name, description, linked_project) VALUES (?, ?, ?)",
                ("frontend-dashboard", "Frontend companion for the deployment console", "aws-cicd-webapp"),
            )


def find_user(username):
    with get_connection() as connection:
        return connection.execute(
            "SELECT name, username, email, role, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def find_user_by_login(login):
    if not login:
        return None
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT name, username, email, role, password_hash
            FROM users
            WHERE username = ? COLLATE NOCASE OR lower(email) = ?
            ORDER BY CASE WHEN username = ? COLLATE NOCASE THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (login, login.lower(), login),
        ).fetchone()


def create_user(name, username, email, password):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (name, username, email, role, password_hash) VALUES (?, ?, ?, ?, ?)",
            (name, username, email, "developer", generate_password_hash(password)),
        )


def username_exists(username):
    with get_connection() as connection:
        return connection.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone() is not None


def update_user_profile(username, name, email, password=None):
    with get_connection() as connection:
        if password:
            connection.execute(
                "UPDATE users SET name = ?, email = ?, password_hash = ? WHERE username = ?",
                (name, email, generate_password_hash(password), username),
            )
        else:
            connection.execute(
                "UPDATE users SET name = ?, email = ? WHERE username = ?",
                (name, email, username),
            )


def create_deployment(deployment_id, username, version, branch, image_tag, notes, created_at, status="Queued"):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO deployments
                (id, username, version, branch, image_tag, notes, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (deployment_id, username, version, branch, image_tag, notes, status, created_at),
        )


def update_deployment_status(deployment_id, username, status):
    with get_connection() as connection:
        connection.execute(
            "UPDATE deployments SET status = ? WHERE id = ? AND username = ?",
            (status, deployment_id, username),
        )


def find_deployment(deployment_id, username):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM deployments WHERE id = ? AND username = ?",
            (deployment_id, username),
        ).fetchone()


def list_deployments(username):
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, version, branch, image_tag, notes, status, created_at FROM deployments WHERE username = ? ORDER BY created_at DESC",
            (username,),
        ).fetchall()


def list_users():
    with get_connection() as connection:
        return connection.execute(
            "SELECT name, username, email, role, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()


def list_projects():
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, name, description, linked_project FROM projects ORDER BY name"
        ).fetchall()


def create_project(name, description, linked_project):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO projects (name, description, linked_project) VALUES (?, ?, ?)",
            (name, description, linked_project),
        )


init_db()
