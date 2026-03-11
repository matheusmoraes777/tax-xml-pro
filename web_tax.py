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
# MOTOR MACH 3 (ESTRATÉGIA DE ALTA VELOCIDADE)
# ==========================================
def baixar_xml_mach3(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"
    
    try:
        # TENTATIVA 1: Tenta baixar direto (Caminho Rápido)
        r = session.get(url_get, headers=headers, timeout=10)
        
        if r.status_code == 200:
            conteudo = r.text.strip()
            if "<nfeProc" in conteudo:
                return True, chave, conteudo[conteudo.find("<"):].encode('utf-8')

        # TENTATIVA 2: Se não achou, adiciona e espera (Caminho de Segurança)
        session.put(url_add, headers=headers, timeout=10)
        time.sleep(4) # Só "sofre" esse delay se a nota for nova
        
        r = session.get(url_get, headers=headers, timeout=10)
        if r.status_code == 200:
            conteudo = r.text.strip()
            if "<nfeProc" in conteudo:
                return True, chave, conteudo[conteudo.find("<"):].encode('utf-8')
                
    except: pass
    return False, chave, None

# ==========================================
# DESIGN PREMIUM (MODO CLARO FIXO)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - MACH 3", page_icon="🏎️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label { color: #1c3d6a !important; }
    .header { background-color: white; padding: 25px; border-bottom: 4px solid #2da9e0; text-align: center; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) { background-color: white !important; padding: 30px !important; border-radius: 15px !important; box-shadow: 0 10px 40px rgba(0,0,0,0.05) !important; }
    .stButton>button { background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important; color: white !important; border-radius: 10px !important; height: 3.5rem !important; font-weight: 700 !important; }
    .stProgress > div > div > div > div { background-color: #76bc43 !important; }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=220)
except: st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

# Layout
col_l, col_r = st.columns([1.3, 1], gap="large")

with col_l:
    st.markdown("### 📥 Entrada de Lote")
    txt_input = st.text_area("Cole as chaves para processamento Mach 3:", height=300)

with col_r:
    st.markdown("### 📊 Monitoramento Turbo")
    if txt_input:
        chaves_v = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_v)
        
        if total_n > 0:
            st.info(f"🚀 Fila pronta: **{total_n}** notas.")
            
            if st.button("INICIAR MOTOR MACH 3"):
                st.write("---")
                prog_bar = st.progress(0)
                prog_txt = st.empty()
                
                zip_o = io.BytesIO()
                sucesso_c = 0
                
                with zipfile.ZipFile(zip_o, "a", zipfile.ZIP_DEFLATED) as zf:
                    with requests.Session() as session:
                        # TURBO: Aumentamos para 10 workers para voar baixo
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            jobs = {executor.submit(baixar_xml_mach3, session, c): c for c in chaves_v}
                            
                            concluidos = 0
                            for j in as_completed(jobs):
                                ok, ch, xml_d = j.result()
                                concluidos += 1
                                
                                # Atualização Visual
                                prog_bar.progress(concluidos / total_n)
                                prog_txt.markdown(f"**Status:** {concluidos}/{total_n} notas processadas...")
                                
                                if ok:
                                    zf.writestr(f"{ch}.xml", xml_d)
                                    sucesso_c += 1
                
                if sucesso_c > 0:
                    st.balloons()
                    st.success(f"✅ Finalizado! {sucesso_c} notas recuperadas.")
                    st.download_button(
                        label=f"⬇️ BAIXAR ZIP ({sucesso_c} notas)",
                        data=zip_o.getvalue(),
                        file_name=f"TaxXML_Turbo.zip",
                        mime="application/zip"
                    )
        else:
            st.warning("Insira chaves válidas.")

st.markdown("<br><p style='text-align: center; color: #a1a1a1; font-size: 0.8rem;'>Tax XML Pro Mach 3 © 2026</p>", unsafe_allow_html=True)
