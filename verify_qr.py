import os
import django
from django.test import Client, override_settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import QRCode, Department

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
def verify_qr_generation():
    print("--- Verifying Visual QR Generation ---")
    
    # 1. Setup Test Data
    dept, _ = Department.objects.get_or_create(name="Visual Dept")
    qr = QRCode.objects.create(
        department=dept,
        title="Visual Test QR",
        destination_url="https://yee.org.tr"
    )

    client = Client()

    # 2. Test Image Response
    print("\nTesting QR Image Request:")
    response = client.get(f"/download-qr/{qr.short_id}/")
    
    content_type = response.get('Content-Type')
    content_disposition = response.get('Content-Disposition')
    
    print(f"  Status Code: {response.status_code}")
    print(f"  Content-Type: {content_type}")
    print(f"  Content-Disposition: {content_disposition}")
    
    # 3. Validations
    is_png = content_type == "image/png"
    is_attachment = content_disposition and "attachment" in content_disposition
    has_image_data = len(response.content) > 100 # PNG header + data
    
    print(f"  Is Valid PNG: {is_png}")
    print(f"  Is Download Attachment: {is_attachment}")
    print(f"  Contains data: {has_image_data}")

    if is_png and is_attachment and has_image_data:
        print("\n  SUCCESS: QR Image generated and served correctly.")
    else:
        print("\n  FAILURE: Image generation failed check.")

    # 4. Test 404
    print("\nTesting 404 for invalid ID:")
    response_404 = client.get("/download-qr/nonexistent/")
    print(f"  Status Code (Expected 404): {response_404.status_code}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_qr_generation()
