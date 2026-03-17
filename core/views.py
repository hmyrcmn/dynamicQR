import qrcode
import io
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpRequest, HttpResponse
from urllib.parse import urlparse
from .models import QRCode, ScanAnalytics, hash_ip

def landing_page_view(request: HttpRequest) -> HttpResponse:
    """
    Renders the public-facing "Apple Glass" landing page.
    """
    return render(request, 'landing.html')

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
