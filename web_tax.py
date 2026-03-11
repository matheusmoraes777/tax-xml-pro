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
                # Garante que o XML comece no caractere correto
                xml_limpo = conteudo[conteudo.find("<"):]
                return True, chave, xml_limpo.encode('utf-8')
    except: pass
    return False, chave, None

# ==========================================
# DESIGN PREMIUM (CLEAN & TRUST)
# ==========================================
st.set_page_config(page_title="Tax XML - Seu XML em Minutos", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    .main { background-color: #fcfcfc; font-family: 'Poppins', sans-serif; }
    
    /* Header e Títulos */
    h1, h2, h3 { color: #1c3d6a !important; font-weight: 700 !important; }
    .stMarkdown p { color: #5a5a5a; font-size: 1.05rem; }
    
    /* Cards Brancos com Sombra Suave */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) {
        background-color: white !important;
        padding: 30px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.04) !important;
        border: 1px solid #f0f0f0 !important;
    }

    /* Botão Verde Profissional */
    .stButton>button {
        background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%);
        color: white;
        border: none;
        border-radius: 12px;
        height: 3.8rem;
        font-weight: 700;
        font-size: 18px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(118, 188, 67, 0.3); }

    /* Botão Flutuante WhatsApp */
    .whatsapp-btn {
        position: fixed;
        bottom: 25px;
        right: 25px;
        background-color: #25d366;
        color: white;
        border-radius: 50px;
        padding: 12px 25px;
        font-weight: bold;
        text-decoration: none;
        z-index: 1000;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# WhatsApp Flutuante
st.markdown('<a href="https://wa.me/595984123456" class="whatsapp-btn">💬 Suporte Online</a>', unsafe_allow_html=True)

# Cabeçalho com Logo do GitHub
st.write("") # Espaçador
col_logo, _ = st.columns([1, 4])
with col_logo:
    # Busca a imagem que você subiu no GitHub
    try:
        st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=220)
    except:
        st.title("Tax XML") # Fallback caso a imagem mude de nome

st.write("") 

# Layout Principal
col_left, col_right = st.columns([1.3, 1], gap="large")

with col_left:
    st.markdown("### 📥 Entrada de Lote")
    st.write("Insira as chaves de acesso para recuperação imediata.")
    txt_input = st.text_area("", height=320, placeholder="Cole as chaves aqui...")
    st.caption("🔒 Processamento criptografado via API Sefaz.")

with col_right:
    st.markdown("### 💳 Pagamento e Liberação")
    if txt_input:
        chaves_lote = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_notas = len(chaves_lote)
        preco_total = total_notas * PRECO_POR_XML
        
        if total_notas > 0:
            st.markdown(f"""
                <div style="background-color: #eef9f1; padding: 20px; border-radius: 12px; border-left: 5px solid #76bc43;">
                    <p style="margin:0; color: #1c3d6a;"><b>{total_notas} Notas Identificadas</b></p>
                    <h2 style="margin:0; color: #1c3d6a;">R$ {preco_total:.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("GERAR PIX DE COBRANÇA"):
                with st.spinner("Conectando ao banco..."):
                    res = sdk.payment().create({
                        "transaction_amount": float(preco_total),
                        "description": f"Recuperação {total_notas} XMLs",
                        "payment_method_id": "pix",
                        "payer": {"email": "contato@taxxml.com", "first_name": "Matheus"}
                    })["response"]
                    
                    st.session_state['qr_base64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['payment_id'] = res["id"]
                    st.session_state['lista_final'] = chaves_lote
                    st.rerun()
        else:
            st.warning("Aguardando chaves válidas de 44 dígitos.")
    else:
        st.write("O valor será calculado automaticamente após a inserção das chaves.")

# Checkout
if 'qr_base64' in st.session_state:
    st.divider()
    st.markdown("### 🚀 Concluir e Baixar")
    c1, c2 = st.columns([1, 1.8])
    with c1:
        st.image(f"data:image/png;base64,{st.session_state['qr_base64']}", width=280)
    with c2:
        st.write("Pague via Pix e clique no botão para processar o download.")
        st.code(st.session_state['pix_str'], language="text")
        
        if st.button("VERIFICAR PAGAMENTO E BAIXAR"):
            status_banco = sdk.payment().get(st.session_state['payment_id'])["response"]["status"]
            if status_banco == "approved":
                st.balloons()
                st.success("Pagamento aprovado! Preparando arquivos...")
                
                zip_out = io.BytesIO()
                sucessos_download = 0
                
                with zipfile.ZipFile(zip_out, "a", zipfile.ZIP_DEFLATED) as zf:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            tarefas = {executor.submit(baixar_xml, session, c): c for c in st.session_state['lista_final']}
                            for t in as_completed(tarefas):
                                ok, ch, xml_data = t.result()
                                if ok:
                                    zf.writestr(f"{ch}.xml", xml_data)
                                    sucessos_download += 1
                
                if sucessos_download > 0:
                    st.download_button(
                        label=f"⬇️ BAIXAR {sucessos_download} XMLs",
                        data=zip_out.getvalue(),
                        file_name=f"TaxXML_Lote.zip",
                        mime="application/zip"
                    )
            else:
                st.info("Pagamento ainda pendente. Aguarde 10 segundos e tente de novo.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #8b949e; font-size: 0.8rem;'>Tax XML Pro © 2026 - Moraes Assessoria Internacional</p>", unsafe_allow_html=True)
