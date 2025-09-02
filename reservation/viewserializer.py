from rest_framework import generics, permissions, status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from Auths import permission
from rest_framework import serializers
from django.db.models import Count, Avg
from .models import Reservation,TagBien, Ville,Bien, HistoriqueStatutReservation, Favori, Tarif, Avis, Type_Bien, Document, Typetarif
from .serializers import (
    ReservationSerializer,
    ReservationCreateSerializer,
    ReservationUpdateSerializer,
    ReservationListSerializer,
    BienSerializer,
    MediaSerializer,
    FavoriSerializer,
    FavoriListSerializer,
    TarifSerializer,
    AvisSerializer, AvisCreateSerializer, 
    ReponseProprietaireSerializer, StatistiquesAvisSerializer,
    TypeBienSerializer,
    DocumentSerializer,
    VilleSerializer,
    TagBienSerializer
)
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .filters import BienFilter
from django.contrib.auth.models import AnonymousUser
import logging
from django.utils import timezone  # <-- ajout
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
# FIX: missing DRF and Django imports
from rest_framework.pagination import PageNumberPagination  # <-- ajout
from rest_framework.response import Response  # <-- ajout
from rest_framework.decorators import api_view, permission_classes  # <-- ajout
from django.db.models import Q
from django.shortcuts import get_object_or_404  # <-- ajout
from rest_framework.exceptions import PermissionDenied  # <-- ajout

logger = logging.getLogger(__name__)

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
    
    def validate(self, data):
        bien = data.get('bien')
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')

        if date_debut > date_fin:
            raise serializers.ValidationError("La date de début doit être avant la date de fin.")

        # Vérifie le chevauchement
        conflits = Reservation.objects.filter(
            bien=bien,
            date_debut__lte=date_fin,
            date_fin__gte=date_debut
        )
        if conflits.exists():
            raise serializers.ValidationError("Ce bien est déjà réservé pendant cette période.")

        return data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        reservation = serializer.instance
        response_serializer = ReservationSerializer(reservation)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class MesReservationsHostView(generics.ListAPIView):

    serializer_class = ReservationListSerializer
    permission_classes = [permission.IsVendor]
    pagination_class = ReservationPagination

    def get_queryset(self):

        # Protection contre les appels Swagger sans utilisateur authentifié
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()
        
        if not self.request.user.is_authenticated and not self.request.user.is_vendor:
            return Reservation.objects.none()

        queryset = Reservation.objects.filter(bien__owner=self.request.user)

        return queryset


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
                'bien',  # Changer annonce_id en bien_id
                openapi.IN_QUERY,
                description="Filtrer par ID du bien",
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
        
        # Changer annonce_id en bien_id
        bien_id = self.request.query_params.get('bien_id')
        if bien_id:
            queryset = queryset.filter(bien=bien_id)
        
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
def reservations_stats(request):
    data = {
        'total_reservations': Reservation.objects.count(),
        'pending': Reservation.objects.filter(status='pending').count(),
        'confirmed': Reservation.objects.filter(status='confirmed').count(),
        'cancelled': Reservation.objects.filter(status='cancelled').count(),
        'completed': Reservation.objects.filter(status='completed').count(),
    }
    return Response(data)


@swagger_auto_schema(
    method='get',
    operation_summary="Historique des statuts des réservations d’un bien",
    operation_description="""
    Retourne combien de fois chaque statut (ex: pending, confirmed, cancelled...) 
    a été enregistré pour les réservations liées à un bien spécifique.
    """,
    manual_parameters=[
        openapi.Parameter(
            'bien_id',
            openapi.IN_PATH,
            description="ID du bien",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Statuts historiques des réservations du bien",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                additional_properties=openapi.Schema(type=openapi.TYPE_INTEGER),
                example={
                    "pending": 3,
                    "confirmed": 5,
                    "cancelled": 1
                }
            )
        ),
        404: openapi.Response(description="Bien non trouvé ou non autorisé"),
        401: "Non authentifié",
        403: "Permission refusée"
    },
    tags=['Réservations']
)
@api_view(['GET'])
@permission_classes([permission.IsVendor])  # ou IsVendor si tu as une permission custom
def historique_statuts_reservations_bien(request, bien_id):
    try:
        user = request.user
        bien = Bien.objects.get(id=bien_id, owner=user)
    except Bien.DoesNotExist:
        return Response({"detail": "Bien non trouvé ou accès interdit"}, status=404)

    stats = (
        HistoriqueStatutReservation.objects
        .filter(reservation__bien=bien)  # Changer annonce_id en bien
        .values('nouveau_statut')
        .annotate(compte=Count('id'))
    )

    result = {item['nouveau_statut']: item['compte'] for item in stats}
    return Response(result)

