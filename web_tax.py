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
API_KEY_MEU_DANFE = "36da320b-1b2d-47fa-b626-cc90dea64471" # SUA CHAVE PRIVADA
MP_ACCESS_TOKEN = "APP_USR-1091359635861022-031115-4083f4ba9bf7da16cf148d67c053efdb-3243990562"
PRECO_POR_XML = 0.15  # Você pode ajustar seu lucro aqui

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# DESIGN E IDENTIDADE VISUAL (CSS)
# ==========================================
st.set_page_config(page_title="Tax XML | Processamento Inteligente", page_icon="🚀", layout="wide")

st.markdown(f"""
    <style>
    /* Fundo e Geral */
    .main {{ background-color: #0b0e14; color: #ffffff; }}
    
    /* Container Principal */
    .block-container {{ padding-top: 2rem; max-width: 800px; }}

    /* Estilo dos Cards */
    .card {{
        background-color: #161b22;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}

    /* Títulos */
    h1, h2, h3 {{ color: #58a6ff !important; font-family: 'Inter', sans-serif; }}
    
    /* Botão Customizado */
    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        height: 3.5rem;
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
        color: white;
        font-weight: bold;
        font-size: 18px;
        border: none;
        transition: 0.3s;
    }}
    .stButton>button:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(46, 160, 67, 0.4); }}

    /* Inputs */
    textarea {{ background-color: #0d1117 !important; border-radius: 10px !important; border: 1px solid #30363d !important; color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# MOTOR DE PROCESSAMENTO
# ==========================================
def processar_nota(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    # PUT para adicionar/solicitar
    session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers)
    time.sleep(2)
    # GET para baixar
    r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers)
    if r.status_code == 200 and "<nfeProc" in r.text:
        return True, chave, r.text.strip()
    return False, chave, None

# ==========================================
# INTERFACE DA LANDING PAGE
# ==========================================

# Hero Section
st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
st.title("⚡ Tax XML Pro")
st.markdown("#### A forma mais rápida e barata de recuperar seus arquivos XML.")
st.markdown("---")
st.markdown("</div>", unsafe_allow_html=True)

# Colunas de Conteúdo
col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("""
    <div class='card'>
        <h3>1. Insira as Chaves</h3>
        <p style='color: #8b949e;'>Cole as chaves de acesso (44 dígitos) abaixo. Nosso sistema identifica e limpa automaticamente o texto.</p>
    </div>
    """, unsafe_allow_html=True)
    
    txt_input = st.text_area("", height=250, placeholder="Cole aqui suas chaves de acesso...")

with col2:
    if txt_input:
        chaves = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves)
        valor = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"""
            <div class='card'>
                <h3>2. Resumo do Pedido</h3>
                <p style='font-size: 18px;'>Notas detectadas: <b style='color: #58a6ff;'>{total}</b></p>
                <p style='font-size: 24px;'>Total: <b style='color: #2ea043;'>R$ {valor:.2f}</b></p>
                <small style='color: #8b949e;'>Custo por nota: R$ {PRECO_POR_XML:.2f}</small>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Gerar Pagamento PIX"):
                with st.spinner("Gerando QR Code..."):
                    payment_data = {
                        "transaction_amount": float(valor),
                        "description": f"Lote {total} XMLs",
                        "payment_method_id": "pix",
                        "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                    }
                    res = sdk.payment().create(payment_data)["response"]
                    st.session_state['pix_qr'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_copia'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pid'] = res["id"]
                    st.session_state['lista_chaves'] = chaves

        else:
            st.warning("Nenhuma chave válida de 44 dígitos detectada.")
    else:
        st.info("Aguardando inserção das chaves...")

# Área de Checkout (Aparece após gerar o PIX)
if 'pix_qr' in st.session_state:
    st.markdown("---")
    c_pix1, c_pix2 = st.columns([1, 1.5])
    
    with c_pix1:
        st.image(f"data:image/png;base64,{st.session_state['pix_qr']}", width=250)
    
    with c_pix2:
        st.markdown("### 💳 Pagamento via PIX")
        st.write("Aponte a câmera do seu celular ou utilize o código Copia e Cola abaixo.")
        st.code(st.session_state['pix_copia'], language="text")
        
        if st.button("🚀 Confirmar Pagamento e Baixar"):
            status = sdk.payment().get(st.session_state['pid'])["response"]["status"]
            
            # Liberação Automática
            if status == "approved" or MP_ACCESS_TOKEN.startswith("TEST-"):
                st.balloons()
                st.success("Pagamento aprovado! Preparando seu lote...")
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futuros = {executor.submit(processar_nota, session, c): c for c in st.session_state['lista_chaves']}
                            for f in as_completed(futuros):
                                ok, chave, xml = f.result()
                                if ok: zip_file.writestr(f"{chave}.xml", xml)
                
                st.download_button(
                    label="⬇️ BAIXAR ARQUIVO .ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"TaxXML_{int(time.time())}.zip",
                    mime="application/zip"
                )
            else:
                st.error("Pagamento ainda não identificado. Se você já pagou, aguarde 10 segundos e clique novamente.")

# Footer

st.markdown("<br><br><div style='text-align: center; color: #8b949e;'>© 2026 Tax XML Pro - Soluções em Inteligência Tributária</div>", unsafe_allow_html=True)
