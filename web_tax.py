import streamlit as st
import requests
import re
import time
import zipfile
import io
import mercadopago
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# CONFIGURAÇÕES PRIVADAS (BACKEND)
# ==========================================
API_KEY_MEU_DANFE = "36da320b-1b2d-47fa-b626-cc90dea64471"
# SUBSTITUA ABAIXO PELA SUA CHAVE APP_USR REAL
MP_ACCESS_TOKEN = "APP_USR-1091359635861022-031115-4083f4ba9bf7da16cf148d67c053efdb-3243990562"
PRECO_POR_XML = 0.1

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# DESIGN E IDENTIDADE VISUAL (CSS)
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .block-container { padding-top: 2rem; max-width: 800px; }
    .card {
        background-color: #161b22;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    h1, h2, h3 { color: #58a6ff !important; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.5rem;
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
        color: white;
        font-weight: bold;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# MOTOR DE PROCESSAMENTO
# ==========================================
def processar_nota(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=10)
        time.sleep(2)
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=10)
        if r.status_code == 200 and "<nfeProc" in r.text:
            return True, chave, r.text.strip()
    except:
        pass
    return False, chave, None

# ==========================================
# INTERFACE
# ==========================================
st.title("⚡ Tax XML Pro")
st.markdown("Plataforma de Recuperação de XMLs")
st.divider()

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("<div class='card'><h3>1. Inserir Chaves</h3></div>", unsafe_allow_html=True)
    txt_input = st.text_area("Cole as chaves de 44 dígitos aqui:", height=250)

with col2:
    if txt_input:
        chaves = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves)
        valor = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"<div class='card'><h3>2. Resumo</h3><p>Notas: {total}<br><b>Total: R$ {valor:.2f}</b></p></div>", unsafe_allow_html=True)

            if st.button("Gerar Pagamento PIX"):
                with st.spinner("Criando ordem de pagamento..."):
                    payment_data = {
                        "transaction_amount": float(valor),
                        "description": f"Lote {total} XMLs",
                        "payment_method_id": "pix",
                        "payer": {
                            "email": "contato@taxxml.com",
                            "first_name": "Cliente",
                            "last_name": "TaxXML"
                        }
                    }
                    
                    resposta = sdk.payment().create(payment_data)
                    res = resposta["response"]

                    # DIAGNÓSTICO DE ERRO
                    if "point_of_interaction" in res:
                        st.session_state['pix_qr'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                        st.session_state['pix_copia'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                        st.session_state['pid'] = res["id"]
                        st.session_state['lista_chaves'] = chaves
                        st.rerun()
                    else:
                        st.error("🚨 Erro na API do Mercado Pago")
                        st.write("O banco retornou a seguinte mensagem:")
                        st.json(res) # Mostra o motivo real do erro
        else:
            st.warning("Aguardando chaves válidas...")

# ÁREA DE CHECKOUT
if 'pix_qr' in st.session_state:
    st.divider()
    c_pix1, c_pix2 = st.columns([1, 1.5])
    
    with c_pix1:
        st.image(f"data:image/png;base64,{st.session_state['pix_qr']}", width=250)
    
    with c_pix2:
        st.markdown("### 💳 Pagamento via PIX")
        st.code(st.session_state['pix_copia'], language="text")
        
        if st.button("🚀 Confirmar Pagamento e Baixar"):
            status_res = sdk.payment().get(st.session_state['pid'])
            status = status_res["response"]["status"]
            
            if status == "approved":
                st.balloons()
                st.success("Pagamento aprovado!")
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futuros = {executor.submit(processar_nota, session, c): c for c in st.session_state['lista_chaves']}
                            for f in as_completed(futuros):
                                ok, chave, xml = f.result()
                                if ok: zip_file.writestr(f"{chave}.xml", xml)
                
                st.download_button("⬇️ BAIXAR ARQUIVO .ZIP", zip_buffer.getvalue(), "TaxXML_Lote.zip", "application/zip")
            else:
                st.error(f"Status: {status}. Pague o PIX e clique novamente.")
