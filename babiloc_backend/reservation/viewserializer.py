from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from Auths import permission
from rest_framework import serializers
from django.db.models import Count, Avg
from .models import Reservation, Bien, HistoriqueStatutReservation, Favori, Tarif, Avis, Type_Bien
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
    TypeBienSerializer
)
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .filters import BienFilter
from django.contrib.auth.models import AnonymousUser


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
        serializer.save(owner=self.request.user)
    
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
                'bien_id',  # Changer annonce_id en bien_id
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
            queryset = queryset.filter(bien_id=bien_id)
        
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
    search_fields = ['nom', 'ville', 'description', 'type_bien__nom']  

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
        operation_description="Créer un avis",
        request_body=AvisCreateSerializer,
        responses={
            201: AvisSerializer,
            400: "Données invalides",
            401: "Non authentifié"
        },
        tags=['Avis']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class AvisDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Détails, modification et suppression d'un avis
    """
    serializer_class = AvisSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Avis.objects.none()
        
        user = self.request.user
        if user.is_staff:
            return Avis.objects.all()
        return Avis.objects.filter(user=user)
    
    @swagger_auto_schema(
        operation_description="Récupérer un avis",
        responses={200: AvisSerializer},
        tags=['Avis']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Modifier un avis",
        responses={200: AvisSerializer},
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
    Permet au propriétaire de répondre à un avis
    """
    serializer_class = ReponseProprietaireSerializer
    permission_classes = [permission.IsVendor]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Avis.objects.none()
        
        return Avis.objects.filter(
            bien__owner=self.request.user,
            reponse_proprietaire__isnull=True
        )
    
    @swagger_auto_schema(
        operation_description="Répondre à un avis en tant que propriétaire",
        request_body=ReponseProprietaireSerializer,
        responses={
            200: AvisSerializer,
            403: "Vous n'êtes pas le propriétaire de ce bien",
            404: "Avis non trouvé"
        },
        tags=['Avis', 'Propriétaire']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

@swagger_auto_schema(
    method='get',
    operation_description="Statistiques des avis pour un bien",
    manual_parameters=[
        openapi.Parameter(
            'bien_id', openapi.IN_PATH,
            description="ID du bien",
            type=openapi.TYPE_INTEGER, required=True
        )
    ],
    responses={
        200: StatistiquesAvisSerializer,
        404: "Bien non trouvé"
    },
    tags=['Avis', 'Statistiques']
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def statistiques_avis_bien(request, bien_id):
    """
    Retourne les statistiques d'avis pour un bien donné
    """
    try:
        bien = Bien.objects.get(id=bien_id)
    except Bien.DoesNotExist:
        return Response({"detail": "Bien non trouvé"}, status=404)
    
    avis = bien.avis.filter(est_valide=True)
    
    # Statistiques de base
    stats = avis.aggregate(
        note_moyenne=Avg('note'),
        nombre_avis=Count('id')
    )
    
    # Répartition des notes
    repartition = {}
    for i in range(1, 6):
        repartition[f"{i}_etoiles"] = avis.filter(note=i).count()
    
    # Pourcentage de recommandation
    total_avis = stats['nombre_avis'] or 0
    recommandations = avis.filter(recommande=True).count()
    pourcentage_recommandation = (recommandations / total_avis * 100) if total_avis > 0 else 0
    
    # Notes moyennes par catégorie
    notes_categories = avis.aggregate(
        proprete=Avg('note_proprete'),
        communication=Avg('note_communication'),
        emplacement=Avg('note_emplacement'),
        rapport_qualite_prix=Avg('note_rapport_qualite_prix')
    )
    
    # Nettoyer les valeurs None
    notes_categories = {
        k: round(v, 1) if v is not None else None 
        for k, v in notes_categories.items()
    }
    
    data = {
        'note_moyenne': round(stats['note_moyenne'], 1) if stats['note_moyenne'] else 0,
        'nombre_avis': total_avis,
        'repartition_notes': repartition,
        'pourcentage_recommandation': round(pourcentage_recommandation, 1),
        'notes_moyennes_categories': notes_categories
    }
    
    return Response(data)

@swagger_auto_schema(
    method='get',
    operation_description="Mes avis donnés",
    responses={200: AvisSerializer(many=True)},
    tags=['Avis', 'Utilisateur']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def mes_avis(request):
    """
    Liste des avis donnés par l'utilisateur connecté
    """
    avis = Avis.objects.filter(user=request.user).select_related(
        'bien', 'reservation'
    ).order_by('-created_at')
    
    serializer = AvisSerializer(avis, many=True, context={'request': request})
    return Response(serializer.data)

@swagger_auto_schema(
    method='get',
    operation_description="Avis reçus sur mes biens",
    responses={200: AvisSerializer(many=True)},
    tags=['Avis', 'Propriétaire']
)
@api_view(['GET'])
@permission_classes([permission.IsVendor])
def avis_recus(request):
    """
    Liste des avis reçus sur les biens du propriétaire
    """
    avis = Avis.objects.filter(
        bien__owner=request.user,
        est_valide=True
    ).select_related('user', 'bien', 'reservation').order_by('-created_at')
    
    serializer = AvisSerializer(avis, many=True, context={'request': request})
    return Response(serializer.data)

class TypeBienListCreateView(generics.ListCreateAPIView):
    """
    Liste et création de types de bien
    """
    queryset = Type_Bien.objects.all()
    serializer_class = TypeBienSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
    
    @swagger_auto_schema(
        operation_description="Lister tous les types de bien",
        responses={200: TypeBienSerializer(many=True)},
        tags=["Types de bien"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Créer un type de bien (admin uniquement)",
        request_body=TypeBienSerializer,
        responses={
            201: TypeBienSerializer,
            400: "Données invalides",
            403: "Permission refusée"
        },
        tags=["Types de bien"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TypeBienDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Détails, modification et suppression d'un type de bien
    """
    queryset = Type_Bien.objects.all()
    serializer_class = TypeBienSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    @swagger_auto_schema(
        operation_description="Récupérer les détails d'un type de bien",
        responses={
            200: TypeBienSerializer,
            404: "Type de bien non trouvé"
        },
        tags=["Types de bien"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Mettre à jour un type de bien (admin uniquement)",
        request_body=TypeBienSerializer,
        responses={
            200: TypeBienSerializer,
            400: "Données invalides",
            403: "Permission refusée",
            404: "Type de bien non trouvé"
        },
        tags=["Types de bien"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Mettre à jour partiellement un type de bien (admin uniquement)",
        request_body=TypeBienSerializer,
        responses={
            200: TypeBienSerializer,
            400: "Données invalides",
            403: "Permission refusée",
            404: "Type de bien non trouvé"
        },
        tags=["Types de bien"]
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Supprimer un type de bien (admin uniquement)",
        responses={
            204: "Supprimé avec succès",
            403: "Permission refusée",
            404: "Type de bien non trouvé"
        },
        tags=["Types de bien"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)