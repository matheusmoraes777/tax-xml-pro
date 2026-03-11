import streamlit as st
import requests
import re
import time
import zipfile
import io
import mercadopago
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# CONFIGURAÇÕES PRIVADAS
# ==========================================
API_KEY_MEU_DANFE = "36da320b-1b2d-47fa-b626-cc90dea64471"
MP_ACCESS_TOKEN = "APP_USR-1091359635861022-031115-4083f4ba9bf7da16cf148d67c053efdb-3243990562"
PRECO_POR_XML = 0.15 

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD (VERSÃO EURECA)
# ==========================================
def baixar_xml(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=12)
        time.sleep(5) 
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=12)
        if r.status_code == 200:
            conteudo = r.text.strip()
            if "<nfeProc" in conteudo:
                xml_limpo = conteudo[conteudo.find("<"):]
                return True, chave, xml_limpo.encode('utf-8')
    except: pass
    return False, chave, None

# ==========================================
# DESIGN PREMIUM (FORCE LIGHT MODE)
# ==========================================
st.set_page_config(page_title="Tax XML - Seu XML em Minutos", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    /* FORÇAR MODO CLARO GLOBAL */
    .stApp {
        background-color: #f7f9fc !important;
        color: #1c3d6a !important;
        font-family: 'Poppins', sans-serif;
    }

    /* Ajuste de Texto para Modo Claro */
    h1, h2, h3, p, span, label {
        color: #1c3d6a !important;
    }

    /* Header Branco */
    .header {
        background-color: white;
        padding: 30px;
        border-bottom: 4px solid #2da9e0;
        text-align: center;
        margin-bottom: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    /* Cards Brancos com Sombra */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) {
        background-color: white !important;
        padding: 35px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important;
        border: 1px solid #eef2f6 !important;
    }

    /* Área de Texto (Input) */
    textarea {
        background-color: #fcfcfc !important;
        color: #1c3d6a !important;
        border: 1px solid #d1d9e6 !important;
    }

    /* Botão Verde (Siga o padrão da Logo) */
    .stButton>button {
        background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 3.8rem !important;
        font-weight: 700 !important;
        font-size: 18px !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(118, 188, 67, 0.3) !important;
    }

    /* WhatsApp Flutuante */
    .whatsapp-btn {
        position: fixed;
        bottom: 25px;
        right: 25px;
        background-color: #25d366;
        color: white !important;
        border-radius: 50px;
        padding: 12px 25px;
        font-weight: bold;
        text-decoration: none;
        z-index: 1000;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Botão de Suporte
st.markdown('<a href="https://wa.me/595984123456" class="whatsapp-btn">💬 Suporte Online</a>', unsafe_allow_html=True)

# Header com Logo
st.markdown('<div class="header">', unsafe_allow_html=True)
try:
    st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except:
    st.title("Tax XML")
st.markdown('</div>', unsafe_allow_html=True)

# Layout Principal
st.write("") 
col_l, col_r = st.columns([1.3, 1], gap="large")

with col_l:
    st.markdown("### 📥 1. Entrada de Lote")
    st.write("Cole suas chaves de acesso abaixo para recuperar os arquivos.")
    txt_input = st.text_area("", height=320, placeholder="Ex: 31250917155730000164550010000846641770615626")
    st.caption("🔐 Processamento direto e seguro via API Sefaz.")

with col_r:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        chaves_validas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_validas)
        valor_n = total_n * PRECO_POR_XML
        
        if total_n > 0:
            st.markdown(f"""
                <div style="background-color: #f0f7ff; padding: 25px; border-radius: 15px; border-left: 6px solid #2da9e0; margin-bottom: 20px;">
                    <p style="margin:0; font-size: 14px; color: #1c3d6a;">Resumo do Pedido:</p>
                    <h3 style="margin:0; color: #1c3d6a;">{total_n} Notas Fiscais</h3>
                    <h2 style="margin:0; color: #2da9e0;">R$ {valor_n:.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("GERAR PAGAMENTO PIX"):
                with st.spinner("Conectando ao banco..."):
                    res = sdk.payment().create({
                        "transaction_amount": float(valor_n),
                        "description": f"Lote {total_n} XMLs",
                        "payment_method_id": "pix",
                        "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                    })["response"]
                    
                    st.session_state['qr_b64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_val'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['mp_id'] = res["id"]
                    st.session_state['lote_ch'] = chaves_validas
                    st.rerun()
        else:
            st.warning("Insira chaves válidas para prosseguir.")
    else:
        st.info("Insira as chaves ao lado para calcular o valor.")

# Área de Checkout
if 'qr_b64' in st.session_state:
    st.divider()
    st.markdown("### 🚀 3. Concluir e Baixar")
    c1, c2 = st.columns([1, 1.8])
    with c1:
        st.image(f"data:image/png;base64,{st.session_state['qr_b64']}", width=280)
    with c2:
        st.write("Aponte a câmera do celular para o QR Code ou use o código abaixo:")
        st.code(st.session_state['pix_val'], language="text")
        
        if st.button("VERIFICAR PAGAMENTO E BAIXAR"):
            status_pg = sdk.payment().get(st.session_state['mp_id'])["response"]["status"]
            if status_pg == "approved":
                st.balloons()
                st.success("Pagamento aprovado!")
                
                zip_o = io.BytesIO()
                sucesso_c = 0
                
                with zipfile.ZipFile(zip_o, "a", zipfile.ZIP_DEFLATED) as z_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            jobs = {executor.submit(baixar_xml, session, c): c for c in st.session_state['lote_ch']}
                            for j in as_completed(jobs):
                                ok, ch, xml_d = j.result()
                                if ok:
                                    z_file.writestr(f"{ch}.xml", xml_data=xml_d)
                                    sucesso_c += 1
                
                if sucesso_c > 0:
                    st.download_button(
                        label=f"⬇️ BAIXAR {sucesso_c} ARQUIVOS XML",
                        data=zip_o.getvalue(),
                        file_name=f"TaxXML_Lote.zip",
                        mime="application/zip"
                    )
            else:
                st.error("Aguardando confirmação... (Pague o PIX e tente novamente em 5 segundos)")

st.markdown("<br><br><p style='text-align: center; color: #a1a1a1; font-size: 0.8rem;'>Tax XML Pro © 2026 - Moraes Assessoria Internacional</p>", unsafe_allow_html=True)
