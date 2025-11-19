from django.urls import path
from .views import RegisterView, LoginView, MeView,Logout_view
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path('me/', MeView.as_view()),
    path('refresh/',TokenRefreshView.as_view()),
    path('AccesTok/', TokenObtainPairView.as_view()),
    path("logout/",Logout_view.as_view())
]
