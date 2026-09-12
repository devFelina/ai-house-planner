import os

ASPNET_API_URL = os.getenv("ASPNET_API_URL", "http://localhost:5000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "shared-internal-secret")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
