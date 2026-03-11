import streamlit as st
import requests
import re
import time
import zipfile
import io
import mercadopago
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# CONFIGURAÇÕES DE INTEGRAÇÃO
# ==========================================
API_KEY_MEU_DANFE = "36da320b-1b2d-47fa-b626-cc90dea64471"
MP_ACCESS_TOKEN = "APP_USR-1091359635861022-031115-4083f4ba9bf7da16cf148d67c053efdb-3243990562"
PRECO_POR_XML = 0.15 
MEU_SITE_URL = "https://taxxml.streamlit.app" # URL para retorno do pagamento

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD (LÓGICA AUTO-REPARO)
# ==========================================
def baixar_xml_original(session, chave):
    headers = { "Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json" }
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"

    try:
        # TENTATIVA 1: GET Direto (Caminho Rápido)
        r = session.get(url_get, headers=headers, timeout=12)
        conteudo = r.text.strip()
        xml_limpo = None

        # --- LÓGICA DE AUTO-REPARO (NÃO REMOVER) ---
        if conteudo.startswith('{'):
            try:
                js = r.json()
                xml_limpo = js.get('data') or js.get('xml')
            except: pass
        elif conteudo.startswith('<'):
            xml_limpo = conteudo

        if xml_limpo and "<nfeProc" in xml_limpo:
            xml_final = xml_limpo[xml_limpo.find("<"):]
            return True, chave, xml_final.encode('utf-8')

        # TENTATIVA 2: PUT + WAIT (Caso seja nota nova)
        session.put(url_add, headers=headers, timeout=12)
        time.sleep(5) 

        r = session.get(url_get, headers=headers, timeout=12)
        conteudo = r.text.strip()
        
        if conteudo.startswith('{'):
            try:
                js = r.json()
                xml_limpo = js.get('data') or js.get('xml')
            except: pass
        elif conteudo.startswith('<'):
            xml_limpo = conteudo

        if xml_limpo and "<nfeProc" in xml_limpo:
            xml_final = xml_limpo[xml_limpo.find("<"):]
            return True, chave, xml_final.encode('utf-8')

    except: pass
    return False, chave, None

