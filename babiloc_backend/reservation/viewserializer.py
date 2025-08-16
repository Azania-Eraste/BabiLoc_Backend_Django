from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from Auths import permission
from rest_framework import serializers
from django.db.models import Count, Avg
from .models import Reservation,TagBien, Ville,Bien, HistoriqueStatutReservation, Favori, Tarif, Avis, Type_Bien, Document, Media
from django.contrib.auth import get_user_model
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
    VilleSerializer
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
    serializer_class = serializers.ModelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return TagBien.objects.all()

    @swagger_auto_schema(
        operation_description="Lister tous les tags",
        responses={200: serializers.ModelSerializer(many=True)},
        tags=["Tags"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

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

    def get_queryset(self):
        owner_id = self.request.query_params.get('owner')
        if owner_id:
            # Gérer le cas spécial où owner=me (mes biens)
            if owner_id == 'me':
                if self.request.user.is_authenticated:
                    queryset = Bien.objects.filter(owner=self.request.user).select_related('type_bien')
                    print(f"=== FILTRE MES BIENS ===")
                    print(f"Utilisateur connecté: {self.request.user.username}")
                    print(f"Nombre de mes biens trouvés: {queryset.count()}")
                    return queryset
                else:
                    print(f"❌ Utilisateur non authentifié pour owner=me")
                    return Bien.objects.none()
            
            # Gérer le cas où owner_id est un ID numérique
            try:
                owner_id = int(owner_id)
                # Pour les biens d'un propriétaire spécifique, inclure TOUS ses biens (vérifiés ou non)
                queryset = Bien.objects.filter(owner_id=owner_id).select_related('type_bien')
                print(f"=== FILTRE PAR PROPRIETAIRE ===")
                print(f"Recherche des biens pour owner_id: {owner_id}")
                print(f"Nombre de biens trouvés: {queryset.count()}")
                return queryset
            except ValueError:
                print(f"❌ owner_id invalide: {owner_id}")
        
        # Pour la liste publique, garder le filtre est_verifie=True
        queryset = super().get_queryset()
        return queryset

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]  # Changé de IsVendor à IsAuthenticated
        return [permissions.AllowAny()]

    # Add this method to set the owner automatically
    def perform_create(self, serializer):
        # Debug: afficher les données reçues
        print(f"=== DEBUG CREATION BIEN ===")
        print(f"Utilisateur: {self.request.user.username} (is_vendor: {self.request.user.is_vendor})")
        print(f"Données reçues: {self.request.data}")
        
        # Promouvoir automatiquement l'utilisateur en vendeur s'il ne l'est pas déjà
        if not self.request.user.is_vendor:
            print(f"Promotion de l'utilisateur {self.request.user.username} en vendeur")
            self.request.user.is_vendor = True
            self.request.user.save()
        else:
            print(f"Utilisateur {self.request.user.username} est déjà vendeur")
            
        # Essayer de sauvegarder avec debug
        try:
            serializer.save(owner=self.request.user)
            print("✅ Bien créé avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de la création: {e}")
            print(f"Erreurs de validation: {serializer.errors if hasattr(serializer, 'errors') else 'N/A'}")
            raise

    @swagger_auto_schema(
        operation_description="Lister tous les biens ou en créer un nouveau",
        responses={200: BienSerializer(many=True)},
        tags=["Biens"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_serializer_context(self):
        """Passe le request au serializer context"""
        return {'request': self.request}

    @swagger_auto_schema(
        operation_description="Créer un bien (admin uniquement)",
        responses={201: BienSerializer, 400: "Données invalides"},
        tags=["Biens"]
    )
    def post(self, request, *args, **kwargs):
        print(f"=== POST /api/location/biens/ ===")
        print(f"Content-Type: {request.content_type}")
        print(f"Data: {request.data}")
        
        # Vérifier que le serializer reçoit bien les données
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ Erreurs de validation du serializer: {serializer.errors}")
            
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

    def get_serializer_context(self):
        """Passe le request au serializer context"""
        return {'request': self.request}

    @swagger_auto_schema(
        operation_description="Mettre à jour un bien",
        responses={200: BienSerializer, 400: "Données invalides"},
        tags=["Biens"]
    )
    def put(self, request, *args, **kwargs):
        print(f"🔧 DEBUG PUT - Bien ID: {kwargs.get('pk')}")
        print(f"🔧 DEBUG PUT - User: {request.user}")
        print(f"🔧 DEBUG PUT - Data: {request.data}")
        print(f"🔧 DEBUG PUT - Content-Type: {request.content_type}")
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Mettre à jour partiellement un bien",
        responses={200: BienSerializer, 400: "Données invalides"},
        tags=["Biens"]
    )
    def patch(self, request, *args, **kwargs):
        print(f"🔧 DEBUG PATCH - Bien ID: {kwargs.get('pk')}")
        print(f"🔧 DEBUG PATCH - User: {request.user}")
        print(f"🔧 DEBUG PATCH - Data: {request.data}")
        print(f"🔧 DEBUG PATCH - Content-Type: {request.content_type}")
        
        try:
            # Vérifier que le serializer peut traiter les données
            instance = self.get_object()
            print(f"🔧 DEBUG PATCH - Instance trouvée: {instance.nom} (ID: {instance.id})")
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            print(f"🔧 DEBUG PATCH - Serializer créé")
            
            if not serializer.is_valid():
                print(f"❌ DEBUG PATCH - Erreurs de validation: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            print(f"✅ DEBUG PATCH - Validation réussie")
            return super().patch(request, *args, **kwargs)
            
        except Exception as e:
            print(f"❌ DEBUG PATCH - Exception: {e}")
            import traceback
            print(f"❌ DEBUG PATCH - Traceback: {traceback.format_exc()}")
            raise

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
        print("DEBUG MediaCreateView.perform_create: Création d'un média")
        print(f"DEBUG: Données reçues = {self.request.data}")
        print(f"DEBUG: Fichier reçu = {self.request.FILES}")
        print(f"DEBUG: User = {self.request.user}")
        
        # Récupérer le type de média et l'ID du bien
        type_media = self.request.data.get('type_media')
        bien_id = self.request.data.get('bien')
        
        print(f"DEBUG: Type de média = {type_media}")
        print(f"DEBUG: Bien ID = {bien_id}")
        
        # Si c'est une image principale, supprimer l'ancienne
        if type_media == 'principale' and bien_id:
            try:
                bien = Bien.objects.get(id=bien_id)
                old_images = Media.objects.filter(bien=bien, type_media='principale')
                if old_images.exists():
                    print(f"DEBUG: Suppression de {old_images.count()} ancienne(s) image(s) principale(s)")
                    old_images.delete()
            except Bien.DoesNotExist:
                print("DEBUG: Bien non trouvé pour suppression ancienne image")
        
        # Sauvegarder le nouveau média
        media = serializer.save()
        print(f"DEBUG: Média créé avec succès - ID: {media.id}")
        return media

class MediaDeleteView(generics.DestroyAPIView):
    queryset = Media.objects.all()
    permission_classes = [permission.IsVendor]
    
    def delete(self, request, *args, **kwargs):
        print(f"DEBUG MediaDeleteView: Suppression du média ID: {kwargs.get('pk')}")
        media = self.get_object()
        
        # Vérifier que l'utilisateur est propriétaire du bien
        if media.bien.owner != request.user:
            print(f"DEBUG: Utilisateur {request.user} n'est pas propriétaire du bien")
            return Response(
                {'error': 'Non autorisé'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        media_id = media.id
        media.delete()
        print(f"DEBUG: Média {media_id} supprimé avec succès")
        
        return Response(
            {'success': True, 'message': f'Média {media_id} supprimé'}, 
            status=status.HTTP_204_NO_CONTENT
        )

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
    operation_description="Réservations terminées sans avis",
    responses={200: "Liste des réservations pour lesquelles donner un avis"},
    tags=['Avis', 'Réservations']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reservations_sans_avis(request):
    """
    Récupère les réservations terminées pour lesquelles l'utilisateur n'a pas encore donné d'avis
    """
    from .services.avis_service import AvisService
    
    reservations = AvisService.obtenir_reservations_sans_avis(request.user)
    
    # Serializer simplifié pour les réservations
    data = []
    for reservation in reservations:
        data.append({
            'id': reservation.id,
            'bien': {
                'id': reservation.bien.id,
                'nom': reservation.bien.nom,
                'images': [media.image.url for media in reservation.bien.medias.all()[:1]]
            },
            'date_debut': reservation.date_debut,
            'date_fin': reservation.date_fin,
            'prix_total': reservation.prix_total,
            'peut_donner_avis': True
        })
    
    return Response({
        'success': True,
        'reservations': data,
        'count': len(data)
    })

@swagger_auto_schema(
    method='post',
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
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def creer_avis_reservation(request):
    """
    Crée un avis pour une réservation terminée avec toutes les validations de sécurité
    """
    from .services.avis_service import AvisService
    from django.core.exceptions import ValidationError
    
    try:
        reservation_id = request.data.get('reservation_id')
        if not reservation_id:
            return Response({
                'success': False,
                'error': 'ID de réservation requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si l'utilisateur peut donner un avis
        peut_donner, message = AvisService.peut_donner_avis(request.user, reservation_id)
        if not peut_donner:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Préparer les données de l'avis
        donnees_avis = {
            'note': request.data.get('note'),
            'commentaire': request.data.get('commentaire', ''),
            'note_proprete': request.data.get('note_proprete'),
            'note_communication': request.data.get('note_communication'),
            'note_emplacement': request.data.get('note_emplacement'),
            'note_rapport_qualite_prix': request.data.get('note_rapport_qualite_prix'),
            'recommande': request.data.get('recommande', True)
        }
        
        # Créer l'avis
        avis = AvisService.creer_avis(request.user, reservation_id, donnees_avis)
        
        # Sérialiser la réponse
        serializer = AvisSerializer(avis, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Avis créé avec succès',
            'avis': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur lors de la création de l\'avis: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    operation_description="Statistiques détaillées des avis d'un bien",
    manual_parameters=[
        openapi.Parameter(
            'bien_id', openapi.IN_PATH,
            description="ID du bien",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    responses={200: "Statistiques des avis"},
    tags=['Avis', 'Statistiques']
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def statistiques_avis_bien(request, bien_id):
    """
    Récupère les statistiques détaillées des avis pour un bien
    """
    from .services.avis_service import AvisService
    
    try:
        # Vérifier que le bien existe
        bien = Bien.objects.get(id=bien_id)
        stats = AvisService.calculer_statistiques_bien(bien_id)
        
        return Response({
            'success': True,
            'bien': {
                'id': bien.id,
                'nom': bien.nom
            },
            'statistiques': stats
        })
        
    except Bien.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Bien introuvable'
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='get',
    operation_description="Profil d'avis du propriétaire",
    responses={200: "Statistiques d'avis du propriétaire"},
    tags=['Avis', 'Propriétaire']
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profil_avis_proprietaire(request, user_id=None):
    """
    Récupère le profil d'avis du propriétaire connecté ou d'un utilisateur spécifique
    """
    from .services.avis_service import AvisService
    
    # Si user_id est fourni (via URL), utiliser cet ID, sinon utiliser l'utilisateur connecté
    target_user_id = user_id if user_id is not None else request.user.id
    
    try:
        # Récupérer l'utilisateur ciblé pour les informations de profil
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Utilisateur non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Récupérer les statistiques d'avis
    stats = AvisService.obtenir_avis_utilisateur(target_user_id)
    
    # Récupérer les avis avec pagination
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))
    
    # Récupérer les avis pour l'utilisateur
    avis_query = Avis.objects.filter(
        bien__owner_id=target_user_id
    ).select_related('user', 'bien').order_by('-created_at')
    
    # Paginer les résultats
    paginator = Paginator(avis_query, limit)
    try:
        avis_page = paginator.page(page)
    except:
        avis_page = paginator.page(1)
    
    # Sérialiser les avis
    avis_data = []
    for avis in avis_page:
        avis_data.append({
            'id': avis.id,
            'note': avis.note,
            'commentaire': avis.commentaire,
            'date_creation': avis.created_at.isoformat(),
            'auteur_nom': avis.user.username,
            'auteur_photo': avis.user.photo_profil.url if hasattr(avis.user, 'photo_profil') and avis.user.photo_profil else None,
            'bien_nom': avis.bien.nom,
            'note_proprete': avis.note_proprete,
            'note_communication': avis.note_communication,
            'note_emplacement': avis.note_emplacement,
            'note_qualite_prix': avis.note_rapport_qualite_prix,
        })
    
    return Response({
        'success': True,
        'avis': avis_data,
        'stats': stats,
        'pagination': {
            'page': page,
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
                'error': 'ID de l\'avis et réponse requis'
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
            'error': f'Erreur lors de l\'ajout de la réponse: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

class DocumentCreateView(generics.CreateAPIView):
    """
    Créer un document (fichier ou image) pour un bien
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Uploader un document ou une image pour un bien",
        # ✅ Remove manual_parameters and use request_body instead
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['bien_id', 'nom', 'type'],
            properties={
                'bien_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID du bien"
                ),
                'nom': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Nom du document"
                ),
                'type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['carte_grise', 'assurance', 'attestation_propriete', 'autre'],
                    description="Type de document"
                ),
                'fichier': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_BINARY,
                    description="Fichier document (PDF, DOC, etc.)"
                ),
                'image': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_BINARY,
                    description="Image du document (JPG, PNG, etc.)"
                ),
            }
        ),
        responses={
            201: DocumentSerializer,
            400: "Données invalides",
            401: "Non authentifié",
            403: "Non autorisé",
            404: "Bien non trouvé"
        },
        tags=['Documents']
    )
    def post(self, request, *args, **kwargs):
        bien_id = request.data.get('bien_id') or request.data.get('bien')
        
        if not bien_id:
            return Response({'error': 'bien_id ou bien requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            bien = Bien.objects.get(id=bien_id)
        except Bien.DoesNotExist:
            return Response({'error': 'Bien non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier que l'utilisateur est le propriétaire du bien
        if bien.owner != request.user:
            return Response({'error': 'Vous n\'êtes pas autorisé à ajouter des documents à ce bien'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Si c'est un remplacement, supprimer l'ancien document du même type
        type_document = request.data.get('type')
        if type_document:
            old_documents = Document.objects.filter(bien=bien, type=type_document)
            if old_documents.exists():
                print(f"DEBUG: Suppression de {old_documents.count()} ancien(s) document(s) de type {type_document}")
                old_documents.delete()
        
        # Ajouter le bien aux données
        data = request.data.copy()
        data['bien'] = bien.id
        
        serializer = self.get_serializer(data=data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save(bien=bien)  # Forcer l'assignation du bien
            print(f"DEBUG: Document créé avec succès - ID: {document.id}, type: {document.type}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DocumentListView(generics.ListAPIView):
    """
    Liste des documents d'un bien
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Récupérer la liste des documents d'un bien",
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
            200: DocumentSerializer(many=True),
            404: "Bien non trouvé"
        },
        tags=['Documents']
    )
    def get(self, request, bien_id, *args, **kwargs):
        try:
            bien = Bien.objects.get(id=bien_id)
        except Bien.DoesNotExist:
            return Response({'error': 'Bien non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        
        documents = Document.objects.filter(bien=bien)
        serializer = self.get_serializer(documents, many=True, context={'request': request})
        return Response(serializer.data)


class DocumentUpdateView(generics.UpdateAPIView):
    """
    Mettre à jour un document
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()
        
        return Document.objects.filter(bien__owner=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Mettre à jour un document",
        consumes=['multipart/form-data'],
        responses={
            200: DocumentSerializer,
            400: "Données invalides",
            401: "Non authentifié",
            403: "Non autorisé",
            404: "Document non trouvé"
        },
        tags=['Documents']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class DocumentDeleteView(generics.DestroyAPIView):
    """
    Supprimer un document
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()
        
        return Document.objects.filter(bien__owner=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Supprimer un document",
        responses={
            204: "Document supprimé",
            401: "Non authentifié",
            403: "Non autorisé",
            404: "Document non trouvé"
        },
        tags=['Documents']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
    
class VilleListView(generics.ListAPIView):
    """
    Liste des villes disponibles pour les biens
    """
    serializer_class = VilleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Ville.objects.all()

    @swagger_auto_schema(
        operation_description="Lister toutes les villes",
        responses={200: VilleSerializer(many=True)},
        tags=["Villes"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MesBiensView(generics.ListAPIView):
    """Vue pour récupérer tous les biens du propriétaire connecté"""
    serializer_class = BienSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = BienPagination

    def get_queryset(self):
        """Retourne uniquement les biens du propriétaire connecté"""
        return Bien.objects.filter(owner=self.request.user).select_related('type_bien').order_by('-created_at')

    @swagger_auto_schema(
        operation_description="Récupérer tous les biens du propriétaire connecté",
        responses={200: BienSerializer(many=True)},
        tags=["Biens", "Propriétaire"]
    )
    def get(self, request, *args, **kwargs):
        print(f"=== MES BIENS ===")
        print(f"Utilisateur: {request.user.username} (ID: {request.user.id})")
        
        queryset = self.get_queryset()
        print(f"Nombre de biens trouvés: {queryset.count()}")
        
        return super().get(request, *args, **kwargs)

    def get_serializer_context(self):
        """Passe le request au serializer context"""
        return {'request': self.request}


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
        }
    )
    def get(self, request, bien_id):
        """
        Vérifie si l'utilisateur peut donner un avis pour le bien spécifié
        """
        print(f"🔍 VerifierDroitAvisView: Vérification pour bien ID {bien_id}, utilisateur {request.user.username} (ID: {request.user.id})")
        try:
            # Vérifier que le bien existe
            bien = Bien.objects.get(id=bien_id)
            print(f"🔍 VerifierDroitAvisView: Bien trouvé: {bien.nom}")

            # Chercher TOUTES les réservations terminées de l'utilisateur pour ce bien
            reservations_terminees = Reservation.objects.filter(
                user=request.user,
                bien=bien,
                status='completed'
            )
            reservations_terminees_exist = reservations_terminees.exists()
            print(f"🔍 VerifierDroitAvisView: Réservations terminées pour l'utilisateur et le bien: {reservations_terminees.count()} (Existe: {reservations_terminees_exist})")
            
            # Vérifier s'il existe déjà un avis pour ce bien et cet utilisateur (peu importe la réservation)
            avis_existants_pour_bien_user = Avis.objects.filter(
                user=request.user,
                bien=bien
            )
            avis_deja_donne = avis_existants_pour_bien_user.exists()
            print(f"🔍 VerifierDroitAvisView: Avis existant pour ce bien et cet utilisateur: {avis_existants_pour_bien_user.count()} (Déjà donné: {avis_deja_donne})")

            if avis_deja_donne:
                print(f"✅ VerifierDroitAvisView: Avis déjà donné. Désactivation du bouton.")
                return Response({
                    'peut_noter': False,
                    'reservation_id': None, # On ne renvoie plus d'ID de réservation spécifique
                    'message': 'Vous avez déjà donné un avis pour ce bien.'
                })
            elif reservations_terminees_exist:
                print(f"⚠️ VerifierDroitAvisView: Réservations terminées existent mais aucun avis trouvé. Autorisation de donner un avis.")
                # Si l'utilisateur a une réservation terminée mais n'a pas encore donné d'avis pour CE bien
                # On doit trouver une réservation terminée pour l'ID afin de la passer à la fonction de création d'avis
                reservation_pour_avis = reservations_terminees.order_by('-date_fin').first()

                if reservation_pour_avis:
                     print(f"✅ VerifierDroitAvisView: Réservation terminée trouvée (ID: {reservation_pour_avis.id}). Autorisation de donner un avis.")
                     return Response({
                        'peut_noter': True,
                        'reservation_id': reservation_pour_avis.id,
                        'message': 'Vous pouvez donner un avis pour cette réservation terminée.'
                    })
                else: # Devrait être couvert par reservations_terminees_exist, mais par sécurité
                    print(f"❌ VerifierDroitAvisView: Erreur logique: reservations_terminees_exist est vrai mais aucune réservation trouvée.")
                    return Response({
                        'peut_noter': False,
                        'reservation_id': None,
                        'message': 'Aucune réservation terminée pour ce bien sans avis.'
                    })
            else:
                print(f"❌ VerifierDroitAvisView: Aucune réservation terminée trouvée pour le bien. Désactivation du bouton.")
                return Response({
                    'peut_noter': False,
                    'reservation_id': None,
                    'message': 'Vous devez avoir une réservation terminée pour donner un avis.'
                })
                
        except Bien.DoesNotExist:
            print(f"❌ VerifierDroitAvisView: Bien ID {bien_id} non trouvé.")
            return Response(
                {'error': 'Bien non trouvé'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ VerifierDroitAvisView: Erreur inattendue: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': 'Erreur interne du serveur'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MoyenneAvisProprietaireView(generics.GenericAPIView):
    """
    Récupère la moyenne des avis pour tous les biens d'un propriétaire
    """
    permission_classes = [permissions.AllowAny]  # Publiquement accessible
    
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
        }
    )
    def get(self, request, user_id):
        User = get_user_model()
        try:
            # Vérifier que l'utilisateur existe
            proprietaire = User.objects.get(id=user_id)
            print(f"🏠 MoyenneAvisProprietaireView: Calcul moyenne pour propriétaire {proprietaire.username} (ID: {user_id})")
            
            # Récupérer tous les biens du propriétaire
            biens_proprietaire = Bien.objects.filter(owner=proprietaire)
            print(f"📊 Biens trouvés: {biens_proprietaire.count()}")
            
            if not biens_proprietaire.exists():
                return Response({
                    'success': True,
                    'moyenne_globale': 0,
                    'nombre_avis': 0,
                    'nombre_biens': 0,
                    'message': 'Aucun bien trouvé pour ce propriétaire'
                })
            
            # Récupérer tous les avis pour tous les biens du propriétaire
            avis_proprietaire = Avis.objects.filter(bien__in=biens_proprietaire)
            nombre_avis = avis_proprietaire.count()
            print(f"⭐ Avis trouvés: {nombre_avis}")
            
            if nombre_avis == 0:
                return Response({
                    'success': True,
                    'moyenne_globale': 0,
                    'nombre_avis': 0,
                    'nombre_biens': biens_proprietaire.count(),
                    'message': 'Aucun avis trouvé pour les biens de ce propriétaire'
                })
            
            # Calculer la moyenne globale
            moyenne = avis_proprietaire.aggregate(
                moyenne=Avg('note')
            )['moyenne']
            
            moyenne_arrondie = round(moyenne, 1) if moyenne else 0
            print(f"✅ Moyenne calculée: {moyenne_arrondie}/5 sur {nombre_avis} avis")
            
            return Response({
                'success': True,
                'moyenne_globale': moyenne_arrondie,
                'nombre_avis': nombre_avis,
                'nombre_biens': biens_proprietaire.count()
            })
            
        except User.DoesNotExist:
            print(f"❌ MoyenneAvisProprietaireView: Utilisateur ID {user_id} non trouvé.")
            return Response(
                {'success': False, 'error': 'Utilisateur non trouvé'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ MoyenneAvisProprietaireView: Erreur inattendue: {e}")
            return Response(
                {'success': False, 'error': 'Erreur interne du serveur'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvisRecusProprietaireView(generics.GenericAPIView):
    """
    Récupère la liste détaillée des avis reçus pour tous les biens d'un propriétaire
    """
    permission_classes = [permissions.AllowAny]  # Publiquement accessible
    
    @swagger_auto_schema(
        operation_description="Récupérer la liste détaillée des avis reçus d'un propriétaire",
        manual_parameters=[
            openapi.Parameter(
                'page', openapi.IN_QUERY, description="Numéro de page", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'limit', openapi.IN_QUERY, description="Nombre d'éléments par page", type=openapi.TYPE_INTEGER
            ),
        ],
        responses={
            200: openapi.Response(
                description="Liste des avis reçus",
                examples={
                    "application/json": {
                        "success": True,
                        "avis": [
                            {
                                "id": 10,
                                "note": 5,
                                "commentaire": "Excellent service",
                                "date_creation": "2025-08-15T04:51:21.558555+00:00",
                                "auteur_nom": "test",
                                "auteur_photo": None,
                                "bien_nom": "Toyota test",
                                "note_proprete": 4,
                                "note_communication": 4,
                                "note_emplacement": 4,
                                "note_qualite_prix": 4
                            }
                        ],
                        "pagination": {
                            "page": 1,
                            "pages": 1,
                            "total": 2,
                            "has_next": False,
                            "has_previous": False
                        }
                    }
                }
            ),
            404: "Utilisateur non trouvé"
        }
    )
    
    def get(self, request, user_id):
        try:
            print(f"📝 AvisRecusProprietaireView: Test pour user_id: {user_id}")
            
            # Version de test avec vraies données de la base
            User = get_user_model()
            try:
                proprietaire = User.objects.get(id=user_id)
                print(f"✅ Utilisateur trouvé: {proprietaire.username}")
                
                # Récupérer les biens du propriétaire
                biens_proprietaire = Bien.objects.filter(owner=proprietaire)
                print(f"🏠 Biens trouvés: {biens_proprietaire.count()}")
                
                # Récupérer les avis
                avis_queryset = Avis.objects.filter(bien__in=biens_proprietaire)
                total_avis = avis_queryset.count()
                print(f"💬 Avis trouvés: {total_avis}")
                
                # Récupérer tous les avis avec leurs vraies données
                avis_data = []
                for avis in avis_queryset:
                    # Récupérer la première image du bien
                    bien_image = None
                    try:
                        if hasattr(avis.bien, 'media') and avis.bien.media.exists():
                            premiere_media = avis.bien.media.first()
                            if premiere_media and hasattr(premiere_media, 'image'):
                                bien_image = request.build_absolute_uri(premiere_media.image.url)
                    except Exception as e:
                        print(f"⚠️ Erreur récupération image pour bien {avis.bien.id}: {e}")
                        bien_image = None
                    
                    avis_data.append({
                        'id': avis.id,
                        'note': avis.note,
                        'commentaire': avis.commentaire or '',
                        'date_creation': avis.created_at.isoformat(),
                        'auteur_nom': avis.user.username if avis.user else 'Utilisateur',
                        'bien_nom': avis.bien.nom if avis.bien else 'Bien',
                        'bien_image': bien_image,
                        'note_proprete': getattr(avis, 'note_proprete', None),
                        'note_communication': getattr(avis, 'note_communication', None),
                        'note_emplacement': getattr(avis, 'note_emplacement', None),
                        'note_qualite_prix': getattr(avis, 'note_rapport_qualite_prix', None),
                    })
                
                return Response({
                    'success': True,
                    'avis': avis_data,
                    'pagination': {
                        'page': 1,
                        'pages': 1,
                        'total': total_avis,
                        'has_next': False,
                        'has_previous': False
                    }
                })
                
            except User.DoesNotExist:
                print(f"❌ Utilisateur ID {user_id} non trouvé")
                return Response({
                    'success': True,
                    'avis': [],
                    'pagination': {'page': 1, 'pages': 0, 'total': 0, 'has_next': False, 'has_previous': False}
                })
                
        except Exception as e:
            print(f"❌ AvisRecusProprietaireView: Erreur: {e}")
            return Response(
                {'success': False, 'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )