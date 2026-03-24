from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from .utils import generate_short_id
import hashlib

def hash_ip(ip_address: str) -> str:
    """
    Hashes an IP address using SHA-256 and a secret salt from settings.
    This ensures GDPR/KVKK compliance by not storing raw PII.
    """
    salt = getattr(settings, 'IP_HASH_SALT', 'default_salt_for_dev')
    return hashlib.sha256(f"{ip_address}{salt}".encode()).hexdigest()

class Department(models.Model):
    """
    Represents an organizational department for strict RBAC.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Departman Adı")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "Departman"
        verbose_name_plural = "Departmanlar"

class CustomUser(AbstractUser):
    """
    Custom User model with department-based access control and specific roles.
    """
    ROLE_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('DEPT_MANAGER', 'Department Manager'),
        ('DEPT_USER', 'Department User'),
    )

    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name="Departman"
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='DEPT_USER',
        verbose_name="Rol"
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"

    def clean(self) -> None:
        super().clean()

        wants_global_access = self.is_superuser or self.role == 'SUPER_ADMIN'
        if not wants_global_access:
            return

        conflict_exists = type(self).objects.exclude(pk=self.pk).filter(
            models.Q(is_superuser=True) | models.Q(role='SUPER_ADMIN')
        ).exists()

        if conflict_exists:
            raise ValidationError(
                "Sistemde yalnızca bir adet tam yetkili Super Admin hesabı tanımlanabilir."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class QRCode(models.Model):
    """
    Dynamic QR Code model with short URL generation and full mutation history.
    """
    short_id = models.CharField(
        max_length=10, 
        primary_key=True, 
        db_index=True, 
        default=generate_short_id,
        editable=False,
        verbose_name="Kısa ID"
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE,
        related_name='qr_codes',
        verbose_name="Departman"
    )
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_qr_codes',
        verbose_name="Oluşturan"
    )
    title = models.CharField(max_length=255, verbose_name="Başlık")
    destination_url = models.URLField(verbose_name="Hedef URL")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    # django-simple-history to track mutations
    history = HistoricalRecords()

    def __str__(self) -> str:
        return f"{self.title} ({self.short_id})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "QR Code"
        verbose_name_plural = "QR Codes"


class ScanAnalytics(models.Model):
    """
    Model for tracking QR code scans with a focus on privacy.
    """
    qr_code = models.ForeignKey(
        QRCode, 
        on_delete=models.CASCADE, 
        related_name='scans',
        verbose_name="QR Kod"
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Zaman")
    
    # GDPR/KVKK Compliance: Store ONLY hashed version of the IP
    ip_address_hash = models.CharField(max_length=64, db_index=True, verbose_name="IP Hash")
    
    user_agent = models.CharField(max_length=512, verbose_name="Tarayıcı Bilgisi")
    
    # Enrichment fields (to be filled by workers/tasks)
    country = models.CharField(max_length=100, null=True, blank=True, verbose_name="Ülke")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="Şehir")
    device_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Cihaz Tipi")

    def __str__(self) -> str:
        return f"Scan for {self.qr_code.short_id} at {self.timestamp}"

    class Meta:
        verbose_name = "Scan Analytics"
        verbose_name_plural = "Scan Analytics"
        ordering = ['-timestamp']
