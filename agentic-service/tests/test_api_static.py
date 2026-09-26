import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.config import OUTPUT_PLANS_DIR

client = TestClient(app)

def test_static_plans_mount_serves_images():
    """Verify that the /plans mount exists and can serve a generated PNG."""
    # Create a dummy image file in the output plans directory
    OUTPUT_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    test_image_path = OUTPUT_PLANS_DIR / "test_dummy_plan.png"
    
    # Write a tiny valid PNG signature (1x1 pixel) or just some bytes that HTTP will serve
    tiny_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff\x3f\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
    test_image_path.write_bytes(tiny_png)
    
    try:
        response = client.get("/plans/test_dummy_plan.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == tiny_png
    finally:
        # Cleanup
        if test_image_path.exists():
            test_image_path.unlink()
