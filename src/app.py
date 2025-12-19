#!/usr/bin/env python3
"""
Application Streamlit pour visualiser et gérer les sorties CAF Crest
"""

import streamlit as st
from src.database import SortiesDB
from src.scraper import CAFWatcher
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="CAF Crest - Sorties",
    page_icon="🏔️",
    layout="wide"
)

# Initialisation de la base de données
@st.cache_resource
def get_db():
    return SortiesDB("data/sorties.db")

db = get_db()

# Titre principal et bouton de scraping
col_title, col_button = st.columns([4, 1])
with col_title:
    st.title("🏔️ CAF Crest - Gestion des Sorties")
with col_button:
    st.write("")  # Spacer
    if st.button("🔄 Rafraîchir", type="primary", use_container_width=True):
        with st.spinner("⏳ Scraping en cours..."):
            try:
                watcher = CAFWatcher('/data')
                watcher.check_for_updates()
                st.success("✅ Sorties mises à jour !")
                st.cache_resource.clear()  # Clear cache to reload DB
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur: {e}")

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
    
    # Filtre par statut
    status_filter = st.radio(
        "Statut",
        ["Toutes", "Nouvelles uniquement", "Vues uniquement"],
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

def display_sorties(db, sorties_list):
    """Affiche la liste des sorties"""
    for sortie in sorties_list:
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
                # Informations de la sortie avec lien
                if sortie.get('url'):
                    st.markdown(f"### {emoji_status} [{sortie['titre']}]({sortie['url']})")
                else:
                    st.markdown(f"### {emoji_status} {sortie['titre']}")
                st.markdown(f"🎯 **{sortie['activite']}**")
                
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    st.markdown(f"📅 **{sortie['date']}**")
                    st.markdown(f"📍 {sortie['lieu']}")
                
                with col_info2:
                    # Niveaux avec étoiles
                    niveau_phys = sortie['niveau_physique']
                    niveau_tech = sortie['niveau_technique']
                    
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
                    st.markdown(f"**Activité:** {sortie['activite']}")
                    st.markdown(f"**Titre:** {sortie['titre']}")
                    st.markdown(f"**Lieu:** {sortie['lieu']}")
                    st.markdown(f"**Date:** {sortie['date']}")
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


# Affichage du nombre de résultats
st.subheader(f"📋 {len(sorties)} sortie(s) trouvée(s)")

if not sorties:
    st.info("Aucune sortie ne correspond aux critères de recherche.")
else:
    # Groupement par activité
    group_by = st.checkbox("Grouper par activité", value=False)
    
    if group_by:
        # Groupe les sorties par activité
        sorties_by_activite = {}
        for sortie in sorties:
            activite = sortie['activite']
            if activite not in sorties_by_activite:
                sorties_by_activite[activite] = []
            sorties_by_activite[activite].append(sortie)
        
        for activite, sorties_groupe in sorties_by_activite.items():
            with st.expander(f"🎯 {activite} ({len(sorties_groupe)})", expanded=True):
                display_sorties(db, sorties_groupe)
    else:
        display_sorties(db, sorties)

# Footer
st.divider()
st.caption("🏔️ CAF Crest Watcher - Dernière mise à jour : " + datetime.now().strftime("%d/%m/%Y %H:%M"))

