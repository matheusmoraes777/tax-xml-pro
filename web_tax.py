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
MP_ACCESS_TOKEN = "APP_USR-1091359635861022-031115-4083f4ba9bf7da16cf148d67c053efdb-3243990562"
PRECO_POR_XML = 0.010

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD (VERSÃO APROVADA "EURECA")
# ==========================================
def baixar_xml(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        # Avisa a Sefaz (PUT)
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=12)
        time.sleep(5) # Tempo de respiro necessário para a Sefaz processar

        # Tenta o download (GET)
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=12)
        if r.status_code == 200:
            conteudo = r.text.strip()
            xml_limpo = None
            
            # Lógica de auto-reparo e validação
            if conteudo.startswith('{'):
                try: xml_limpo = r.json().get('data') or r.json().get('xml')
                except: pass
            elif conteudo.startswith('<'):
                xml_limpo = conteudo
                
            if xml_limpo and "<nfeProc" in xml_limpo:
                # Remove lixo antes do início do XML se houver
                xml_limpo = xml_limpo[xml_limpo.find("<"):]
                return True, chave, xml_limpo
    except:
        pass
    return False, chave, "Erro"

# ==========================================
# DESIGN E IDENTIDADE VISUAL
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5rem; background: #238636; color: white; font-weight: bold; border: none; }
    h1, h3 { color: #58a6ff !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.title("⚡ Tax XML Pro")
st.markdown("Recuperação automatizada de notas fiscais diretamente da Sefaz.")
st.divider()

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("<div class='card'><h3>1. Inserir Chaves</h3></div>", unsafe_allow_html=True)
    txt_input = st.text_area("Cole as chaves de 44 dígitos aqui (uma por linha):", height=280)

with col2:
    if txt_input:
        chaves_validadas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves_validadas)
        valor_total = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"""
            <div class='card'>
                <h3>2. Resumo do Lote</h3>
                <p>Notas identificadas: <b>{total}</b></p>
                <p style='font-size: 20px;'>Total: <b style='color: #2ea043;'>R$ {valor_total:.2f}</b></p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("💳 Gerar Pagamento PIX"):
                with st.spinner("Conectando ao Mercado Pago..."):
                    payment_data = {
                        "transaction_amount": float(valor_total),
                        "description": f"Lote {total} XMLs",
                        "payment_method_id": "pix",
                        "payer": {"email": "cliente@taxxml.com", "first_name": "Matheus"}
                    }
                    res = sdk.payment().create(payment_data)["response"]

                    if "point_of_interaction" in res:
                        st.session_state['qr_code'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                        st.session_state['pix_copy'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                        st.session_state['pay_id'] = res["id"]
                        st.session_state['lote_chaves'] = chaves_validadas
                        st.rerun()
                    else:
                        st.error("Erro ao gerar PIX. Verifique sua conta Mercado Pago.")
        else:
            st.warning("Aguardando chaves válidas...")

# ==========================================
# CHECKOUT E PROCESSAMENTO
# ==========================================
if 'qr_code' in st.session_state:
    st.divider()
    c_pay1, c_pay2 = st.columns([1, 1.5])
    
    with c_pay1:
        st.image(f"data:image/png;base64,{st.session_state['qr_code']}", caption="Escaneie o QR Code", width=250)
    
    with c_pay2:
        st.markdown("### 🏦 Pagamento via PIX")
        st.write("Após realizar o pagamento, clique no botão abaixo para liberar o download.")
        st.code(st.session_state['pix_copy'], language="text")
        
        if st.button("🚀 Confirmar Pagamento e Baixar"):
            status_res = sdk.payment().get(st.session_state['pay_id'])
            status = status_res["response"].get("status")
            
            if status == "approved":
                st.balloons()
                st.success("Pagamento confirmado! Iniciando processamento Turbo...")
                
                # Interface de progresso
                barra = st.progress(0)
                status_txt = st.empty()
                
                zip_buffer = io.BytesIO()
                sucessos = 0
                total_lote = len(st.session_state['lote_chaves'])
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            tarefas = {executor.submit(baixar_xml, session, c): c for c in st.session_state['lote_chaves']}
                            
                            concluidos = 0
                            for t in as_completed(tarefas):
                                ok, chave, xml = t.result()
                                if ok:
                                    zip_file.writestr(f"{chave}.xml", xml)
                                    sucessos += 1
                                
                                concluidos += 1
                                barra.progress(concluidos / total_lote)
                                status_txt.markdown(f"**Progresso:** {int((concluidos/total_lote)*100)}% | ✅ **Sucessos:** {sucessos}")

                if sucessos > 0:
                    st.divider()
                    st.download_button(
                        label=f"⬇️ BAIXAR {sucessos} XMLs AGORA",
                        data=zip_buffer.getvalue(),
                        file_name=f"TaxXML_Lote_{int(time.time())}.zip",
                        mime="application/zip"
                    )
                else:
                    st.error("As notas ainda não foram liberadas pela Sefaz. Tente novamente em instantes.")
            else:
                st.warning(f"Pagamento ainda {status}. Se já pagou, aguarde 10 segundos e tente de novo.")
