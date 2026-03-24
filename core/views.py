import qrcode
import io
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Count
from django.urls import reverse
from urllib.parse import urlencode, urlparse
from .models import QRCode, ScanAnalytics, hash_ip
from .forms import QRCodeFrontendForm


def user_has_global_access(user) -> bool:
    return user.is_authenticated and (user.is_superuser or user.role == 'SUPER_ADMIN')


def get_accessible_qr_codes(user):
    base_queryset = QRCode.objects.select_related('department', 'created_by')

    if not user.is_authenticated:
        return base_queryset.none()

    if user_has_global_access(user):
        return base_queryset

    if user.department_id:
        return base_queryset.filter(department_id=user.department_id)

    return base_queryset.none()


def build_dashboard_url(active_selected: bool = False, scanned_selected: bool = False) -> str:
    params = {}
    if active_selected:
        params['active'] = '1'
    if scanned_selected:
        params['scanned'] = '1'

    base_url = reverse('dashboard')
    if not params:
        return base_url
    return f"{base_url}?{urlencode(params)}"

def landing_page_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the public-facing "Apple Glass" landing page.
    """
    return render(request, 'landing.html')

def custom_logout_view(request: HttpRequest) -> HttpResponse:
    """
    Logs the user out and redirects to the landing page.
    """
    logout(request)
    return redirect('landing')

def custom_404_view(request: HttpRequest, exception=None) -> HttpResponse:
    """
    Renders a branded 404 error page.
    """
    return render(request, '404.html', status=404)

def qr_redirect_view(request: HttpRequest, short_id: str) -> HttpResponse:
    """
    Synchronous redirection engine (YAGNI simplification).
    1. Look up QR code in DB.
    2. Save scan analytics synchronously.
    3. Return 302 Redirect.
    """
    # 1. Look up QR code
    qr_code = get_object_or_404(QRCode, short_id=short_id, is_active=True)
    destination_url = qr_code.destination_url
    
    # 2. Infinite Loop Protection
    current_host = request.get_host()
    parsed_destination = urlparse(destination_url)
    
    if parsed_destination.netloc == current_host:
        return HttpResponseBadRequest("Recursive redirection detected.")

    # 3. Process Analytics Synchronously
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    user_agent = request.META.get('HTTP_USER_AGENT', '')
    hashed_ip = hash_ip(ip_address)

    # Save to database
    ScanAnalytics.objects.create(
        qr_code=qr_code,
        ip_address_hash=hashed_ip,
        user_agent=user_agent
    )

    # 4. Fast Redirect
    return HttpResponseRedirect(destination_url)


@login_required
def generate_qr_image_view(request: HttpRequest, short_id: str) -> HttpResponse:
    """
    Generates a high-resolution QR code image for a given short URL.
    Returns the image as a downloadable attachment.
    """
    # 1. Ensure QR code exists and is active
    qr_code = get_object_or_404(
        get_accessible_qr_codes(request.user).filter(is_active=True),
        short_id=short_id,
    )
    
    # 2. Build the absolute redirection URL
    full_url = request.build_absolute_uri(f"/{short_id}/")
    
    # 3. Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(full_url)
    qr.make(fit=True)

    # 4. Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 5. Save image to memory buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    # 6. Return response as downloadable PNG
    response = HttpResponse(buffer.read(), content_type="image/png")
    
    if request.GET.get('inline') == '1':
        response['Content-Disposition'] = f'inline; filename="qr_{short_id}.png"'
    else:
        response['Content-Disposition'] = f'attachment; filename="qr_{short_id}.png"'
    
    return response

@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Bespoke "Apple Glass" dashboard for staff members.
    Shows department-specific QR codes and analytics.
    """
    user = request.user
    
    base_qr_codes = get_accessible_qr_codes(user)

    base_qr_codes = base_qr_codes.annotate(scan_count=Count('scans'))
    active_filter_selected = request.GET.get('active') == '1'
    scanned_filter_selected = request.GET.get('scanned') == '1'

    qr_codes = base_qr_codes
    if active_filter_selected:
        qr_codes = qr_codes.filter(is_active=True)
    if scanned_filter_selected:
        qr_codes = qr_codes.filter(scan_count__gt=0)

    if active_filter_selected and scanned_filter_selected:
        qr_codes = qr_codes.order_by('-scan_count', '-created_at')
        filter_title = "Aktif ve taranan kayıtlar"
        filter_description = "Yalnızca aktif olan ve en az bir kez taranan bağlantılar listeleniyor."
    elif active_filter_selected:
        qr_codes = qr_codes.order_by('-created_at')
        filter_title = "Aktif kayıtlar"
        filter_description = "Yalnızca aktif bağlantılar listeleniyor."
    elif scanned_filter_selected:
        qr_codes = qr_codes.order_by('-scan_count', '-created_at')
        filter_title = "Taranan kayıtlar"
        filter_description = "En az bir kez taranan bağlantılar öne çıkarılıyor."
    else:
        qr_codes = qr_codes.order_by('-created_at')
        filter_title = "Tüm kayıtlar"
        filter_description = "Tüm bağlantılar, hedef adresler ve işlem araçları tek tabloda listelenir."

    # Calculate statistics
    all_qr_count = base_qr_codes.count()
    total_qr_count = base_qr_codes.filter(is_active=True).count()
    total_scans = ScanAnalytics.objects.filter(qr_code__in=base_qr_codes).count()
    
    context = {
        'qr_codes': qr_codes,
        'all_qr_count': all_qr_count,
        'filtered_qr_count': qr_codes.count(),
        'total_qr_count': total_qr_count,
        'total_scans': total_scans,
        'filter_title': filter_title,
        'filter_description': filter_description,
        'active_filter_selected': active_filter_selected,
        'scanned_filter_selected': scanned_filter_selected,
        'filters_active': active_filter_selected or scanned_filter_selected,
        'active_filter_url': build_dashboard_url(not active_filter_selected, scanned_filter_selected),
        'scanned_filter_url': build_dashboard_url(active_filter_selected, not scanned_filter_selected),
        'reset_filter_url': build_dashboard_url(False, False),
        'department_name': "Tüm Birimler" if user_has_global_access(user) else user.department.name if user.department else "Genel Müdürlük",
    }
    return render(request, 'dashboard.html', context)

