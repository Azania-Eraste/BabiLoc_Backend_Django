from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Reservation
from .serializers import (
    ReservationSerializer,
    ReservationCreateSerializer,
    ReservationUpdateSerializer,
    ReservationListSerializer
)

class ReservationPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CreateReservationView(generics.CreateAPIView):
    """
    Créer une nouvelle réservation pour une annonce
    """
    serializer_class = ReservationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Créer une nouvelle réservation",
        responses={
            201: ReservationSerializer,
            400: "Données invalides",
            401: "Non authentifié"
        },
        tags=['Réservations']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Retourner la réservation complète
        reservation = serializer.instance
        response_serializer = ReservationSerializer(reservation)
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

class MesReservationsView(generics.ListAPIView):
    """
    Liste des réservations de l'utilisateur connecté
    """
    serializer_class = ReservationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ReservationPagination
    
    @swagger_auto_schema(
        operation_description="Récupérer mes réservations",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filtrer par statut",
                type=openapi.TYPE_STRING,
                enum=['pending', 'confirmed', 'cancelled', 'completed']
            ),
            openapi.Parameter(
                'annonce_id',
                openapi.IN_QUERY,
                description="Filtrer par ID d'annonce",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: ReservationListSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Réservations']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Reservation.objects.filter(user=self.request.user)
        
        # Filtres optionnels
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        annonce_id = self.request.query_params.get('annonce_id')
        if annonce_id:
            queryset = queryset.filter(annonce_id=annonce_id)
        
        return queryset

class AllReservationsView(generics.ListAPIView):
    """
    Liste de toutes les réservations (pour la modération)
    """
    serializer_class = ReservationListSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = ReservationPagination
    
    @swagger_auto_schema(
        operation_description="Récupérer toutes les réservations (admin)",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filtrer par statut",
                type=openapi.TYPE_STRING,
                enum=['pending', 'confirmed', 'cancelled', 'completed']
            ),
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                description="Filtrer par ID utilisateur",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="Recherche par nom d'utilisateur ou email",
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: ReservationListSerializer(many=True),
            401: "Non authentifié",
            403: "Permission refusée"
        },
        tags=['Administration']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Reservation.objects.all().select_related('user')
        
        # Filtres
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        
        return queryset

class ReservationDetailView(generics.RetrieveUpdateAPIView):
    """
    Détails et mise à jour d'une réservation
    """
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Récupérer les détails d'une réservation",
        responses={
            200: ReservationSerializer,
            401: "Non authentifié",
            403: "Permission refusée",
            404: "Réservation non trouvée"
        },
        tags=['Réservations']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Mettre à jour une réservation",
        request_body=ReservationUpdateSerializer,
        responses={
            200: ReservationSerializer,
            400: "Données invalides",
            401: "Non authentifié",
            403: "Permission refusée",
            404: "Réservation non trouvée"
        },
        tags=['Réservations']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return ReservationUpdateSerializer
        return ReservationSerializer

@swagger_auto_schema(
    method='get',
    operation_description="Statistiques des réservations (admin)",
    responses={
        200: openapi.Response(
            description="Statistiques",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_reservations': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'pending': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'confirmed': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'cancelled': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'completed': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        401: "Non authentifié",
        403: "Permission refusée"
    },
    tags=['Administration']
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def reservation_stats(request):
    """
    Statistiques des réservations pour l'administration
    """
    stats = {
        'total_reservations': Reservation.objects.count(),
        'pending': Reservation.objects.filter(status='pending').count(),
        'confirmed': Reservation.objects.filter(status='confirmed').count(),
        'cancelled': Reservation.objects.filter(status='cancelled').count(),
        'completed': Reservation.objects.filter(status='completed').count(),
    }
    
    return Response(stats)