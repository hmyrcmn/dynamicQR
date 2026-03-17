import os
import django
import uuid
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import Department, CustomUser, QRCode

def verify_setup():
    print("--- Verifying Core Setup ---")
    
    # 1. Create Department
    dept, created = Department.objects.get_or_create(name="IT Department")
    print(f"Department created: {dept} (New: {created})")
    
    # 2. Create Custom User
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    user = CustomUser.objects.create_user(
        username=username,
        email=f"{username}@yee.org.tr",
        password="testpassword123",
        department=dept,
        role='DEPT_MANAGER'
    )
    print(f"Custom user created: {user} with role {user.role}")
    
    # 3. Create QR Code
    qr = QRCode.objects.create(
        department=dept,
        created_by=user,
        title="Main Website",
        destination_url="https://yee.org.tr"
    )
    print(f"QR Code created: {qr}")
    print(f"Generated Short ID: {qr.short_id}")
    
    # 4. Verify History
    qr.destination_url = "https://google.com"
    qr.save()
    history = qr.history.all()
    print(f"History entries: {history.count()}")
    for entry in history:
        print(f"  - Changed at {entry.history_date}: {entry.destination_url}")

    print("--- Verification Complete ---")

if __name__ == "__main__":
    verify_setup()
