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
MEU_SITE_URL = "https://taxxml.streamlit.app"

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD (AUTO-REPARO ORIGINAL)
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
# DESIGN PREMIUM
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    .header { background-color: white; padding: 30px; border-bottom: 4px solid #2da9e0; text-align: center; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 12px !important; height: 3.5rem !important; font-weight: 700 !important; }
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
    txt_input = st.text_area("Insira suas chaves aqui:", height=320)

with col_check:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        ch_limpas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(ch_limpas)
        valor = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f'<div style="background-color:#f0f7ff;padding:25px;border-radius:15px;border-left:6px solid #2da9e0;margin-bottom:20px;">'
                        f'<h2 style="margin:0;">{total} XMLs</h2>'
                        f'<h3 style="margin:0;color:#2da9e0;">Total: R$ {valor:.2f}</h3>'
                        f'</div>', unsafe_allow_html=True)
            
            # BOTAO PIX
            if st.button("📱 PAGAR COM PIX"):
                with st.spinner("Gerando PIX..."):
                    res = sdk.payment().create({"transaction_amount": float(valor), "description": f"Lote {total} XMLs", "payment_method_id": "pix", "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}})["response"]
                    if "point_of_interaction" in res:
                        st.session_state['qr_b64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                        st.session_state['pix_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                        st.session_state['pay_id'] = res["id"]
                        st.session_state['l_chaves'] = ch_limpas
                        if 'c_url' in st.session_state: del st.session_state['c_url']
                        st.rerun()

            # BOTAO CARTAO (COM TRATAMENTO DE ERRO MELHORADO)
            if st.button("💳 CARTÃO DE CRÉDITO", key="btn_card"):
                with st.spinner("Criando link de pagamento..."):
                    pref_data = {
                        "items": [{"title": f"Lote {total} XMLs", "quantity": 1, "unit_price": float(valor), "currency_id": "BRL"}],
                        "payer": {"email": "cliente@taxxml.com"},
                        "payment_methods": {"installments": 1},
                        "back_urls": {"success": MEU_SITE_URL, "failure": MEU_SITE_URL, "pending": MEU_SITE_URL},
                        "auto_return": "approved"
                    }
                    result = sdk.preference().create(pref_data)
                    pref_res = result["response"]
                    
                    if "init_point" in pref_res:
                        st.session_state['c_url'] = pref_res["init_point"]
                        st.session_state['l_chaves'] = ch_limpas
                        st.session_state['pay_id'] = "CARD"
                        if 'qr_b64' in st.session_state: del st.session_state['qr_b64']
                        st.rerun()
                    else:
                        st.error("Erro na API do Mercado Pago ao gerar Cartão:")
                        st.json(pref_res) # Isso vai nos dizer por que "nada acontece"

# --- AREA DE PAGAMENTO ---
if 'qr_b64' in st.session_state:
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1: st.image(f"data:image/png;base64,{st.session_state['qr_b64']}", width=250)
    with c2:
        st.write("### Escaneie o PIX")
        st.code(st.session_state['pix_str'])
        if st.button("✅ CONFIRMAR PIX E BAIXAR"):
            p_status = sdk.payment().get(st.session_state['pay_id'])["response"]["status"]
            if p_status == "approved": st.session_state['pago'] = True
            else: st.error("Pagamento não detectado ainda.")

if 'c_url' in st.session_state:
    st.divider()
    st.markdown(f'<div style="text-align:center;padding:30px;background:white;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.05);">'
                f'<h3>Finalize no Cartão de Crédito</h3>'
                f'<a href="{st.session_state["c_url"]}" target="_blank">'
                f'<button style="background:#2da9e0;color:white;border:none;padding:15px 30px;border-radius:10px;font-weight:bold;cursor:pointer;width:280px;">💳 PAGAR AGORA</button></a>'
                f'<p style="margin-top:15px;">Após pagar, volte aqui e clique no botão abaixo.</p></div>', unsafe_allow_html=True)
    if st.button("🚀 LIBERAR MEUS XMLS"): st.session_state['pago'] = True

# --- MOTOR ---
if st.session_state.get('pago'):
    st.balloons()
    pb = st.progress(0)
    zip_buf = io.BytesIO()
    sucessos = 0
    total_lote = len(st.session_state['l_chaves'])
    with zipfile.ZipFile(zip_buf, "a", zipfile.ZIP_DEFLATED) as zf:
        with requests.Session() as sess:
            with ThreadPoolExecutor(max_workers=10) as exe:
                jobs = {exe.submit(baixar_xml_original, sess, c): c for c in st.session_state['l_chaves']}
                for i, j in enumerate(as_completed(jobs)):
                    ok, ch, xml_data = j.result()
                    pb.progress((i + 1) / total_lote)
                    if ok:
                        zf.writestr(f"{ch}.xml", xml_data)
                        sucessos += 1
    if sucessos > 0:
        st.download_button(f"⬇️ BAIXAR {sucessos} XMLs", zip_buf.getvalue(), "TaxXML_Lote.zip", "application/zip")
        st.session_state['pago'] = False
