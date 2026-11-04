"""
URL configuration for server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.vacancy_list, name='vacancy_list'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.update_profile, name='update_profile'),
    path('users/<str:username>/', views.public_profile, name='public_profile'),
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('vacancies/new/', views.vacancy_form, name='vacancy_create'),
    path('vacancies/<int:pk>/', views.vacancy_detail, name='vacancy_detail'),
    path('vacancies/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('vacancies/<int:pk>/edit/', views.vacancy_update, name='vacancy_update'),
    path('vacancies/<int:pk>/delete/', views.vacancy_delete, name='vacancy_delete'),
    path('vacancies/<int:vacancy_id>/apply/', views.application_create, name='application_create'),
    path('applications/', views.application_list, name='application_list'),
    path('my-vacancies/applications/', views.request_to_my_vacancy, name='my_vacancy_applications'),
    path('applications/<int:pk>/edit/', views.application_update, name='application_update'),
    path('applications/<int:pk>/delete/', views.application_delete, name='application_delete'),
    path('assistant/', views.send_message_to_ai, name='ai_assistant'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
