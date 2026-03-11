import streamlit as st
import requests
import re
import time
import zipfile
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# CONFIGURAÇÕES PRIVADAS
# ==========================================
API_KEY_MEU_DANFE = "36da320b-1b2d-47fa-b626-cc90dea64471"

# ==========================================
# MOTOR MACH 3 - VERSÃO "CIRURGIA DE CABEÇALHO"
# ==========================================
def baixar_xml_turbo(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"
    
    def limpar_xml(texto):
        """Reconstrói o XML para evitar erros de aspas e formatação"""
        if "<nfeProc" in texto:
            corpo = texto[texto.find("<nfeProc"):]
            # Injeta um cabeçalho padrão perfeito (Resolve o erro da Coluna 15)
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{corpo}'.encode('utf-8')
        return None

    try:
        # 1. TENTATIVA RÁPIDA (GET) - Se já estiver no cache da API, baixa em ms
        r = session.get(url_get, headers=headers, timeout=10)
        if r.status_code == 200:
            xml_ok = limpar_xml(r.text)
            if xml_ok: return True, chave, xml_ok

        # 2. TENTATIVA COMPLETA (PUT + WAIT + GET) - Se for nota nova
        session.put(url_add, headers=headers, timeout=10)
        time.sleep(5) # Espera obrigatória para a Sefaz
        
        r = session.get(url_get, headers=headers, timeout=10)
        if r.status_code == 200:
            xml_ok = limpar_xml(r.text)
            if xml_ok: return True, chave, xml_ok
                
    except: pass
    return False, chave, None

# ==========================================
# DESIGN PREMIUM (MODO CLARO FIXO)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - MODO TESTE", page_icon="🧪", layout="wide")

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

    .stButton>button {
        background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 3.8rem !important;
        font-weight: 700 !important;
        font-size: 18px !important;
    }
    
    .stProgress > div > div > div > div { background-color: #76bc43 !important; }
    </style>
    """, unsafe_allow_html=True)

# WhatsApp Suporte
st.markdown('<a href="https://wa.me/595984123456" style="position:fixed; bottom:25px; right:25px; background:#25d366; color:white; padding:12px 25px; border-radius:50px; text-decoration:none; font-weight:bold; z-index:1000; box-shadow:0 4px 15px rgba(0,0,0,0.15);">💬 Suporte Online</a>', unsafe_allow_html=True)

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
try: 
    st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except: 
    st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

# Interface
col_l, col_r = st.columns([1.3, 1], gap="large")

with col_l:
    st.markdown("### 📥 1. Entrada de Chaves")
    st.write("Insira as chaves de 44 dígitos para processamento gratuito.")
    txt_input = st.text_area("", height=320, placeholder="Cole as chaves aqui...")

with col_r:
    st.markdown("### 📊 2. Monitoramento Mach 3")
    if txt_input:
        chaves_lote = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_lote)
        
        if total_n > 0:
            st.success(f"🚀 Fila detectada: **{total_n}** notas fiscais.")
            
            if st.button("INICIAR DOWNLOAD TURBO"):
                st.write("---")
                
                # Barra de Progresso Real-Time
                prog_bar = st.progress(0)
                prog_txt = st.empty()
                
                zip_o = io.BytesIO()
                sucesso_c = 0
                
                with zipfile.ZipFile(zip_o, "a", zipfile.ZIP_DEFLATED) as zf:
                    with requests.Session() as session:
                        # 10 WORKERS SIMULTÂNEOS (MACH 3)
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            jobs = {executor.submit(baixar_xml_turbo, session, c): c for c in chaves_lote}
                            
                            concluidos = 0
                            for j in as_completed(jobs):
                                ok, ch, xml_data = j.result()
                                concluidos += 1
                                
                                # Atualização da Barra de Progresso
                                prog_bar.progress(concluidos / total_n)
                                prog_txt.markdown(f"**Status:** Processando {concluidos} de {total_n}...")
                                
                                if ok:
                                    zf.writestr(f"{ch}.xml", xml_data)
                                    sucesso_c += 1
                
                if sucesso_c > 0:
                    st.balloons()
                    st.success(f"✅ Concluído! {sucesso_c} notas recuperadas.")
                    st.download_button(
                        label=f"⬇️ BAIXAR ARQUIVO .ZIP ({sucesso_c} XMLs)",
                        data=zip_o.getvalue(),
                        file_name=f"TaxXML_Lote.zip",
                        mime="application/zip"
                    )
                else:
                    st.error("Nenhuma nota foi recuperada. Verifique o saldo na API ou as chaves.")
        else:
            st.warning("Insira chaves válidas de 44 dígitos.")
    else:
        st.info("Insira as chaves ao lado para testar a velocidade Mach 3.")

st.markdown("<br><p style='text-align: center; color: #a1a1a1; font-size: 0.8rem;'>Tax XML Pro © 2026 - Moraes Assessoria Internacional</p>", unsafe_allow_html=True)
