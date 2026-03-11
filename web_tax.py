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
# MOTOR DE DOWNLOAD (VELOCIDADE MACH 3)
# ==========================================
def baixar_xml(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=12)
        time.sleep(5) # Delay de segurança para a Sefaz liberar o arquivo
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=12)
        if r.status_code == 200:
            conteudo = r.text.strip()
            if "<nfeProc" in conteudo:
                xml_limpo = conteudo[conteudo.find("<"):]
                return True, chave, xml_limpo.encode('utf-8')
    except: pass
    return False, chave, None

# ==========================================
# DESIGN PREMIUM (ESTILO CLEAN / LIGHT MODE)
# ==========================================
st.set_page_config(page_title="Tax XML - Seu XML em Minutos", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label { color: #1c3d6a !important; }

    .header {
        background-color: white;
        padding: 30px;
        border-bottom: 4px solid #2da9e0;
        text-align: center;
        margin-bottom: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) {
        background-color: white !important;
        padding: 35px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 3.8rem !important;
        font-weight: 700 !important;
    }
    
    /* Cor da barra de progresso */
    .stProgress > div > div > div > div { background-color: #76bc43 !important; }
    </style>
    """, unsafe_allow_html=True)

# Header com Logo
st.markdown('<div class="header">', unsafe_allow_html=True)
try:
    st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except:
    st.title("Tax XML")
st.markdown('</div>', unsafe_allow_html=True)

# Layout
col_l, col_r = st.columns([1.3, 1], gap="large")

with col_l:
    st.markdown("### 📥 1. Entrada de Notas")
    txt_input = st.text_area("Cole as chaves abaixo:", height=300, placeholder="44 dígitos...")

with col_r:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        chaves_v = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_v = len(chaves_v)
        valor_v = total_v * PRECO_POR_XML
        
        if total_v > 0:
            st.markdown(f"""
                <div style="background-color: #f0f7ff; padding: 25px; border-radius: 15px; border-left: 6px solid #2da9e0;">
                    <h3 style="margin:0;">{total_v} Notas Fiscais</h3>
                    <h2 style="margin:0; color: #2da9e0;">R$ {valor_v:.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("GERAR PAGAMENTO PIX"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor_v),
                    "description": f"Recuperação {total_v} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Matheus"}
                })["response"]
                
                st.session_state['qr_64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                st.session_state['pix_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                st.session_state['pay_id'] = res["id"]
                st.session_state['lote'] = chaves_v
                st.rerun()

# 3. Processamento e Download
if 'qr_64' in st.session_state:
    st.divider()
    st.markdown("### 🚀 3. Status do Lote")
    c1, c2 = st.columns([1, 1.8])
    with c1:
        st.image(f"data:image/png;base64,{st.session_state['qr_64']}", width=250)
    with c2:
        st.write("Aguardando pagamento...")
        st.code(st.session_state['pix_str'])
        
        if st.button("VERIFICAR PAGAMENTO E INICIAR DOWNLOAD"):
            status_api = sdk.payment().get(st.session_state['pay_id'])["response"]["status"]
            if status_api == "approved":
                st.balloons()
                st.success("Pagamento confirmado! Iniciando motor Mach 3...")
                
                # --- BARRA DE PROGRESSO ---
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                zip_o = io.BytesIO()
                sucesso_n = 0
                total_n = len(st.session_state['lote'])
                
                with zipfile.ZipFile(zip_o, "a", zipfile.ZIP_DEFLATED) as z_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            jobs = {executor.submit(baixar_xml, session, c): c for c in st.session_state['lote']}
                            
                            concluidos = 0
                            for j in as_completed(jobs):
                                ok, ch, xml_d = j.result()
                                concluidos += 1
                                # Atualiza Barra e Texto
                                progress_bar.progress(concluidos / total_n)
                                status_text.write(f"🔄 **Processando:** {concluidos} de {total_n} notas...")
                                
                                if ok:
                                    z_file.writestr(f"{ch}.xml", xml_d)
                                    sucesso_n += 1
                
                if sucesso_n > 0:
                    status_text.markdown(f"✅ **Concluído!** {sucesso_n} notas recuperadas com sucesso.")
                    st.download_button(
                        label=f"⬇️ BAIXAR ARQUIVO .ZIP ({sucesso_n} notas)",
                        data=zip_o.getvalue(),
                        file_name=f"TaxXML_Lote.zip",
                        mime="application/zip"
                    )
            else:
                st.error("Aguardando confirmação do Pix. Tente em 5 segundos.")

st.markdown("<br><br><p style='text-align: center; color: #a1a1a1;'>Tax XML Pro © 2026</p>", unsafe_allow_html=True)

