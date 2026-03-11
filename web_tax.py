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
# O Mercado Pago foi removido desta versão para facilitar seus testes de carga.

# ==========================================
# MOTOR DE DOWNLOAD (REGRAS DE SEGURANÇA API)
# ==========================================
def baixar_xml_seguro(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    
    try:
        # REGRA 1: Adiciona a nota na fila
        session.put(url_add, headers=headers, timeout=12)
        
        # REGRA 2: Tentativas com descanso (Segurança contra bloqueio de IP)
        for tentativa in range(3):
            time.sleep(3) # Espera 3 segundos para a Sefaz processar
            
            r = session.get(url_get, headers=headers, timeout=12)
            if r.status_code == 200:
                conteudo = r.text.strip()
                if not conteudo.startswith('{') and "<nfeProc" in conteudo:
                    xml_limpo = conteudo[conteudo.find("<"):]
                    return True, chave, xml_limpo.encode('utf-8')
            elif r.status_code == 404:
                return False, chave, "Não encontrada"
                
    except: pass
    return False, chave, "Falha"

# ==========================================
# DESIGN PREMIUM (MODO CLARO FIXO)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - MODO TESTE", page_icon="🧪", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label { color: #1c3d6a !important; }
    .header { background-color: white; padding: 30px; border-bottom: 4px solid #2da9e0; text-align: center; margin-bottom: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) { background-color: white !important; padding: 35px !important; border-radius: 20px !important; box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important; }
    .stButton>button { background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important; color: white !important; border-radius: 12px !important; height: 3.8rem !important; font-weight: 700 !important; }
    .whatsapp-btn { position: fixed; bottom: 25px; right: 25px; background-color: #25d366; color: white !important; border-radius: 50px; padding: 12px 25px; font-weight: bold; text-decoration: none; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<a href="https://wa.me/595984123456" class="whatsapp-btn">💬 Suporte Online</a>', unsafe_allow_html=True)

st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except: st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

# Interface
col_l, col_r = st.columns([1.3, 1], gap="large")

with col_l:
    st.markdown("### 📥 Entrada de Lote (Teste)")
    txt_input = st.text_area("Cole as chaves para teste de carga:", height=320, placeholder="Insira várias chaves aqui...")

with col_r:
    st.markdown("### 📊 Status do Processamento")
    if txt_input:
        chaves_t = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_t = len(chaves_t)
        
        if total_t > 0:
            st.info(f"🚀 **{total_t}** notas prontas para baixar.")
            
            if st.button("INICIAR DOWNLOAD AGORA"):
                st.write("---")
                prog_bar = st.progress(0)
                prog_txt = st.empty()
                
                zip_o = io.BytesIO()
                sucesso_c = 0
                
                with zipfile.ZipFile(zip_o, "a", zipfile.ZIP_DEFLATED) as zf:
                    with requests.Session() as session:
                        # Respeitando o limite de segurança de 3 threads
                        with ThreadPoolExecutor(max_workers=3) as executor:
                            jobs = {executor.submit(baixar_xml_seguro, session, c): c for c in chaves_t}
                            
                            concluidos = 0
                            for j in as_completed(jobs):
                                ok, ch, xml_d = j.result()
                                concluidos += 1
                                
                                prog_bar.progress(concluidos / total_t)
                                prog_txt.markdown(f"**Progresso:** {concluidos}/{total_t} notas processadas...")
                                
                                if ok:
                                    zf.writestr(f"{ch}.xml", xml_d)
                                    sucesso_c += 1
                
                if sucesso_c > 0:
                    st.balloons()
                    st.success(f"✅ Download finalizado: {sucesso_c} notas recuperadas.")
                    st.download_button(
                        label=f"⬇️ BAIXAR ARQUIVO .ZIP",
                        data=zip_o.getvalue(),
                        file_name=f"Teste_TaxXML.zip",
                        mime="application/zip"
                    )
                else:
                    st.error("Nenhuma nota foi recuperada. Verifique se as chaves são válidas e se há saldo na API.")
        else:
            st.warning("Aguardando chaves válidas.")
    else:
        st.info("Insira as chaves ao lado para testar o motor Mach 3.")

st.markdown("<br><p style='text-align: center; color: #a1a1a1;'>Tax XML Pro © 2026 - Modo Desenvolvedor Ativado</p>", unsafe_allow_html=True)
