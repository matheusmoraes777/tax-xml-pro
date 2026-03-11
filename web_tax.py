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
# MOTOR DE DOWNLOAD (AUTO-REPARO BLINDADO)
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
# DESIGN E ESTILIZAÇÃO (LIGHT MODE)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - Recuperação de Notas", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    .header { background-color: white; padding: 30px; border-bottom: 4px solid #2da9e0; text-align: center; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 12px !important; height: 3.5rem !important; font-weight: 700 !important; }
    .btn-pix { background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important; color: white !important; border: none !important; }
    .btn-card { background: linear-gradient(135deg, #2da9e0 0%, #1c3d6a 100%) !important; color: white !important; border: none !important; }
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
    txt_input = st.text_area("Cole as chaves aqui:", height=300, placeholder="Insira as chaves de 44 dígitos...")

with col_check:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        chaves_v = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_v)
        valor_t = total_n * PRECO_POR_XML
        
        if total_n > 0:
            st.markdown(f"""<div style="background-color:#f0f7ff;padding:25px;border-radius:15px;border-left:6px solid #2da9e0;margin-bottom:20px;">
                <h3 style="margin:0;">{total_n} XMLs</h3><h2 style="margin:0;color:#2da9e0;">R$ {valor_t:.2f}</h2></div>""", unsafe_allow_html=True)
            
            # OPÇÃO 1: PIX
            if st.button("📱 PAGAR COM PIX (Instantâneo)", key="btn_pix"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor_t), "description": f"Lote {total_n} XMLs",
                    "payment_method_id": "pix", "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                })["response"]
                st.session_state['qr'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                st.session_state['p_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                st.session_state['p_id'] = res["id"]
                st.session_state['lote'] = chaves_v
                st.rerun()
            
            # OPÇÃO 2: CARTÃO DE CRÉDITO
            if st.button("💳 CARTÃO DE CRÉDITO / OUTROS", key="btn_card"):
                pref_data = {
                    "items": [{"title": f"Lote {total_n} XMLs", "quantity": 1, "unit_price": float(valor_t)}],
                    "payment_methods": {"installments": 1}, # Trava em 1x se você desejar
                    "auto_return": "approved",
                }
                pref_res = sdk.preference().create(pref_data)["response"]
                st.session_state['checkout_url'] = pref_res["init_point"]
                st.session_state['lote'] = chaves_v
                # Simula um ID para o fluxo de download
                st.session_state['p_id'] = "CHECKOUT_PRO" 
                st.rerun()

# --- ÁREA DE PAGAMENTO ---
if 'qr' in st.session_state:
    st.divider()
    c_qr, c_txt = st.columns([1, 2])
    with c_qr: st.image(f"data:image/png;base64,{st.session_state['qr']}", width=250)
    with c_txt:
        st.write("### Escaneie para pagar via PIX")
        st.code(st.session_state['p_str'])
        if st.button("🚀 CONFIRMAR E BAIXAR"):
            # Lógica de download que já funciona...
            st.success("Verificando...")

if 'checkout_url' in st.session_state:
    st.divider()
    st.markdown(f"""
        <div style="text-align: center; padding: 30px; background-color: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h3>Finalize seu pagamento com segurança</h3>
            <p>Clique no botão abaixo para pagar com Cartão de Crédito ou Boleto via Mercado Pago.</p>
            <a href="{st.session_state['checkout_url']}" target="_blank">
                <button style="background-color: #2da9e0; color: white; border: none; padding: 15px 30px; border-radius: 10px; font-weight: bold; font-size: 18px; cursor: pointer;">
                    💳 Pagar com Mercado Pago
                </button>
            </a>
            <p style="margin-top: 20px; font-size: 14px; color: #8b949e;">Após pagar, volte aqui e clique em "Confirmar Download".</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 CONFIRMAR DOWNLOAD (APÓS PAGAR)"):
        # Lógica de download
        st.success("Processando...")
