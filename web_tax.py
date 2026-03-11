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
PRECO_POR_XML = 0.01

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# MOTOR DE DOWNLOAD COM LIMPEZA DE FORMATO
# ==========================================
def processar_nota(session, chave):
    headers = {"Api-Key": API_KEY_MEU_DANFE, "Content-Type": "application/json"}
    try:
        # 1. Avisa a Sefaz
        session.put(f"https://api.meudanfe.com.br/v2/fd/add/{chave}", headers=headers, timeout=15)
        
        # 2. Tempo de respiro para processamento
        time.sleep(5) 
        
        # 3. Baixa o conteúdo
        r = session.get(f"https://api.meudanfe.com.br/v2/fd/get/xml/{chave}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            texto_bruto = r.text.strip()
            
            # --- LIMPEZA DE FORMATAÇÃO (O SEGREDO) ---
            # Remove qualquer caractere antes do primeiro '<' (caracteres invisíveis/lixo)
            if "<" in texto_bruto:
                indice_inicio = texto_bruto.find("<")
                xml_limpo = texto_bruto[indice_inicio:]
                
                # Validação final se é uma nota
                if "<nfeProc" in xml_limpo:
                    # Retorna em bytes UTF-8 puro para o ZIP não corromper
                    return True, chave, xml_limpo.encode('utf-8')
                    
        return False, chave, "Formato Inválido ou Sem Crédito"
    except Exception as e:
        return False, chave, str(e)

# ==========================================
# INTERFACE VISUAL
# ==========================================
st.set_page_config(page_title="Tax XML Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    .card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5rem; background: #238636; color: white; font-weight: bold; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Tax XML Pro")
st.markdown("Recuperação inteligente de arquivos XML diretamente da Sefaz.")

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("<div class='card'><h3>1. Chaves de Acesso</h3></div>", unsafe_allow_html=True)
    txt_input = st.text_area("Cole as chaves aqui (uma por linha):", height=250)

with col2:
    if txt_input:
        chaves_limpas = [re.sub(r'[^0-9]', '', l) for l in txt_input.split('\n') if len(re.sub(r'[^0-9]', '', l)) == 44]
        total = len(chaves_limpas)
        valor_total = total * PRECO_POR_XML
        
        if total > 0:
            st.markdown(f"<div class='card'><h3>2. Checkout</h3><p>Notas: {total}<br>Valor Total: <b>R$ {valor_total:.2f}</b></p></div>", unsafe_allow_html=True)
            
            if st.button("💳 Gerar PIX"):
                res = sdk.payment().create({
                    "transaction_amount": float(valor_total),
                    "description": f"Recuperação de {total} XMLs",
                    "payment_method_id": "pix",
                    "payer": {"email": "contato@taxxml.com", "first_name": "Matheus"}
                })["response"]
                
                if "point_of_interaction" in res:
                    st.session_state['qr_code'] = res["point_of_interaction"]["transaction_data"]["qr_code_base64"]
                    st.session_state['pix_copy'] = res["point_of_interaction"]["transaction_data"]["qr_code"]
                    st.session_state['pay_id'] = res["id"]
                    st.session_state['chaves_lote'] = chaves_limpas
                    st.rerun()

# ÁREA DE PAGAMENTO
if 'qr_code' in st.session_state:
    st.divider()
    c_pix1, c_pix2 = st.columns([1, 1.5])
    with c_pix1:
        st.image(f"data:image/png;base64,{st.session_state['qr_code']}", width=250)
    with c_pix2:
        st.write("### Escaneie o código acima")
        st.code(st.session_state['pix_copy'], language="text")
        if st.button("🚀 Confirmar e Baixar Arquivos"):
            status = sdk.payment().get(st.session_state['pay_id'])["response"]["status"]
            
            if status == "approved":
                st.success("Pagamento aprovado! Limpando e preparando ZIP...")
                zip_buffer = io.BytesIO()
                cont_sucesso = 0
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    with requests.Session() as session:
                        with ThreadPoolExecutor(max_workers=5) as executor:
                            tarefas = {executor.submit(processar_nota, session, c): c for c in st.session_state['chaves_lote']}
                            for t in as_completed(tarefas):
                                ok, chave, xml_bytes = t.result()
                                if ok:
                                    zip_file.writestr(f"{chave}.xml", xml_bytes)
                                    cont_sucesso += 1
                
                if cont_sucesso > 0:
                    st.balloons()
                    st.download_button(f"⬇️ BAIXAR {cont_sucesso} XMLs (FORMATADOS)", zip_buffer.getvalue(), "TaxXML_Lote.zip", "application/zip")
                else:
                    st.error("Erro na Sefaz ou saldo insuficiente. Verifique o painel Meu Danfe.")
            else:
                st.warning("Pagamento ainda pendente.")
