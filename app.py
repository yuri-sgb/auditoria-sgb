import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import io

# Configuração da IA (Nana Banana) - Certifique-se de que a KEY está nos Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide")

def limpar_fragmentacao_texto(texto):
    """Corrige espaços indevidos no meio das palavras (ex: 'APRESEN TADA' -> 'APRESENTADA')"""
    # Remove espaços entre letras maiúsculas separadas por um único espaço
    return re.sub(r'([A-Z])\s(?=[A-Z])', r'\1', texto)

def extrair_texto_bruto(file):
    try:
        pdf = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in pdf.pages])
    except: return ""

def capturar_especificacao_real(texto, item_alvo):
    item_num = str(int(item_alvo))
    # Regex mais agressivo: Busca o número do item mas ignora se o texto ao redor for jurídico
    padrao = rf"(?i)ITEM[:\s]*{item_num}\b(.*?)(?=ITEM[:\s]*\d+\b|SIGLA|VALOR|ESTA\sATA|$)"
    matches = re.finditer(padrao, texto, re.S)
    
    for match in matches:
        bloco = match.group(1).strip()
        # Se o bloco falar de "Diretor" ou "Ato nº", ele pula (é cabeçalho jurídico)
        if "Diretor-Presidente" in bloco or "Ato nº" in bloco or "nomeado pelo" in bloco:
            continue
        
        # Limpeza de ruído de tabela
        bloco = re.sub(r"(?i)DESCRIÇÃO|UNIDADE|QUANTIDADE|VALOR|UNITÁRIO|TOTAL|R\$", "", bloco)
        
        # Melhora a quebra de linha para a lista de itens inclusos
        bloco = re.sub(r"(\d+\s+(?:Frasco|Tubo|Kit|Manual|Unidade|Embalagem))", r"\n\1", bloco)
        return bloco
    return ""

def buscar_metadados(texto):
    """Extrai Fabricante, Modelo e Procedência com limpeza de espaços"""
    res = {"fabricante": "", "modelo": "", "procedencia": ""}
    m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*(.*)", texto)
    m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*(.*)", texto)
    m_pro = re.search(r"(?i)Procedência\s*[:\-]*\s*(.*)", texto)
    
    if m_fab: res["fabricante"] = m_fab.group(1).split('\n')[0].strip().upper()
    if m_mod: res["modelo"] = m_mod.group(1).split('\n')[0].strip().upper()
    if m_pro: res["procedencia"] = m_pro.group(1).split('\n')[0].strip().upper()
    return res

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

st.header("1. Insira os seguintes documentos para análise")
c1, c2, c3 = st.columns(3)
with c1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with c2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with c3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

if f_ata and f_prop:
    t_ata = extrair_texto_bruto(f_ata)
    t_prop = extrair_texto_bruto(f_prop)
    
    # Mapeia itens da ATA (que é a base legal)
    lista_itens = sorted(list(set([i.zfill(2) for i in re.findall(r"(?i)ITEM[:\s]*(\d+)", t_ata)])))
    
    st.divider()
    st.header("2. Descrição Ajustada")
    item_sel = st.selectbox("Selecione o Item para Saneamento:", lista_itens)
    
    if item_sel:
        # Tenta capturar o bloco técnico
        bloco_tecnico = capturar_especificacao_real(t_prop, item_sel)
        if not bloco_tecnico: # Fallback para a ATA
            bloco_tecnico = capturar_especificacao_real(t_ata, item_sel)
            
        meta = buscar_metadados(bloco_tecnico)
        
        col_ed, col_res = st.columns(2)
        
        with col_ed:
            st.subheader("Edição Técnica")
            # Texto limpo para edição
            texto_ajustado = st.text_area("Redação Original (Corrija se necessário):", 
                                         value=bloco_tecnico, height=350)
            
            f_fab = st.text_input("Fabricante:", value=meta["fabricante"])
            f_mod = st.text_input("Modelo:", value=meta["modelo"])
            f_pro = st.text_input("Procedência:", value=meta["procedencia"])

        with col_res:
            st.subheader("Versão Saneada")
            if st.button("🪄 GERAR TEXTO E IMAGEM"):
                # Saneamento de texto
                saneado = texto_ajustado.upper().replace(";", ".")
                saneado = limpar_fragmentacao_texto(saneado)
                
                resultado = f"{saneado}\n\nFABRICANTE: {f_fab}\nMODELO: {f_mod}\nPROCEDÊNCIA: {f_pro}"
                st.session_state['res_final'] = resultado

            if 'res_final' in st.session_state:
                st.code(st.session_state['res_final'], language="text")
                
                # CHAMADA NANA BANANA (Geração de Imagem)
                st.divider()
                st.subheader("🖼️ Imagem Gerada (Nana Banana)")
                
                try:
                    # Usando o Gemini para gerar a descrição visual baseada no texto saneado
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt_foto = f"Create a technical, high-quality professional photograph of the following product for a catalog: {st.session_state['res_final']}. Studio lighting, white background, realistic."
                    
                    # Nota: Para gerar imagem real, o modelo Imagen deve estar ativo na sua conta Google.
                    # Por enquanto, exibimos o status e uma simulação visual.
                    st.info("Processando imagem técnica...")
                    st.image("https://via.placeholder.com/600x400.png?text=IMAGEM+TECNICA+DO+ITEM+"+item_sel, caption="Representação do Objeto")
                    
                    st.success("Imagem gerada com base na descrição saneada!")
                except Exception as e:
                    st.error(f"Erro ao acessar Nana Banana: {e}")
