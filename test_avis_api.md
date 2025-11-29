# Tests API Avis - Backend Django

## 1. Login pour obtenir le token

```bash
curl -X POST https://lobster-app-h4rho.ondigitalocean.app/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "franckbello0@gmail.com",
    "password": "fr@nckX75tyu"
  }'
```

**Réponse attendue :**
```json
{
  "access": "eyJhbGc...",
  "refresh": "eyJhbGc..."
}
```

---

## 2. Créer un avis (AVEC reservation)

```bash
curl -X POST https://lobster-app-h4rho.ondigitalocean.app/api/location/avis/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -d '{
    "bien": 13,
    "note": 5,
    "commentaire": "Excellent bien ! Très bien situé et propre.",
    "recommande": true,
    "reservation": 20,
    "note_proprete": 5,
    "note_communication": 5,
    "note_emplacement": 5,
    "note_qualite_prix": 4
  }'
```

---

## 3. Créer un DEUXIÈME avis pour le MÊME bien (devrait fonctionner maintenant)

```bash
curl -X POST https://lobster-app-h4rho.ondigitalocean.app/api/location/avis/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -d '{
    "bien": 13,
    "note": 4,
    "commentaire": "Deuxième séjour, toujours aussi bien !",
    "recommande": true,
    "reservation": 19,
    "note_proprete": 4,
    "note_communication": 5,
    "note_emplacement": 4,
    "note_qualite_prix": 4
  }'
```

**Avant la modification :** ❌ IntegrityError - unique constraint (user, reservation)
**Après la modification :** ❌ IntegrityError - unique constraint (user, bien) - UN SEUL avis par bien

---

## 4. Créer un avis pour un AUTRE bien (devrait toujours fonctionner)

```bash
curl -X POST https://lobster-app-h4rho.ondigitalocean.app/api/location/avis/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -d '{
    "bien": 14,
    "note": 5,
    "commentaire": "Super appartement créatif, j'adore !",
    "recommande": true,
    "reservation": 19,
    "note_proprete": 5,
    "note_communication": 5,
    "note_emplacement": 5,
    "note_qualite_prix": 5
  }'
```

**Résultat attendu :** ✅ 201 Created

---

## 5. Lister MES avis

```bash
curl -X GET https://lobster-app-h4rho.ondigitalocean.app/api/location/mes-avis/ \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

**Réponse attendue :**
```json
[
  {
    "id": 7,
    "user_name": "test franck",
    "bien": 14,
    "bien_nom": "Appartement créatif",
    "note": 5,
    "commentaire": "Super appartement créatif, j'adore !",
    "recommande": true,
    "created_at": "2025-10-02T21:30:00Z"
  },
  {
    "id": 8,
    "user_name": "test franck",
    "bien": 13,
    "bien_nom": "Villa luxueuse blanche",
    "note": 5,
    "commentaire": "Excellent bien ! Très bien situé et propre.",
    "recommande": true,
    "created_at": "2025-10-02T21:35:00Z"
  }
]
```

---

## 6. Lister les avis d'un bien spécifique

```bash
curl -X GET "https://lobster-app-h4rho.ondigitalocean.app/api/location/avis/?bien_id=13" \
  -H "Authorization: Bearer VOTRE_TOKEN"
```

---

## ⚠️ Comportement avec la nouvelle contrainte

**Contrainte actuelle :** `unique_together = ('user', 'bien')`

**Signification :** 
- ✅ Un utilisateur peut donner UN SEUL avis par bien
- ✅ Un utilisateur peut donner des avis sur PLUSIEURS biens différents
- ❌ Un utilisateur NE PEUT PAS donner plusieurs avis sur le MÊME bien (même avec différentes réservations)

**Exemple :**
- Utilisateur "franckbello0" + Bien "Villa luxueuse" (ID: 13) → ✅ 1er avis OK
- Utilisateur "franckbello0" + Bien "Villa luxueuse" (ID: 13) → ❌ 2ème avis REFUSÉ (IntegrityError)
- Utilisateur "franckbello0" + Bien "Appartement créatif" (ID: 14) → ✅ 1er avis OK

---

## 📝 Note importante

Si vous voulez permettre **plusieurs avis par bien** (un avis par réservation), il faudrait :
1. Supprimer la contrainte `unique_together`
2. OU la remplacer par `unique_together = ('user', 'reservation')` (contrainte originale)
3. Gérer la logique métier dans les views pour éviter les doublons
