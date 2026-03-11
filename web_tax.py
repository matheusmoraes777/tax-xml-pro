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
# MOTOR MACH 3 - VERSÃO "CIRURGIA DE CABEÇALHO"
# ==========================================
def baixar_xml_turbo(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"
    
    def limpar_xml(texto):
        """Reconstrói o XML para evitar erros de aspas e formatação"""
        if "<nfeProc" in texto:
            corpo = texto[texto.find("<nfeProc"):]
            # Injeta um cabeçalho padrão perfeito (Resolve o erro da Coluna 15)
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{corpo}'.encode('utf-8')
        return None

    try:
        # 1. TENTATIVA RÁPIDA (GET)
        r = session.get(url_get, headers=headers, timeout=8)
        if r.status_code == 200:
            xml_ok = limpar_xml(r.text)
            if xml_ok: return True, chave, xml_ok

        # 2. TENTATIVA COMPLETA (PUT + WAIT + GET)
        session.put(url_add, headers=headers, timeout=8)
        time.sleep(4) # Espera necessária para processamento Sefaz
        
        r = session.get(url_get, headers=headers, timeout=8)
        if r.status_code == 200:
            xml_ok = limpar_xml(r.text)
            if xml_ok: return True, chave, xml_ok
                
    except: pass
    return False, chave, None

# ==========================================
# DESIGN PREMIUM (MODO CLARO FORÇADO)
# ==========================================
st.set_page_config(page_title="Tax XML Pro - Mach 3", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    /* FORÇAR MODO CLARO */
    .stApp { background-color: #f7f9fc !important; color: #1c3d6a !important; font-family: 'Poppins', sans-serif; }
    h1, h2, h3, p, span, label, div { color: #1c3d6a !important; }

    .header {
        background-color: white;
        padding: 30px;
        border-bottom: 4px solid #2da9e0;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    /* Input Area */
    textarea { background-color: white !important; color: #1c3d6a !important; border: 1px solid #d1d9e6 !important; }

    /* Botão Mach 3 */
    .stButton>button {
        background: linear-gradient(135deg, #76bc43 0%, #5fa332 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 3.8rem !important;
        font-weight: 700 !important;
        font-size: 18px !important;
    }
    
    /* Barra de Progresso Verde */
    .stProgress > div > div > div > div { background-color: #76bc43 !important; }
    </style>
    """, unsafe_allow_html=True)

# WhatsApp Suporte
st.markdown('<a href="https://wa.me/595984123456" style="position:fixed; bottom:20px; right:20px; background:#25d366; color:white; padding:12px 20px; border-radius:50px; text-decoration:none; font-weight:bold; z-index:1000; box-shadow:0 4px 12px rgba(0,0,0,0.15);">💬 Suporte Online</a>', unsafe_allow_html=True)

# Cabeçalho
st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=250)
except: st.title("Tax XML Pro")
st.markdown('</div>', unsafe_allow_html=True)

# Layout
col_in, col_res = st.columns([1.3, 1], gap="large")

with col_in:
    st.markdown("### 📥 1. Entrada de Lote")
    txt_input = st.text_area("Cole as chaves aqui (uma por linha):", height=320, placeholder="Ex: 31250917155730000164550010000846641770615626")

with col_res:
    st.markdown("### 💳 2. Checkout")
    if txt_input:
        chaves_limpas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves_limpas)
        valor = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"""
                <div style="background-color: #f0f7ff; padding: 25px; border-radius: 15px; border-left: 6px solid #2da9e0;">
                    <p style="margin:0; font-size:14px;">Resumo do Lote:</p>
                    <h2 style="margin:0; color:#1c3d6a;">{total} XMLs</h2>
                    <h3 style="margin:0; color:#2da9e0;">R$ {valor:.2f}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("GERAR PAGAMENTO PIX"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor),
                    "description": f"Lote {total} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Matheus"}
                })["response"]
                
                st.session_state['q_code'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                st.session_state['p_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                st.session_state['p_id'] = res["id"]
                st.session_state['l_chaves'] = chaves_limpas
                st.rerun()
        else:
            st.warning("Aguardando chaves válidas...")

# Área de Processamento
if 'q_code' in st.session_state:
    st.divider()
    st.markdown("### 🚀 3. Processamento Mach 3")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.image(f"data:image/png;base64,{st.session_state['q_code']}", width=280)
    
    with c2:
        st.write("Pague o PIX e clique abaixo para iniciar o download turbo.")
        st.code(st.session_state['p_str'], language="text")
        
        if st.button("✅ VERIFICAR PAGAMENTO E BAIXAR"):
            status = sdk.payment().get(st.session_state['p_id'])["response"]["status"]
            if status == "approved":
                st.balloons()
                
                # BARRA DE PROGRESSO
                barra = st.progress(0)
                txt_status = st.empty()
                
                zip_buffer = io.BytesIO()
                sucessos = 0
                total_notas = len(st.session_state['l_chaves'])
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
                    with requests.Session() as session:
                        # 10 WORKERS PARA MÁXIMA VELOCIDADE
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            tarefas = {executor.submit(baixar_xml_turbo, session, c): c for c in st.session_state['l_chaves']}
                            
                            contagem = 0
                            for t in as_completed(tarefas):
                                ok, ch, xml_data = t.result()
                                contagem += 1
                                barra.progress(contagem / total_notas)
                                txt_status.markdown(f"**Progresso Mach 3:** {contagem} de {total_notas} notas processadas...")
                                
                                if ok:
                                    zf.writestr(f"{ch}.xml", xml_data)
                                    sucessos += 1
                
                if sucessos > 0:
                    st.success(f"Finalizado! {sucessos} notas recuperadas.")
                    st.download_button(f"⬇️ BAIXAR LOTE COMPLETO ({sucessos} XMLs)", zip_buffer.getvalue(), "TaxXML_Lote.zip", "application/zip")
            else:
                st.error("Pagamento pendente. Verifique seu banco.")

st.markdown("<br><p style='text-align: center; color: #a1a1a1; font-size: 0.8rem;'>Tax XML Pro © 2026 - Moraes Assessoria Internacional</p>", unsafe_allow_html=True)
