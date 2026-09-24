import streamlit as st
import requests
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime
import json

st.set_page_config(page_title="Patrimoine App", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e8eaf0; }
    h1 { color: #4fc3f7; font-size: 2rem; font-weight: 700; border-bottom: 2px solid #4fc3f7; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
    h2 { color: #b0bec5; font-size: 1.3rem; font-weight: 600; margin-top: 1.5rem; }
    div[data-testid="metric-container"] { background: linear-gradient(135deg, #1a1f2e, #232a3b); border: 1px solid #2d3748; border-radius: 12px; padding: 1rem; }
    div[data-testid="metric-container"] label { color: #90a4ae !important; font-size: 0.85rem; }
    div[data-testid="metric-container"] div { color: #4fc3f7 !important; font-size: 1.8rem; font-weight: 700; }
    .stSuccess { background-color: #1b2e22 !important; border-left: 4px solid #43a047 !important; color: #81c784 !important; border-radius: 8px; }
    .stInfo { background-color: #1a2535 !important; border-left: 4px solid #4fc3f7 !important; color: #90caf9 !important; border-radius: 8px; }
    .stWarning { background-color: #2e2210 !important; border-left: 4px solid #ffa726 !important; color: #ffcc80 !important; border-radius: 8px; }
    .streamlit-expanderHeader { background-color: #1a1f2e !important; border-radius: 8px !important; color: #b0bec5 !important; font-weight: 600; }
    .position-line { background-color: #1a1f2e; border-radius: 8px; padding: 0.6rem 1rem; margin: 0.3rem 0; border: 1px solid #2d3748; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

API_URL = "https://patrimoine-api-production.up.railway.app"

# ─── Session state ───
if "token" not in st.session_state:
    st.session_state.token = None
if "email" not in st.session_state:
    st.session_state.email = None

# ─── Page connexion ───
if st.session_state.token is None:
    st.title("📊 Patrimoine App")
    onglet_login, onglet_register = st.tabs(["Se connecter", "Créer un compte"])
    with onglet_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Se connecter"):
            response = requests.post(f"{API_URL}/login", json={"email": email, "password": password})
            if response.status_code == 200:
                data = response.json()
                st.session_state.token = data["token"]
                st.session_state.email = data["user"]
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect")
    with onglet_register:
        email_r = st.text_input("Email", key="register_email")
        password_r = st.text_input("Mot de passe", type="password", key="register_password")
        if st.button("Créer un compte"):
            response = requests.post(f"{API_URL}/register", json={"email": email_r, "password": password_r})
            if response.status_code == 200:
                st.success("Compte créé ! Tu peux maintenant te connecter.")
            else:
                st.error("Erreur lors de la création du compte")

# ─── Page principale ───
else:
    st.title(f"📊 Tableau de bord — {st.session_state.email}")
    if st.button("Se déconnecter"):
        st.session_state.token = None
        st.session_state.email = None
        st.rerun()

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # ─── Chargement données API ───
    positions = requests.get(f"{API_URL}/positions", headers=headers).json()
    ctos = requests.get(f"{API_URL}/cto", headers=headers).json()
    cryptos = requests.get(f"{API_URL}/crypto", headers=headers).json()
    livrets = requests.get(f"{API_URL}/livrets", headers=headers).json()

    def get_prix(ticker_str):
        try:
            t = yf.Ticker(ticker_str)
            h = t.history(period="1d")
            if not h.empty:
                return h["Close"].iloc[-1]
        except:
            pass
        return None

    onglet1, onglet2, onglet3, onglet4 = st.tabs(["📊 Patrimoine", "💶 Budget & Objectifs", "📐 Simulation", "📉 Performance"])

    with onglet1:

        # ─── PEA ───
        st.header("📈 PEA")
        data_pea = []
        total_pea_valeur = 0
        total_pea_pv = 0

        for p in positions:
            prix = get_prix(p["ticker"])
            if prix:
                valeur = prix * p["quantite"]
                pv = (prix - p["px_moyen"]) * p["quantite"]
                rendement = (pv / (p["px_moyen"] * p["quantite"])) * 100
                total_pea_valeur += valeur
                total_pea_pv += pv
                couleur = "🟢" if pv > 0 else "🔴"
                rend_couleur = "🟢" if rendement > 0 else "🔴"
                st.markdown(f'<div class="position-line">{couleur} <b>{p["nom"]}</b> — Quantité : {p["quantite"]} — Prix actuel : {prix:.2f}€ — Prix moyen : {p["px_moyen"]:.2f}€ — Valeur : {valeur:.2f}€ — PV : {pv:.2f}€ — Rendement : {rend_couleur} {rendement:.2f}%</div>', unsafe_allow_html=True)
                data_pea.append({"Nom": p["nom"], "Valeur": valeur, "PV Latente": pv})

        st.success(f"**Total PEA : {total_pea_valeur:.2f}€ (PV latente : {total_pea_pv:.2f}€)**")

        with st.expander("➕ Ajouter une position PEA"):
            nom = st.text_input("Nom")
            ticker = st.text_input("Ticker Yahoo Finance")
            quantite = st.number_input("Quantité", min_value=0.0)
            px_moyen = st.number_input("Prix moyen d'achat", min_value=0.0)
            if st.button("Ajouter la position"):
                requests.post(f"{API_URL}/positions", headers=headers, json={"nom": nom, "ticker": ticker, "quantite": quantite, "px_moyen": px_moyen, "type": "pea"})
                st.success(f"{nom} ajouté ! Rechargez la page.")
                st.rerun()

        with st.expander("✏️ Modifier une position PEA"):
            if positions:
                nom_choisi = st.selectbox("Choisir la position à modifier", [p["nom"] for p in positions])
                position = next(p for p in positions if p["nom"] == nom_choisi)
                st.markdown(f"**Quantité actuelle :** {position['quantite']} — **Prix moyen :** {position['px_moyen']}€")
                nouvel_achat = st.number_input("Quantité achetée", min_value=0.0)
                prix_achat = st.number_input("Prix d'achat", min_value=0.0)
                if nouvel_achat > 0 and prix_achat > 0:
                    nouvelle_quantite = position["quantite"] + nouvel_achat
                    nouveau_px = ((position["quantite"] * position["px_moyen"]) + (nouvel_achat * prix_achat)) / nouvelle_quantite
                    st.info(f"➡️ Nouvelle quantité : {nouvelle_quantite} — Nouveau prix moyen : {nouveau_px:.3f}€")
                    if st.button("Confirmer l'achat"):
                        requests.put(f"{API_URL}/positions/{nom_choisi}", headers=headers, json={"quantite": nouvelle_quantite, "px_moyen": round(nouveau_px, 3)})
                        st.success(f"{nom_choisi} mis à jour !")
                        st.rerun()

        with st.expander("💰 Vendre une partie PEA"):
            if positions:
                nom_vente = st.selectbox("Choisir", [p["nom"] for p in positions], key="vente_pea")
                pos_vente = next(p for p in positions if p["nom"] == nom_vente)
                st.markdown(f"**Quantité actuelle :** {pos_vente['quantite']} — **Prix moyen :** {pos_vente['px_moyen']}€")
                qte_vendue = st.number_input("Quantité à vendre", min_value=0.0, max_value=float(pos_vente["quantite"]))
                prix_vente = st.number_input("Prix de vente", min_value=0.0)
                if qte_vendue > 0 and prix_vente > 0:
                    pv_realisee = (prix_vente - pos_vente["px_moyen"]) * qte_vendue
                    st.info(f"➡️ Quantité restante : {pos_vente['quantite'] - qte_vendue} — PV réalisée : {pv_realisee:.2f}€")
                    if st.button("Confirmer la vente"):
                        requests.put(f"{API_URL}/positions/{nom_vente}", headers=headers, json={"quantite": pos_vente["quantite"] - qte_vendue, "px_moyen": pos_vente["px_moyen"]})
                        st.success("Vente confirmée !")
                        st.rerun()

        with st.expander("🗑️ Supprimer une position PEA"):
            if positions:
                nom_suppr = st.selectbox("Choisir", [p["nom"] for p in positions], key="suppr_pea")
                st.warning(f"⚠️ Supprimer {nom_suppr} ?")
                if st.button("Supprimer la position"):
                    requests.delete(f"{API_URL}/positions/{nom_suppr}", headers=headers)
                    st.success(f"{nom_suppr} supprimé !")
                    st.rerun()

        # ─── CTO ───
        st.header("🌍 CTO")
        total_cto_valeur = 0
        total_cto_pv = 0
        for p in ctos:
            prix = get_prix(p["ticker"])
            if prix:
                valeur = prix * p["quantite"]
                pv = (prix - p["px_moyen"]) * p["quantite"]
                rendement_cto = (pv / (p["px_moyen"] * p["quantite"])) * 100
                total_cto_valeur += valeur
                total_cto_pv += pv
                couleur = "🟢" if pv > 0 else "🔴"
                rend_couleur = "🟢" if rendement_cto > 0 else "🔴"
                st.markdown(f'<div class="position-line">{couleur} <b>{p["nom"]}</b> — Quantité : {p["quantite"]} — Prix actuel : {prix:.2f}$ — Prix moyen : {p["px_moyen"]:.2f}$ — Valeur : {valeur:.2f}€ — PV : {pv:.2f}€ — Rendement : {rend_couleur} {rendement_cto:.2f}%</div>', unsafe_allow_html=True)
        st.info(f"**Total CTO : {total_cto_valeur:.2f}€**")

        with st.expander("➕ Ajouter une position CTO"):
            nom_cto = st.text_input("Nom", key="nom_cto")
            ticker_cto = st.text_input("Ticker", key="ticker_cto")
            quantite_cto = st.number_input("Quantité", min_value=0.0, key="qte_cto")
            px_moyen_cto = st.number_input("Prix moyen", min_value=0.0, key="px_cto")
            if st.button("Ajouter", key="add_cto"):
                requests.post(f"{API_URL}/cto", headers=headers, json={"nom": nom_cto, "ticker": ticker_cto, "quantite": quantite_cto, "px_moyen": px_moyen_cto})
                st.success(f"{nom_cto} ajouté !")
                st.rerun()

        with st.expander("✏️ Modifier une position CTO"):
            if ctos:
                nom_cto_mod = st.selectbox("Position", [p["nom"] for p in ctos], key="mod_cto")
                cto = next(p for p in ctos if p["nom"] == nom_cto_mod)
                st.markdown(f"**Quantité actuelle :** {cto['quantite']} — **Prix moyen :** {cto['px_moyen']}$")
                nouvel_achat_cto = st.number_input("Quantité achetée", min_value=0.0, key="qte_achat_cto")
                prix_achat_cto = st.number_input("Prix d'achat", min_value=0.0, key="px_achat_cto")
                if nouvel_achat_cto > 0 and prix_achat_cto > 0:
                    nouvelle_qte_cto = cto["quantite"] + nouvel_achat_cto
                    nouveau_px_cto = ((cto["quantite"] * cto["px_moyen"]) + (nouvel_achat_cto * prix_achat_cto)) / nouvelle_qte_cto
                    st.info(f"➡️ Nouvelle quantité : {nouvelle_qte_cto} — Nouveau prix moyen : {nouveau_px_cto:.3f}$")
                    if st.button("Confirmer", key="confirm_cto"):
                        requests.put(f"{API_URL}/cto/{nom_cto_mod}", headers=headers, json={"quantite": nouvelle_qte_cto, "px_moyen": round(nouveau_px_cto, 3)})
                        st.success(f"{nom_cto_mod} modifié !")
                        st.rerun()

        with st.expander("💰 Vendre une partie CTO"):
            if ctos:
                nom_vente_cto = st.selectbox("Position", [p["nom"] for p in ctos], key="vente_cto")
                pos_vente_cto = next(p for p in ctos if p["nom"] == nom_vente_cto)
                qte_vendue_cto = st.number_input("Quantité à vendre", min_value=0.0, max_value=float(pos_vente_cto["quantite"]), key="qte_vente_cto")
                prix_vente_cto = st.number_input("Prix de vente", min_value=0.0, key="px_vente_cto")
                if qte_vendue_cto > 0 and prix_vente_cto > 0:
                    pv_cto = (prix_vente_cto - pos_vente_cto["px_moyen"]) * qte_vendue_cto
                    st.info(f"➡️ Quantité restante : {pos_vente_cto['quantite'] - qte_vendue_cto} — PV réalisée : {pv_cto:.2f}$")
                    if st.button("Confirmer la vente", key="confirm_vente_cto"):
                        requests.put(f"{API_URL}/cto/{nom_vente_cto}", headers=headers, json={"quantite": pos_vente_cto["quantite"] - qte_vendue_cto, "px_moyen": pos_vente_cto["px_moyen"]})
                        st.success("Vente confirmée !")
                        st.rerun()

        with st.expander("🗑️ Supprimer une position CTO"):
            if ctos:
                nom_suppr_cto = st.selectbox("Position", [p["nom"] for p in ctos], key="suppr_cto")
                st.warning(f"⚠️ Supprimer {nom_suppr_cto} ?")
                if st.button("Supprimer", key="del_cto"):
                    requests.delete(f"{API_URL}/cto/{nom_suppr_cto}", headers=headers)
                    st.success(f"{nom_suppr_cto} supprimé !")
                    st.rerun()

        # ─── Crypto ───
        st.header("₿ Crypto")
        total_crypto_valeur = 0
        for p in cryptos:
            prix = get_prix(p["ticker"])
            if prix:
                valeur = prix * p["quantite"]
                total_crypto_valeur += valeur
                st.markdown(f'<div class="position-line">🔵 <b>{p["nom"]}</b> — Quantité : {p["quantite"]} — Prix actuel : {prix:.2f}€ — Valeur : {valeur:.2f}€</div>', unsafe_allow_html=True)
        st.info(f"**Total Crypto : {total_crypto_valeur:.2f}€**")

        with st.expander("➕ Ajouter une crypto"):
            nom_crypto = st.text_input("Nom", key="nom_crypto")
            ticker_crypto = st.text_input("Ticker (ex: BTC-EUR)", key="ticker_crypto")
            quantite_crypto = st.number_input("Quantité", min_value=0.0, key="qte_crypto")
            if st.button("Ajouter", key="add_crypto"):
                requests.post(f"{API_URL}/crypto", headers=headers, json={"nom": nom_crypto, "ticker": ticker_crypto, "quantite": quantite_crypto})
                st.success(f"{nom_crypto} ajouté !")
                st.rerun()

        with st.expander("✏️ Modifier une crypto"):
            if cryptos:
                nom_crypto_mod = st.selectbox("Crypto", [p["nom"] for p in cryptos], key="mod_crypto")
                pos_crypto = next(p for p in cryptos if p["nom"] == nom_crypto_mod)
                nouvelle_qte_crypto = st.number_input("Nouvelle quantité", min_value=0.0, value=float(pos_crypto["quantite"]), key="qte_mod_crypto")
                if st.button("Modifier", key="confirm_mod_crypto"):
                    requests.put(f"{API_URL}/crypto/{nom_crypto_mod}", headers=headers, json={"quantite": nouvelle_qte_crypto})
                    st.success(f"{nom_crypto_mod} modifié !")
                    st.rerun()

        with st.expander("💰 Vendre une partie crypto"):
            if cryptos:
                nom_vente_crypto = st.selectbox("Crypto", [p["nom"] for p in cryptos], key="vente_crypto")
                pos_vente_crypto = next(p for p in cryptos if p["nom"] == nom_vente_crypto)
                qte_vendue_crypto = st.number_input("Quantité à vendre", min_value=0.0, max_value=float(pos_vente_crypto["quantite"]), key="qte_vente_crypto")
                if qte_vendue_crypto > 0:
                    st.info(f"➡️ Quantité restante : {pos_vente_crypto['quantite'] - qte_vendue_crypto}")
                    if st.button("Confirmer la vente", key="confirm_vente_crypto"):
                        requests.put(f"{API_URL}/crypto/{nom_vente_crypto}", headers=headers, json={"quantite": pos_vente_crypto["quantite"] - qte_vendue_crypto})
                        st.success("Vente confirmée !")
                        st.rerun()

        with st.expander("🗑️ Supprimer une crypto"):
            if cryptos:
                nom_suppr_crypto = st.selectbox("Crypto", [p["nom"] for p in cryptos], key="suppr_crypto")
                st.warning(f"⚠️ Supprimer {nom_suppr_crypto} ?")
                if st.button("Supprimer", key="del_crypto"):
                    requests.delete(f"{API_URL}/crypto/{nom_suppr_crypto}", headers=headers)
                    st.success(f"{nom_suppr_crypto} supprimé !")
                    st.rerun()

        # ─── Livrets ───
        st.header("🏦 Épargne & Livrets")
        total_livrets = sum(l["valeur"] for l in livrets)
        for l in livrets:
            st.markdown(f'<div class="position-line">💰 <b>{l["nom"]}</b> : {l["valeur"]:.2f}€</div>', unsafe_allow_html=True)
        st.info(f"**Total Épargne : {total_livrets:.2f}€**")

        with st.expander("➕ Ajouter un livret"):
            nom_liv = st.text_input("Nom du livret", key="nom_liv")
            valeur_liv = st.number_input("Valeur (€)", min_value=0.0, key="val_liv")
            if st.button("Ajouter le livret"):
                requests.post(f"{API_URL}/livrets", headers=headers, json={"nom": nom_liv, "valeur": valeur_liv})
                st.success(f"{nom_liv} ajouté !")
                st.rerun()

        with st.expander("✏️ Modifier un livret"):
            if livrets:
                nom_liv_mod = st.selectbox("Choisir", [l["nom"] for l in livrets], key="mod_liv")
                liv = next(l for l in livrets if l["nom"] == nom_liv_mod)
                nouvelle_valeur = st.number_input("Nouvelle valeur (€)", min_value=0.0, value=float(liv["valeur"]), key="val_mod_liv")
                if st.button("Modifier", key="confirm_mod_liv"):
                    requests.put(f"{API_URL}/livrets/{nom_liv_mod}", headers=headers, json={"valeur": nouvelle_valeur})
                    st.success(f"{nom_liv_mod} modifié !")
                    st.rerun()

        with st.expander("🗑️ Supprimer un livret"):
            if livrets:
                nom_suppr_liv = st.selectbox("Choisir", [l["nom"] for l in livrets], key="suppr_liv")
                st.warning(f"⚠️ Supprimer {nom_suppr_liv} ?")
                if st.button("Supprimer", key="del_liv"):
                    requests.delete(f"{API_URL}/livrets/{nom_suppr_liv}", headers=headers)
                    st.success(f"{nom_suppr_liv} supprimé !")
                    st.rerun()

        # ─── Total ───
        total_patrimoine = total_pea_valeur + total_cto_valeur + total_crypto_valeur + total_livrets
        st.header("💼 Patrimoine Total")
        st.metric("Total", f"{total_patrimoine:.2f}€")

        # ─── Résumé fiscal ───
        st.header("🧾 Résumé fiscal")
        FLAT_TAX = 0.30
        st.subheader("📈 PEA")
        st.info("✅ Les plus-values sur PEA sont exonérées d'impôt après 5 ans (hors prélèvements sociaux de 17.2%)")
        pv_pea_imposable = total_pea_pv * 0.172
        st.markdown(f'<div class="position-line">💰 PV latente totale PEA : <b>{total_pea_pv:.2f}€</b> — Prélèvements sociaux estimés si retrait : <b>{pv_pea_imposable:.2f}€</b></div>', unsafe_allow_html=True)
        st.subheader("🌍 CTO")
        impot_cto = total_cto_pv * FLAT_TAX if total_cto_pv > 0 else 0
        st.markdown(f'<div class="position-line">💰 PV latente totale CTO : <b>{total_cto_pv:.2f}€</b> — Flat tax estimée (30%) si cession : <b>{impot_cto:.2f}€</b></div>', unsafe_allow_html=True)
        st.subheader("₿ Crypto")
        st.info("ℹ️ Les plus-values crypto sont soumises à la flat tax de 30% au-delà de 305€ de gains annuels")
        st.markdown(f'<div class="position-line">💰 Valeur totale Crypto : <b>{total_crypto_valeur:.2f}€</b></div>', unsafe_allow_html=True)
        total_impots = pv_pea_imposable + impot_cto
        st.warning(f"⚠️ Impôts estimés si tout est cédé aujourd'hui : {total_impots:.2f}€")
        st.caption("Ces estimations sont indicatives et ne constituent pas un conseil fiscal.")

        # ─── Graphiques ───
        st.header("📊 Répartition du patrimoine")
        col1, col2 = st.columns(2)
        with col1:
            fig_global = px.pie(
                values=[total_pea_valeur, total_cto_valeur, total_crypto_valeur, total_livrets],
                names=["PEA", "CTO", "Crypto", "Épargne"],
                title="Répartition globale",
                color_discrete_sequence=["#4fc3f7", "#81c784", "#ffb74d", "#ce93d8"]
            )
            fig_global.update_layout(paper_bgcolor="#0f1117", font_color="#e8eaf0")
            st.plotly_chart(fig_global, use_container_width=True)
        with col2:
            if data_pea:
                fig_pea = px.pie(
                    values=[d["Valeur"] for d in data_pea],
                    names=[d["Nom"] for d in data_pea],
                    title="Répartition PEA",
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                fig_pea.update_layout(paper_bgcolor="#0f1117", font_color="#e8eaf0")
                st.plotly_chart(fig_pea, use_container_width=True)

        if data_pea:
            fig_pv = go.Figure([go.Bar(
                x=[d["Nom"] for d in data_pea],
                y=[d["PV Latente"] for d in data_pea],
                marker_color=["#43a047" if d["PV Latente"] > 0 else "#e53935" for d in data_pea]
            )])
            fig_pv.update_layout(title="PV latentes PEA", xaxis_tickangle=-45, paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0")
            st.plotly_chart(fig_pv, use_container_width=True)

    with onglet2:
        st.header("💶 Budget & Objectifs")

        transactions_path = "transactions.json"
        try:
            with open(transactions_path, "r", encoding="utf-8-sig") as f:
                transactions = json.load(f)
            df = pd.DataFrame(transactions)
            df["date"] = pd.to_datetime(df["date"])
            st.success("✅ Données chargées depuis la mémoire.")
        except:
            df = None

        with st.expander("📂 Importer ou mettre à jour un fichier Excel"):
            fichier = st.file_uploader("Choisir un fichier Excel", type=["xlsx", "xls"])
            mode_import = st.radio("Mode d'import", ["Fusionner avec les données existantes", "Remplacer toutes les données"])
            if fichier:
                df_import = pd.read_excel(fichier)
                df_import.columns = [c.strip().lower() for c in df_import.columns]
                df_import["date"] = pd.to_datetime(df_import["date"], dayfirst=True)
                if st.button("Confirmer l'import"):
                    nouvelles = json.loads(df_import.to_json(orient="records", date_format="iso"))
                    if mode_import == "Fusionner avec les données existantes":
                        try:
                            with open(transactions_path, "r") as f:
                                existantes = json.load(f)
                        except:
                            existantes = []
                        toutes = existantes + nouvelles
                    else:
                        toutes = nouvelles
                    with open(transactions_path, "w", encoding="utf-8") as f:
                        json.dump(toutes, f, indent=2, ensure_ascii=True)
                    st.success("✅ Import réussi ! Rechargez la page.")

        if df is not None:
            df["mois"] = df["date"].dt.to_period("M").astype(str)
            col_cat = "catégorie" if "catégorie" in df.columns else "categorie"

            annees_disponibles = sorted(df["date"].dt.year.unique(), reverse=True)
            annee_choisie = st.selectbox("📅 Année", annees_disponibles)
            mois_options = ["Toute l'année"] + [f"{annee_choisie}-{str(m).zfill(2)}" for m in sorted(df[df["date"].dt.year == annee_choisie]["date"].dt.month.unique())]
            mois_choisi = st.selectbox("📅 Mois", mois_options)
            if mois_choisi == "Toute l'année":
                df_mois = df[df["date"].dt.year == annee_choisie]
            else:
                df_mois = df[df["mois"] == mois_choisi]

            with st.expander("➕ Ajouter une transaction"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    date_trans = st.date_input("Date", value=datetime.date.today())
                    type_trans = st.selectbox("Type", ["revenu", "depense", "facture", "credit", "epargne"], key="type_trans")
                categories_par_type = df[df["type"].str.lower().str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii") == type_trans][col_cat].dropna().unique().tolist()
                categories_par_type = sorted(set(categories_par_type))
                categories_par_type.append("➕ Nouvelle catégorie")
                with col_f2:
                    montant_trans = st.number_input("Montant", min_value=0.0, key="montant_trans")
                    cat_choisie = st.selectbox("Catégorie", categories_par_type, key="cat_trans")
                    if cat_choisie == "➕ Nouvelle catégorie":
                        cat_trans = st.text_input("Nouvelle catégorie")
                    else:
                        cat_trans = cat_choisie
                if st.button("Ajouter la transaction"):
                    nouvelle_trans = {"date": date_trans.isoformat(), "type": type_trans, "catégorie": cat_trans, "montant": montant_trans}
                    transactions_list = json.loads(df.to_json(orient="records", date_format="iso"))
                    transactions_list.append(nouvelle_trans)
                    with open(transactions_path, "w", encoding="utf-8") as f:
                        json.dump(transactions_list, f, indent=2, ensure_ascii=True)
                    st.success("Transaction ajoutée !")
                    st.rerun()

            with st.expander("✏️ Modifier une transaction"):
                df_affich = df.copy()
                df_affich["label"] = df_affich["date"].dt.strftime("%d/%m/%Y") + " — " + df_affich["type"] + " — " + df_affich[col_cat].astype(str) + " — " + df_affich["montant"].astype(str) + "€"
                trans_choisie = st.selectbox("Choisir", df_affich["label"].tolist(), key="mod_trans")
                idx = df_affich[df_affich["label"] == trans_choisie].index[0]
                row = df.iloc[idx]
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    date_mod = st.date_input("Date", value=row["date"].date(), key="date_mod")
                    type_mod = st.selectbox("Type", ["revenu", "depense", "facture", "credit", "epargne"], key="type_mod")
                with col_m2:
                    cat_mod = st.text_input("Catégorie", value=str(row[col_cat]), key="cat_mod")
                    montant_mod = st.number_input("Montant", min_value=0.0, value=float(row["montant"]), key="montant_mod")
                if st.button("Modifier", key="confirm_mod_trans"):
                    transactions_list = json.loads(df.to_json(orient="records", date_format="iso"))
                    transactions_list[idx]["date"] = date_mod.isoformat()
                    transactions_list[idx]["type"] = type_mod
                    transactions_list[idx][col_cat] = cat_mod
                    transactions_list[idx]["montant"] = montant_mod
                    with open(transactions_path, "w", encoding="utf-8") as f:
                        json.dump(transactions_list, f, indent=2, ensure_ascii=True)
                    st.success("Transaction modifiée !")
                    st.rerun()

            with st.expander("🗑️ Supprimer une transaction"):
                df_affich2 = df.copy()
                df_affich2["label"] = df_affich2["date"].dt.strftime("%d/%m/%Y") + " — " + df_affich2["type"] + " — " + df_affich2[col_cat].astype(str) + " — " + df_affich2["montant"].astype(str) + "€"
                trans_suppr = st.selectbox("Choisir", df_affich2["label"].tolist(), key="suppr_trans")
                idx_suppr = df_affich2[df_affich2["label"] == trans_suppr].index[0]
                st.warning(f"⚠️ Supprimer : {trans_suppr}")
                if st.button("Supprimer", key="del_trans"):
                    transactions_list = json.loads(df.to_json(orient="records", date_format="iso"))
                    transactions_list.pop(idx_suppr)
                    with open(transactions_path, "w", encoding="utf-8") as f:
                        json.dump(transactions_list, f, indent=2, ensure_ascii=True)
                    st.success("Transaction supprimée !")
                    st.rerun()

            col_rev, col_dep = st.columns(2)
            df_revenus = df_mois[df_mois["type"].str.lower() == "revenu"]
            df_depenses = df_mois[df_mois["type"].str.lower().isin(["dépense", "depense", "facture", "crédit", "credit"])]
            df_epargne = df_mois[df_mois["type"].str.lower().str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii") == "epargne"]

            with col_rev:
                st.subheader("💰 Revenus")
                if not df_revenus.empty:
                    par_cat_rev = df_revenus.groupby(col_cat)["montant"].sum().reset_index().sort_values("montant", ascending=False)
                    html_rev = '<table style="width:100%;text-align:center;border-collapse:collapse;">'
                    html_rev += '<tr style="background:#1a1f2e;"><th style="padding:8px;border:1px solid #2d3748;">Catégorie</th><th style="padding:8px;border:1px solid #2d3748;">Montant €</th></tr>'
                    for _, row in par_cat_rev.iterrows():
                        html_rev += f'<tr><td style="padding:8px;border:1px solid #2d3748;">{row[col_cat]}</td><td style="padding:8px;border:1px solid #2d3748;">{row["montant"]:.2f}€</td></tr>'
                    html_rev += '</table>'
                    st.markdown(html_rev, unsafe_allow_html=True)
                    st.success(f"**Total : {df_revenus['montant'].sum():.2f}€**")
                else:
                    st.info("Aucun revenu ce mois.")

            with col_dep:
                st.subheader("💸 Dépenses")
                if not df_depenses.empty:
                    par_categorie = df_depenses.groupby(col_cat)["montant"].sum().reset_index().sort_values("montant", ascending=False)
                    html_dep = '<table style="width:100%;text-align:center;border-collapse:collapse;">'
                    html_dep += '<tr style="background:#1a1f2e;"><th style="padding:8px;border:1px solid #2d3748;">Catégorie</th><th style="padding:8px;border:1px solid #2d3748;">Montant €</th></tr>'
                    for _, row in par_categorie.iterrows():
                        html_dep += f'<tr><td style="padding:8px;border:1px solid #2d3748;">{row[col_cat]}</td><td style="padding:8px;border:1px solid #2d3748;">{row["montant"]:.2f}€</td></tr>'
                    html_dep += '</table>'
                    st.markdown(html_dep, unsafe_allow_html=True)
                    st.warning(f"**Total : {df_depenses['montant'].sum():.2f}€**")
                else:
                    st.info("Aucune dépense ce mois.")

            if not df_epargne.empty:
                st.subheader("💎 Épargne")
                par_cat_ep = df_epargne.groupby(col_cat)["montant"].sum().reset_index()
                html_ep = '<table style="width:100%;text-align:center;border-collapse:collapse;">'
                html_ep += '<tr style="background:#1a1f2e;"><th style="padding:8px;border:1px solid #2d3748;">Catégorie</th><th style="padding:8px;border:1px solid #2d3748;">Montant €</th></tr>'
                for _, row in par_cat_ep.iterrows():
                    html_ep += f'<tr><td style="padding:8px;border:1px solid #2d3748;">{row[col_cat]}</td><td style="padding:8px;border:1px solid #2d3748;">{row["montant"]:.2f}€</td></tr>'
                html_ep += '</table>'
                st.markdown(html_ep, unsafe_allow_html=True)
                st.info(f"**Total épargne : {df_epargne['montant'].sum():.2f}€**")

            st.subheader("📊 Bilan mensuel")
            total_rev = df_revenus["montant"].sum() if not df_revenus.empty else 0
            total_dep = df_depenses["montant"].sum() if not df_depenses.empty else 0
            epargne = total_rev - total_dep
            taux = (epargne / total_rev * 100) if total_rev > 0 else 0
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Revenus", f"{total_rev:.2f}€")
            with col2:
                st.metric("Dépenses", f"{total_dep:.2f}€")
            with col3:
                st.metric("Épargne", f"{epargne:.2f}€")
            st.info(f"**Taux d'épargne : {taux:.1f}%**")

            st.subheader("📈 Évolution mensuelle")
            df_evolution = df[df["date"].dt.year == annee_choisie].copy()
            df_evolution["mois"] = df_evolution["date"].dt.to_period("M").astype(str)
            revenus_par_mois = df_evolution[df_evolution["type"].str.lower() == "revenu"].groupby("mois")["montant"].sum()
            depenses_par_mois = df_evolution[df_evolution["type"].str.lower().isin(["dépense", "depense", "facture", "crédit", "credit"])].groupby("mois")["montant"].sum()
            epargne_par_mois = df_evolution[df_evolution["type"].str.lower().str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii") == "epargne"].groupby("mois")["montant"].sum()
            tous_mois = sorted(df_evolution["mois"].unique())
            fig_evol = go.Figure()
            fig_evol.add_trace(go.Bar(name="Revenus", x=tous_mois, y=[revenus_par_mois.get(m, 0) for m in tous_mois], marker_color="#43a047"))
            fig_evol.add_trace(go.Bar(name="Dépenses", x=tous_mois, y=[depenses_par_mois.get(m, 0) for m in tous_mois], marker_color="#e53935"))
            fig_evol.add_trace(go.Bar(name="Épargne", x=tous_mois, y=[epargne_par_mois.get(m, 0) for m in tous_mois], marker_color="#4fc3f7"))
            fig_evol.update_layout(barmode="group", title=f"Revenus / Dépenses / Épargne — {annee_choisie}", paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0", xaxis_tickangle=-45)
            st.plotly_chart(fig_evol, use_container_width=True)

            st.subheader("💎 Taux d'épargne annuel")
            df_annee = df[df["date"].dt.year == annee_choisie]
            rev_annee = df_annee[df_annee["type"].str.lower() == "revenu"]["montant"].sum()
            dep_annee = df_annee[df_annee["type"].str.lower().isin(["dépense", "depense", "facture", "crédit", "credit"])]["montant"].sum()
            ep_annee = df_annee[df_annee["type"].str.lower().str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii") == "epargne"]["montant"].sum()
            taux_ep_annee = (ep_annee / rev_annee * 100) if rev_annee > 0 else 0
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                st.metric("Revenus annuels", f"{rev_annee:.2f}€")
            with col_a2:
                st.metric("Dépenses annuelles", f"{dep_annee:.2f}€")
            with col_a3:
                st.metric("Épargne annuelle", f"{ep_annee:.2f}€")
            with col_a4:
                st.metric("Taux d'épargne", f"{taux_ep_annee:.1f}%")
            st.progress(min(int(taux_ep_annee), 100))

            st.subheader("🔀 Comparaison mois par mois")
            mois_dispo = sorted(df[df["date"].dt.year == annee_choisie]["mois"].unique())
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                mois_a = st.selectbox("Mois A", mois_dispo, key="mois_a")
            with col_c2:
                mois_b = st.selectbox("Mois B", mois_dispo, index=min(1, len(mois_dispo)-1), key="mois_b")

            def calcul_mois(mois):
                df_m = df[df["mois"] == mois]
                rev = df_m[df_m["type"].str.lower() == "revenu"]["montant"].sum()
                dep = df_m[df_m["type"].str.lower().isin(["dépense", "depense", "facture", "crédit", "credit"])]["montant"].sum()
                ep = df_m[df_m["type"].str.lower().str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii") == "epargne"]["montant"].sum()
                return rev, dep, ep

            rev_a, dep_a, ep_a = calcul_mois(mois_a)
            rev_b, dep_b, ep_b = calcul_mois(mois_b)
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(name=mois_a, x=["Revenus", "Dépenses", "Épargne"], y=[rev_a, dep_a, ep_a], marker_color="#4fc3f7"))
            fig_comp.add_trace(go.Bar(name=mois_b, x=["Revenus", "Dépenses", "Épargne"], y=[rev_b, dep_b, ep_b], marker_color="#ffb74d"))
            fig_comp.update_layout(barmode="group", title=f"Comparaison {mois_a} vs {mois_b}", paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0")
            st.plotly_chart(fig_comp, use_container_width=True)
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                st.metric("Revenus", f"{rev_b:.2f}€", delta=f"{rev_b - rev_a:.2f}€")
            with col_e2:
                st.metric("Dépenses", f"{dep_b:.2f}€", delta=f"{dep_b - dep_a:.2f}€")
            with col_e3:
                st.metric("Épargne", f"{ep_b:.2f}€", delta=f"{ep_b - ep_a:.2f}€")

        else:
            st.info("Importe un fichier Excel pour voir tes données.")

        st.subheader("🎯 Objectif de patrimoine")
        objectif = st.number_input("Objectif (€)", min_value=0.0, value=0.0, step=1000.0)
        if objectif > 0:
            progression = min((total_patrimoine / objectif) * 100, 100)
            st.progress(int(progression))
            st.markdown(f'<div class="position-line">📈 Progression : <b>{progression:.1f}%</b> — {total_patrimoine:.2f}€ / {objectif:.2f}€</div>', unsafe_allow_html=True)

    with onglet3:
        st.header("📐 Simulation d'investissement")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            apport_initial = st.number_input("Apport initial (€)", min_value=0.0, value=1000.0, step=100.0)
            versement_mensuel = st.number_input("Versement mensuel (€)", min_value=0.0, value=200.0, step=50.0)
        with col_s2:
            duree_ans = st.slider("Durée (années)", min_value=1, max_value=40, value=10)
            rendement_annuel = st.slider("Rendement annuel (%)", min_value=0.0, max_value=20.0, value=7.0, step=0.5)

        rendement_mensuel = rendement_annuel / 100 / 12
        valeurs = []
        valeurs_sans_interet = []
        capital = apport_initial
        capital_sans_interet = apport_initial
        for mois in range(duree_ans * 12):
            capital = capital * (1 + rendement_mensuel) + versement_mensuel
            capital_sans_interet += versement_mensuel
            valeurs.append(round(capital, 2))
            valeurs_sans_interet.append(round(capital_sans_interet, 2))

        mois_labels = [f"Mois {i+1}" for i in range(duree_ans * 12)]
        total_investi = apport_initial + versement_mensuel * duree_ans * 12
        interets = capital - total_investi

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Capital final", f"{capital:.2f}€")
        with col_m2:
            st.metric("Total investi", f"{total_investi:.2f}€")
        with col_m3:
            st.metric("Intérêts générés", f"{interets:.2f}€")

        fig_sim = go.Figure()
        fig_sim.add_trace(go.Scatter(x=mois_labels, y=valeurs, name="Avec intérêts composés", line=dict(color="#4fc3f7")))
        fig_sim.add_trace(go.Scatter(x=mois_labels, y=valeurs_sans_interet, name="Sans intérêts", line=dict(color="#e53935", dash="dash")))
        fig_sim.update_layout(title=f"Simulation sur {duree_ans} ans", paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0")
        st.plotly_chart(fig_sim, use_container_width=True)

        st.subheader("🔀 Comparaison de scénarios")
        rendements = [3.0, 5.0, 7.0, 10.0]
        fig_scen = go.Figure()
        couleurs_scen = ["#90caf9", "#4fc3f7", "#43a047", "#ffb74d"]
        for i, r in enumerate(rendements):
            rm = r / 100 / 12
            cap = apport_initial
            vals = []
            for _ in range(duree_ans * 12):
                cap = cap * (1 + rm) + versement_mensuel
                vals.append(round(cap, 2))
            fig_scen.add_trace(go.Scatter(x=mois_labels, y=vals, name=f"{r}% / an", line=dict(color=couleurs_scen[i])))
        fig_scen.update_layout(title=f"Comparaison rendements sur {duree_ans} ans", paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0")
        st.plotly_chart(fig_scen, use_container_width=True)

        st.header("🏖️ Simulateur retraite")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            age_actuel = st.number_input("Ton âge actuel", min_value=18, max_value=70, value=28)
            age_retraite = st.number_input("Âge de retraite souhaité", min_value=30, max_value=80, value=50)
            patrimoine_actuel = st.number_input("Patrimoine actuel (€)", min_value=0.0, value=float(total_patrimoine), step=1000.0)
        with col_r2:
            versement_retraite = st.number_input("Épargne mensuelle (€)", min_value=0.0, value=500.0, step=50.0)
            rendement_retraite = st.slider("Rendement annuel (%)", min_value=0.0, max_value=15.0, value=7.0, step=0.5, key="rend_retraite")
            depenses_retraite = st.number_input("Dépenses mensuelles à la retraite (€)", min_value=0.0, value=2000.0, step=100.0)

        duree_retraite = age_retraite - age_actuel
        rm = rendement_retraite / 100 / 12
        capital_r = patrimoine_actuel
        valeurs_r = []
        for _ in range(duree_retraite * 12):
            capital_r = capital_r * (1 + rm) + versement_retraite
            valeurs_r.append(round(capital_r, 2))

        revenu_passif = capital_r * 0.04 / 12
        capital_necessaire = depenses_retraite * 12 / 0.04

        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.metric("Capital à la retraite", f"{capital_r:.2f}€")
        with col_res2:
            st.metric("Revenu passif mensuel", f"{revenu_passif:.2f}€")
        with col_res3:
            st.metric("Capital nécessaire", f"{capital_necessaire:.2f}€")

        if capital_r >= capital_necessaire:
            st.success(f"🎉 Objectif atteint à {age_retraite} ans !")
        else:
            manque = capital_necessaire - capital_r
            st.warning(f"⚠️ Il manque **{manque:.2f}€** pour couvrir tes dépenses à la retraite.")

        mois_labels_r = [f"Mois {i+1}" for i in range(duree_retraite * 12)]
        fig_ret = go.Figure()
        fig_ret.add_trace(go.Scatter(x=mois_labels_r, y=valeurs_r, name="Capital projeté", line=dict(color="#4fc3f7")))
        fig_ret.add_hline(y=capital_necessaire, line_dash="dash", line_color="#e53935", annotation_text="Capital nécessaire")
        fig_ret.update_layout(title=f"Projection vers la retraite à {age_retraite} ans", paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0")
        st.plotly_chart(fig_ret, use_container_width=True)

    with onglet4:
        st.header("📉 Suivi des performances")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            periode = st.selectbox("Période", ["1 mois", "3 mois", "6 mois", "1 an", "2 ans", "5 ans"])
        with col_p2:
            indice = st.selectbox("Indice de référence", ["S&P 500", "CAC 40", "MSCI World", "Nasdaq 100"])

        periodes_map = {"1 mois": "1mo", "3 mois": "3mo", "6 mois": "6mo", "1 an": "1y", "2 ans": "2y", "5 ans": "5y"}
        indices_map = {"S&P 500": "^GSPC", "CAC 40": "^FCHI", "MSCI World": "IWDA.AS", "Nasdaq 100": "^NDX"}

        try:
            df_indice = yf.Ticker(indices_map[indice]).history(period=periodes_map[periode])
            df_indice["rendement"] = (df_indice["Close"] / df_indice["Close"].iloc[0] - 1) * 100
        except:
            df_indice = None

        historique_perf = requests.get(f"{API_URL}/historique", headers=headers)
        if historique_perf.status_code == 200 and historique_perf.json():
            df_histo = pd.DataFrame(historique_perf.json())
            df_histo["date"] = pd.to_datetime(df_histo["date"])
            df_histo = df_histo.sort_values("date")
            df_histo["rendement"] = (df_histo["valeur"] / df_histo["valeur"].iloc[0] - 1) * 100

            if df_indice is not None:
                fig_perf = go.Figure()
                fig_perf.add_trace(go.Scatter(x=df_histo["date"], y=df_histo["rendement"], name="Mon portefeuille", line=dict(color="#4fc3f7")))
                fig_perf.add_trace(go.Scatter(x=df_indice.index, y=df_indice["rendement"], name=indice, line=dict(color="#ffb74d", dash="dash")))
                fig_perf.add_hline(y=0, line_dash="dot", line_color="#666")
                fig_perf.update_layout(title=f"Mon portefeuille vs {indice} — {periode}", paper_bgcolor="#0f1117", plot_bgcolor="#1a1f2e", font_color="#e8eaf0")
                st.plotly_chart(fig_perf, use_container_width=True)

                rend_portfolio = df_histo["rendement"].iloc[-1]
                rend_indice = df_indice["rendement"].iloc[-1]
                diff = rend_portfolio - rend_indice
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Mon portefeuille", f"{rend_portfolio:.2f}%")
                with col_m2:
                    st.metric(indice, f"{rend_indice:.2f}%")
                with col_m3:
                    st.metric("Écart", f"{'🟢' if diff > 0 else '🔴'} {diff:.2f}%")
                if diff > 0:
                    st.success(f"🎉 Tu surperformes le {indice} de **{diff:.2f}%** !")
                else:
                    st.warning(f"⚠️ Tu sous-performes le {indice} de **{abs(diff):.2f}%**.")
        else:
            st.info("Pas assez de données historiques pour comparer. Le graphique s'enrichira au fil du temps. 😊")
