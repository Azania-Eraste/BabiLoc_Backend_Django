# 🧪 Test de l'endpoint /api/location/reservations-bien/

## 📋 **Guide de Test**

### **1. Prérequis**
- Serveur Django en cours d'exécution
- Base de données avec au moins un bien et quelques réservations
- Token d'authentification valide

### **2. Tests à effectuer**

#### **Test 1: Récupération des réservations confirmées (défaut)**
```bash
curl -X GET \
  "http://localhost:8000/api/location/reservations-bien/?bien_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

**Réponse attendue :**
```json
{
  "success": true,
  "reservations": [
    {
      "id": 1,
      "date_debut": "2025-08-10",
      "date_fin": "2025-08-15",
      "statut": "confirmed",
      "utilisateur_nom": "Jean Dupont",
      "prix_total": 250.0,
      "created_at": "2025-08-01 10:30:00"
    }
  ],
  "count": 1,
  "bien_info": {
    "id": 1,
    "titre": "Appartement moderne Cocody",
    "proprietaire": "Marie Martin"
  }
}
```

#### **Test 2: Récupération de toutes les réservations (sauf annulées)**
```bash
curl -X GET \
  "http://localhost:8000/api/location/reservations-bien/?bien_id=1&statut=all" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

#### **Test 3: Récupération des réservations en attente**
```bash
curl -X GET \
  "http://localhost:8000/api/location/reservations-bien/?bien_id=1&statut=pending" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

#### **Test 4: Erreur - bien_id manquant**
```bash
curl -X GET \
  "http://localhost:8000/api/location/reservations-bien/" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

**Réponse attendue :**
```json
{
  "success": false,
  "error": "Le paramètre bien_id est obligatoire"
}
```

#### **Test 5: Erreur - bien inexistant**
```bash
curl -X GET \
  "http://localhost:8000/api/location/reservations-bien/?bien_id=99999" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

**Réponse attendue :**
```json
{
  "success": false,
  "error": "Aucun bien trouvé avec l'ID 99999"
}
```

### **3. Tests depuis l'application Flutter**

#### **Vérification dans la console Flutter :**
1. Ouvrir l'application Flutter en mode debug
2. Naviguer vers la page de réservation d'un bien
3. Vérifier les logs dans la console :

```
🏠 Réservations du bien 1: {success: true, reservations: [...], count: 2}
✅ 2 réservations chargées pour ce bien
```

#### **Vérification visuelle :**
1. **Si aucune réservation :** Bordure verte avec "Aucune réservation - Disponible"
2. **Si réservations existantes :** Bordure orange avec liste des périodes réservées
3. **Test de conflit :** Sélectionner des dates qui chevauchent → Message d'erreur

### **4. Tests de Performance**

#### **Test avec beaucoup de réservations :**
```sql
-- Créer des données de test (à exécuter dans la base Django)
INSERT INTO reservation_reservation 
(bien_id, user_id, date_debut, date_fin, status, prix_total, created_at, updated_at)
VALUES 
(1, 1, '2025-08-01', '2025-08-05', 'confirmed', 200.00, NOW(), NOW()),
(1, 2, '2025-08-10', '2025-08-15', 'confirmed', 300.00, NOW(), NOW()),
(1, 3, '2025-08-20', '2025-08-25', 'pending', 250.00, NOW(), NOW()),
(1, 4, '2025-09-01', '2025-09-05', 'confirmed', 200.00, NOW(), NOW());
```

### **5. Logs à surveiller**

#### **Côté Django (dans debug.log) :**
```
INFO - Réservations bien 1: 3 trouvées (statut: confirmed)
```

#### **Côté Flutter (dans la console) :**
```
🔍 obtenirReservationsBien - URL complète: http://localhost:8000/api/location/reservations-bien/?bien_id=1&statut=confirmed
📡 obtenirReservationsBien - Status: 200
📊 obtenirReservationsBien - Response: {"success":true,"reservations":[...],"count":3}
```

### **6. Sécurité**

#### **Test d'authentification :**
```bash
curl -X GET \
  "http://localhost:8000/api/location/reservations-bien/?bien_id=1" \
  -H "Content-Type: application/json"
```

**Réponse attendue :** Status 401 Unauthorized

### **7. Dépannage**

#### **Problèmes courants :**

1. **404 Not Found :**
   - Vérifier que l'URL est bien `/api/location/reservations-bien/`
   - Vérifier que la route est ajoutée dans `urls.py`

2. **500 Internal Server Error :**
   - Vérifier les logs Django pour l'erreur exacte
   - Vérifier que les imports sont corrects
   - Vérifier que le modèle Bien existe

3. **Pas de données côté Flutter :**
   - Vérifier que `bienId` est bien passé au widget BookingPage
   - Vérifier que l'URL de base est correcte dans la configuration

#### **Commandes de diagnostic :**
```bash
# Vérifier les URLs Django
python manage.py show_urls | grep reservations

# Vérifier les migrations
python manage.py showmigrations

# Tester la connexion à la base
python manage.py shell
>>> from reservation.models import Bien, Reservation
>>> Bien.objects.all()
>>> Reservation.objects.all()
```

### **8. Optimisations Futures**

1. **Cache Redis :** Mettre en cache les réservations fréquemment consultées
2. **Pagination :** Pour les biens avec beaucoup de réservations
3. **Filtres avancés :** Par date, type de réservation, etc.
4. **WebSocket :** Mise à jour en temps réel des disponibilités

---

**🎯 Objectif :** Cet endpoint doit retourner les réservations d'un bien en moins de 200ms pour garantir une UX fluide sur l'application mobile.
