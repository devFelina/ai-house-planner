"""
Configuration for the agentic service.
Loads environment variables with safe defaults for local development.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Gemini API key for vision analysis
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ASP.NET Core API base URL (for internal callbacks)
ASPNET_API_URL = os.environ.get("ASPNET_API_URL", "http://localhost:5265/api/v1")

# Shared secret for internal service-to-service authentication
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "shared-internal-secret")
