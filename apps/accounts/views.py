from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.accounts.serializers import RegisterSerializer


class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
