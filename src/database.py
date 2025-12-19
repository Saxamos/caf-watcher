#!/usr/bin/env python3
"""
Gestion de la base de données SQLite pour les sorties CAF
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class SortiesDB:
    def __init__(self, db_path: str = "data/sorties.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def get_connection(self):
        """Crée une connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_backup(self) -> str:
        """Crée un backup de la base de données
        
        Returns:
            Path du fichier de backup créé
        """
        if not self.db_path.exists():
            return ""
        
        # Crée le dossier backups
        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Nom du backup avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"sorties_backup_{timestamp}.db"
        
        # Copie la DB
        shutil.copy2(self.db_path, backup_path)
        
        # Garde seulement les 10 derniers backups
        backups = sorted(backup_dir.glob("sorties_backup_*.db"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
        
        return str(backup_path)
    
    def init_db(self):
        """Initialise la base de données"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sorties (
                id TEXT PRIMARY KEY,
                activite TEXT NOT NULL,
                titre TEXT NOT NULL,
                lieu TEXT NOT NULL,
                date TEXT NOT NULL,
                niveau_physique INTEGER,
                niveau_technique INTEGER,
                places TEXT,
                contact TEXT,
                url TEXT,
                vu INTEGER DEFAULT 0,
                date_ajout TEXT NOT NULL,
                date_modification TEXT
            )
        """)
        
        # Index pour améliorer les performances
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vu ON sorties(vu)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_activite ON sorties(activite)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date ON sorties(date)
        """)
        
        conn.commit()
        conn.close()
    
    def upsert_sortie(self, sortie: Dict, force_update: bool = False) -> bool:
        """Insère ou met à jour une sortie
        
        Args:
            sortie: Dictionnaire avec les données de la sortie
            force_update: Si True, met à jour tous les champs même si la sortie existe
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Vérifie si la sortie existe déjà
            cursor.execute("SELECT vu FROM sorties WHERE id = ?", (sortie['id'],))
            existing = cursor.fetchone()
            
            if existing:
                if force_update:
                    # Met à jour TOUS les champs sauf 'vu' et 'date_ajout'
                    vu_status = sortie.get('vu', existing['vu'])
                    cursor.execute("""
                        UPDATE sorties SET
                            activite = ?,
                            titre = ?,
                            lieu = ?,
                            date = ?,
                            niveau_physique = ?,
                            niveau_technique = ?,
                            places = ?,
                            contact = ?,
                            url = ?,
                            vu = ?,
                            date_modification = ?
                        WHERE id = ?
                    """, (
                        sortie['activite'],
                        sortie['titre'],
                        sortie['lieu'],
                        sortie['date'],
                        sortie['niveau_physique'],
                        sortie['niveau_technique'],
                        sortie['places'],
                        sortie['contact'],
                        sortie.get('url', ''),
                        vu_status,
                        datetime.now().isoformat(),
                        sortie['id']
                    ))
                else:
                    # Met à jour seulement les champs qui peuvent changer, garde le statut 'vu'
                    cursor.execute("""
                        UPDATE sorties SET
                            places = ?,
                            contact = ?,
                            date_modification = ?
                        WHERE id = ?
                    """, (
                        sortie['places'],
                        sortie['contact'],
                        datetime.now().isoformat(),
                        sortie['id']
                    ))
                is_new = False
            else:
                # Insère une nouvelle sortie
                cursor.execute("""
                    INSERT INTO sorties (
                        id, activite, titre, lieu, date,
                        niveau_physique, niveau_technique, places, contact, url,
                        vu, date_ajout
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (
                    sortie['id'],
                    sortie['activite'],
                    sortie['titre'],
                    sortie['lieu'],
                    sortie['date'],
                    sortie['niveau_physique'],
                    sortie['niveau_technique'],
                    sortie['places'],
                    sortie['contact'],
                    sortie.get('url', ''),
                    datetime.now().isoformat()
                ))
                is_new = True
            
            conn.commit()
            return is_new
        finally:
            conn.close()
    
    def mark_as_seen(self, sortie_id: str, seen: bool = True):
        """Marque une sortie comme vue ou non vue"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sorties SET vu = ?, date_modification = ?
            WHERE id = ?
        """, (1 if seen else 0, datetime.now().isoformat(), sortie_id))
        
        conn.commit()
        conn.close()
    
    def mark_multiple_as_seen(self, sortie_ids: List[str], seen: bool = True):
        """Marque plusieurs sorties comme vues ou non vues"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(sortie_ids))
        cursor.execute(f"""
            UPDATE sorties SET vu = ?, date_modification = ?
            WHERE id IN ({placeholders})
        """, [1 if seen else 0, datetime.now().isoformat()] + sortie_ids)
        
        conn.commit()
        conn.close()
    
    def get_all_sorties(self, seen_filter: Optional[bool] = None) -> List[Dict]:
        """Récupère toutes les sorties, avec filtre optionnel"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if seen_filter is None:
            cursor.execute("SELECT * FROM sorties ORDER BY date_ajout DESC")
        else:
            cursor.execute(
                "SELECT * FROM sorties WHERE vu = ? ORDER BY date_ajout DESC",
                (1 if seen_filter else 0,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_sortie_by_id(self, sortie_id: str) -> Optional[Dict]:
        """Récupère une sortie par son ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sorties WHERE id = ?", (sortie_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_statistics(self) -> Dict:
        """Récupère des statistiques sur les sorties"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM sorties")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as vues FROM sorties WHERE vu = 1")
        vues = cursor.fetchone()['vues']
        
        cursor.execute("SELECT COUNT(*) as nouvelles FROM sorties WHERE vu = 0")
        nouvelles = cursor.fetchone()['nouvelles']
        
        cursor.execute("""
            SELECT activite, COUNT(*) as count
            FROM sorties
            GROUP BY activite
            ORDER BY count DESC
        """)
        par_activite = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total': total,
            'vues': vues,
            'nouvelles': nouvelles,
            'par_activite': par_activite
        }
    
    def search_sorties(self, 
                      activite: Optional[str] = None,
                      niveau_min: Optional[int] = None,
                      niveau_max: Optional[int] = None,
                      seen_filter: Optional[bool] = None) -> List[Dict]:
        """Recherche des sorties avec filtres"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM sorties WHERE 1=1"
        params = []
        
        if activite:
            query += " AND activite LIKE ?"
            params.append(f"%{activite}%")
        
        if niveau_min is not None:
            query += " AND (niveau_physique >= ? OR niveau_technique >= ?)"
            params.extend([niveau_min, niveau_min])
        
        if niveau_max is not None:
            query += " AND (niveau_physique <= ? OR niveau_technique <= ?)"
            params.extend([niveau_max, niveau_max])
        
        if seen_filter is not None:
            query += " AND vu = ?"
            params.append(1 if seen_filter else 0)
        
        query += " ORDER BY date_ajout DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

