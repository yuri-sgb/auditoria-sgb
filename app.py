import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import io
import time # Para simular carregamento

# Configuração da IA (Nana Banana / Gemini) - Certifique-se de ter a chave no st.secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Chave API 'GEMINI_API_KEY' não encontrada no Streamlit secrets. A geração de descrição não funcionará.")

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide")

def extrair_texto_pdf(file):
    try:
        pdf = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in pdf.pages])
    except: return ""

def tentar_extrair_item(texto, num_item):
    """Tenta localizar o item de forma mais flexível"""
    num_limpo = str(int(num_item))
    padrao = rf"(?i)ITEM[:\s]*{num_limpo}\b(.*?)(?=ITEM[:\s]*\d+\b|VALOR|ESTA\sATA|$)"
    match = re.search(padrao, texto, re.S)
    
    if match:
        bloco = match.group(1).strip()
        if "Diretor" in bloco or "Ato nº" in bloco:
            return ""
        return bloco
    return ""

def refinar_para_gems_com_gemini(texto_bruto, fabricante, modelo, procedencia):
    """Usa o Gemini para reescrever a descrição no padrão GEMS (Letras maiúsculas, sem quebras de linha irregulares)."""
    if "GEMINI_API_KEY" not in st.secrets:
        return f"ERRO: Chave API não configurada. {texto_bruto}"

    prompt = f"""
    Saneamento Técnico e Formatação GEMS de Itens de Licitação.

    Instrução: Reescreva a descrição técnica abaixo seguindo RIGOROSAMENTE as regras do padrão GEMS:
    1.  CONVERTA TODO O TEXTO PARA LETRAS MAIÚSCULAS.
    2.  Remova quebras de linha irregulares e espaços duplos.
    3.  Ajuste pontuação e regência conforme o Manual de Redação da Presidência, garantindo clareza e fluidez, mantendo todas as especificações técnicas.
    4.  Mantenha Marca, Modelo e Fabricante se fornecidos.
    5.  A descrição técnica deve vir primeiro, em parágrafo único, justificado.
    6.  Marca, Modelo, Fabricante e Procedência devem vir ao final, cada um em sua própria linha.

    **Texto Bruto Original:**
    {texto_bruto}

    **Informações Adicionais:**
    FABRICANTE: {fabricante}
    MODELO: {modelo}
    PROCEDÊNCIA: {procedencia}

    **Texto Saneado GEMS:**
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Erro na IA para refinar texto: {e}")
        return texto_bruto # Retorna o bruto em caso de erro

def gerar_imagem_ficticia():
    """Simula a chamada de uma API de imagem e retorna uma URL ou bytes de imagem fictícia."""
    # --- ATENÇÃO ---
    # Para gerar imagem real, substitua este bloco por uma chamada de API (ex: DALL-E)
    # Exemplo:
    # response = dall_e_client.images.generate(prompt=prompt, ...)
    # return response.data[0].url
    # ----------------
    return "https://via.placeholder.com/600x400.png?text=IMAGEM+TECNICA+SGB+SIMULADA"

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

st.header("1. Insira os seguintes documentos para análise")
c1, c2, c3 = st.columns(3)
with c1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with c2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with c3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

if 'texto_original' not in st.session_state:
    st.session_state.texto_original = ""
if 'res_final_gems' not in st.session_state:
    st.session_state.res_final_gems = ""
if 'imagem_url' not in st.session_state:
    st.session_state.imagem_url = None

if f_ata and f_prop:
    t_ata = extrair_texto_pdf(f_ata)
    t_prop = extrair_texto_pdf(f_prop)
    lista_itens = sorted(list(set([i.zfill(2) for i in re.findall(r"(?i)ITEM[:\s]*(\d+)", t_ata)])))
    
    st.divider()
    st.header("2. Descrição Ajustada")
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        item_sel = st.selectbox("Selecione o Item da ATA:", lista_itens)
    with col_btn:
        if st.button("🔍 Extrair Automático"):
            extraido = tentar_extrair_item(t_prop, item_sel)
            if not extraido:
                extraido = tentar_extrair_item(t_ata, item_sel)
            st.session_state.texto_original = extraido

    st.info("💡 Você pode clicar em 'Extrair Automático' ou simplesmente colar o texto original abaixo.")

    c_edit, c_res = st.columns(2)

    with c_edit:
        txt_manual = st.text_area("Redação Original (Cole aqui ou use o automático):", 
                                 value=st.session_state.texto_original, height=400)
        
        m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*([^\n]+)", txt_manual)
        m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*([^\n]+)", txt_manual)
        
        f_fab = st.text_input("Fabricante:", value=m_fab.group(1).strip() if m_fab else "")
        f_mod = st.text_input("Modelo:", value=m_mod.group(1).strip() if m_mod else "")
        f_pro = st.text_input("Procedência (Ex: Importado/USA):")

    with c_res:
        # 1. BOTÃO PARA REFINAR TEXTO NO PADRÃO GEMS USANDO GEMINI
        if st.button("🪄 PROCESSAR SANEAMENTO GEMS (Nana Banana)"):
            if txt_manual:
                with st.spinner("Nana Banana refinando descrição para padrão GEMS..."):
                    desc_refinada = refinar_para_gems_com_gemini(txt_manual, f_fab, f_mod, f_pro)
                    st.session_state.res_final_gems = desc_refinada
            else:
                st.error("Por favor, insira o texto original primeiro.")

        # Exibe o texto saneado se existir
        if 'res_final_gems' in st.session_state and st.session_state.res_final_gems:
            st.subheader("Texto Saneado Padrão GEMS")
            # Exibe com st.code para facilitar a cópia
            st.code(st.session_state.res_final_gems, language="text")
            
            # 2. BOTÃO PARA GERAR IMAGEM TÉCNICA
            st.divider()
            st.subheader("Representação Visual")
            if st.button("🖼️ Gerar Imagem do Item"):
                with st.spinner("Nana Banana criando imagem técnica (Simulada)..."):
                    time.sleep(2) # Simula o tempo de geração
                    st.session_state.imagem_url = gerar_imagem_ficticia() # Retorna URL da imagem simulada

        # Exibe a imagem se existir no estado
        if 'imagem_url' in st.session_state and st.session_state.imagem_url:
            st.image(st.session_state.imagem_url, caption="Representação do Item (Simulada)", use_container_width=True)
            st.success("Imagem gerada com sucesso! Valide se a imagem corresponde ao item almejado, podendo sugerir trocas ou melhorias.")
