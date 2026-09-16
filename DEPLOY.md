# 🚀 Déployer l'appli en ligne (gratuit)

On met l'appli sur **Streamlit Community Cloud**. Le code va sur **GitHub**,
Streamlit le lit et héberge l'appli. Résultat : un lien à partager au club.

---

## Étape 1 — Vérifier que la clé n'ira PAS sur GitHub

Ouvre le fichier `.gitignore` : il doit contenir `.env` et `.venv/`.
👉 C'est déjà le cas dans ton projet. Ta clé API reste donc privée.

---

## Étape 2 — Mettre le projet sur GitHub

### Option A — avec l'interface de VS Code (le plus simple)
1. Clique sur l'icône **Source Control** dans la barre de gauche (les branches).
2. Clique **Initialize Repository**.
3. Écris un message (ex. « premier commit ») et clique **Commit**.
4. Clique **Publish Branch** → choisis **private** (dépôt privé) → VS Code crée
   le dépôt sur ton compte GitHub et pousse le code.

### Option B — en ligne de commande
```bash
git init
git add .
git commit -m "premier commit"
```
Crée ensuite un dépôt vide sur https://github.com/new (sans README), puis :
```bash
git remote add origin https://github.com/TON_PSEUDO/finance-bot.git
git branch -M main
git push -u origin main
```

> Vérifie sur github.com que ton dépôt **ne contient pas** de fichier `.env`.
> S'il y est, c'est que le `.gitignore` n'a pas été pris en compte — dis-le moi.

---

## Étape 3 — Déployer sur Streamlit Cloud
1. Va sur **https://share.streamlit.io** et connecte-toi **avec GitHub**.
2. Clique **Create app** → **Deploy a public app from GitHub**.
3. Renseigne :
   - **Repository** : `TON_PSEUDO/finance-bot`
   - **Branch** : `main`
   - **Main file path** : `app.py`
4. Avant de lancer, clique **Advanced settings ▸ Secrets** et colle :
   ```toml
   GEMINI_API_KEY = "colle_ta_cle_ici"
   ```
   (format TOML, avec les guillemets.)
5. Clique **Deploy**. Patiente 1-2 minutes → ton appli est en ligne. 🎉

---

## Étape 4 — Partager
Tu obtiens une URL du type `https://ton-appli.streamlit.app`.
C'est ce lien que tu envoies au club — ça marche depuis n'importe quel navigateur.

---

## En cas de souci
- **L'appli plante avec « clé manquante »** → tu as oublié le secret à l'étape 3.4.
  Va dans les réglages de l'app (menu ⋮ ▸ Settings ▸ Secrets) et ajoute la clé.
- **Une librairie manque** → vérifie que `requirements.txt` est bien sur GitHub.
- **Tu changes le code plus tard** → un simple `git push` (ou Commit + Sync dans
  VS Code) met l'appli en ligne à jour automatiquement.
