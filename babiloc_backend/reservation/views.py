from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .models import Reservation
from .serializers import ReservationSerializer, ReservationCreateSerializer

class CreateReservationView(generics.CreateAPIView):
    serializer_class = ReservationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MesReservationsView(generics.ListAPIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

class AllReservationsView(generics.ListAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admin can see all reservations
