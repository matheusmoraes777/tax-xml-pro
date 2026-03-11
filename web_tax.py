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
# MOTOR MACH 3 - LÓGICA ORIGINAL (PyQt6)
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

        # Lógica de Auto-Reparo idêntica ao seu código PyQt6
        if conteudo.startswith('{'):
            try:
                js = r.json()
                xml_limpo = js.get('data') or js.get('xml')
            except: pass
        elif conteudo.startswith('<'):
            xml_limpo = conteudo

        # Se funcionou de primeira, já retorna
        if xml_limpo and "<nfeProc" in xml_limpo:
            # Garante que o arquivo comece no caractere '<' (Remove BOM/Lixo)
            xml_final = xml_limpo[xml_limpo.find("<"):]
            return True, chave, xml_final.encode('utf-8')

        # TENTATIVA 2: Se não veio, manda Adicionar (PUT)
        session.put(url_add, headers=headers, timeout=12)
        time.sleep(4) # Espera padrão para Sefaz

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

    except:
        pass
    return False, chave, None

# ==========================================
# INTERFACE VISUAL (LIGHT MODE PREMIUM)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - Mach 3", page_icon="🏎️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label { color: #1c3d6a !important; }
    .header { background-color: white; padding: 30px; border-bottom: 4px solid #2da9e0; text-align: center; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) { background-color: white !important; padding: 35px !important; border-radius: 20px !important; box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important; }
    .stButton>button { background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important; color: white !important; border-radius: 12px !important; height: 3.8rem !important; font-weight: 700 !important; font-size: 18px !important; }
    .stProgress > div > div > div > div { background-color: #76bc43 !important; }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except: st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

# Layout
col_left, col_right = st.columns([1.3, 1], gap="large")

with col_left:
    st.markdown("### 📥 Entrada de Chaves")
    txt_input = st.text_area("Cole as chaves para teste de velocidade:", height=320, placeholder="44 dígitos por linha...")

with col_right:
    st.markdown("### 📊 Status Mach 3")
    if txt_input:
        chaves_lote = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_lote)
        
        if total_n > 0:
            st.success(f"🚀 Fila pronta: **{total_n}** notas fiscais.")
            
            if st.button("INICIAR DOWNLOAD TURBO"):
                st.write("---")
                p_bar = st.progress(0)
                p_txt = st.empty()
                
                zip_o = io.BytesIO()
                sucesso_c = 0
                
                with zipfile.ZipFile(zip_o, "a", zipfile.ZIP_DEFLATED) as zf:
                    with requests.Session() as session:
                        # 10 Workers para manter a velocidade que você comemorou!
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            jobs = {executor.submit(baixar_xml_original, session, c): c for c in chaves_lote}
                            
                            contagem = 0
                            for j in as_completed(jobs):
                                ok, ch, xml_data = j.result()
                                contagem += 1
                                p_bar.progress(contagem / total_n)
                                p_txt.markdown(f"**Progresso:** {contagem} de {total_n} notas...")
                                
                                if ok:
                                    zf.writestr(f"{ch}.xml", xml_data)
                                    sucesso_c += 1
                
                if sucesso_c > 0:
                    st.balloons()
                    st.success(f"✅ Motor Mach 3 finalizado: {sucesso_c} notas recuperadas.")
                    st.download_button(
                        label=f"⬇️ BAIXAR ARQUIVO .ZIP",
                        data=zip_o.getvalue(),
                        file_name=f"TaxXML_Turbo.zip",
                        mime="application/zip"
                    )
        else:
            st.warning("Insira chaves válidas.")
    else:
        st.info("Insira as chaves ao lado para iniciar.")

st.markdown("<br><p style='text-align: center; color: #a1a1a1; font-size: 0.8rem;'>Tax XML Pro © 2026 - Versão Turbo Consolidada</p>", unsafe_allow_html=True)
