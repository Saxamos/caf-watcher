#!/usr/bin/env python3
"""
Application Streamlit pour visualiser et gérer les sorties CAF Crest et FFCAM
"""

import streamlit as st
from src.database import SortiesDB
from src.ffcam_scraper import FFCAMScraper
from src.ffcam_formations_scraper import FFCAMFormationsScraper
from src.clubs import get_clubs
from datetime import datetime
import os

MOIS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")


def source_info(sortie_id: str) -> tuple[str, str]:
    """Retourne (emoji, label) de la source d'une sortie à partir de son ID."""
    if sortie_id.startswith("ffcam_form_"):
        return "📚", "FFCAM Formations"
    for club in get_clubs():
        if sortie_id.startswith(f"ffcam_{club['key']}_"):
            return "🏔️", club["label"]
    return "🌐", "FFCAM"


def scrape_all_clubs(db: SortiesDB) -> int:
    """Scrape tous les clubs FFCAM configurés et upsert les sorties. Retourne le nb de sorties traitées."""
    count = 0
    for club in get_clubs():
        try:
            scraper = FFCAMScraper(club_id=club["club_id"], club_label=club["label"], source_key=club["key"])
            for sortie in scraper.scrape_sorties():
                db.upsert_sortie(sortie)
                count += 1
        except Exception as e:
            print(f"❌ Erreur scraping {club['label']}: {e}")
    return count


def format_date_lecture(iso_date: str) -> str:
    """Formate une date ISO (2026-07-11T07:00:00.000Z) en format lisible (11 juil. 2026)."""
    if not iso_date:
        return iso_date or "—"
    try:
        s = iso_date.replace("Z", "+00:00").strip()
        if "T" in s:
            s = s.split("T")[0]
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return f"{dt.day} {MOIS[dt.month - 1]} {dt.year}"
    except (ValueError, TypeError):
        return iso_date

# Configuration de la page
st.set_page_config(
    page_title="CAF Crest - Sorties",
    page_icon="🏔️",
    layout="wide"
)

# Initialisation de la base de données
@st.cache_resource
def get_db():
    db_path = os.getenv('DB_PATH', '/data/sorties.db')
    return SortiesDB(db_path)

db = get_db()

# Scraping automatique au chargement de la page (une fois par session)
if "auto_scrape_done" not in st.session_state:
    with st.spinner("🔄 Mise à jour des sorties..."):
        try:
            scrape_all_clubs(db)
        except Exception:
            pass
        try:
            for sortie in FFCAMFormationsScraper().scrape_formations():
                db.upsert_sortie(sortie)
        except Exception:
            pass
    st.session_state["auto_scrape_done"] = True

# Titre principal
st.title("🏔️ CAF - Gestion des Sorties")

# Sidebar pour les filtres et statistiques
with st.sidebar:
    st.header("📊 Statistiques")
    stats = db.get_statistics()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total", stats['total'])
        st.metric("Nouvelles", stats['nouvelles'])
    with col2:
        st.metric("Vues", stats['vues'])
        if stats['total'] > 0:
            pourcentage = (stats['vues'] / stats['total']) * 100
            st.metric("% Vues", f"{pourcentage:.0f}%")

    st.divider()

    st.header("🔍 Filtres")

    # Filtre par statut (par défaut: Nouvelles uniquement)
    status_filter = st.radio(
        "Statut",
        ["Toutes", "Nouvelles uniquement", "Vues uniquement"],
        index=1,  # Par défaut: Nouvelles uniquement
        key="status_filter"
    )

    # Filtre par activité
    activites = ["Toutes"] + [a['activite'] for a in stats['par_activite']]
    activite_filter = st.selectbox("Activité", activites)

    # Filtre par niveau
    st.subheader("Niveau")
    niveau_min = st.slider("Niveau minimum", 0, 5, 0)
    niveau_max = st.slider("Niveau maximum", 0, 5, 5)

    st.divider()

    # Actions rapides
    st.header("⚡ Actions rapides")
    if st.button("✅ Tout marquer comme vu", use_container_width=True):
        sorties = db.get_all_sorties(seen_filter=False)
        if sorties:
            ids = [s['id'] for s in sorties]
            db.mark_multiple_as_seen(ids, seen=True)
            st.success(f"{len(ids)} sorties marquées comme vues")
            st.rerun()

    if st.button("🔄 Réinitialiser tout", use_container_width=True):
        sorties = db.get_all_sorties()
        if sorties:
            ids = [s['id'] for s in sorties]
            db.mark_multiple_as_seen(ids, seen=False)
            st.success("Toutes les sorties réinitialisées")
            st.rerun()

    # FFCAM : clubs suivis (plateforme ALPI, API publique sans authentification)
    st.divider()
    st.subheader("🌐 Clubs FFCAM suivis")
    for club in get_clubs():
        st.caption(f"🏔️ {club['label']} — `{club['club_id']}`")

    # Filtre par source
    st.divider()
    source_options = [c["label"] for c in get_clubs()] + ["FFCAM Formations"]
    source_filter = st.multiselect(
        "Source",
        source_options,
        default=source_options
    )

# Récupère les sorties en fonction des filtres
seen_filter_value = None
if status_filter == "Nouvelles uniquement":
    seen_filter_value = False
elif status_filter == "Vues uniquement":
    seen_filter_value = True

activite_search = None if activite_filter == "Toutes" else activite_filter

