# Guide : Appliquer la migration sur DigitalOcean

## 🚀 Méthode 1 : Auto-déploiement (Le plus simple)

### Étape 1 : Vérifier le déploiement automatique

1. Allez sur **DigitalOcean Dashboard** : https://cloud.digitalocean.com/apps
2. Sélectionnez votre application **BabiLoc Backend**
3. Vérifiez dans **Settings → App-Level** si l'auto-deploy est activé pour la branche `babiloc_v0`

Si c'est activé, votre app va automatiquement :
- ✅ Récupérer le dernier code de GitHub
- ✅ Appliquer les migrations pendant le build
- ✅ Redémarrer l'application

### Étape 2 : Forcer un nouveau déploiement

Si l'auto-deploy n'est pas activé ou ne se déclenche pas :

1. Dans le Dashboard DigitalOcean, allez dans votre app
2. Cliquez sur **"Actions"** → **"Force Rebuild and Deploy"**
3. Attendez la fin du déploiement (5-10 minutes)

---

## 🔧 Méthode 2 : Via la Console SSH

### Étape 1 : Se connecter en SSH

```bash
# Trouvez le nom de votre conteneur
doctl apps list

# Connectez-vous au conteneur
doctl apps exec YOUR_APP_ID --component backend -- /bin/bash
```

### Étape 2 : Appliquer la migration

```bash
# Une fois connecté dans le conteneur
python manage.py migrate reservation

# Vérifier que la migration est appliquée
python manage.py showmigrations reservation
```

**Sortie attendue :**
```
reservation
 ...
 [X] 0026_merge_0024_alter_tarif_created_at_0024_bien_tags_and_more
 [X] 0027_alter_avis_unique_together
```

---

## 📝 Méthode 3 : Via Run Command (DigitalOcean)

### Étape 1 : Ouvrir la Console

1. Allez dans **DigitalOcean Dashboard** → Votre App
2. Cliquez sur **"Console"** en haut à droite
3. Sélectionnez le composant **backend** ou **web**

### Étape 2 : Exécuter la commande

Dans la console web qui s'ouvre :

```bash
python manage.py migrate reservation
```

---

## ✅ Vérifier que la migration est appliquée

### Test 1 : Créer un avis via l'app Flutter

1. Ouvrez l'app Flutter
2. Allez dans "Mes Réservations"
3. Ouvrez une réservation terminée
4. Cliquez sur "Donner un avis"
5. Remplissez le formulaire et envoyez

**Résultat attendu :**
- ✅ 201 Created (Avis créé avec succès)
- ❌ Si vous avez déjà donné un avis pour ce BIEN → IntegrityError "unique constraint (user, bien)"

### Test 2 : Via l'API directement

```bash
curl -X POST "https://lobster-app-h4rho.ondigitalocean.app/api/location/avis/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer VOTRE_TOKEN" \
  -d '{
    "bien": 15,
    "note": 5,
    "commentaire": "Test après migration",
    "recommande": true,
    "reservation": 20,
    "note_proprete": 5,
    "note_communication": 5,
    "note_emplacement": 5,
    "note_qualite_prix": 5
  }'
```

---

## 🔍 Vérifier les logs du serveur

Pour voir si la migration s'est bien passée :

1. **DigitalOcean Dashboard** → Votre App
2. Cliquez sur **"Runtime Logs"**
3. Cherchez des lignes comme :
   ```
   Running migrations:
     Applying reservation.0027_alter_avis_unique_together... OK
   ```

---

## ⚠️ En cas de problème

### Erreur : "Migration already applied"

C'est bon signe ! Cela signifie que la migration est déjà appliquée.

### Erreur : "Table does not exist"

Appliquez toutes les migrations :
```bash
python manage.py migrate
```

### Erreur : "IntegrityError" lors de l'application

Il y a des données qui violent la nouvelle contrainte. Solution :

```bash
# Se connecter au shell Django
python manage.py shell

# Supprimer les avis en double (gardez le plus récent)
from reservation.models import Avis
from django.db.models import Count

# Trouver les doublons (user + bien)
doublons = Avis.objects.values('user', 'bien').annotate(
    count=Count('id')
).filter(count__gt=1)

print(f"Nombre de doublons trouvés : {len(doublons)}")

# Pour chaque doublon, garder le plus récent et supprimer les autres
for doublon in doublons:
    avis_list = Avis.objects.filter(
        user_id=doublon['user'],
        bien_id=doublon['bien']
    ).order_by('-created_at')
    
    # Garder le premier (plus récent), supprimer les autres
    avis_a_supprimer = avis_list[1:]
    for avis in avis_a_supprimer:
        print(f"Suppression avis {avis.id}")
        avis.delete()
```

---

## 📌 Notes importantes

1. **La migration est NON-DESTRUCTIVE** : Elle ne supprime aucune donnée, elle change juste la contrainte d'unicité
2. **Les avis existants ne seront pas affectés** sauf s'il y a des doublons
3. **Après la migration**, un utilisateur ne pourra donner qu'UN SEUL avis par bien (au lieu d'un par réservation)

---

## 🎯 Commande rapide (si vous avez doctl installé)

```bash
# Déployer automatiquement
doctl apps create-deployment YOUR_APP_ID

# OU forcer un rebuild
doctl apps update YOUR_APP_ID --force-rebuild
```