# ==========================================
# DESIGN E ESTILIZAÇÃO (LIGHT MODE PREMIUM)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - Gestão Tributária", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    /* FORÇAR MODO CLARO */
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label, div { color: #1c3d6a !important; }

    .header {
        background-color: white;
        padding: 30px;
        border-bottom: 4px solid #2da9e0;
        text-align: center;
        margin-bottom: 35px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) {
        background-color: white !important;
        padding: 35px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important;
    }

    textarea { background-color: white !important; color: #1c3d6a !important; border: 1px solid #d1d9e6 !important; }

    .stButton>button { width: 100%; border-radius: 12px !important; height: 3.5rem !important; font-weight: 700 !important; font-size: 16px !important; }
    
    /* Cores dos Botões */
    div.stButton > button:first-child { background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important; color: white !important; border: none !important; }
    div.stButton > button[key="btn_card"] { background: linear-gradient(135deg, #2da9e0 0%, #1c3d6a 100%) !important; color: white !important; border: none !important; }

    .stProgress > div > div > div > div { background-color: #76bc43 !important; }
    </style>
    """, unsafe_allow_html=True)

# WhatsApp Suporte
st.markdown('<a href="https://wa.me/595984123456" style="position:fixed; bottom:25px; right:25px; background:#25d366; color:white; padding:12px 25px; border-radius:50px; text-decoration:none; font-weight:bold; z-index:1000; box-shadow:0 4px 15px rgba(0,0,0,0.15);">💬 Suporte Online</a>', unsafe_allow_html=True)

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except: st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

# Interface Principal
col_in, col_check = st.columns([1.3, 1], gap="large")

with col_in:
    st.markdown("### 📥 1. Entrada de Lote")
    st.write("Insira as chaves de acesso para iniciar a recuperação.")
    txt_input = st.text_area("", height=320, placeholder="Uma chave por linha...")

with col_check:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        chaves_v = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_v)
        valor_total = total_n * PRECO_POR_XML
        
        if total_n > 0:
            st.markdown(f"""
                <div style="background-color: #f0f7ff; padding: 25px; border-radius: 15px; border-left: 6px solid #2da9e0; margin-bottom: 20px;">
                    <p style="margin:0; font-size: 14px;">Total de Documentos:</p>
                    <h2 style="margin:0; color: #1c3d6a;">{total_n} XMLs</h2>
                    <h3 style="margin:0; color: #2da9e0;">R$ {valor_total:.2f}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            # OPÇÃO PIX
            if st.button("📱 PAGAR COM PIX (Instantâneo)"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor_total),
                    "description": f"Recuperação {total_n} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                })["response"]
                
                if "point_of_interaction" in res:
                    st.session_state['qr_b64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pay_id'] = res["id"]
                    st.session_state['lista_chaves'] = chaves_v
                    if 'checkout_url' in st.session_state: del st.session_state['checkout_url']
                    st.rerun()

            st.write("ou")

            # OPÇÃO CARTÃO DE CRÉDITO (CORRIGIDO COM BACK_URLS)
            if st.button("💳 CARTÃO DE CRÉDITO", key="btn_card"):
                with st.spinner("Conectando ao checkout seguro..."):
                    pref_data = {
                        "items": [{"title": f"Lote {total_n} XMLs - Tax XML", "quantity": 1, "unit_price": float(valor_total), "currency_id": "BRL"}],
                        "payment_methods": {"installments": 1},
                        "back_urls": {
                            "success": MEU_SITE_URL,
                            "failure": MEU_SITE_URL,
                            "pending": MEU_SITE_URL
                        },
                        "auto_return": "approved",
                    }
                    result = sdk.preference().create(pref_data)
                    pref_res = result["response"]
                    
                    if "init_point" in pref_res:
                        st.session_state['checkout_url'] = pref_res["init_point"]
                        st.session_state['lista_chaves'] = chaves_v
                        st.session_state['pay_id'] = "CHECKOUT_PRO"
                        if 'qr_b64' in st.session_state: del st.session_state['qr_b64']
                        st.rerun()
                    else:
                        st.error("Erro técnico no checkout. Tente PIX ou suporte.")
        else:
            st.warning("Insira chaves de 44 dígitos válidas.")

# --- ÁREA DE PAGAMENTO ---
if 'qr_b64' in st.session_state:
    st.divider()
    c_qr, c_status = st.columns([1, 1.8])
    with c_qr: st.image(f"data:image/png;base64,{st.session_state['qr_b64']}", width=280)
    with c_status:
        st.write("### Pague o PIX para liberar o lote")
        st.code(st.session_state['pix_str'], language="text")
        if st.button("✅ CONFIRMAR PAGAMENTO E BAIXAR"):
            p_status = sdk.payment().get(st.session_state['pay_id'])["response"]["status"]
            if p_status == "approved": st.session_state['pago'] = True
            else: st.error("Pagamento pendente no sistema bancário.")

if 'checkout_url' in st.session_state:
    st.divider()
    st.markdown(f"""
        <div style="text-align: center; padding: 40px; background-color: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eef2f6;">
            <h3 style="color: #1c3d6a;">Pagamento via Cartão de Crédito</h3>
            <p>Clique no botão abaixo para abrir o ambiente seguro do Mercado Pago.</p>
            <a href="{st.session_state['checkout_url']}" target="_blank">
                <button style="background-color: #2da9e0; color: white; border: none; padding: 18px 40px; border-radius: 12px; font-weight: bold; font-size: 18px; cursor: pointer; width: 320px; transition: 0.3s;">
                    💳 Finalizar Pagamento
                </button
