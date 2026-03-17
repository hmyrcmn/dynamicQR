import qrcode
import io
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Count, Sum
from urllib.parse import urlparse
from .models import QRCode, ScanAnalytics, hash_ip
from .forms import QRCodeFrontendForm

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


def generate_qr_image_view(request: HttpRequest, short_id: str) -> HttpResponse:
    """
    Generates a high-resolution QR code image for a given short URL.
    Returns the image as a downloadable attachment.
    """
    # 1. Ensure QR code exists and is active
    qr_code = get_object_or_404(QRCode, short_id=short_id, is_active=True)
    
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
    response['Content-Disposition'] = f'attachment; filename="qr_{short_id}.png"'
    
    return response

@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Bespoke "Apple Glass" dashboard for staff members.
    Shows department-specific QR codes and analytics.
    """
    user = request.user
    
    # Filter based on department (RBAC)
    if user.is_superuser or user.role == 'SUPER_ADMIN':
        qr_codes = QRCode.objects.all().order_by('-created_at')
    elif user.department:
        qr_codes = QRCode.objects.filter(department=user.department).order_by('-created_at')
    else:
        qr_codes = QRCode.objects.none()

    # Calculate statistics
    total_qr_count = qr_codes.count()
    total_scans = ScanAnalytics.objects.filter(qr_code__in=qr_codes).count()
    
    context = {
        'qr_codes': qr_codes,
        'total_qr_count': total_qr_count,
        'total_scans': total_scans,
        'department_name': user.department.name if user.department else "Genel Müdürlük",
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
            qr_code.department = request.user.department
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
    qr_code = get_object_or_404(QRCode, short_id=short_id)
    user = request.user

    # Strict RBAC Check
    if not user.is_superuser and user.role != 'SUPER_ADMIN':
        if qr_code.department != user.department:
            return HttpResponseBadRequest("Security Error: Insufficient permissions to edit this QR Code.")

    if request.method == 'POST':
        form = QRCodeFrontendForm(request.POST, instance=qr_code, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = QRCodeFrontendForm(instance=qr_code, user=request.user)
    
    return render(request, 'qr_edit.html', {'form': form, 'qr_code': qr_code})

@login_required
def qr_delete_view(request: HttpRequest, short_id: str) -> HttpResponse:
    """
    View for permanently deleting a QR code.
    Enforces RBAC so users can only delete QR codes belonging to their department.
    """
    qr_code = get_object_or_404(QRCode, short_id=short_id)
    user = request.user

    # Strict RBAC Check
    if not user.is_superuser and user.role != 'SUPER_ADMIN':
        if qr_code.department != user.department:
            return HttpResponseBadRequest("Security Error: Insufficient permissions to delete this QR Code.")

    if request.method == 'POST':
        qr_code.delete()
        return redirect('dashboard')
        
    return render(request, 'qr_confirm_delete.html', {'qr_code': qr_code})
