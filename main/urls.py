from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_video, name='upload_video'),
    path('reports/', views.reports_all, name='reports_all'),
    path('reports/in-progress/', views.reports_in_progress, name='reports_in_progress'),
    path('reports/completed/', views.reports_completed, name='reports_completed'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('api/reports/<int:pk>/status/', views.report_status_json, name='report_status_json'),
]


