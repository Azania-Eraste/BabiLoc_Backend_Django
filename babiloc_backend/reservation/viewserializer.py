from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Reservation, Bien, Favori
from .serializers import (
    ReservationSerializer,
    ReservationCreateSerializer,
    ReservationUpdateSerializer,
    ReservationListSerializer,
    BienSerializer,
    MediaSerializer,
    FavoriSerializer,
    FavoriListSerializer
)
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .filters import BienFilter


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
        # Protection contre les appels Swagger sans utilisateur authentifié
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
        if not self.request.user.is_authenticated:
            return Reservation.objects.none()
            
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
        # Protection contre les appels Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
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
        # Protection contre les appels Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
        if not self.request.user.is_authenticated:
            return Reservation.objects.none()
            
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
    data = {
        'total_reservations': Reservation.objects.count(),
        'pending': Reservation.objects.filter(status='pending').count(),
        'confirmed': Reservation.objects.filter(status='confirmed').count(),
        'cancelled': Reservation.objects.filter(status='cancelled').count(),
        'completed': Reservation.objects.filter(status='completed').count(),
    }
    return Response(data)


class BienPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class BienListCreateView(generics.ListCreateAPIView):
    queryset = Bien.objects.all().select_related('type_bien')
    serializer_class = BienSerializer
    pagination_class = BienPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BienFilter
    search_fields = ['nom', 'ville', 'description', 'type_bien__nom']  

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @swagger_auto_schema(
        operation_description="Lister tous les biens ou en créer un nouveau",
        responses={200: BienSerializer(many=True)},
        tags=["Biens"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Créer un bien (admin uniquement)",
        responses={201: BienSerializer, 400: "Données invalides"},
        tags=["Biens"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BienDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bien.objects.all()
    serializer_class = BienSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @swagger_auto_schema(
        operation_description="Récupérer les détails d’un bien",
        responses={200: BienSerializer, 404: "Bien non trouvé"},
        tags=["Biens"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Mettre à jour un bien",
        responses={200: BienSerializer, 400: "Données invalides"},
        tags=["Biens"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Supprimer un bien",
        responses={204: "Supprimé"},
        tags=["Biens"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

class MediaCreateView(generics.CreateAPIView):
    serializer_class = MediaSerializer
    permission_classes = [permissions.IsAdminUser]


class FavoriPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AjouterFavoriView(generics.CreateAPIView):
    """
    Ajouter un bien aux favoris
    """
    serializer_class = FavoriSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Ajouter un bien aux favoris",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'bien_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID du bien à ajouter')
            },
            required=['bien_id']
        ),
        responses={
            201: FavoriSerializer,
            400: "Données invalides ou bien déjà en favoris",
            401: "Non authentifié",
            404: "Bien non trouvé"
        },
        tags=['Favoris']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MesFavorisView(generics.ListAPIView):
    """
    Liste des favoris de l'utilisateur connecté
    """
    serializer_class = FavoriListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FavoriPagination
    
    @swagger_auto_schema(
        operation_description="Récupérer mes favoris",
        responses={
            200: FavoriListSerializer(many=True),
            401: "Non authentifié"
        },
        tags=['Favoris']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        # Protection contre les appels Swagger sans utilisateur authentifié
        if getattr(self, 'swagger_fake_view', False):
            return Favori.objects.none()
        
        if not self.request.user.is_authenticated:
            return Favori.objects.none()
            
        return Favori.objects.filter(user=self.request.user).select_related('bien')


class RetirerFavoriView(generics.DestroyAPIView):
    """
    Retirer un bien des favoris
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Retirer un bien des favoris",
        responses={
            204: "Favori supprimé",
            401: "Non authentifié",
            404: "Favori non trouvé"
        },
        tags=['Favoris']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
    
    def get_queryset(self):
        # Protection contre les appels Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Favori.objects.none()
        
        if not self.request.user.is_authenticated:
            return Favori.objects.none()
            
        return Favori.objects.filter(user=self.request.user)


@swagger_auto_schema(
    method='post',
    operation_description="Basculer un bien en favori (ajouter ou retirer)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'bien_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID du bien')
        },
        required=['bien_id']
    ),
    responses={
        200: openapi.Response(
            description="Résultat de l'opération",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'action': openapi.Schema(type=openapi.TYPE_STRING, enum=['added', 'removed']),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'favori': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'bien_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        400: "Données invalides",
        401: "Non authentifié",
        404: "Bien non trouvé"
    },
    tags=['Favoris']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_favori(request):
    """
    Basculer un bien en favori : l'ajouter s'il n'y est pas, le retirer s'il y est
    """
    bien_id = request.data.get('bien_id')
    
    if not bien_id:
        return Response({'error': 'bien_id requis'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        bien = Bien.objects.get(id=bien_id)
    except Bien.DoesNotExist:
        return Response({'error': 'Bien non trouvé'}, status=status.HTTP_404_NOT_FOUND)
    
    # Vérifier si le favori existe
    favori = Favori.objects.filter(user=request.user, bien=bien).first()
    
    if favori:
        # Retirer des favoris
        favori.delete()
        return Response({
            'action': 'removed',
            'message': 'Bien retiré des favoris'
        }, status=status.HTTP_200_OK)
    else:
        # Ajouter aux favoris
        favori = Favori.objects.create(user=request.user, bien=bien)
        serializer = FavoriSerializer(favori)
        return Response({
            'action': 'added',
            'message': 'Bien ajouté aux favoris',
            'favori': serializer.data
        }, status=status.HTTP_200_OK)