class TagListView(generics.ListAPIView):
    """
    Liste des tags disponibles pour les biens
    """
    serializer_class = TagBienSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return TagBien.objects.all()

    @swagger_auto_schema(
        operation_description="Lister tous les tags",
        responses={200: TagBienSerializer(many=True)},
        tags=["Tags"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class TarifLookupView(generics.GenericAPIView):
    """
    Récupère le tarif d'un bien pour un type donné (Journalier, Hebdomadaire, ...).
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = TarifSerializer

    @swagger_auto_schema(
        operation_summary="Obtenir le tarif d'un bien par type",
        manual_parameters=[
            openapi.Parameter(
                'type_tarif',
                openapi.IN_QUERY,
                description="Type de tarif (JOURNALIER, HEBDOMADAIRE, MENSUEL, ...)",
                type=openapi.TYPE_STRING,
                enum=[t.name for t in Typetarif]
            )
        ],
        responses={
            200: TarifSerializer,
            400: "Paramètre type_tarif manquant",
            404: "Bien ou tarif introuvable",
        },
        tags=["Tarifs"],
    )
    def get(self, request, bien_id):
        type_tarif = request.query_params.get('type_tarif')
        if not type_tarif:
            return Response({"detail": "Le paramètre 'type_tarif' est requis."}, status=status.HTTP_400_BAD_REQUEST)

        bien = get_object_or_404(Bien, pk=bien_id)
        tarif = Tarif.objects.filter(bien=bien, type_tarif=type_tarif).first()
        if not tarif:
            return Response({"detail": "Aucun tarif trouvé pour ce type."}, status=status.HTTP_404_NOT_FOUND)

        return Response(TarifSerializer(tarif).data)

class BienPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class BienListCreateView(generics.ListCreateAPIView):
    queryset = Bien.objects.all().select_related('type_bien').filter(est_verifie=True)
    serializer_class = BienSerializer
    pagination_class = BienPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BienFilter
    search_fields = ['nom', 'ville__nom', 'description', 'type_bien__nom']  

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permission.IsVendor()]
        return [permissions.AllowAny()]

    # Add this method to set the owner automatically
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

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

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.vues += 1
        instance.save(update_fields=["vues"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Récupérer les détails d’un bien",
        responses={200: BienSerializer, 404: "Bien non trouvé"},
        tags=["Biens"]
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

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
    permission_classes = [permission.IsVendor]

    def perform_create(self, serializer):
        serializer.save()

class TarifCreateView(generics.CreateAPIView):
    serializer_class = TarifSerializer
    
    permission_classes = [permissions.IsAuthenticated, permission.IsVendor]

    @swagger_auto_schema(
        operation_summary="Créer un tarif pour un bien",
        tags=["Tarifs"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class TarifUpdateView(generics.UpdateAPIView):
    serializer_class = TarifSerializer
    permission_classes = [permissions.IsAuthenticated, permission.IsVendor]
    lookup_field = 'pk'

    def get_queryset(self):
        # Vérifier si c'est pour la génération du schéma Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Tarif.objects.none()
        
        # Vérifier si l'utilisateur est authentifié
        if isinstance(self.request.user, AnonymousUser):
            return Tarif.objects.none()
        
        return Tarif.objects.filter(bien__owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Mettre à jour un tarif",
        tags=["Tarifs"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

# 🔹 DELETE : Supprimer un tarif
class TarifDeleteView(generics.DestroyAPIView):
    serializer_class = TarifSerializer
    permission_classes = [permission.IsVendor]
    lookup_field = 'pk'

    def get_queryset(self):
        # Vérifier si c'est pour la génération du schéma Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Tarif.objects.none()
        
        # Vérifier si l'utilisateur est authentifié
        if isinstance(self.request.user, AnonymousUser):
            return Tarif.objects.none()
        
        return Tarif.objects.filter(bien__owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Supprimer un tarif",
        tags=["Tarifs"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

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
        bien_id = request.data.get('bien_id')

        if not bien_id:
            return Response({'error': 'Le champ bien_id est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            bien = Bien.objects.get(pk=bien_id)
        except Bien.DoesNotExist:
            return Response({'error': 'Bien non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

        # Vérifier si le favori existe déjà
        favori_existe = Favori.objects.filter(user=request.user, bien=bien).exists()
        if favori_existe:
            return Response({'error': 'Ce bien est déjà dans vos favoris.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Création du favori
        favori = Favori.objects.create(user=request.user, bien=bien)
        serializer = self.get_serializer(favori)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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

@swagger_auto_schema(
    method='get',
    operation_summary="Voir les utilisateurs qui ont liké un bien",
    operation_description="""
    Permet à un vendeur de voir tous les utilisateurs qui ont ajouté ce bien à leurs favoris.
    Le bien doit appartenir au vendeur connecté.
    """,
    manual_parameters=[
        openapi.Parameter(
            'bien_id',
            openapi.IN_PATH,
            description="ID du bien",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    responses={
        200: openapi.Response(
            description="Liste des utilisateurs ayant liké le bien",
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_OBJECT)
            )
        ),
        404: "Bien non trouvé ou non autorisé",
        401: "Non authentifié"
    },
    tags=["Favoris", "Vendeur"]
)
@api_view(['GET'])
@permission_classes([permission.IsVendor])
def likes_de_mon_bien(request, bien_id):
    user = request.user
    
    try:
        bien = Bien.objects.get(id=bien_id, owner=user)
    except Bien.DoesNotExist:
        return Response({"detail": "Bien non trouvé ou vous n'en êtes pas le propriétaire."}, status=status.HTTP_404_NOT_FOUND)

    favoris = Favori.objects.filter(bien=bien).select_related('user')
    serializer = FavoriSerializer(favoris, many=True)
    return Response(serializer.data)

class AvisPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class AvisListCreateView(generics.ListCreateAPIView):
    """
    Liste et création d'avis
    """
    pagination_class = AvisPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['commentaire', 'user__username']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AvisCreateSerializer
        return AvisSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        queryset = Avis.objects.filter(est_valide=True).select_related(
            'user', 'bien', 'reservation'
        ).order_by('-created_at')
        
        # Filtrer par bien
        bien_id = self.request.query_params.get('bien_id')
        if bien_id:
            queryset = queryset.filter(bien_id=bien_id)
        
        # Filtrer par note
        note_min = self.request.query_params.get('note_min')
        if note_min:
            try:
                queryset = queryset.filter(note__gte=int(note_min))
            except ValueError:
                pass
        
        return queryset

    @swagger_auto_schema(
        operation_description="Lister les avis ou en créer un nouveau",
        manual_parameters=[
            openapi.Parameter(
                'bien_id', openapi.IN_QUERY,
                description="Filtrer par ID du bien",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'note_min', openapi.IN_QUERY,
                description="Note minimale (1-5)",
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={
            200: AvisSerializer(many=True),
            201: AvisSerializer,
            400: "Données invalides"
        },
        tags=['Avis']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Créer un avis pour une réservation terminée",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'note': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5),
                'commentaire': openapi.Schema(type=openapi.TYPE_STRING),
                'note_proprete': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5),
                'note_communication': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5),
                'note_emplacement': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5),
                'note_rapport_qualite_prix': openapi.Schema(type=openapi.TYPE_INTEGER, minimum=1, maximum=5),
                'recommande': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
            required=['reservation_id', 'note', 'commentaire']
        ),
        responses={
            201: "Avis créé avec succès",
            400: "Données invalides ou conditions non remplies",
            401: "Non authentifié"
        },
        tags=['Avis', 'Réservations']
    )
    def post(self, request, *args, **kwargs):
        # Implémente la logique de creer_avis_reservation sur la route existante /api/reservation/avis/
        from django.core.exceptions import ValidationError
        try:
            try:
                from .services.avis_service import AvisService  # type: ignore
            except Exception:
                return Response({
                    'success': False,
                    'error': "Service d'avis indisponible"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            reservation_id = request.data.get('reservation_id')
            if not reservation_id:
                return Response({
                    'success': False,
                    'error': 'ID de réservation requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier autorisation de noter cette réservation
            peut_donner, message = AvisService.peut_donner_avis(request.user, reservation_id)
            if not peut_donner:
                return Response({
                    'success': False,
                    'error': message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Préparer données
            donnees_avis = {
                'note': request.data.get('note'),
                'commentaire': request.data.get('commentaire', ''),
                'note_proprete': request.data.get('note_proprete'),
                'note_communication': request.data.get('note_communication'),
                'note_emplacement': request.data.get('note_emplacement'),
                'note_rapport_qualite_prix': request.data.get('note_rapport_qualite_prix'),
                'recommande': request.data.get('recommande', True)
            }

            # Créer l'avis via service
            avis = AvisService.creer_avis(request.user, reservation_id, donnees_avis)
            serializer = AvisSerializer(avis, context={'request': request})
            return Response({
                'success': True,
                'message': 'Avis créé avec succès',
                'avis': serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f"Erreur lors de la création de l'avis: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='post',
    operation_description="Répondre à un avis en tant que propriétaire",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'avis_id': openapi.Schema(type=openapi.TYPE_INTEGER),
            'reponse': openapi.Schema(type=openapi.TYPE_STRING, maxLength=500),
        },
        required=['avis_id', 'reponse']
    ),
    responses={
        200: "Réponse ajoutée avec succès",
        400: "Données invalides ou conditions non remplies",
        401: "Non authentifié",
        403: "Seul le propriétaire peut répondre"
    },
    tags=['Avis', 'Propriétaire']
)
@api_view(['POST'])
@permission_classes([permission.IsVendor])
def repondre_avis(request):
    """
    Permet au propriétaire de répondre à un avis sur son bien
    """
    from .services.avis_service import AvisService
    from django.core.exceptions import ValidationError
    
    try:
        avis_id = request.data.get('avis_id')
        reponse = request.data.get('reponse', '').strip()
        
        if not avis_id or not reponse:
            return Response({
                'success': False,
                'error': "ID de l'avis et réponse requis"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si l'utilisateur peut répondre
        peut_repondre, message = AvisService.peut_repondre_avis(request.user, avis_id)
        if not peut_repondre:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Ajouter la réponse
        avis = AvisService.repondre_avis(request.user, avis_id, reponse)
        
        # Sérialiser la réponse
        serializer = AvisSerializer(avis, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Réponse ajoutée avec succès',
            'avis': serializer.data
        })
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': f"Erreur lors de l'ajout de la réponse: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AvisDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Détail, mise à jour et suppression d'un avis
    """
    queryset = Avis.objects.select_related('user', 'bien', 'reservation')
    serializer_class = AvisSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        # Limiter les opérations d’écriture à l’auteur de l’avis, au propriétaire du bien ou à un admin
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if self.request.user.is_staff:
                return qs
            return qs.filter(Q(user=self.request.user) | Q(bien__owner=self.request.user))
        return qs

    @swagger_auto_schema(
        operation_description="Récupérer un avis",
        responses={200: AvisSerializer, 404: "Avis non trouvé"},
        tags=['Avis']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Mettre à jour un avis",
        responses={200: AvisSerializer, 400: "Données invalides", 403: "Permission refusée"},
        tags=['Avis']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Supprimer un avis",
        responses={204: "Supprimé"},
        tags=['Avis']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class ReponseProprietaireView(generics.UpdateAPIView):
    """
    Permet au propriétaire (vendor) de répondre à un avis via /avis/<pk>/repondre/
    """
    serializer_class = ReponseProprietaireSerializer
    permission_classes = [permission.IsVendor]

    @swagger_auto_schema(
        operation_description="Répondre à un avis (propriétaire uniquement)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reponse': openapi.Schema(type=openapi.TYPE_STRING, maxLength=500),
            },
            required=['reponse']
        ),
        responses={200: "Réponse ajoutée", 400: "Données invalides", 403: "Permission refusée", 404: "Avis non trouvé"},
        tags=['Avis', 'Propriétaire']
    )
    def put(self, request, *args, **kwargs):
        avis = self.get_object()
        reponse = request.data.get('reponse', '').strip()
        if not reponse:
            return Response({'success': False, 'error': 'Réponse requise'}, status=status.HTTP_400_BAD_REQUEST)

        avis.reponse_proprietaire = reponse
        avis.date_reponse = timezone.now()
        avis.save(update_fields=['reponse_proprietaire', 'date_reponse', 'updated_at'])

        serializer = AvisSerializer(avis, context={'request': request})
        return Response({'success': True, 'message': 'Réponse ajoutée avec succès', 'avis': serializer.data})

    def get_object(self):
        avis = get_object_or_404(Avis, pk=self.kwargs['pk'])
        user = self.request.user
        if not (user.is_staff or avis.bien.owner_id == user.id):
            raise PermissionDenied("Seul le propriétaire du bien peut répondre à cet avis.")
        return avis

@swagger_auto_schema(
    method='get',
    operation_description="Statistiques des avis pour un bien (moyenne, distribution, moyennes par catégorie)",
    responses={
        200: openapi.Response(
            description="Statistiques d'avis",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'bien_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'nombre_avis': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'moyenne_globale': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'distribution': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        additional_properties=openapi.Schema(type=openapi.TYPE_INTEGER),
                        description="Nombre d'avis par note 1..5"
                    ),
                    'moyennes_categories': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'proprete': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                            'communication': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                            'emplacement': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                            'rapport_qualite_prix': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                        }
                    ),
                }
            )
        ),
        404: "Bien non trouvé"
    },
    tags=['Avis']
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def statistiques_avis_bien(request, bien_id: int):
    try:
        # Vérifier l’existence du bien
        Bien.objects.get(id=bien_id)
    except Bien.DoesNotExist:
        return Response({'success': False, 'error': 'Bien non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    avis_qs = Avis.objects.filter(bien_id=bien_id, est_valide=True)

    nombre_avis = avis_qs.count()
    if nombre_avis == 0:
        return Response({
            'success': True,
            'bien_id': bien_id,
            'nombre_avis': 0,
            'moyenne_globale': 0,
            'distribution': {str(i): 0 for i in range(1, 6)},
            'moyennes_categories': {
                'proprete': None,
                'communication': None,
                'emplacement': None,
                'rapport_qualite_prix': None
            }
        })

    # Moyenne globale
    moyenne = avis_qs.aggregate(m=Avg('note'))['m'] or 0
    moyenne_globale = round(float(moyenne), 1)

    # Distribution des notes
    distribution = {str(i): 0 for i in range(1, 6)}
    for row in avis_qs.values('note').annotate(c=Count('id')):
        note_val = str(row['note'])
        if note_val in distribution:
            distribution[note_val] = row['c']

    # Moyennes par catégorie
    cats = avis_qs.aggregate(
        proprete=Avg('note_proprete'),
        communication=Avg('note_communication'),
        emplacement=Avg('note_emplacement'),
        rapport_qualite_prix=Avg('note_rapport_qualite_prix'),
    )
    moyennes_categories = {
        'proprete': round(float(cats['proprete']), 1) if cats['proprete'] is not None else None,
        'communication': round(float(cats['communication']), 1) if cats['communication'] is not None else None,
        'emplacement': round(float(cats['emplacement']), 1) if cats['emplacement'] is not None else None,
        'rapport_qualite_prix': round(float(cats['rapport_qualite_prix']), 1) if cats['rapport_qualite_prix'] is not None else None,
    }

    return Response({
        'success': True,
        'bien_id': bien_id,
        'nombre_avis': nombre_avis,
        'moyenne_globale': moyenne_globale,
        'distribution': distribution,
        'moyennes_categories': moyennes_categories
    })

@swagger_auto_schema(
    method='get',
    operation_description="Lister les avis créés par l'utilisateur connecté",
    manual_parameters=[
        openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Numéro de page", required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Taille de page", required=False),
    ],
    responses={200: AvisSerializer(many=True), 401: "Non authentifié"},
    tags=['Avis']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def mes_avis(request):
    """
    Avis créés par l'utilisateur connecté
    """
    qs = Avis.objects.filter(user=request.user)\
                     .select_related('bien', 'reservation')\
                     .order_by('-created_at')

    # Pagination simple
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except ValueError:
        page = 1
    try:
        limit = int(request.query_params.get('limit', 20))
        limit = 20 if limit <= 0 else min(limit, 100)
    except ValueError:
        limit = 20

    paginator = Paginator(qs, limit)
    try:
        avis_page = paginator.page(page)
    except Exception:
        avis_page = paginator.page(1)

    serializer = AvisSerializer(avis_page.object_list, many=True, context={'request': request})
    return Response({
        'success': True,
        'results': serializer.data,
        'pagination': {
            'page': avis_page.number,
            'pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': avis_page.has_next(),
            'has_previous': avis_page.has_previous(),
        }
    })


@swagger_auto_schema(
    method='get',
    operation_description="Lister les avis reçus pour les biens du propriétaire connecté",
    manual_parameters=[
        openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Numéro de page", required=False),
        openapi.Parameter('limit', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Taille de page", required=False),
    ],
    responses={200: AvisSerializer(many=True), 401: "Non authentifié"},
    tags=['Avis', 'Propriétaire']
)
@api_view(['GET'])
@permission_classes([permission.IsVendor])
def avis_recus(request):
    """
    Avis reçus par le propriétaire (sur ses biens)
    """
    qs = Avis.objects.filter(bien__owner=request.user, est_valide=True)\
                     .select_related('user', 'bien', 'reservation')\
                     .order_by('-created_at')

    # Pagination simple
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except ValueError:
        page = 1
    try:
        limit = int(request.query_params.get('limit', 20))
        limit = 20 if limit <= 0 else min(limit, 100)
    except ValueError:
        limit = 20

    paginator = Paginator(qs, limit)
    try:
        avis_page = paginator.page(page)
    except Exception:
        avis_page = paginator.page(1)

    serializer = AvisSerializer(avis_page.object_list, many=True, context={'request': request})
    return Response({
        'success': True,
        'results': serializer.data,
        'pagination': {
            'page': avis_page.number,
            'pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': avis_page.has_next(),
            'has_previous': avis_page.has_previous(),
        }
    })

class VilleListView(generics.ListAPIView):
    """
    Lister les villes disponibles
    """
    serializer_class = VilleSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Ville.objects.none()
        return Ville.objects.all().order_by('nom')

    @swagger_auto_schema(
        operation_description="Lister toutes les villes",
        responses={200: VilleSerializer(many=True)},
        tags=["Villes"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TypeBienListCreateView(generics.ListCreateAPIView):
    """
    Lister les types de bien et en créer (admin)
    """
    serializer_class = TypeBienSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Type_Bien.objects.none()
        return Type_Bien.objects.all().order_by('nom')

    @swagger_auto_schema(
        operation_description="Lister les types de bien",
        responses={200: TypeBienSerializer(many=True)},
        tags=["Types de bien"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Créer un type de bien (admin uniquement)",
        responses={201: TypeBienSerializer, 400: "Données invalides"},
        tags=["Types de bien"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TypeBienDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Détail/Mise à jour/Suppression d’un type de bien (admin)
    """
    queryset = Type_Bien.objects.all()
    serializer_class = TypeBienSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @swagger_auto_schema(
        operation_description="Récupérer un type de bien",
        responses={200: TypeBienSerializer, 404: "Non trouvé"},
        tags=["Types de bien"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Mettre à jour un type de bien",
        responses={200: TypeBienSerializer, 400: "Données invalides"},
        tags=["Types de bien"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Supprimer un type de bien",
        responses={204: "Supprimé"},
        tags=["Types de bien"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class DocumentCreateView(generics.CreateAPIView):
    """
    Créer un document pour un bien (propriétaire)
    """
    serializer_class = DocumentSerializer
    permission_classes = [permission.IsVendor]

    def perform_create(self, serializer):
        serializer.save()

    @swagger_auto_schema(
        operation_description="Créer un document (propriétaire)",
        responses={201: DocumentSerializer, 400: "Données invalides"},
        tags=["Documents"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentListView(generics.ListAPIView):
    """
    Lister mes documents (propriétaire)
    """
    serializer_class = DocumentSerializer
    permission_classes = [permission.IsVendor]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()
        return Document.objects.filter(bien__owner=self.request.user).select_related('bien').order_by('-created_at')

    @swagger_auto_schema(
        operation_description="Lister les documents (propriétaire)",
        responses={200: DocumentSerializer(many=True)},
        tags=["Documents"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DocumentUpdateView(generics.UpdateAPIView):
    """
    Mettre à jour un document (propriétaire)
    """
    serializer_class = DocumentSerializer
    permission_classes = [permission.IsVendor]
    lookup_field = 'pk'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()
        return Document.objects.filter(bien__owner=self.request.user)

    @swagger_auto_schema(
        operation_description="Mettre à jour un document (propriétaire)",
        responses={200: DocumentSerializer, 400: "Données invalides"},
        tags=["Documents"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class DocumentDeleteView(generics.DestroyAPIView):
    """
    Supprimer un document (propriétaire)
    """
    serializer_class = DocumentSerializer
    permission_classes = [permission.IsVendor]
    lookup_field = 'pk'

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()
    # Propriétaire uniquement
        return Document.objects.filter(bien__owner=self.request.user)

    @swagger_auto_schema(
        operation_description="Supprimer un document (propriétaire)",
        responses={204: "Supprimé"},
        tags=["Documents"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

@swagger_auto_schema(
    method='post',
    operation_description="Annuler une réservation",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID de la réservation à annuler"),
            'raison': openapi.Schema(type=openapi.TYPE_STRING, description="Raison de l'annulation", default=''),
        },
        required=['reservation_id']
    ),
    responses={
        200: openapi.Response(
            description="Réservation annulée",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: "Requête invalide",
        403: "Permission refusée",
        404: "Réservation non trouvée"
    },
    tags=['Réservations']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_reservation(request):
    """
    Annuler une réservation (client, propriétaire du bien, ou admin).
    Autorisé si statut actuel est 'pending' ou 'confirmed'.
    """
    reservation_id = request.data.get('reservation_id')
    if not reservation_id:
        return Response({'success': False, 'error': "ID de réservation requis"}, status=status.HTTP_400_BAD_REQUEST)

    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Permissions: client, propriétaire du bien, ou admin
    if not (request.user == reservation.user or
            request.user == reservation.bien.owner or
            request.user.is_staff):
        return Response({'success': False, 'error': "Permission refusée"}, status=status.HTTP_403_FORBIDDEN)

    if reservation.status == 'cancelled':
        return Response({'success': False, 'error': "Réservation déjà annulée"}, status=status.HTTP_400_BAD_REQUEST)
    if reservation.status == 'completed':
        return Response({'success': False, 'error': "Impossible d'annuler une réservation terminée"}, status=status.HTTP_400_BAD_REQUEST)

    ancien_statut = reservation.status
    reservation.status = 'cancelled'
    reservation.save(update_fields=['status', 'updated_at'])

    # Historiser le changement de statut (si modèle disponible)
    try:
        HistoriqueStatutReservation.objects.create(
            reservation=reservation,
            ancien_statut=ancien_statut,
            nouveau_statut='cancelled'
        )
    except Exception:
        pass

    logger.info(f"Réservation {reservation_id} annulée par {request.user.username}")

    return Response({
        'success': True,
        'message': 'Réservation annulée avec succès',
        'data': {
            'reservation_id': reservation.id,
            'status': reservation.status
        }
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Confirmer le paiement d'une réservation et la marquer comme confirmée",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID de la réservation"),
        },
        required=['reservation_id']
    ),
    responses={
        200: openapi.Response(
            description="Réservation confirmée",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'confirmed_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        400: "Requête invalide",
        403: "Permission refusée",
        404: "Réservation non trouvée"
    },
    tags=['Réservations']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_reservation_payment(request):
    """
    Confirme le paiement et passe la réservation au statut 'confirmed'.
    Autorisé pour: le client, le propriétaire du bien ou un admin.
    """
    reservation_id = request.data.get('reservation_id')
    if not reservation_id:
        return Response({'success': False, 'error': "ID de réservation requis"}, status=status.HTTP_400_BAD_REQUEST)

    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Permissions
    if not (request.user == reservation.user or
            request.user == reservation.bien.owner or
            request.user.is_staff):
        return Response({'success': False, 'error': "Permission refusée"}, status=status.HTTP_403_FORBIDDEN)

    # Validations de statut
    if reservation.status == 'cancelled':
        return Response({'success': False, 'error': "Réservation annulée"}, status=status.HTTP_400_BAD_REQUEST)
    if reservation.status == 'completed':
        return Response({'success': False, 'error': "Réservation déjà terminée"}, status=status.HTTP_400_BAD_REQUEST)
    if reservation.status == 'confirmed':
        return Response({
            'success': True,
            'message': "Réservation déjà confirmée",
            'data': {
                'reservation_id': reservation.id,
                'status': reservation.status,
                'confirmed_at': reservation.confirmed_at.isoformat() if reservation.confirmed_at else None
            }
        }, status=status.HTTP_200_OK)

    # Confirmer
    reservation.status = 'confirmed'
    if not reservation.confirmed_at:
        reservation.confirmed_at = timezone.now()
    reservation.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    # Historiser
    try:
        HistoriqueStatutReservation.objects.create(
            reservation=reservation,
            ancien_statut='pending',
            nouveau_statut='confirmed'
        )
    except Exception:
        pass

    logger.info(f"Réservation {reservation_id} confirmée par {request.user.username}")

    return Response({
        'success': True,
        'message': "Paiement confirmé, réservation passée à 'confirmed'.",
        'data': {
            'reservation_id': reservation.id,
            'status': reservation.status,
            'confirmed_at': reservation.confirmed_at.isoformat() if reservation.confirmed_at else None
        }
    }, status=status.HTTP_200_OK)

class MoyenneAvisProprietaireView(generics.GenericAPIView):
    """
    Récupère la moyenne des avis pour tous les biens d'un propriétaire
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Récupérer la moyenne des avis d'un propriétaire",
        responses={
            200: openapi.Response(
                description="Moyenne des avis du propriétaire",
                examples={
                    "application/json": {
                        "success": True,
                        "moyenne_globale": 4.2,
                        "nombre_avis": 15,
                        "nombre_biens": 3
                    }
                }
            ),
            404: "Utilisateur non trouvé"
        },
        tags=['Avis', 'Propriétaire']
    )
    def get(self, request, user_id):
        User = get_user_model()
        try:
            proprietaire = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        biens = Bien.objects.filter(owner=proprietaire)
        if not biens.exists():
            return Response({'success': True, 'moyenne_globale': 0, 'nombre_avis': 0, 'nombre_biens': 0})

        avis_qs = Avis.objects.filter(bien__in=biens, est_valide=True)
        nombre_avis = avis_qs.count()
        if nombre_avis == 0:
            return Response({'success': True, 'moyenne_globale': 0, 'nombre_avis': 0, 'nombre_biens': biens.count()})

        moyenne = avis_qs.aggregate(m=Avg('note'))['m'] or 0
        return Response({
            'success': True,
            'moyenne_globale': round(float(moyenne), 1),
            'nombre_avis': nombre_avis,
            'nombre_biens': biens.count()
        })


class AvisRecusProprietaireView(generics.GenericAPIView):
    """
    Liste les avis reçus pour tous les biens d'un propriétaire (par user_id)
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Récupérer la liste détaillée des avis reçus d'un propriétaire",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="Numéro de page", type=openapi.TYPE_INTEGER),
            openapi.Parameter('limit', openapi.IN_QUERY, description="Nombre d'éléments par page", type=openapi.TYPE_INTEGER),
        ],
        responses={200: "Liste paginée des avis", 404: "Utilisateur non trouvé"},
        tags=['Avis', 'Propriétaire']
    )
    def get(self, request, user_id):
        User = get_user_model()
        try:
            proprietaire = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'success': True, 'avis': [], 'pagination': {'page': 1, 'pages': 0, 'total': 0, 'has_next': False, 'has_previous': False}})

        biens = Bien.objects.filter(owner=proprietaire)
        avis_qs = Avis.objects.filter(bien__in=biens, est_valide=True).select_related('user', 'bien').order_by('-created_at')

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        try:
            limit = int(request.query_params.get('limit', 20))
            limit = 20 if limit <= 0 else min(limit, 100)
        except ValueError:
            limit = 20

        paginator = Paginator(avis_qs, limit)
        try:
            avis_page = paginator.page(page)
        except Exception:
            avis_page = paginator.page(1)

        avis_data = []
        for a in avis_page:
            bien_image = None
            try:
                # si un related name media existe avec un champ image
                if hasattr(a.bien, 'media') and a.bien.media.exists():
                    m = a.bien.media.first()
                    if getattr(m, 'image', None):
                        bien_image = request.build_absolute_uri(m.image.url)
            except Exception:
                bien_image = None

            avis_data.append({
                'id': a.id,
                'note': a.note,
                'commentaire': a.commentaire or '',
                'date_creation': a.created_at.isoformat(),
                'auteur_nom': a.user.username if a.user else 'Utilisateur',
                'bien_nom': a.bien.nom if a.bien else '',
                'bien_image': bien_image,
                'note_proprete': getattr(a, 'note_proprete', None),
                'note_communication': getattr(a, 'note_communication', None),
                'note_emplacement': getattr(a, 'note_emplacement', None),
                'note_qualite_prix': getattr(a, 'note_rapport_qualite_prix', None),
            })

        return Response({
            'success': True,
            'avis': avis_data,
            'pagination': {
                'page': avis_page.number,
                'pages': paginator.num_pages,
                'total': paginator.count,
                'has_next': avis_page.has_next(),
                'has_previous': avis_page.has_previous(),
            }
        })


@swagger_auto_schema(
    method='get',
    operation_description="Profil d'avis du propriétaire (connecté ou par user_id)",
    responses={200: "Statistiques et avis du propriétaire"},
    tags=['Avis', 'Propriétaire']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profil_avis_proprietaire(request, user_id=None):
    """
    Récupère le profil d'avis du propriétaire connecté ou d'un utilisateur spécifique
    """
    # Service optionnel
    try:
        from .services.avis_service import AvisService  # type: ignore
    except Exception:
        AvisService = None

    target_user_id = user_id if user_id is not None else request.user.id
    User = get_user_model()
    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return Response({'success': False, 'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    # Stats via service sinon fallback
    stats = None
    if AvisService and hasattr(AvisService, 'obtenir_avis_utilisateur'):
        try:
            stats = AvisService.obtenir_avis_utilisateur(target_user_id)
        except Exception:
            stats = None
    if stats is None:
        avis_all = Avis.objects.filter(bien__owner_id=target_user_id, est_valide=True)
        total = avis_all.count()
        moyenne = avis_all.aggregate(m=Avg('note'))['m'] or 0
        recos = avis_all.filter(recommande=True).count()
        pourc = round((recos / total * 100), 1) if total else 0
        stats = {
            'note_moyenne': round(float(moyenne), 1) if moyenne else 0,
            'nombre_avis': total,
            'nombre_biens': Bien.objects.filter(owner_id=target_user_id).count(),
            'pourcentage_recommandation': pourc,
            'notes_moyennes_categories': {
                'proprete': round(float(avis_all.aggregate(v=Avg('note_proprete'))['v'] or 0), 1) if total else None,
                'communication': round(float(avis_all.aggregate(v=Avg('note_communication'))['v'] or 0), 1) if total else None,
                'emplacement': round(float(avis_all.aggregate(v=Avg('note_emplacement'))['v'] or 0), 1) if total else None,
                'rapport_qualite_prix': round(float(avis_all.aggregate(v=Avg('note_rapport_qualite_prix'))['v'] or 0), 1) if total else None,
            }
        }

    # Pagination des avis
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    try:
        limit = int(request.GET.get('limit', 10))
        limit = 10 if limit <= 0 else min(limit, 100)
    except ValueError:
        limit = 10

    avis_qs = Avis.objects.filter(bien__owner_id=target_user_id, est_valide=True)\
                          .select_related('user', 'bien').order_by('-created_at')
    paginator = Paginator(avis_qs, limit)
    try:
        avis_page = paginator.page(page)
    except Exception:
        avis_page = paginator.page(1)

    avis_data = []
    for a in avis_page:
        try:
            photo = getattr(a.user, 'photo_profil', None)
            photo_url = request.build_absolute_uri(photo.url) if getattr(photo, 'url', None) else None
        except Exception:
            photo_url = None
        avis_data.append({
            'id': a.id,
            'note': a.note,
            'commentaire': a.commentaire or '',
            'date_creation': a.created_at.isoformat(),
            'auteur_nom': a.user.username if a.user else 'Utilisateur',
            'auteur_photo': photo_url,
            'bien_nom': a.bien.nom if a.bien else '',
            'note_proprete': a.note_proprete,
            'note_communication': a.note_communication,
            'note_emplacement': a.note_emplacement,
            'note_qualite_prix': a.note_rapport_qualite_prix,
        })

    return Response({
        'success': True,
        'avis': avis_data,
        'stats': stats,
        'pagination': {
            'page': avis_page.number,
            'pages': paginator.num_pages,
            'count': paginator.count,
            'has_next': avis_page.has_next(),
            'has_previous': avis_page.has_previous(),
        },
        'profil_proprietaire': {
            'utilisateur': {
                'id': target_user.id,
                'username': target_user.username,
                'nom_complet': f"{target_user.first_name} {target_user.last_name}".strip()
            },
            'statistiques': stats
        }
    })

class VerifierDroitAvisView(generics.GenericAPIView):
    """
    Vérifie si l'utilisateur connecté peut donner un avis pour un bien donné
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Vérifier si l'utilisateur peut donner un avis sur un bien",
        responses={
            200: openapi.Response(
                description="Résultat de la vérification",
                examples={
                    "application/json": {
                        "peut_noter": True,
                        "reservation_id": 30,
                        "message": "Vous pouvez donner un avis pour cette réservation terminée"
                    }
                }
            ),
            404: "Bien non trouvé",
            401: "Non authentifié"
        },
        tags=['Avis']
    )
    def get(self, request, bien_id):
        try:
            bien = Bien.objects.get(id=bien_id)
        except Bien.DoesNotExist:
            return Response({'error': 'Bien non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        # L'utilisateur a-t-il déjà noté ce bien ?
        if Avis.objects.filter(user=request.user, bien=bien).exists():
            return Response({
                'peut_noter': False,
                'reservation_id': None,
                'message': "Vous avez déjà donné un avis pour ce bien."
            })

        # A-t-il au moins une réservation terminée sur ce bien ?
        reservations_terminees = Reservation.objects.filter(
            user=request.user,
            bien=bien,
            status='completed'
        ).order_by('-date_fin')

        if reservations_terminees.exists():
            return Response({
                'peut_noter': True,
                'reservation_id': reservations_terminees.first().id,
                'message': "Vous pouvez donner un avis pour cette réservation terminée."
            })

        return Response({
            'peut_noter': False,
            'reservation_id': None,
            'message': "Vous devez avoir une réservation terminée pour donner un avis."
        })
@swagger_auto_schema(
    method='post',
    operation_description="Marquer une réservation comme terminée",
    manual_parameters=[
        openapi.Parameter(
            'reservation_id',
            openapi.IN_PATH,
            description="ID de la réservation",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Réservation terminée",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'reservation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: "Requête invalide",
        403: "Permission refusée",
        404: "Réservation non trouvée",
    },
    tags=['Réservations']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def terminer_reservation(request, reservation_id: int):
    """
    Marque la réservation comme 'completed'.
    Autorisé pour le client, le propriétaire du bien, ou un admin.
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Permissions
    if not (request.user == reservation.user or
            request.user == reservation.bien.owner or
            request.user.is_staff):
        return Response({'success': False, 'error': "Permission refusée"}, status=status.HTTP_403_FORBIDDEN)

    # Vérifications de statut
    if reservation.status == 'cancelled':
        return Response({'success': False, 'error': "Réservation annulée"}, status=status.HTTP_400_BAD_REQUEST)
    if reservation.status == 'completed':
        return Response({
            'success': True,
            'message': "Déjà terminée",
            'data': {'reservation_id': reservation.id, 'status': reservation.status}
        }, status=status.HTTP_200_OK)

    ancien_statut = reservation.status
    reservation.status = 'completed'
    reservation.save(update_fields=['status', 'updated_at'])

    # Historique (si modèle présent)
    try:
        HistoriqueStatutReservation.objects.create(
            reservation=reservation,
            ancien_statut=ancien_statut,
            nouveau_statut='completed'
        )
    except Exception:
        pass

    logger.info(f"Réservation {reservation_id} terminée par {request.user.username}")

    return Response({
        'success': True,
        'message': "Réservation marquée comme terminée.",
        'data': {'reservation_id': reservation.id, 'status': reservation.status}
    }, status=status.HTTP_200_OK)