from django.urls import path
from .views import RegisterView, LoginView, MeView, Logout_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = 'auth_app'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', MeView.as_view(), name='me'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('AccesTok/', TokenObtainPairView.as_view(), name='access_token'),
    path('logout/', Logout_view.as_view(), name='logout'),
]
