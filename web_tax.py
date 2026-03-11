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
# DESIGN PREMIUM (CSS AVANÇADO)
# ==========================================
st.set_page_config(page_title="Tax XML Pro | Inteligência Tributária", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    .main { background-color: #0d1117; font-family: 'Inter', sans-serif; }
    
    /* Sidebar Customizada */
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Cards Estilo SaaS */
    .st-emotion-cache-12w0qpk { background-color: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 2rem; }
    
    /* Títulos */
    h1 { color: #58a6ff; font-weight: 700; font-size: 2.5rem !important; margin-bottom: 0px !important; }
    h3 { color: #f0f6fc; font-size: 1.2rem !important; }
    
    /* Botão Principal */
    .stButton>button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        border: none;
        border-radius: 12px;
        color: white;
        height: 3.5rem;
        font-weight: 700;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(35, 134, 54, 0.4); }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        background: #21262d;
        color: #8b949e;
        border: 1px solid #30363d;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# BARRA LATERAL (AJUDA E CONTATO)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/5623/5623011.png", width=80)
    st.markdown("## Central de Ajuda")
    st.write("Dúvidas sobre o processamento ou pagamentos?")
    
    # Botão de WhatsApp
    st.markdown("""
        <a href="https://wa.me/5551995759692" target="_blank">
            <button style="width:100%; border-radius:10px; border:none; background-color:#25D366; color:white; padding:10px; font-weight:bold; cursor:pointer;">
                💬 Chamar no WhatsApp
            </button>
        </a>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 🔒 Segurança")
    st.caption("• Dados criptografados via SSL")
    st.caption("• Conexão Direta Sefaz via API")
    st.caption("• Pagamento Garantido Mercado Pago")

# ==========================================
# CONTEÚDO PRINCIPAL
# ==========================================
st.markdown("<span class='badge'>v2.4 - OPERAÇÃO TURBO ATIVADA</span>", unsafe_allow_html=True)
st.title("Tax XML Pro")
st.markdown("##### Transforme chaves de acesso em arquivos XML em segundos.")

st.write("") # Espaçador

col1, col2 = st.columns([1.4, 1], gap="large")

with col1:
    st.markdown("### 📥 1. Entrada de Dados")
    txt_input = st.text_area(
        "Cole aqui suas chaves de acesso (44 dígitos):", 
        height=300, 
        placeholder="31250917155730000164550010000846641770615626\n..."
    )
    st.caption("💡 Dica: Você pode copiar chaves direto do seu Excel ou PDF.")

with col2:
    st.markdown("### 🏷️ 2. Checkout")
    if txt_input:
        chaves = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves)
        valor = total * PRECO_POR_XML
        
        if total > 0:
            st.info(f"✨ **{total}** Notas detectadas")
            st.markdown(f"### Total: R$ {valor:.2f}")
            
            if st.button("GERAR PAGAMENTO PIX"):
                with st.spinner("Gerando QR Code seguro..."):
                    res = sdk.payment().create({
                        "transaction_amount": float(valor),
                        "description": f"Lote {total} XMLs",
                        "payment_method_id": "pix",
                        "payer": {"email": "contato@taxxml.com", "first_name": "Cliente"}
                    })["response"]
                    
                    st.session_state['qr'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['copy'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pid'] = res["id"]
                    st.session_state['lote'] = chaves
                    st.rerun()
        else:
            st.warning("Nenhuma chave válida detectada.")
    else:
        st.markdown("""
            <div style="background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px dashed #30363d; text-align: center;">
                <p style="color: #8b949e;">Aguardando inserção de chaves...</p>
            </div>
        """, unsafe_allow_html=True)

# Área de Checkout (Aparece após gerar o PIX)
if 'qr' in st.session_state:
    st.divider()
    st.markdown("### 🏁 3. Concluir Processamento")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.image(f"data:image/png;base64,{st.session_state['qr']}", width=250)
    
    with c2:
        st.write("Escaneie o QR Code ao lado ou use o código Copia e Cola:")
        st.code(st.session_state['copy'], language="text")
        
        if st.button("✅ JÁ PAGUEI! LIBERAR DOWNLOAD"):
            status = sdk.payment().get(st.session_state['pid'])["response"]["status"]
            if status == "approved":
                st.balloons()
                # (Aqui entra o motor de download que já funciona...)
                st.success("Download liberado!")
            else:
                st.error("Pagamento ainda não aprovado. Aguarde 5 segundos.")

# Rodapé
st.markdown("---")
st.markdown("<div style='text-align: center; color: #8b949e; font-size: 12px;'>Tax XML Pro © 2026 - Moraes Assessoria Internacional</div>", unsafe_allow_html=True)

