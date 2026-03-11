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
# MOTOR DE DOWNLOAD (LÓGICA ORIGINAL QUE FUNCIONA)
# ==========================================
def baixar_xml(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    url = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    
    # O código original solicita e tenta o download
    try:
        # Primeiro avisa a Sefaz (PUT)
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=12)
        time.sleep(4) # Tempo de respiro para a Sefaz

        r = session.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            conteudo = r.text.strip()
            xml_limpo = None
            
            # Lógica de auto-reparo do seu código original
            if conteudo.startswith('{'):
                try: xml_limpo = r.json().get('data') or r.json().get('xml')
                except: pass
            elif conteudo.startswith('<'):
                xml_limpo = conteudo
                
            if xml_limpo and "<nfeProc" in xml_limpo:
                return True, chave, xml_limpo
    except:
        pass
    return False, chave, "Erro no processamento"

# ==========================================
# INTERFACE VISUAL
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .card { background-color: #161b22; padding: 25px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 20px; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5rem; background: #238636; color: white; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Tax XML Pro")
st.divider()

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("<div class='card'><h3>1. Chaves de Acesso</h3></div>", unsafe_allow_html=True)
    txt_input = st.text_area("Cole aqui as chaves (44 dígitos):", height=250)

with col2:
    if txt_input:
        chaves_limpas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves_limpas)
        valor_total = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"<div class='card'><h3>2. Resumo</h3><p>Notas detectadas: {total}<br>Total: <b>R$ {valor_total:.2f}</b></p></div>", unsafe_allow_html=True)
            
            if st.button("💳 Gerar PIX"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor_total),
                    "description": f"Lote {total} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Matheus"}
                })["response"]
                
                if "point_of_interaction" in res:
                    st.session_state['qr'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['copy'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pid'] = res["id"]
                    st.session_state['lote'] = chaves_limpas
                    st.rerun()

if 'qr' in st.session_state:
    st.divider()
    c1, c2 = st.columns([1, 1.5])
    with c1: st.image(f"data:image/png;base64,{st.session_state['qr']}", width=250)
    with c2:
        st.write("### Pagamento via PIX")
        st.code(st.session_state['copy'], language="text")
        if st.button("🚀 Confirmar e Baixar Lote"):
            status = sdk.payment().get(st.session_state['pid'])["response"]["status"]
            
            if status == "approved":
                st.success("Pagamento aprovado! Iniciando download...")
                zip_buffer = io.BytesIO()
                sucessos = 0
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            tarefas = {executor.submit(baixar_xml, session, c): c for c in st.session_state['lote']}
                            for t in as_completed(tarefas):
                                ok, chave, xml = t.result()
                                if ok:
                                    zip_file.writestr(f"{chave}.xml", xml)
                                    sucessos += 1
                
                if sucessos > 0:
                    st.balloons()
                    st.download_button(f"⬇️ BAIXAR {sucessos} XMLs", zip_buffer.getvalue(), "TaxXML_Lote.zip", "application/zip")
            else:
                st.warning("Aguardando confirmação do pagamento...")
