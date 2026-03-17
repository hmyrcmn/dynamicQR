import os
import django
from django.test import RequestFactory
from django.forms import ValidationError

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import Department, CustomUser, QRCode
from core.forms import QRCodeAdminForm

def verify_whitelisting():
    print("--- Verifying Domain Whitelisting (Security Guard) ---")
    
    # 1. Setup Test Data
    dept, _ = Department.objects.get_or_create(name="Security Dept")
    
    super_admin, _ = CustomUser.objects.get_or_create(
        username='sec_admin',
        defaults={'email': 'sec@yee.org.tr', 'role': 'SUPER_ADMIN', 'is_staff': True, 'is_superuser': True}
    )
    if not super_admin.check_password('pass'):
        super_admin.set_password('pass')
        super_admin.save()
    
    dept_user, _ = CustomUser.objects.get_or_create(
        username="sec_user",
        defaults={'department': dept, 'role': 'DEPT_USER'}
    )

    # 2. Test SuperAdmin Bypass
    print("\nTesting SuperAdmin Bypass:")
    form_super = QRCodeAdminForm(
        data={'title': 'Evil Link', 'destination_url': 'https://evil.com', 'department': dept.id},
        user=super_admin
    )
    is_valid_super = form_super.is_valid()
    print(f"  SuperAdmin can save evil.com: {is_valid_super}")
    if not is_valid_super:
        print(f"  Errors: {form_super.errors}")

    # 3. Test Regular User Blocking
    print("\nTesting Regular User Blocking:")
    form_user_evil = QRCodeAdminForm(
        data={'title': 'Evil Link', 'destination_url': 'https://malicious-site.com', 'department': dept.id},
        user=dept_user
    )
    is_valid_user_evil = form_user_evil.is_valid()
    print(f"  Regular user can save malicious-site.com: {is_valid_user_evil}")
    if not is_valid_user_evil:
        print(f"  Validation Error (Expected): {form_user_evil.errors['destination_url'][0]}")

    # 4. Test Whitelisted Domain (Exact)
    print("\nTesting Whitelisted Domain (Exact):")
    form_user_ok = QRCodeAdminForm(
        data={'title': 'Official Link', 'destination_url': 'https://yee.org.tr/about', 'department': dept.id},
        user=dept_user
    )
    print(f"  Regular user can save yee.org.tr: {form_user_ok.is_valid()}")

    # 5. Test Whitelisted Subdomain
    print("\nTesting Whitelisted Subdomain:")
    form_user_sub = QRCodeAdminForm(
        data={'title': 'Subdomain Link', 'destination_url': 'https://portal.ik.gov.tr/login', 'department': dept.id},
        user=dept_user
    )
    print(f"  Regular user can save sub.gov.tr: {form_user_sub.is_valid()}")

    # 6. Test Invalid URL Format
    print("\nTesting Invalid URL Format:")
    form_invalid = QRCodeAdminForm(
        data={'title': 'Junk', 'destination_url': 'not-a-url', 'department': dept.id},
        user=dept_user
    )
    print(f"  Invalid URL format rejected: {not form_invalid.is_valid()}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_whitelisting()
