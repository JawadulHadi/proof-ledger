from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('core.api')),
    path('skills/<int:pk>/revise/', views.revise, name='revise'),
    path('app/', views.dashboard_app, name='dashboard_app'),
    path('', views.dashboard, name='dashboard'),
]
