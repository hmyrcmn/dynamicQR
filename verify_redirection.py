import os
import django
from django.test import RequestFactory, Client
from django.urls import reverse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import QRCode, ScanAnalytics, Department, hash_ip

def verify_redirection():
    print("--- Verifying Redirection & Analytics ---")
    
    # 1. Setup Test Data
    dept, _ = Department.objects.get_or_create(name="Redirection Test Dept")
    qr = QRCode.objects.create(
        department=dept,
        title="Test Redirect",
        destination_url="https://google.com"
    )
    print(f"Created Test QR: {qr.short_id} -> {qr.destination_url}")

    client = Client()

    # 2. Test Success Redirection
    print("\nTesting valid redirection:")
    response = client.get(f"/{qr.short_id}/") # Path defined in urls.py
    
    print(f"  Status Code: {response.status_code}") # Should be 302
    redirect_url = response.get('Location') or response.get('location')
    print(f"  Redirect location: {redirect_url}")
    
    # Check Analytics
    scan = ScanAnalytics.objects.filter(qr_code=qr).first()
    if scan:
        print(f"  Analytics captured: Yes")
        print(f"  IP Hash: {scan.ip_address_hash}")
        print(f"  User Agent: {scan.user_agent}")
    else:
        print(f"  Analytics captured: NO")

    # 3. Test Loop Protection
    print("\nTesting loop protection:")
    # We need a hostname that matches the request.get_host() logic
    # Client defaults to 'testserver'
    qr_loop = QRCode.objects.create(
        department=dept,
        title="Loop QR",
        destination_url="http://testserver/somepath"
    )
    response_loop = client.get(f"/{qr_loop.short_id}/")
    print(f"  Status Code: {response_loop.status_code}") # Should be 400
    if response_loop.status_code == 400:
        print("  Loop protected successfully.")

    # 4. Test 404
    print("\nTesting 404 for missing QR:")
    response_404 = client.get("/missing-id/")
    print(f"  Status Code: {response_404.status_code}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_redirection()
