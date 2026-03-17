import os
import django
from django.test import Client

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import QRCode, Department, CustomUser, ScanAnalytics

def verify_analytics_dashboard():
    print("--- Verifying Analytics Dashboard & RBAC ---")
    
    # 1. Setup Test Data
    dept_a, _ = Department.objects.get_or_create(name="Analytics Dept A")
    dept_b, _ = Department.objects.get_or_create(name="Analytics Dept B")
    
    manager_a, _ = CustomUser.objects.get_or_create(
        username="manager_a",
        defaults={'department': dept_a, 'role': 'DEPT_MANAGER'}
    )
    
    qr_a = QRCode.objects.create(department=dept_a, title="QR A", destination_url="https://yee.org.tr")
    qr_b = QRCode.objects.create(department=dept_b, title="QR B", destination_url="https://gov.tr")
    
    # Simulate scans for QR A
    ScanAnalytics.objects.create(qr_code=qr_a, ip_address_hash="hash1", user_agent="UA1")
    ScanAnalytics.objects.create(qr_code=qr_a, ip_address_hash="hash1", user_agent="UA1") # Same IP
    ScanAnalytics.objects.create(qr_code=qr_a, ip_address_hash="hash2", user_agent="UA2") # Diff IP
    
    # 2. Verify Summary Stats in QRCodeAdmin (via logic simulation)
    print("\nTesting QRCode Summary Stats:")
    total_a = qr_a.scans.count()
    unique_a = qr_a.scans.values('ip_address_hash').distinct().count()
    print(f"  QR A - Total Scans (Expected 3): {total_a}")
    print(f"  QR A - Unique Visitors (Expected 2): {unique_a}")
    
    if total_a == 3 and unique_a == 2:
        print("  SUCCESS: Summary stats logic is correct.")

    # 3. Verify Admin RBAC
    print("\nTesting ScanAnalyticsAdmin RBAC:")
    from core.admin import ScanAnalyticsAdmin
    from django.contrib.admin.sites import AdminSite
    
    admin_site = AdminSite()
    sa_admin = ScanAnalyticsAdmin(ScanAnalytics, admin_site)
    
    # Mock request
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    # Manager A should only see QR A scans
    req_a = MockRequest(manager_a)
    qs_a = sa_admin.get_queryset(req_a)
    print(f"  Manager A sees logs count: {qs_a.count()}")
    
    all_logs_belong_to_dept_a = all(log.qr_code.department == dept_a for log in qs_a)
    print(f"  All visible logs belong to Dept A: {all_logs_belong_to_dept_a}")
    
    if qs_a.count() == 3 and all_logs_belong_to_dept_a:
        print("  SUCCESS: RBAC filtering is strictly enforced.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_analytics_dashboard()
