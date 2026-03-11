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

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD (LÓGICA AUTO-REPARO)
# ==========================================
def baixar_xml_original(session, chave):
    headers = { "Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json" }
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"
    try:
        r = session.get(url_get, headers=headers, timeout=12)
        conteudo = r.text.strip()
        xml_limpo = None
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
# DESIGN E ESTILIZAÇÃO (MODO CLARO)
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label, div { color: #1c3d6a !important; }
    .header { background-color: white; padding: 30px; border-bottom: 4px solid #2da9e0; text-align: center; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) { background-color: white !important; padding: 35px !important; border-radius: 20px !important; box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important; }
    textarea { background-color: white !important; color: #1c3d6a !important; border: 1px solid #d1d9e6 !important; }
    .stButton>button { width: 100%; border-radius: 12px !important; height: 3.5rem !important; font-weight: 700 !important; font-size: 16px !important; }
    div.stButton > button:first-child { background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important; color: white !important; }
    div.stButton > button[key="btn_card"] { background: linear-gradient(135deg, #2da9e0 0%, #1c3d6a 100%) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except: st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

col_in, col_check = st.columns([1.3, 1], gap="large")

with col_in:
    st.markdown("### 📥 1. Entrada de Lote")
    txt_input = st.text_area("", height=320, placeholder="Insira as chaves aqui...")

with col_check:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        chaves_v = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_v)
        valor_t = total_n * PRECO_POR_XML
        
        if total_n > 0:
            st.markdown(f"""<div style="background-color:#f0f7ff;padding:25px;border-radius:15px;border-left:6px solid #2da9e0;margin-bottom:20px;">
                <h2 style="margin:0; color: #1c3d6a;">{total_n} XMLs</h2><h3 style="margin:0; color: #2da9e0;">Total: R$ {valor_t:.2f}</h3></div>""", unsafe_allow_html=True)
            
            if st.button("📱 PAGAR COM PIX (Instantâneo)"):
                res = sdk.payment().create({"transaction_amount": float(valor_t), "description": f"Lote {total_n} XMLs", "payment_method_id": "pix", "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}})["response"]
                if "point_of_interaction" in res:
                    st.session_state['qr_b64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pay_id'] = res["id"]
                    st.session_state['lista_chaves'] = chaves_v
                    if 'checkout_url' in st.session_state: del st.session_state['checkout_url']
                    st.rerun()

            st.write("ou")

            # BOTÃO DE CARTÃO COM DIAGNÓSTICO
            if st.button("💳 CARTÃO DE CRÉDITO", key="btn_card"):
                with st.spinner("Conectando ao Mercado Pago..."):
                    pref_data = {
                        "items": [{"title": f"Lote {total_n} XMLs", "quantity": 1, "unit_price": float(valor_t), "currency_id": "BRL"}],
                        "payment_methods": {"installments": 1},
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
                        st.error("🛑 Erro detalhado da API:")
                        st.json(pref_res) # Isso vai nos dizer o motivo real!

# Exibição de Pagamento e Download (Omitido para brevidade, mas deve ser mantido igual ao anterior)
if 'qr_b64' in st.session_state or 'checkout_url' in st.session_state:
    st.info("Área de pagamento ativa abaixo...")
