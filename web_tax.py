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
# MOTOR DE DOWNLOAD (VERSÃO ULTRA-LIMPEZA)
# ==========================================
def processar_nota(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        # 1. Solicita a nota
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=15)
        
        # 2. Espera o processamento da Sefaz
        time.sleep(5) 
        
        # 3. Baixa o conteúdo bruto
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            # Remove espaços em branco do início e fim
            texto_bruto = r.text.strip()
            
            if "<nfeProc" in texto_bruto:
                # Encontra o início real da nota fiscal
                pos_inicio = texto_bruto.find("<nfeProc")
                corpo_nota = texto_bruto[pos_inicio:]
                
                # RECONSTRUÇÃO USANDO ASPAS SIMPLES NO CABEÇALHO (Mais seguro contra erros de parser)
                # O \n garante que a nota comece na linha 2, bem limpa.
                xml_final = "<?xml version='1.0' encoding='UTF-8'?>\n" + corpo_nota
                
                # Retorna em bytes UTF-8 explícito
                return True, chave, xml_final.encode('utf-8')
                    
        return False, chave, "Conteúdo da API não é um XML válido"
    except Exception as e:
        return False, chave, f"Erro: {str(e)}"

# ==========================================
# INTERFACE VISUAL
# ==========================================
st.set_page_config(page_title="Tax XML Pro - Debug", page_icon="🧪")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: white; }
    .stButton>button { background: #58a6ff; color: white; font-weight: bold; border: none; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧪 Tax XML - Teste de Formatação")
st.info("Este modo ignora o PIX para testarmos a abertura do arquivo no navegador.")

txt_input = st.text_area("Cole as chaves aqui:", height=200)

if txt_input:
    chaves = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
    
    if chaves:
        st.write(f"✅ {len(chaves)} notas prontas para teste.")
        
        if st.button("🚀 BAIXAR E TESTAR FORMATO"):
            zip_buffer = io.BytesIO()
            sucessos = 0
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                with requests.Session() as session:
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futuros = {executor.submit(processar_nota, session, c): c for c in chaves}
                        for f in as_completed(futuros):
                            ok, chave, xml_bytes = f.result()
                            if ok:
                                zip_file.writestr(f"{chave}.xml", xml_bytes)
                                sucessos += 1
            
            if sucessos > 0:
                st.success(f"Gerado! Teste abrir o arquivo abaixo no Chrome.")
                st.download_button(
                    label="⬇️ BAIXAR XML AGORA",
                    data=zip_buffer.getvalue(),
                    file_name="DEBUG_TAX.zip",
                    mime="application/zip"
                )
            else:
                st.error("Nenhuma nota foi processada corretamente. Verifique o saldo.")
