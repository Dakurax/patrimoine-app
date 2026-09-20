import streamlit as st
import requests
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Patrimoine App", page_icon="📊")

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
    st.title(f"📊 Bonjour {st.session_state.email} !")
    
    if st.button("Se déconnecter"):
        st.session_state.token = None
        st.session_state.email = None
        st.rerun()

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # ─── Positions ───
    st.header("📈 Mes positions")
    response = requests.get(f"{API_URL}/positions", headers=headers)
    positions = response.json()

    if positions:
        total = 0
        noms = []
        valeurs = []

        for p in positions:
            try:
                prix = yf.Ticker(p["ticker"]).history(period="1d")["Close"].iloc[-1]
                valeur = prix * p["quantite"]
                pv = (prix - p["px_moyen"]) * p["quantite"]
                total += valeur
                noms.append(p["nom"])
                valeurs.append(round(valeur, 2))
                couleur = "🟢" if pv > 0 else "🔴"
                st.markdown(f'<div style="background:#1a1f2e;padding:10px;border-radius:8px;margin:5px 0;">{couleur} <b>{p["nom"]}</b> — Prix : {prix:.2f}€ — Valeur : {valeur:.2f}€ — PV : {pv:.2f}€</div>', unsafe_allow_html=True)
            except:
                st.markdown(f'<div style="background:#1a1f2e;padding:10px;border-radius:8px;margin:5px 0;">📌 <b>{p["nom"]}</b> — Prix non disponible</div>', unsafe_allow_html=True)

        st.success(f"**Total positions : {total:.2f}€**")

        # ─── Ajouter une position ───
        with st.expander("➕ Ajouter une position"):
            nom = st.text_input("Nom")
            ticker = st.text_input("Ticker")
            quantite = st.number_input("Quantité", min_value=0.0)
            px_moyen = st.number_input("Prix moyen", min_value=0.0)
            type_pos = st.selectbox("Type", ["pea", "cto", "crypto"])
            if st.button("Ajouter"):
                response = requests.post(
                    f"{API_URL}/positions",
                    headers=headers,
                    json={"nom": nom, "ticker": ticker, "quantite": quantite, "px_moyen": px_moyen, "type": type_pos}
                )
                if response.status_code == 200:
                    st.success("Position ajoutée !")
                    st.rerun()

            # ─── Modifier une position ───
    with st.expander("✏️ Modifier une position"):
        if positions:
            noms_pos = [p["nom"] for p in positions]
            nom_choisi = st.selectbox("Choisir", noms_pos, key="mod_pos")
            pos = next(p for p in positions if p["nom"] == nom_choisi)
            nouvel_achat = st.number_input("Quantité achetée", min_value=0.0, key="qte_mod")
            prix_achat = st.number_input("Prix d'achat", min_value=0.0, key="px_mod")
            if nouvel_achat > 0 and prix_achat > 0:
                nouvelle_qte = pos["quantite"] + nouvel_achat
                nouveau_px = ((pos["quantite"] * pos["px_moyen"]) + (nouvel_achat * prix_achat)) / nouvelle_qte
                st.info(f"➡️ Nouvelle quantité : {nouvelle_qte} — Nouveau prix moyen : {nouveau_px:.3f}€")
                if st.button("Confirmer", key="confirm_mod_pos"):
                    requests.put(f"{API_URL}/positions/{nom_choisi}",
                        headers=headers,
                        json={"quantite": nouvelle_qte, "px_moyen": round(nouveau_px, 3)}
                    )
                    st.success("Position modifiée !")
                    st.rerun()

    # ─── Supprimer une position ───
    with st.expander("🗑️ Supprimer une position"):
        if positions:
            nom_suppr = st.selectbox("Choisir", [p["nom"] for p in positions], key="suppr_pos")
            st.warning(f"⚠️ Supprimer {nom_suppr} ?")
            if st.button("Supprimer", key="del_pos"):
                requests.delete(f"{API_URL}/positions/{nom_suppr}", headers=headers)
                st.success("Position supprimée !")
                st.rerun()

        # ─── Camembert positions ───
        if valeurs:
            fig = px.pie(values=valeurs, names=noms, title="Répartition du portefeuille")
            fig.update_layout(paper_bgcolor="#0f1117", font_color="#e8eaf0")
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Aucune position pour l'instant.")

    # ─── Livrets ───
    st.header("🏦 Mes livrets")
    response_liv = requests.get(f"{API_URL}/livrets", headers=headers)
    livrets = response_liv.json()

    if livrets:
        total_livrets = 0
        for l in livrets:
            total_livrets += l["valeur"]
            st.markdown(f'<div style="background:#1a1f2e;padding:10px;border-radius:8px;margin:5px 0;">💰 <b>{l["nom"]}</b> : {l["valeur"]:.2f}€</div>', unsafe_allow_html=True)
        st.success(f"**Total livrets : {total_livrets:.2f}€**")
    else:
        st.info("Aucun livret pour l'instant.")

    # ─── Ajouter un livret ───
    with st.expander("➕ Ajouter un livret"):
        nom_liv = st.text_input("Nom du livret", key="nom_liv")
        valeur_liv = st.number_input("Valeur (€)", min_value=0.0, key="val_liv")
        if st.button("Ajouter le livret"):
            response = requests.post(
                f"{API_URL}/livrets",
                headers=headers,
                json={"nom": nom_liv, "valeur": valeur_liv}
            )
            if response.status_code == 200:
                st.success("Livret ajouté !")
                st.rerun()

    # ─── Crypto ───
    st.header("₿ Mes cryptos")
    response_crypto = requests.get(f"{API_URL}/crypto", headers=headers)
    cryptos = response_crypto.json()

    if cryptos:
        total_crypto = 0
        for c in cryptos:
            try:
                prix = yf.Ticker(c["ticker"]).history(period="1d")["Close"].iloc[-1]
                valeur = prix * c["quantite"]
                total_crypto += valeur
                st.markdown(f'<div style="background:#1a1f2e;padding:10px;border-radius:8px;margin:5px 0;">🔵 <b>{c["nom"]}</b> — Prix : {prix:.2f}€ — Valeur : {valeur:.2f}€</div>', unsafe_allow_html=True)
            except:
                st.markdown(f'<div style="background:#1a1f2e;padding:10px;border-radius:8px;margin:5px 0;">🔵 <b>{c["nom"]}</b> — Prix non disponible</div>', unsafe_allow_html=True)
        st.success(f"**Total crypto : {total_crypto:.2f}€**")
    else:
        st.info("Aucune crypto pour l'instant.")

    # ─── Ajouter une crypto ───
    with st.expander("➕ Ajouter une crypto"):
        nom_crypto = st.text_input("Nom", key="nom_crypto")
        ticker_crypto = st.text_input("Ticker (ex: BTC-EUR)", key="ticker_crypto")
        quantite_crypto = st.number_input("Quantité", min_value=0.0, key="qte_crypto")
        if st.button("Ajouter la crypto"):
            response = requests.post(
                f"{API_URL}/crypto",
                headers=headers,
                json={"nom": nom_crypto, "ticker": ticker_crypto, "quantite": quantite_crypto}
            )
            if response.status_code == 200:
                st.success("Crypto ajoutée !")
                st.rerun()
