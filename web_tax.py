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
# O Mercado Pago está desativado neste código para facilitar seus testes

# ==========================================
# MOTOR DE DOWNLOAD (VERSÃO TESTE/FREE)
# ==========================================
def processar_nota(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        # 1. Avisa a Sefaz
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=15)
        
        # 2. Tempo para processamento (Sefaz/MeuDanfe)
        time.sleep(5) 
        
        # 3. Baixa o XML
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            texto_bruto = r.text.strip()
            
            # --- LIMPEZA E RECONSTRUÇÃO DO XML ---
            if "<nfeProc" in texto_bruto:
                # Localiza o início real da nota e ignora lixo anterior
                inicio_nota = texto_bruto.find("<nfeProc")
                corpo_nota = texto_bruto[inicio_nota:]
                
                # Gera um cabeçalho novo e limpo para evitar erros de aspas/formato
                cabecalho_novo = '<?xml version="1.0" encoding="UTF-8"?>\n'
                xml_final = cabecalho_novo + corpo_nota
                
                return True, chave, xml_final.encode('utf-8')
                    
        return False, chave, "XML não encontrado ou saldo zerado"
    except Exception as e:
        return False, chave, f"Erro: {str(e)}"

# ==========================================
# INTERFACE VISUAL
# ==========================================
st.set_page_config(page_title="Tax XML Pro - MODO TESTE", page_icon="🧪", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5rem; background: #58a6ff; color: white; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧪 Tax XML Pro - Modo de Teste")
st.warning("⚠️ O sistema de pagamentos está desativado para testes do motor de download.")

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("<div class='card'><h3>1. Chaves de Acesso</h3></div>", unsafe_allow_html=True)
    txt_input = st.text_area("Cole as chaves aqui (uma por linha):", height=250)

with col2:
    if txt_input:
        chaves_limpas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves_limpas)
        
        if total > 0:
            st.markdown(f"<div class='card'><h3>2. Status do Motor</h3><p>Notas detectadas: <b>{total}</b></p><p style='color: #58a6ff;'>Pronto para baixar sem cobrança.</p></div>", unsafe_allow_html=True)
            
            if st.button("🚀 INICIAR DOWNLOAD DE TESTE"):
                st.info("Processando... Isso pode levar alguns segundos.")
                
                zip_buffer = io.BytesIO()
                cont_sucesso = 0
                erros = []
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        # Processamento paralelo para ser mais rápido
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            tarefas = {executor.submit(processar_nota, session, c): c for c in chaves_limpas}
                            for t in as_completed(tarefas):
                                ok, chave, xml_bytes = t.result()
                                if ok:
                                    zip_file.writestr(f"{chave}.xml", xml_bytes)
                                    cont_sucesso += 1
                                else:
                                    erros.append(f"Nota {chave}: {xml_bytes}")
                
                if cont_sucesso > 0:
                    st.balloons()
                    st.success(f"Sucesso! {cont_sucesso} notas prontas.")
                    st.download_button(
                        label=f"⬇️ BAIXAR {cont_sucesso} XMLs AGORA",
                        data=zip_buffer.getvalue(),
                        file_name="TESTE_TaxXML.zip",
                        mime="application/zip"
                    )
                
                if erros:
                    st.error("Algumas notas falharam:")
                    for e in erros:
                        st.write(e)
        else:
            st.warning("Insira chaves válidas para testar.")
