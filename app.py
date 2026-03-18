import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import io

# Configuração da IA (Nana Banana)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide")

def extrair_texto_completo(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except: return ""

def mapear_itens_da_ata(texto_ata):
    """Identifica quais itens existem na ATA para criar o menu"""
    itens = re.findall(r"(?i)ITEM\s*(\d+)", texto_ata)
    # Remove duplicados e ordena
    return sorted(list(set([i.zfill(2) for i in itens])))

def extrair_bloco_item(texto, num_item):
    """Isola o texto de um item específico, parando no próximo item"""
    num_limpo = str(int(num_item))
    # Procura pelo Item X e pega tudo até o próximo "ITEM" ou fim do arquivo
    padrao = rf"(?i)ITEM\s*{num_limpo}\b(.*?)(?=ITEM\s*\d+\b|$)"
    match = re.search(padrao, texto, re.S)
    if match:
        conteudo = match.group(1).strip()
        # Limpeza de ruído de tabela
        conteudo = re.sub(r"(?i)QTDE|UF|PREÇO|UNITARIO|TOTAL|R\$", "", conteudo)
        # Formatação de listas (ex: 1 Frasco, 40 Tubos)
        conteudo = re.sub(r"(\d+\s+(?:Frasco|Tubo|Kit|Manual|Unidade))", r"\n\1", conteudo)
        return conteudo
    return ""

def buscar_metadados(texto_bloco):
    """Busca Fabricante/Modelo dentro do bloco isolado do item"""
    res = {"fabricante": "", "modelo": "", "procedencia": ""}
    m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*([^\n]+)", texto_bloco)
    m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*([^\n]+)", texto_bloco)
    m_pro = re.search(r"(?i)Procedência\s*[:\-]*\s*([^\n]+)", texto_bloco)
    
    if m_fab: res["fabricante"] = m_fab.group(1).strip().upper()
    if m_mod: res["modelo"] = m_mod.group(1).strip().upper()
    if m_pro: res["procedencia"] = m_pro.group(1).strip().upper()
    return res

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

st.header("1. Insira os seguintes documentos para análise")
c1, c2, c3 = st.columns(3)
with c1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with c2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with c3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

if f_ata and f_prop:
    texto_ata = extrair_texto_completo(f_ata)
    texto_prop = extrair_texto_completo(f_prop)
    
    lista_itens = mapear_itens_da_ata(texto_ata)
    
    st.divider()
    st.header("2. Seleção e Ajuste")
    
    # Menu para escolher qual item da ATA será saneado
    item_selecionado = st.selectbox("Selecione o Item da ATA para sanear:", lista_itens)
    
    if item_selecionado:
        # Extrai dados apenas do item escolhido
        bloco_ata = extrair_bloco_item(texto_ata, item_selecionado)
        bloco_prop = extrair_bloco_item(texto_prop, item_selecionado)
        
        # Prioriza a descrição técnica da proposta se disponível
        texto_base = bloco_prop if len(bloco_prop) > 20 else bloco_ata
        meta = buscar_metadados(bloco_prop)

        col_in, col_out = st.columns(2)
        
        with col_in:
            txt_ajuste = st.text_area("Redação Original Detectada:", value=texto_base, height=300)
            f_fab = st.text_input("Fabricante:", value=meta["fabricante"])
            f_mod = st.text_input("Modelo:", value=meta["modelo"])
            f_pro = st.text_input("Procedência:", value=meta["procedencia"])
            
        with col_out:
            if st.button(f"🪄 GERAR DESCRIÇÃO FINAL - ITEM {item_selecionado}"):
                saneado = txt_ajuste.upper().replace(";", ".")
                resultado_final = f"{saneado}\n\nFABRICANTE: {f_fab}\nMODELO: {f_mod}\nPROCEDÊNCIA: {f_pro}"
                
                st.code(resultado_final, language="text")
                
                # Chamada Nana Banana
                st.subheader("🖼️ Imagem Técnica (IA)")
                try:
                    # Aqui entra a lógica de geração com o prompt do item selecionado
                    st.image("https://via.placeholder.com/500x300.png?text=IA+Gerando+Item+"+item_selecionado)
                except:
                    st.error("Erro na geração da imagem.")
