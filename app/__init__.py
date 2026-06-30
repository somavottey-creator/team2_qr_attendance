"""
Application factory for the Digital Attendance System.
Hardened with dynamic environment loading and cookie protection flags.
"""

import os
from flask import Flask
from .database import init_db
from .routes import register_routes


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    
    # 1. Secure Secret Key Configuration
    # Pulls from environment variables. If it doesn't exist, it falls back to a development key.
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-fallback-insecure-key-9x8y7z")

    # Strict Security Guard: Prevent deploying to school with the default insecure key
    is_production = os.environ.get("FLASK_ENV") == "production"
    if is_production and app.secret_key == "dev-fallback-insecure-key-9x8y7z":
        raise ValueError(
            "CRITICAL SECURITY CONFIGURATION ERROR:\n"
            "The application is set to production mode, but is using the insecure fallback secret key.\n"
            "You MUST define a secure 'FLASK_SECRET_KEY' environment variable on your hosting server!"
        )

    # 2. Hardening Cookie & Session Integrity
    # These configurations protect your 'once-a-day per device' rule from client-side tampering.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,   # Prevents malicious client scripts from reading/stealing cookies
        SESSION_COOKIE_SAMESITE="Lax",   # Mitigates Cross-Site Request Forgery (CSRF) tracking bugs
        PERMANENT_SESSION_LIFETIME=86400 # Ensures server tracking references expire logically after 24 hours
    )

    # 3. Initialize Database (Creates tables and optimized autocomplete indexes automatically)
    init_db()

    # 4. Register All Modular API & Page View Routes
    register_routes(app)

    return app