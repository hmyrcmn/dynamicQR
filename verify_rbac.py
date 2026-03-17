import os
import django
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import Department, CustomUser, QRCode
from core.admin import DepartmentAdmin, CustomUserAdmin, QRCodeAdmin

def verify_rbac():
    print("--- Verifying Admin RBAC Logic ---")
    
    # Setup data
    dept1, _ = Department.objects.get_or_create(name="IT")
    dept2, _ = Department.objects.get_or_create(name="Marketing")
    
    super_admin = CustomUser.objects.filter(is_superuser=True).first()
    if not super_admin:
        super_admin = CustomUser.objects.create_superuser('admin', 'admin@yee.org.tr', 'pass')
    
    manager1 = CustomUser.objects.create_user(
        username="manager1", department=dept1, role='DEPT_MANAGER', is_staff=True
    )
    user1 = CustomUser.objects.create_user(
        username="user1", department=dept1, role='DEPT_USER', is_staff=True
    )
    
    QRCode.objects.create(department=dept1, title="QR1", destination_url="http://a.com")
    QRCode.objects.create(department=dept2, title="QR2", destination_url="http://b.com")

    site = AdminSite()
    rf = RequestFactory()

    # 1. Test DepartmentAdmin.get_queryset
    print("\nTesting DepartmentAdmin.get_queryset:")
    admin_dept = DepartmentAdmin(Department, site)
    
    req_super = rf.get('/')
    req_super.user = super_admin
    print(f"  SuperAdmin count: {admin_dept.get_queryset(req_super).count()}") # Should be all
    
    req_manager = rf.get('/')
    req_manager.user = manager1
    print(f"  Manager1 count: {admin_dept.get_queryset(req_manager).count()}") # Should be 1 (dept1)
    
    # 2. Test CustomUserAdmin.has_module_permission
    print("\nTesting CustomUserAdmin permissions:")
    admin_user = CustomUserAdmin(CustomUser, site)
    
    print(f"  SuperAdmin can see User module: {admin_user.has_module_permission(req_super)}")
    print(f"  Manager1 can see User module: {admin_user.has_module_permission(req_manager)}")
    
    req_user = rf.get('/')
    req_user.user = user1
    print(f"  User1 can see User module: {admin_user.has_module_permission(req_user)}") # Should be False

    # 3. Test QRCodeAdmin.get_queryset
    print("\nTesting QRCodeAdmin.get_queryset:")
    admin_qr = QRCodeAdmin(QRCode, site)
    
    print(f"  SuperAdmin QR count: {admin_qr.get_queryset(req_super).count()}") # Should be all (2)
    print(f"  Manager1 QR count: {admin_qr.get_queryset(req_manager).count()}") # Should be 1 (dept1)
    print(f"  User1 QR count: {admin_qr.get_queryset(req_user).count()}") # Should be 1 (dept1)

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_rbac()