@login_required
def qr_create_view(request: HttpRequest) -> HttpResponse:
    """
    View for creating a new QR code via the frontend portal.
    """
    if request.method == 'POST':
        form = QRCodeFrontendForm(request.POST, user=request.user)
        if form.is_valid():
            qr_code = form.save(commit=False)
            qr_code.created_by = request.user
            department = request.user.department

            if not department:
                return HttpResponseBadRequest(
                    "Uyarı: QR kod oluşturabilmek için LDAP üzerinden bir birime atanmış olmalısınız."
                )

            qr_code.department = department
            qr_code.save()
            return redirect('dashboard')
    else:
        form = QRCodeFrontendForm(user=request.user)
    
    return render(request, 'qr_create.html', {'form': form})

@login_required
def qr_edit_view(request: HttpRequest, short_id: str) -> HttpResponse:
    """
    View for editing an existing QR code. 
    Enforces RBAC so users can only edit QR codes belonging to their department.
    """
    qr_code = get_object_or_404(get_accessible_qr_codes(request.user), short_id=short_id)

    if request.method == 'POST':
        form = QRCodeFrontendForm(request.POST, instance=qr_code, user=request.user)
        if form.is_valid():
            updated_qr_code = form.save(commit=False)
            if not user_has_global_access(request.user):
                updated_qr_code.department = request.user.department
            updated_qr_code.save()
            return redirect('dashboard')
    else:
        form = QRCodeFrontendForm(instance=qr_code, user=request.user)

    return render(request, 'qr_edit.html', {'form': form, 'qr_code': qr_code, 'object': qr_code})

@login_required
def qr_delete_view(request: HttpRequest, short_id: str) -> HttpResponse:
    """
    View for permanently deleting a QR code.
    Enforces RBAC so users can only delete QR codes belonging to their department.
    """
    qr_code = get_object_or_404(get_accessible_qr_codes(request.user), short_id=short_id)

    if request.method == 'POST':
        qr_code.delete()
        return redirect('dashboard')

    return render(request, 'qr_confirm_delete.html', {'qr_code': qr_code, 'object': qr_code})
