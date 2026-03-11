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
PRECO_POR_XML = 0.03

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# DESIGN PREMIUM
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .card { background-color: #161b22; padding: 20px; border-radius: 15px; border: 1px solid #30363d; margin-bottom: 15px; }
    h1, h3 { color: #58a6ff !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5rem; background: linear-gradient(90deg, #238636 0%, #2ea043 100%); color: white; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# MOTOR DE PROCESSAMENTO (ESCUDO DE VALIDAÇÃO)
# ==========================================
def processar_nota(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        # 1. Solicita a nota
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=15)
        
        # 2. Espera um pouco mais para a Sefaz (5 segundos)
        time.sleep(5) 
        
        # 3. Tenta baixar
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            conteudo = r.text.strip()
            
            # SÓ CONSIDERA SUCESSO SE TIVER A TAG DA NOTA FISCAL
            if "<nfeProc" in conteudo:
                return True, chave, conteudo
            else:
                return False, chave, f"Retorno Inválido: {conteudo[:50]}" # Pega o erro que veio
        
        return False, chave, f"Erro HTTP {r.status_code}"
    except Exception as e:
        return False, chave, str(e)

# ==========================================
# INTERFACE
# ==========================================
st.title("⚡ Tax XML Pro")
st.divider()

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("<div class='card'><h3>1. Inserir Chaves</h3></div>", unsafe_allow_html=True)
    txt_input = st.text_area("Cole as chaves aqui:", height=250)

with col2:
    if txt_input:
        chaves = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves)
        valor = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"<div class='card'><h3>2. Resumo</h3><p>Notas: {total}<br><b>Total: R$ {valor:.2f}</b></p></div>", unsafe_allow_html=True)

            if st.button("💳 Gerar PIX"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor),
                    "description": f"Lote {total} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                })["response"]

                if "point_of_interaction" in res:
                    st.session_state['pix_qr'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_copia'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pid'] = res["id"]
                    st.session_state['chaves_ok'] = chaves
                    st.rerun()

# CHECKOUT
if 'pix_qr' in st.session_state:
    st.divider()
    c1, c2 = st.columns([1, 1.5])
    with c1: st.image(f"data:image/png;base64,{st.session_state['pix_qr']}", width=250)
    with c2:
        st.write("### Pague o PIX e clique abaixo:")
        if st.button("🚀 Verificar e Baixar"):
            status = sdk.payment().get(st.session_state['pid'])["response"]["status"]
            
            if status == "approved":
                st.success("Pagamento aprovado! Processando...")
                zip_buffer = io.BytesIO()
                sucessos = 0
                erros = []

                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futuros = {executor.submit(processar_nota, session, c): c for c in st.session_state['chaves_ok']}
                            for f in as_completed(futuros):
                                ok, chave, result = f.result()
                                if ok:
                                    zip_file.writestr(f"{chave}.xml", result)
                                    sucessos += 1
                                else:
                                    erros.append(f"{chave}: {result}")

                if sucessos > 0:
                    st.balloons()
                    st.download_button(f"⬇️ BAIXAR {sucessos} NOTAS", zip_buffer.getvalue(), "notas.zip", "application/zip")
                
                if erros:
                    st.error("Algumas notas falharam:")
                    for e in erros: st.write(e)
            else:
                st.warning("Pagamento pendente.")
