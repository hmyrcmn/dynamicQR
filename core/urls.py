from django.urls import path
from . import views

urlpatterns = [
    # Mapping the root-level short IDs to the redirect view
    path('download-qr/<str:short_id>/', views.generate_qr_image_view, name='generate_qr_image'),
    path('<str:short_id>/', views.qr_redirect_view, name='qr_redirect'),
]
