from django import forms
from django.conf import settings
from urllib.parse import urlparse
from .models import QRCode

class QRCodeAdminForm(forms.ModelForm):
    """
    Custom form for QRCode Admin with strict domain whitelisting.
    """
    class Meta:
        model = QRCode
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_destination_url(self):
        url = self.cleaned_data.get('destination_url')
        if not url:
            return url

        # 1. SuperAdmins are exempt from domain whitelisting
        if self.request_user and (self.request_user.is_superuser or self.request_user.role == 'SUPER_ADMIN'):
            return url

        # 2. Parse the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if not domain:
            raise forms.ValidationError("Invalid URL format. Hostname is missing.")

        # 3. Check against whitelist
        allowed_domains = getattr(settings, 'ALLOWED_QR_DOMAINS', [])
        
        # Check if the domain itself or any parent domain is whitelisted
        is_authorized = False
        for allowed in allowed_domains:
            allowed = allowed.lower()
            if domain == allowed or domain.endswith(f".{allowed}"):
                is_authorized = True
                break

        if not is_authorized:
            raise forms.ValidationError(
                f"Security Error: The domain '{domain}' is not authorized for redirection. "
                "Only corporate domains (yee.org.tr, gov.tr, etc.) are allowed. "
                "Please contact IT for external domain whitelisting."
            )

        return url
