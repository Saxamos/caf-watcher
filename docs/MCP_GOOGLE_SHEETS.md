# Configurer le MCP Google Sheets avec ton compte perso

Ce guide permet de connecter Cursor à Google Sheets via **OAuth 2.0** (compte Google personnel), sans Service Account.

## 1. Google Cloud Console

1. Va sur [Google Cloud Console](https://console.cloud.google.com/).
2. **Créer ou sélectionner un projet** (ex. "Mon MCP Sheets").
3. **Activer les APIs**  
   Menu **APIs & Services** → **Library** → active :
   - **Google Sheets API**
   - **Google Drive API**
4. **Écran de consentement OAuth**  
   **APIs & Services** → **OAuth consent screen** :
   - Type : **External**
   - Nom de l’app : ex. "MCP Sheets"
   - Email de support : ton email
   - **Scopes** : ajoute  
     `https://www.googleapis.com/auth/spreadsheets`  
     `https://www.googleapis.com/auth/drive`
   - **Test users** : ajoute ton adresse Google (ex. samuel.rochette06@gmail.com)
5. **Créer des identifiants OAuth**  
   **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID** :
   - Type : **Desktop app**
   - Nom : ex. "MCP Sheets Desktop"
   - **Create** → **Download JSON**
6. **Renommer le fichier** en `credentials.json` et le mettre dans un dossier dédié, par ex. :
   ```
   ~/.config/mcp-google-sheets/credentials.json
   ```
   (ou `~/PycharmProjects/SAM/caf-watcher/.config/mcp-google-sheets/` si tu préfères dans le projet.)

## 2. Installer uv (si besoin)

Tu utilises déjà `uv` pour caf-watcher. Vérifie que `uvx` est dispo :

```bash
which uvx
# ou
uvx --version
```

Si besoin : <https://astral.sh/uv>

## 3. Premier lancement (génération du token)

Une seule fois, il faut faire un login Google pour créer `token.json` :

```bash
mkdir -p ~/.config/mcp-google-sheets
# Mets credentials.json dans ce dossier, puis :
export CREDENTIALS_PATH="$HOME/.config/mcp-google-sheets/credentials.json"
export TOKEN_PATH="$HOME/.config/mcp-google-sheets/token.json"
uvx mcp-google-sheets@latest
```

Une page Google s’ouvre dans le navigateur : connecte-toi avec ton compte perso et autorise l’app.  
Ensuite le serveur MCP peut tourner ; tu peux l’arrêter (Ctrl+C). Le fichier `token.json` a été créé et sera réutilisé.

## 4. Config Cursor (MCP)

- **Global** (tous les projets) : `~/.cursor/mcp.json`
- **Projet** : `.cursor/mcp.json` à la racine du projet

Ouvre les paramètres MCP : **Cmd+Shift+P** (ou Ctrl+Shift+P) → "Open MCP Settings", ou édite directement le fichier.

Exemple pour **OAuth** (compte perso) :

```json
{
  "mcpServers": {
    "google-sheets": {
      "command": "uvx",
      "args": ["mcp-google-sheets@latest"],
      "env": {
        "CREDENTIALS_PATH": "/Users/samos/.config/mcp-google-sheets/credentials.json",
        "TOKEN_PATH": "/Users/samos/.config/mcp-google-sheets/token.json"
      }
    }
  }
}
```

Remplace `/Users/samos` par ton vrai `$HOME` si différent.

Sur macOS, si Cursor ne trouve pas `uvx`, utilise le chemin complet :

```json
"command": "/Users/samos/.local/bin/uvx",
```

(trouve le chemin avec `which uvx`.)

## 5. Redémarrer Cursor

Ferme et rouvre Cursor (ou recharge la fenêtre) pour que le MCP soit pris en compte.

## 6. Vérifier que ça marche

Dans le chat Cursor, tu devrais pouvoir demander par exemple :

- "Liste les spreadsheets auxquels j’ai accès."
- "Crée une feuille nommée Test MCP."
- "Dans la feuille [nom], lis la plage A1:C5."

Si une erreur s’affiche, vérifie :

- Que `credentials.json` et `token.json` sont aux chemins indiqués dans `mcp.json`.
- Que l’email du compte Google utilisé est bien dans les "Test users" de l’écran de consentement OAuth.
- Que les deux APIs (Sheets + Drive) sont activées sur le projet GCP.

## Références

- [mcp-google-sheets (xing5)](https://github.com/xing5/mcp-google-sheets) – serveur MCP utilisé ici.
- [Cursor – Model Context Protocol (MCP)](https://cursor.com/docs/context/mcp)
