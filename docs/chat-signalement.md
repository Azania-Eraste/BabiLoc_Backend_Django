# Signalement de chat — Guide d'utilisation (Flutter)

Ce document explique comment utiliser l'API de signalement de salon de chat depuis une application Flutter. Il couvre l'endpoint, le format des requêtes/réponses, un exemple complet en Dio, et les cas d'erreur courants.

## Endpoints disponibles

- POST /api/chat/signalement/ — créer un signalement (auth requis)
  - Headers : `Authorization: Bearer <token>` (JWT)
  - Payload (JSON) :
    - `chat_room_supabase_id` (string, requis) — identifiant Supabase de la room ou l'identifiant unique utilisé par le service de chat.
    - `message` (string, optionnel) — raison du signalement (comportement, contenu, spam, etc.)

## Réponse attendue

- Succès (201 Created)

```json
{
  "success": true,
  "data": { "id": 123 }
}
```

- Erreur (400 Bad Request)

```json
{
  "success": false,
  "errors": { "chat_room_supabase_id": ["Salon de chat introuvable."] }
}
```

## Exemple Flutter (Dio)

Voici une fonction réutilisable que tu peux ajouter dans ton service de communication (par ex. `Bien_service_Api.dart` ou `Chat_service.dart`). Elle reprend la logique de token que tu utilises déjà dans le projet :

```dart
import 'package:dio/dio.dart';
import 'package:babiloc/services/api_service.dart';

class ChatService {
  /// Crée un signalement pour une room de chat.
  /// Retourne la Map de résultat {'success': bool, 'data' or 'error'}
  static Future<Map<String, dynamic>> signalerRoom({
    required String chatRoomSupabaseId,
    String? message,
  }) async {
    String? token = await ApiService.storage.read(key: 'auth_token');

    final payload = {
      'chat_room_supabase_id': chatRoomSupabaseId,
      if (message != null) 'message': message,
    };

    try {
      final response = await ApiService.dio.post(
        '/api/chat/signalement/',
        data: payload,
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );

      if (response.statusCode == 201) {
        return {'success': true, 'data': response.data['data']};
      }

      return {'success': false, 'error': response.data};
    } on DioException catch (e) {
      final resp = e.response;
      if (resp != null && resp.statusCode == 400) {
        return {'success': false, 'error': resp.data};
      }
      return {'success': false, 'error': e.message};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }
}
```

## Utilisation depuis l'UI Flutter

```dart
final result = await ChatService.signalerRoom(
  chatRoomSupabaseId: 'room-abc-123',
  message: 'Comportement inapproprié de l\'utilisateur',
);

if (result['success']) {
  // Afficher confirmation à l'utilisateur
} else {
  // Afficher l'erreur
}
```

## Cas d'erreur et conseils

- 401 Unauthorized : le token est absent ou invalide — invite l'utilisateur à se reconnecter.
- 400 Bad Request : paramètres invalides (par ex. `chat_room_supabase_id` introuvable) — afficher le message retourné.
- 5xx / erreurs réseau : réessayer et afficher une erreur générique.

## Admin UI

Un tableau d'administration est disponible sur le backend (uniquement pour les utilisateurs admin) :

- GET HTML : `/chat/signalements/` — liste paginée des signalements.
- Détail + action marquer traité : `/chat/signalements/<id>/` (POST pour marquer traité).

## Améliorations possibles

- Rate-limiting côté API pour éviter le spam.
- Notifications internes (model Notification) pour conserver l'historique des alertes plutôt que dépendre d'emails.
- Webhook / message temps réel vers une console admin.

Si tu veux, je peux aussi :

- ajouter un exemple complet Flutter widget pour la page de signalement,
- créer la migration et un test unitaire pour l'API.
