import os
import django
from django.test import Client

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import QRCode, Department

def verify_frontend_and_routing():
    print("--- Verifying Frontend Routing & Redemption ---")
    client = Client()

    # 1. Test Landing Page (Root)
    print("\nTesting Landing Page (Root /):")
    response_root = client.get('/')
    print(f"  Status Code: {response_root.status_code}")
    is_landing = "Enterprise QR Code Management" in response_root.content.decode('utf-8')
    print(f"  Includes Landing Content: {is_landing}")

    # 2. Test QR Redirection (Catch-all)
    print("\nTesting QR Redirection alongside Landing:")
    # Ensure a QR code exists
    dept, _ = Department.objects.get_or_create(name="Routing Dept")
    dept, _ = Department.objects.get_or_create(name="Routing Dept")
    qr, created = QRCode.objects.get_or_create(
        short_id="TESTROUT",
        defaults={
            'department': dept,
            'title': "Routing Test",
            'destination_url': "https://yee.org.tr"
        }
    )

    
    response_qr = client.get('/TESTROUT/')
    print(f"  Status Code (Redirect): {response_qr.status_code}")
    print(f"  Redirect Location: {response_qr.get('Location')}")
    
    if is_landing and response_qr.status_code == 302:
        print("\n  SUCCESS: Landing Page and Redirect Engine coexist perfectly.")
    else:
        print("\n  FAILURE: Routing conflict detected.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_frontend_and_routing()
