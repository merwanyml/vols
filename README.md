# ✈️ Détecteur d'offres de vols (100 % gratuit)

Chaque jour, GitHub lance le script, qui teste des centaines de combinaisons
(aéroports × destinations × dates), compare les prix à l'historique et
t'envoie une notification sur ton téléphone quand un prix sort du lot.

## Installation (environ 20 minutes, une seule fois)

### 1. Créer ton compte et ton dépôt GitHub
1. Va sur https://github.com et crée un compte gratuit.
2. Clique sur **New repository**, nomme-le `vols`, choisis **Public**
   (c'est ce qui rend GitHub Actions illimité et gratuit), puis **Create**.
   Ne mets aucune information personnelle dans les fichiers : ton adresse
   de notification sera stockée à part, dans un secret (étape 3).
3. Sur la page du dépôt : **Add file → Upload files**, glisse tout le contenu de ce
   dossier (y compris le dossier caché `.github`, voir remarque plus bas), puis **Commit changes**.

> Remarque : si le dossier `.github` n'apparaît pas dans ton explorateur de fichiers,
> c'est qu'il est masqué. Sinon, crée le fichier à la main sur GitHub :
> **Add file → Create new file**, tape `.github/workflows/daily.yml` comme nom
> et colle le contenu du fichier.

### 2. Installer ntfy sur ton téléphone (gratuit)
1. Installe l'appli **ntfy** (App Store ou Google Play).
2. Invente un nom de « canal » difficile à deviner, par exemple `vols-merwan-k8x2p9`.
   Ce nom sert de mot de passe : n'importe qui le connaissant peut lire tes alertes.
3. Dans l'appli : **+** puis saisis ce nom de canal pour t'y abonner.

### 3. Donner le nom du canal à GitHub
Dans ton dépôt : **Settings → Secrets and variables → Actions → New repository secret**
- Nom : `NTFY_TOPIC`
- Valeur : ton nom de canal (ex. `vols-merwan-k8x2p9`)

### 4. (Optionnel) Recevoir aussi un mail
Crée un « mot de passe d'application » Gmail (compte Google → Sécurité → Validation en
2 étapes → Mots de passe des applications), puis ajoute deux secrets :
`GMAIL_USER` (ton adresse) et `GMAIL_APP_PASSWORD` (le mot de passe généré).

### 5. Premier lancement
Onglet **Actions** → **Chercher les offres de vols** → **Run workflow**,
coche « Envoyer une notification de test ». Après quelques minutes, tu dois recevoir
le message de test sur ton téléphone.

Si l'exécution est en rouge : clique dessus, copie le texte de l'erreur et envoie-le-moi,
je corrige. C'est normal que la première exécution demande un ajustement.

## Utilisation au quotidien

Tout se règle dans `config.yaml` (modifiable directement sur GitHub, bouton crayon) :
- ajouter un aéroport : ajoute son code dans `aeroports_week_end` ou `aeroports_long_courrier`
- changer les jours de week-end, la durée des longs séjours, les destinations
- rendre l'outil plus ou moins sélectif : `reduction_minimum`

## Comment il décide qu'une offre est bonne

- Après quelques semaines, il connaît le prix habituel de chaque route et te prévient
  quand le tarif est nettement en dessous (30 % par défaut).
- Dès le premier jour, tu es aussi prévenu si un prix passe sous le plafond
  `prix_max_alerte` du config (60 € pour un week-end, 400 € pour un long séjour,
  à ajuster selon ton ressenti).
- Les premières semaines, il y aura plus de fausses alertes ou de silences : l'historique
  se construit petit à petit.

## Limites à connaître
- Il ne teste pas toutes les combinaisons chaque jour (limite de 250 recherches), mais
  tire au hasard : sur plusieurs jours, tout est couvert.
- Il utilise Google Flights de façon non officielle : ça peut tomber en panne si Google
  change quelque chose. Dans ce cas, reviens me voir avec le message d'erreur.
- Les prix peuvent changer entre l'alerte et ta réservation : vérifie toujours via le
  lien dans la notification.
