from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Management
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/create/', views.qr_create_view, name='qr_create'),
    path('dashboard/edit/<str:short_id>/', views.qr_edit_view, name='qr_edit'),
    path('dashboard/delete/<str:short_id>/', views.qr_delete_view, name='qr_delete'),
    path('logout/', views.custom_logout_view, name='custom_logout'),
    
    # Mapping the root-level short IDs to the redirect view
    path('download-qr/<str:short_id>/', views.generate_qr_image_view, name='generate_qr_image'),
    path('<str:short_id>/', views.qr_redirect_view, name='qr_redirect'),
]