sorties = db.search_sorties(
    activite=activite_search,
    niveau_min=niveau_min if niveau_min > 0 else None,
    niveau_max=niveau_max if niveau_max < 5 else None,
    seen_filter=seen_filter_value
)

# Filtre par source
if source_filter and len(source_filter) < len(source_options):
    def keep_by_source(s):
        _, label = source_info(s['id'])
        return label in source_filter
    sorties = [s for s in sorties if keep_by_source(s)]

def display_sorties(db, sorties_list):
    """Affiche la liste des sorties"""
    for sortie in sorties_list:
        source_emoji, source_label = source_info(sortie['id'])

        # Couleur selon le statut
        if sortie['vu']:
            border_color = "#90EE90"  # Vert clair
            emoji_status = "✅"
        else:
            border_color = "#FFD700"  # Jaune/or
            emoji_status = "🆕"

        # Container avec style personnalisé
        with st.container():
            col1, col2, col3 = st.columns([0.5, 8, 1.5])

            with col1:
                # Checkbox pour marquer comme vu
                vu = st.checkbox(
                    "Vu",
                    value=bool(sortie['vu']),
                    key=f"vu_{sortie['id']}",
                    label_visibility="collapsed"
                )

                # Met à jour si changement
                if vu != bool(sortie['vu']):
                    db.mark_as_seen(sortie['id'], vu)
                    st.rerun()

            with col2:
                # Informations de la sortie avec lien et source
                if sortie.get('url'):
                    st.markdown(f"### {emoji_status} {source_emoji} [{sortie['titre']}]({sortie['url']})")
                else:
                    st.markdown(f"### {emoji_status} {source_emoji} {sortie['titre']}")
                st.caption(f"Source: {source_label}")
                st.markdown(f"🎯 **{sortie['activite']}**")

                col_info1, col_info2, col_info3 = st.columns(3)

                with col_info1:
                    st.markdown(f"📅 **{format_date_lecture(sortie['date'])}**")
                    st.markdown(f"📍 {sortie['lieu']}")

                with col_info2:
                    # Niveaux avec étoiles (peuvent être int ou str "N/A")
                    try:
                        niveau_phys = int(sortie['niveau_physique']) if sortie.get('niveau_physique') not in (None, "", "N/A") else 0
                    except (TypeError, ValueError):
                        niveau_phys = 0
                    try:
                        niveau_tech = int(sortie['niveau_technique']) if sortie.get('niveau_technique') not in (None, "", "N/A") else 0
                    except (TypeError, ValueError):
                        niveau_tech = 0

                    phys_stars = "⭐" * niveau_phys if niveau_phys > 0 else "N/A"
                    tech_stars = "⭐" * niveau_tech if niveau_tech > 0 else "N/A"

                    st.markdown(f"💪 Physique: {phys_stars}")
                    st.markdown(f"🎯 Technique: {tech_stars}")

                with col_info3:
                    st.markdown(f"👥 {sortie['places']}")
                    if sortie['contact']:
                        st.markdown(f"📞 {sortie['contact'][:30]}...")

            with col3:
                # Bouton pour voir les détails
                if st.button("ℹ️ Détails", key=f"details_{sortie['id']}", use_container_width=True):
                    st.session_state[f"show_details_{sortie['id']}"] = True

                # Modal pour les détails
                if st.session_state.get(f"show_details_{sortie['id']}", False):
                    with st.expander("📋 Détails complets", expanded=True):
                        st.markdown(f"**ID:** `{sortie['id']}`")
                        st.markdown(f"**Source:** {source_label}")
                        st.markdown(f"**Activité:** {sortie['activite']}")
                        st.markdown(f"**Titre:** {sortie['titre']}")
                        st.markdown(f"**Lieu:** {sortie['lieu']}")
                        st.markdown(f"**Date:** {format_date_lecture(sortie['date'])}")
                        st.markdown(f"**Niveau Physique:** {sortie['niveau_physique']}")
                        st.markdown(f"**Niveau Technique:** {sortie['niveau_technique']}")
                        st.markdown(f"**Places:** {sortie['places']}")
                        st.markdown(f"**Contact:** {sortie['contact']}")
                        st.markdown(f"**Ajouté le:** {sortie['date_ajout']}")
                        if sortie['date_modification']:
                            st.markdown(f"**Modifié le:** {sortie['date_modification']}")

                        if st.button("Fermer", key=f"close_{sortie['id']}"):
                            st.session_state[f"show_details_{sortie['id']}"] = False
                            st.rerun()

                st.divider()


# Liste des sorties : titre + bouton refresh
col_title, col_spacer, col_refresh = st.columns([5, 4, 1])
with col_title:
    st.subheader(f"📋 {len(sorties)} sortie(s) trouvée(s)")
with col_refresh:
    if st.button("🔄", key="refresh_list", help="Rafraîchir la liste"):
        with st.spinner("🔄 Mise à jour..."):
            try:
                scrape_all_clubs(db)
            except Exception:
                pass
            try:
                for sortie in FFCAMFormationsScraper().scrape_formations():
                    db.upsert_sortie(sortie)
            except Exception:
                pass
        st.rerun()

if not sorties:
    st.info("Aucune sortie ne correspond aux critères de recherche.")
else:
    # Groupement par activité
    display_sorties(db, sorties)

# Footer
st.divider()
st.caption("🏔️ CAF Watcher - Dernière mise à jour : " + datetime.now().strftime("%d/%m/%Y %H:%M"))

