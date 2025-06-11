from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .models import Reservation, Paiement
from rest_framework.views import APIView
from django.db.models import Sum, F
from Auths import permission
from .serializers import ReservationSerializer, ReservationCreateSerializer, HistoriquePaiementSerializer
from decimal import Decimal

class HistoriquePaiementsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        paiements = Paiement.objects.filter(utilisateur=request.user).order_by('-created_at')
        serializer = HistoriquePaiementSerializer(paiements, many=True)
        return Response(serializer.data)

class SoldeHoteView(APIView):
    permission_classes = [permissions.IsAuthenticated, permission.IsVendor]

    def get(self, request):
        user = request.user
        reservations = Reservation.objects.filter(
            annonce_id__owner=user,
            status="completed"
        )

        total_revenus = reservations.aggregate(total=Sum('prix_total'))['total'] or 0
        frais_total = total_revenus * Decimal("0.15")
        solde = total_revenus - frais_total

        return Response({
            "total_revenus": total_revenus,
            "frais_service": frais_total,
            "solde_disponible": solde
        })

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
