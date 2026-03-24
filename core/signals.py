import os
from django.dispatch import receiver
import logging

try:
    from django_auth_ldap.backend import populate_user
    ldap_available = True
except ImportError:
    # Dummy signal if python-ldap is missing
    from django.dispatch import Signal
    populate_user = Signal()
    ldap_available = False

logger = logging.getLogger(__name__)
LDAP_SUPER_ADMIN_USERNAME = os.getenv('LDAP_SUPER_ADMIN_USERNAME', '').strip().lower()

@receiver(populate_user)
def map_ldap_user_to_department(sender, user, ldap_user, **kwargs):
    """
    Signal receiver triggered when a user logs in via LDAP.
    We intercept this to extract their Active Directory 'department' attribute
    and automatically assign them to a local Django Department model.
    """
    if not ldap_available:
        return
        
    from .models import Department

    try:
        # Many AD setups use 'department', 'company', or 'physicalDeliveryOfficeName'
        # Adjust this key based on the actual AD structure.
        ad_dept_name_list = ldap_user.attrs.get('department')
        
        if ad_dept_name_list and len(ad_dept_name_list) > 0:
            # AD attributes are returned as lists of bytes
            dept_name = ad_dept_name_list[0].decode('utf-8').strip()
            
            # Find or create the department in our local DB
            department, created = Department.objects.get_or_create(
                name=dept_name
            )
            
            # Auto-assign the user to this department
            dirty_fields = []
            if user.department_id != department.id:
                user.department = department
                dirty_fields.append('department')

            if not user.is_staff:
                user.is_staff = True
                dirty_fields.append('is_staff')

            # If role was never assigned, default to the scoped department role
            if not user.role:
                user.role = 'DEPT_USER'
                dirty_fields.append('role')

            if LDAP_SUPER_ADMIN_USERNAME and user.username.lower() == LDAP_SUPER_ADMIN_USERNAME:
                if user.role != 'SUPER_ADMIN':
                    user.role = 'SUPER_ADMIN'
                    dirty_fields.append('role')
                if not user.is_superuser:
                    user.is_superuser = True
                    dirty_fields.append('is_superuser')

            if dirty_fields:
                user.save(update_fields=dirty_fields)

            logger.info(f"Automatically mapped LDAP user {user.username} to department {dept_name}")
            
    except Exception as e:
        logger.error(f"Error mapping LDAP department for user {user.username}: {e}")
