from django.dispatch import receiver
from django.db.models.signals import post_save
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
                name=dept_name,
                defaults={'description': f'Auto-created from Active Directory login'}
            )
            
            # Auto-assign the user to this department
            user.department = department
            
            # Set default role to standard user if they don't have one
            if not user.role:
                user.role = 'DEPT_USER'
                
            logger.info(f"Automatically mapped LDAP user {user.username} to department {dept_name}")
            
    except Exception as e:
        logger.error(f"Error mapping LDAP department for user {user.username}: {e}")
