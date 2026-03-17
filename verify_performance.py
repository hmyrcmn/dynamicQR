import os
import django
from django.core.cache import cache
from django.test import Client, override_settings
from unittest.mock import patch

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_project.settings')
django.setup()

from core.models import QRCode, Department

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
def verify_performance():
    print("--- Verifying Performance Refactor (Cache & Celery) ---")
    
    # 1. Setup Test Data
    dept, _ = Department.objects.get_or_create(name="Perf Test Dept")
    qr = QRCode.objects.create(
        department=dept,
        title="Perf QR",
        destination_url="https://example.com"
    )
    cache_key = f"qr_cache:{qr.short_id}"
    cache.delete(cache_key) # Clear initial cache

    client = Client()

    # 2. Test Cache Population (First Request)
    print("\nTesting Cache Population (First Hit):")
    with patch('core.tasks.process_scan_analytics.delay') as mock_task:
        response = client.get(f"/{qr.short_id}/")
        cached_url = cache.get(cache_key)
        print(f"  Response Status: {response.status_code}")
        print(f"  URL in Cache: {cached_url}")
        print(f"  Celery Task Dispatched: {mock_task.called}")
        if cached_url == qr.destination_url and mock_task.called:
            print("  SUCCESS: Cache populated and task dispatched.")

    # 3. Test Cache Hits (Second Request)
    print("\nTesting Cache Hit (Second Request):")
    # Even if we change the DB value, the cache should persist until invalidated
    QRCode.objects.filter(short_id=qr.short_id).update(destination_url="https://wrong.com")
    
    response2 = client.get(f"/{qr.short_id}/")
    redirect_url2 = response2.get('Location') or response2.get('location')
    print(f"  Redirected to (should be cached original): {redirect_url2}")
    if redirect_url2 == "https://example.com":
        print("  SUCCESS: Redirection served from Cache.")

    # 4. Test Cache Invalidation
    print("\nTesting Cache Invalidation:")
    qr.destination_url = "https://new-destination.com"
    qr.save() # This should trigger cache.delete()
    
    cached_after_save = cache.get(cache_key)
    print(f"  Cache after save: {cached_after_save} (Expected: None)")
    
    response3 = client.get(f"/{qr.short_id}/")
    redirect_url3 = response3.get('Location') or response3.get('location')
    print(f"  Redirected to (after invalidation): {redirect_url3}")
    if cached_after_save is None and redirect_url3 == "https://new-destination.com":
        print("  SUCCESS: Cache invalidated and repopulated correctly.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_performance()
