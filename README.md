# 💰 Bot Financier — Étape 1

Un assistant financier pédagogique propulsé par **Gemini** (gratuit).
Deux versions : une en terminal pour comprendre le cœur (`chat.py`), une avec
interface web pour la démo du club (`app.py`).

---

## 🗺️ Vue d'ensemble (comment ça marche)

```
Toi (question)  ──▶  app.py / chat.py  ──▶  API Gemini  ──▶  réponse  ──▶  affichée
                         (ton code)         (le "cerveau")
```

Ton code ne "pense" pas : il envoie la question au modèle Gemini via internet et
affiche la réponse. Le fichier `.env` garde ta clé secrète à part du code.

---

## ✅ Étapes d'installation (à faire une seule fois)

### 1. Récupérer une clé API Gemini (gratuit)
1. Va sur **https://aistudio.google.com/apikey** (connecte-toi avec ton compte Google).
2. Clique sur **"Create API key"**.
3. Copie la clé (une longue suite de caractères).

### 2. Préparer le projet dans VS Code
Ouvre le dossier `finance-bot` dans VS Code, puis ouvre un terminal
(**Terminal ▸ New Terminal**) et tape ces commandes une par une :

```bash
# Crée un environnement Python isolé (bonne pratique : n'installe rien globalement)
python3 -m venv .venv

# Active-le  (Mac/Linux)
source .venv/bin/activate
#  ⤷ sous Windows ce serait :  .venv\Scripts\activate

# Installe les librairies nécessaires
pip install -r requirements.txt
```

### 3. Mettre ta clé dans le fichier .env
1. Duplique le fichier `.env.example` et renomme la copie en **`.env`**.
2. Remplace `colle_ta_cle_ici` par ta vraie clé (sans guillemets, sans espace).
3. Ne partage jamais ce fichier (le `.gitignore` l'empêche déjà d'aller sur GitHub).

---

## ▶️ Lancer le bot

**Version terminal (pour comprendre le cœur) :**
```bash
python chat.py
```
Pose une question (ex. *« C'est quoi un ratio cours/bénéfice ? »*), tape `quit` pour arrêter.

**Version démo (pour la présentation) :**
```bash
streamlit run app.py
```
Une page web s'ouvre. C'est ça que tu montres au club. 🎤

---

## 🛠️ En cas de souci

- **`model not found`** → lance `python list_models.py`, copie un nom de modèle
  contenant `flash`, et colle-le dans la variable `MODEL` de `chat.py` et `app.py`.
- **`No API key found`** → vérifie que le fichier s'appelle bien `.env` (pas `.env.txt`)
  et qu'il contient `GEMINI_API_KEY=...`.
- **`command not found: streamlit`** → vérifie que ton environnement `.venv` est activé
  (tu dois voir `(.venv)` au début de la ligne du terminal).

---

## 🔜 La suite (prochaines étapes)

1. **RAG** : le bot lit des PDF/actus et répond en citant ses sources.
2. **Module marché** : récupérer des cours (`yfinance`), calculer des indicateurs.
3. **Perso** : basculer sur un modèle local (Ollama sur ton Mac Mini M4) pour
   traiter tes données bancaires en privé.

> ⚠️ Rappel : ce bot est un projet d'apprentissage. Il ne remplace pas un conseil
> financier professionnel.
