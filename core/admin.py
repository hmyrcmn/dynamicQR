import csv
from django.http import HttpResponse
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin
from .models import Department, CustomUser, QRCode, ScanAnalytics
from .forms import QRCodeAdminForm

# --- Helper Logic ---

def is_super_admin(user) -> bool:
    if not user.is_authenticated:  # Kullanıcı giriş yapmamışsa (Misafirse)
        return False               # Direkt Hayır de, kodu aşağı indirme!
    return user.is_superuser or user.role == 'SUPER_ADMIN'

def is_dept_manager(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.role == 'DEPT_MANAGER'

def is_dept_user(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.role == 'DEPT_USER'


# --- Admin Classes ---

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        if is_super_admin(request.user):
            return qs
        return qs.none()

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_super_admin(request.user)

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_super_admin(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return is_super_admin(request.user)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_super_admin(request.user)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_super_admin(request.user)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom User Admin with department-based isolation.
    """
    list_display = ('username', 'email', 'department', 'role', 'is_staff')
    list_filter = ('role', 'department', 'is_staff')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Kurumsal Yapı', {'fields': ('department', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Kurumsal Yapı', {'fields': ('department', 'role')}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        if is_super_admin(request.user):
            return qs
        return qs.none()

    def has_module_permission(self, request: HttpRequest) -> bool:
        return is_super_admin(request.user)

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_super_admin(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return is_super_admin(request.user)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_super_admin(request.user)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return is_super_admin(request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Restrict department choices for Dept Managers to only their own department.
        """
        if db_field.name == "department" and not is_super_admin(request.user):
            kwargs["queryset"] = Department.objects.filter(id=request.user.department_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(QRCode)
class QRCodeAdmin(SimpleHistoryAdmin):
    """
    QR Code Admin with audit logs, strict department isolation, and statistics.
    """
    form = QRCodeAdminForm
    list_display = (
        'title', 'short_id', 'destination_url', 'department', 
        'total_scans', 'unique_visitors', 'download_qr_button', 'is_active'
    )
    readonly_fields = ('short_id', 'created_at', 'updated_at', 'created_by', 'download_qr_button', 'total_scans', 'unique_visitors')

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        if is_super_admin(request.user):
            return qs
        # Both DEPT_MANAGER and DEPT_USER can only see QRCodes for their department
        if request.user.department:
            return qs.filter(department=request.user.department)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        """
        Formu oluşturur ve request.user (Kullanıcı) bilgisini forma güvenli bir şekilde aktarır.
        """
        Form = super().get_form(request, obj, **kwargs)
        
        # Formu dinamik olarak sarıyoruz (Wrapper) ki request.user'ı içine fırlatabilelim.
        class FormWithUser(Form):
            def __init__(self, *args, **kwargs):
                kwargs['user'] = request.user
                super().__init__(*args, **kwargs)
                
            # Eğer işlemi yapan Süper Admin değilse, departmanı otomatik seç ve kilitli tut
            def __new__(cls, *args, **kwargs):
                instance = super(FormWithUser, cls).__new__(cls)
                return instance

        if not is_super_admin(request.user):
            if not obj and request.user.department:
                # Yeni kayıtta departmanı formda otomatik doldur
                kwargs['initial'] = {'department': request.user.department}

        return FormWithUser
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Restrict department choices for non-supervisors.
        """
        if db_field.name == "department" and not is_super_admin(request.user):
            kwargs["queryset"] = Department.objects.filter(id=request.user.department_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def download_qr_button(self, obj):
        """
        Returns a download button for the QR code image.
        """
        if obj.pk:
            url = reverse('generate_qr_image', args=[obj.short_id])
            return format_html(
                '<a class="button" href="{}" style="background-color: #264b5d; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">QR İndir</a>',
                url
            )
        return "Oluşturunca hazır olur"
    
    download_qr_button.short_description = "QR Kod Dosyası"

    def total_scans(self, obj):
        return obj.scans.count()
    total_scans.short_description = "Toplam Tarama"

    def unique_visitors(self, obj):
        return obj.scans.values('ip_address_hash').distinct().count()
    unique_visitors.short_description = "Tekil Ziyaretçi"

    def save_model(self, request: HttpRequest, obj: QRCode, form, change: bool) -> None:
        """
        Automatically set metadata on save.
        """
        if not change:  # On creation
            obj.created_by = request.user
            # Double check department assignment for non-super-admins
            if not is_super_admin(request.user):
                obj.department = request.user.department
        super().save_model(request, obj, form, change)


@admin.register(ScanAnalytics)
class ScanAnalyticsAdmin(admin.ModelAdmin):
    """
    Read-only Analytics Dashboard with strict department isolation.
    """
    list_display = ('qr_code', 'ip_address_hash', 'timestamp', 'user_agent')
    list_filter = ('qr_code__department', 'timestamp')
    search_fields = ('qr_code__title', 'qr_code__short_id', 'ip_address_hash')
    date_hierarchy = 'timestamp'
    actions = ['export_to_csv']

    def export_to_csv(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        """
        Exports selected scan logs to a CSV file.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="yee_scan_analytics.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['QR Code Title', 'Short ID', 'IP Hash', 'User Agent', 'Timestamp'])
        
        for scan in queryset:
            writer.writerow([
                scan.qr_code.title,
                scan.qr_code.short_id,
                scan.ip_address_hash,
                scan.user_agent,
                scan.timestamp
            ])
            
        return response
    
    export_to_csv.short_description = "Seçili Kayıtları CSV Olarak Dışa Aktar"

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request).select_related('qr_code', 'qr_code__department')
        if is_super_admin(request.user):
            return qs
        # DEPT_MANAGER and DEPT_USER can only see analytics for their department's QRCodes
        if request.user.department:
            return qs.filter(qr_code__department=request.user.department)
        return qs.none()

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
