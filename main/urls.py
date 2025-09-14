from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public routes
    path('', views.home, name='home'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Protected routes (dashboard and reports)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_video, name='upload_video'),
    path('reports/', views.reports_all, name='reports_all'),
    path('reports/in-progress/', views.reports_in_progress, name='reports_in_progress'),
    path('reports/completed/', views.reports_completed, name='reports_completed'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('reports/<int:pk>/professional/', views.professional_report, name='professional_report'),
    path('reports/<int:pk>/pdf/', views.report_pdf, name='report_pdf'),
    path('api/reports/<int:pk>/status/', views.report_status_json, name='report_status_json'),
    path('api/reports/<int:pk>/update/', views.update_report, name='update_report'),
    
    # XRPL Digital Signature URLs
    path('setup-wallet/', views.setup_wallet, name='setup_wallet'),
    path('wallet-dashboard/', views.wallet_dashboard, name='wallet_dashboard'),
    path('reports/<int:pk>/sign/', views.sign_report, name='sign_report'),
    path('reports/<int:pk>/verify/', views.verify_signature, name='verify_signature'),
    path('api/reports/<int:pk>/signature-status/', views.signature_status_api, name='signature_status_api'),
]


