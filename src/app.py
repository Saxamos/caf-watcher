#!/usr/bin/env python3
"""
Application Streamlit pour visualiser et gérer les sorties CAF Crest et FFCAM
"""

import streamlit as st
from src.database import SortiesDB
from src.scraper import CAFWatcher
from src.ffcam_scraper import FFCAMScraper
from datetime import datetime
import os

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

@st.cache_resource
def get_ffcam_scraper():
    data_dir = os.getenv('DATA_DIR', '/data')
    return FFCAMScraper(data_dir)

db = get_db()
ffcam_scraper = get_ffcam_scraper()

# Titre principal
st.title("🏔️ CAF - Gestion des Sorties")

# Onglets pour les différentes sources
tab_list, tab_scraping = st.tabs(["📋 Liste des sorties", "🔄 Scraping"])

with tab_scraping:
    st.header("🔄 Scraping des sorties")
    
    col_crest, col_ffcam = st.columns(2)
    
    with col_crest:
        st.subheader("🏔️ CAF Crest")
        st.caption("Source: crest.ffcam.fr")
        
        if st.button("🔄 Scraper CAF Crest", type="primary", use_container_width=True):
            with st.spinner("⏳ Scraping en cours..."):
                try:
                    watcher = CAFWatcher('/data')
                    watcher.check_for_updates()
                    st.success("✅ Sorties CAF Crest mises à jour !")
                    st.cache_resource.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
    
    with col_ffcam:
        st.subheader("🌐 FFCAM National")
        st.caption("Source: sorties.ffcam.fr")
        
        # Test de l'authentification
        if ffcam_scraper.test_authentication():
            auth_status = "✅ Authentifié"
            auth_color = "green"
        else:
            auth_status = "❌ Non authentifié"
            auth_color = "red"
        
        st.markdown(f":{auth_color}[{auth_status}]")
        
        # Import des cookies
        with st.expander("🍪 Configurer l'authentification", expanded=not ffcam_scraper.test_authentication()):
            st.markdown("""
            **Instructions:**
            1. Connecte-toi à [sorties.ffcam.fr](https://sorties.ffcam.fr)
            2. Ouvre les DevTools (F12)
            3. Va dans **Network** > Rafraîchis la page
            4. Clique sur une requête vers `sorties.ffcam.fr`
            5. Dans **Request Headers**, copie la valeur de `Cookie:`
            6. Colle-la ci-dessous
            """)
            
            cookie_input = st.text_area(
                "Cookies (format: name1=value1; name2=value2)",
                height=100,
                placeholder="PHPSESSID=abc123; auth_token=xyz789; ..."
            )
            
            if st.button("💾 Sauvegarder les cookies", use_container_width=True):
                if cookie_input:
                    # Parse les cookies
                    cookies = {}
                    for item in cookie_input.split(';'):
                        item = item.strip()
                        if '=' in item:
                            name, value = item.split('=', 1)
                            cookies[name.strip()] = value.strip()
                    
                    if ffcam_scraper.save_cookies(cookies):
                        st.success(f"✅ {len(cookies)} cookies sauvegardés!")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la sauvegarde")
                else:
                    st.warning("⚠️ Aucun cookie fourni")
        
        # Scraping FFCAM
        st.divider()
        
        if st.button("🔄 Scraper FFCAM", type="primary", use_container_width=True, disabled=not ffcam_scraper.test_authentication()):
            with st.spinner("⏳ Scraping FFCAM en cours..."):
                try:
                    # D'abord, récupère le HTML pour debug
                    html = ffcam_scraper.get_page_html(save_to_file=True)
                    
                    # Scrape
                    sorties_ffcam = ffcam_scraper.scrape_sorties(max_pages=3)
                    
                    if sorties_ffcam:
                        # Sauvegarde dans la DB
                        new_count = 0
                        for sortie in sorties_ffcam:
                            is_new = db.upsert_sortie(sortie)
                            if is_new:
                                new_count += 1
                        
                        st.success(f"✅ {len(sorties_ffcam)} sorties FFCAM récupérées ({new_count} nouvelles)")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.warning("⚠️ Aucune sortie FFCAM récupérée")
                        st.info("💡 Vérifie le fichier `/data/ffcam_page.html` pour analyser la structure HTML")
                except Exception as e:
                    st.error(f"❌ Erreur: {e}")
        
        if not ffcam_scraper.test_authentication():
            st.warning("⚠️ Configure d'abord l'authentification pour scraper FFCAM")

with tab_list:

    # Sidebar pour les filtres et statistiques (dans l'onglet liste)
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
    
    # Filtre par source
    st.divider()
    source_filter = st.multiselect(
        "Source",
        ["CAF Crest", "FFCAM"],
        default=["CAF Crest", "FFCAM"]
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
    if source_filter and len(source_filter) < 2:
        if "CAF Crest" in source_filter:
            sorties = [s for s in sorties if not s['id'].startswith('ffcam_')]
        elif "FFCAM" in source_filter:
            sorties = [s for s in sorties if s['id'].startswith('ffcam_')]

    def display_sorties(db, sorties_list):
        """Affiche la liste des sorties"""
        for sortie in sorties_list:
            # Emoji de source
            if sortie['id'].startswith('ffcam_'):
                source_emoji = "🌐"
                source_label = "FFCAM"
            else:
                source_emoji = "🏔️"
                source_label = "CAF Crest"
            
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
                        st.markdown(f"**Source:** {source_label}")
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
    st.caption("🏔️ CAF Watcher - Dernière mise à jour : " + datetime.now().strftime("%d/%m/%Y %H:%M"))

