from django.urls import path

from . import views

app_name = 'accounts'
urlpatterns = [
    path('', views.gate, name='gate'),
    path('setup', views.access, {'mode': 'setup'}, name='setup'),
    path('login', views.access, {'mode': 'login'}, name='login'),
    path('register', views.access, {'mode': 'register'}, name='register'),
    path('logout', views.browser_logout, name='logout'),
    path('api/security/csrf', views.csrf, name='csrf'),
    path('__gravewright/csrf', views.csrf),
    path('api/auth/status', views.status, name='status'),
    path('api/auth/session', views.session, name='session'),
    path('api/auth/setup', views.api_access, {'mode': 'setup'}),
    path('api/auth/register', views.api_access, {'mode': 'register'}),
    path('api/auth/login', views.api_access, {'mode': 'login'}),
    path('api/auth/logout', views.api_logout),
    path('api/auth/account', views.account),
    path('api/home/<str:kind>', views.home, name='home'),
]
