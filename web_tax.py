import streamlit as st
import requests
import re
import time
import zipfile
import io
import mercadopago
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# CONFIGURAÇÕES DA EMPRESA E APIS
# ==========================================
API_KEY_MEU_DANFE = "36da320b-1b2d-47fa-b626-cc90dea64471"
MP_ACCESS_TOKEN = "APP_USR-1091359635861022-031115-4083f4ba9bf7da16cf148d67c053efdb-3243990562"
PRECO_POR_XML = 0.15 
MEU_SITE_URL = "https://taxxml.streamlit.app"

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD (BLINDADO)
# ==========================================
def baixar_xml_original(session, chave):
    headers = { "Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json" }
    url_get = f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}"
    url_add = f"https://api.meudanfe.com.br/v2/fd/add/{chave}"

    try:
        r = session.get(url_get, headers=headers, timeout=12)
        conteudo = r.text.strip()
        xml_limpo = None

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

        session.put(url_add, headers=headers, timeout=12)
        time.sleep(5) 

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
    except: pass
    return False, chave, None

# ==========================================
# DESIGN ULTRA MODERNO (ESTILO BASE44/TAILWIND)
# ==========================================
st.set_page_config(page_title="Tax XML - Recuperação de Notas", page_icon="🧾", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Fundo e Fonte Modernos */
    .stApp { background-color: #f8fafc !important; font-family: 'Inter', sans-serif !important; color: #0f172a !important; }
    h1, h2, h3, p, span, label, div { color: #0f172a !important; font-family: 'Inter', sans-serif !important; }

    /* Cabeçalho Clean */
    .header {
        background-color: white;
        padding: 20px 40px;
        border-bottom: 1px solid #e2e8f0;
        text-align: center;
        margin-bottom: 40px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    /* Cards (Painéis) Estilo React */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) {
        background-color: white !important;
        padding: 30px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* Caixa de Texto Clean */
    textarea { 
        background-color: #f8fafc !important; 
        color: #0f172a !important; 
        border: 1px solid #cbd5e1 !important; 
        border-radius: 8px !important;
        padding: 15px !important;
    }
    textarea:focus { border: 2px solid #3b82f6 !important; outline: none !important; }

    /* Estilo dos Botões Shadcn/Tailwind */
    .stButton>button { 
        width: 100%; 
        border-radius: 8px !important; 
        height: 3rem !important; 
        font-weight: 600 !important; 
        font-size: 15px !important; 
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    }
    
    /* Botão PIX (Verde Sofisticado) */
    div.stButton > button:first-child { background-color: #10b981 !important; color: white !important; border: none !important; }
    div.stButton > button:first-child:hover { background-color: #059669 !important; }
    
    /* Botão Cartão (Azul Moderno) */
    div.stButton > button[key="btn_card"] { background-color: #2563eb !important; color: white !important; border: none !important; }
    div.stButton > button[key="btn_card"]:hover { background-color: #1d4ed8 !important; }

    /* Barra de Progresso Suave */
    .stProgress > div > div > div > div { background-color: #10b981 !important; border-radius: 10px !important; }
    
    /* Botão Suporte Flutuante Moderno */
    .whatsapp-btn {
        position: fixed; bottom: 30px; right: 30px;
        background-color: #25d366; color: white !important;
        border-radius: 50px; padding: 12px 24px;
        font-weight: 600; text-decoration: none;
        box-shadow: 0 10px 15px -3px rgba(37, 211, 102, 0.3);
        z-index: 1000; transition: transform 0.2s;
    }
    .whatsapp-btn:hover { transform: scale(1.05); }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<a href="https://wa.me/595984123456" class="whatsapp-btn">💬 Falar com Suporte</a>', unsafe_allow_html=True)

# Header com Logo Centralizada
st.markdown('<div class="header">', unsafe_allow_html=True)
try: st.image("WhatsApp Image 2026-03-11 at 5.30.06 PM.jpeg", width=200)
except: st.title("Tax XML")
st.markdown('</div>', unsafe_allow_html=True)

col_in, col_check = st.columns([1.2, 1], gap="large")

with col_in:
    st.markdown("<h3 style='margin-bottom: 20px;'>📥 Inserir Chaves de Acesso</h3>", unsafe_allow_html=True)
    txt_input = st.text_area("", height=280, placeholder="Cole as chaves de 44 dígitos aqui (uma por linha)...")
    st.caption("🔒 Conexão criptografada de ponta a ponta.")

with col_check:
    st.markdown("<h3 style='margin-bottom: 20px;'>💳 Resumo do Pedido</h3>", unsafe_allow_html=True)
    if txt_input:
        chaves_validas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total_n = len(chaves_validas)
        valor_total = total_n * PRECO_POR_XML
        
        if total_n > 0:
            st.markdown(f"""
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="color: #64748b; font-weight: 500;">Documentos XML</span>
                        <span style="font-weight: 600;">{total_n} unid.</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid #e2e8f0;">
                        <span style="font-size: 18px; font-weight: 600;">Total a pagar</span>
                        <span style="font-size: 24px; font-weight: 700; color: #10b981;">R$ {valor_total:.2f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # OPÇÃO PIX
            if st.button("❖ Pagar com PIX"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor_total),
                    "description": f"Recuperação de {total_n} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                })["response"]
                
                if "point_of_interaction" in res:
                    st.session_state['qr_b64'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_str'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pay_id'] = res["id"]
                    st.session_state['lista_chaves'] = chaves_validas
                    if 'checkout_url' in st.session_state: del st.session_state['checkout_url']
                    st.rerun()

            st.markdown("<div style='text-align: center; margin: 10px 0; color: #94a3b8; font-size: 14px;'>ou</div>", unsafe_allow_html=True)

            # OPÇÃO CARTÃO
            if st.button("💳 Pagar com Cartão", key="btn_card"):
                with st.spinner("Gerando ambiente seguro..."):
                    pref_data = {
                        "items": [{"title": f"Lote {total_n} XMLs", "quantity": 1, "unit_price": float(valor_total), "currency_id": "BRL"}],
                        "payment_methods": {"installments": 1},
                        "back_urls": {"success": MEU_SITE_URL, "failure": MEU_SITE_URL, "pending": MEU_SITE_URL},
                        "auto_return": "approved",
                    }
                    result = sdk.preference().create(pref_data)
                    if "init_point" in result["response"]:
                        st.session_state['checkout_url'] = result["response"]["init_point"]
                        st.session_state['lista_chaves'] = chaves_validas
                        st.session_state['pay_id'] = "CHECKOUT_PRO"
                        if 'qr_b64' in st.session_state: del st.session_state['qr_b64']
                        st.rerun()
                    else:
                        st.error("Erro ao conectar com Mercado Pago.")
        else:
            st.warning("Nenhuma chave válida de 44 dígitos detectada.")

# --- TELAS DE PAGAMENTO ---
if 'qr_b64' in st.session_state:
    st.markdown("---")
    st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>Escaneie o QR Code</h3>", unsafe_allow_html=True)
    c_qr, c_status = st.columns([1, 1.5], gap="large")
    with c_qr: 
        st.image(f"data:image/png;base64,{st.session_state['qr_b64']}", use_column_width=True)
    with c_status:
        st.code(st.session_state['pix_str'], language="text")
        st.write("Após realizar o pagamento, clique no botão abaixo para verificar.")
        if st.button("Verificar Pagamento PIX"):
            p_status = sdk.payment().get(st.session_state['pay_id'])["response"]["status"]
            if p_status == "approved": st.session_state['pago'] = True
            else: st.error("Pagamento não identificado. Tente novamente em alguns segundos.")

if 'checkout_url' in st.session_state:
    st.markdown("---")
    st.markdown(f"""
        <div style="text-align: center; padding: 40px; background-color: white; border-radius: 16px; border: 1px solid #e2e8f0; max-width: 600px; margin: 0 auto;">
            <h3 style="margin-bottom: 20px;">Pagamento Seguro</h3>
            <p style="color: #64748b; margin-bottom: 30px;">Você será redirecionado para o ambiente do Mercado Pago para inserir os dados do cartão.</p>
            <a href="{st.session_state['checkout_url']}" target="_blank" style="text-decoration: none;">
                <button style="background-color: #2563eb; color: white; border: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; cursor: pointer; width: 100%; transition: background-color 0.2s;">
                    Abrir Checkout Mercado Pago
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
    st.write("")
    if st.button("✅ Já paguei, liberar download"):
        st.session_state['pago'] = True

# --- MOTOR DE PROCESSAMENTO ---
if st.session_state.get('pago'):
    st.markdown("---")
    st.markdown("<h3>🚀 Processando Lote</h3>", unsafe_allow_html=True)
    prog_bar = st.progress(0)
    status_txt = st.empty()
    zip_output = io.BytesIO()
    sucesso_count = 0
    total_lote = len(st.session_state['lista_chaves'])
    
    with zipfile.ZipFile(zip_output, "a", zipfile.ZIP_DEFLATED) as zf:
        with requests.Session() as session:
            with ThreadPoolExecutor(max_workers=10) as executor:
                jobs = {executor.submit(baixar_xml_original, session, c): c for c in st.session_state['lista_chaves']}
                concluidos = 0
                for j in as_completed(jobs):
                    ok, ch, xml_data = j.result()
                    concluidos += 1
                    prog_bar.progress(concluidos / total_lote)
                    status_txt.markdown(f"<p style='color: #64748b;'>Baixando: {concluidos} de {total_lote} documentos...</p>", unsafe_allow_html=True)
                    if ok:
                        zf.writestr(f"{ch}.xml", xml_data)
                        sucesso_count += 1
    
    if sucesso_count > 0:
        st.balloons()
        st.success(f"Sucesso! {sucesso_count} notas fiscais recuperadas.")
        st.download_button(f"⬇️ BAIXAR ARQUIVOS (.ZIP)", zip_output.getvalue(), "TaxXML_Lote.zip", "application/zip")
        st.session_state['pago'] = False
