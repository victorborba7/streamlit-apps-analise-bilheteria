import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO
from urllib.parse import quote
import geopandas as gpd
import json

# Imports dos módulos de gráficos
from graficos.gerais.index import grafico_vendas_ao_longo_do_tempo, analise_comportamento_compra
from graficos.demograficos.index import analise_demografica
from graficos.geograficos.index import mapa_brasil, mapa_estado_rj, mapa_ras_capital, grafico_bairros_por_tipo_ingresso


# ==============================
# Carregamento dos dados
# ==============================
def load_file_from_github(url, headers):
    """Baixa arquivo do GitHub com autenticação"""
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Debug: verifica se o conteúdo é realmente um arquivo Excel
    content = response.content
    if len(content) < 100 or content[:4] != b'PK\x03\x04':
        # Não é um arquivo ZIP/Excel válido
        st.error(f"❌ Erro ao baixar arquivo de: {url}")
        st.error(f"Tamanho do conteúdo: {len(content)} bytes")
        st.error(f"Primeiros bytes: {content[:100]}")
        raise ValueError(f"Arquivo baixado não é um Excel válido. URL: {url}")
    
    file_obj = BytesIO(content)
    file_obj.seek(0)  # Garante que o ponteiro está no início
    return file_obj


@st.cache_data
def load_data():
    # Base URL do repositório GitHub (raw)
    github_pat = st.secrets["github_pat"]
    github_base = "https://raw.githubusercontent.com/victorborba7/streamlit-apps-analise-bilheteria-data/main"
    
    headers = {"Authorization": f"Bearer {github_pat}"}
    
    # ==============================
    # Bilhetagem principal
    # ==============================
    bilhetes_filename = quote("Bilhetes.xlsx")
    bilhetes_url = f"{github_base}/{bilhetes_filename}"
    bilhetes = pd.read_excel(load_file_from_github(bilhetes_url, headers), sheet_name="Sheet1", engine='openpyxl')

    if "TDL Event Date" in bilhetes.columns:
        bilhetes["TDL Event Date"] = pd.to_datetime(bilhetes["TDL Event Date"])

    # Garante CPF como string e padroniza formato
    if "TDL Customer CPF" in bilhetes.columns:
        bilhetes["TDL Customer CPF"] = bilhetes["TDL Customer CPF"].astype(str)
        # Remove valores inválidos (nan, None, etc)
        bilhetes["TDL Customer CPF"] = bilhetes["TDL Customer CPF"].replace(['nan', 'None', 'NaN', ''], None)
        # Preenche com zeros à esquerda para ter 11 dígitos
        bilhetes["TDL Customer CPF"] = bilhetes["TDL Customer CPF"].apply(
            lambda x: x.zfill(11) if x is not None and x not in ['nan', 'None', 'NaN', ''] else None
        )

    if "Status do ingresso":
        bilhetes = bilhetes[(bilhetes["Status do ingresso"].str.contains("Cancelado") == False) | (bilhetes["Status do ingresso"].isna())]

    # Processa data de nascimento e calcula idade
    if "TDL Customer Birth Date" in bilhetes.columns:
        bilhetes["TDL Customer Birth Date"] = pd.to_datetime(bilhetes["TDL Customer Birth Date"], errors="coerce")
        bilhetes["Idade"] = (pd.Timestamp.now() - bilhetes["TDL Customer Birth Date"]).dt.days // 365
        
        # Cria faixas etárias
        bilhetes["Faixa Etária"] = pd.cut(
            bilhetes["Idade"],
            bins=[0, 18, 25, 35, 45, 55, 65, 100],
            labels=["Menor de 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
        )

    # ==============================
    # Bilhetagem Marisa Monte
    # ==============================
    # marisa = pd.read_excel(
    #     load_file_from_github(bilhetes_url, headers),
    #     sheet_name="MarisaMonte",
    #     engine='openpyxl'
    # )

    # # Coluna J = índice 9
    # marisa["CPF_LOGICO"] = marisa.iloc[:, 9].astype(str)

    # # Cria estrutura compatível
    # marisa_ajustada = pd.DataFrame({
    #     "TDL Event": "MARISA MONTE",
    #     "TDL Event Date": pd.to_datetime(marisa.iloc[:, 0], errors="coerce"),
    #     "TDL Customer CPF": marisa["CPF_LOGICO"],
    #     "TDL Sum Tickets (B+S-A)": 1,
    #     "TDL Sum Ticket Net Price (B+S-A)": pd.to_numeric(marisa.iloc[:, 5], errors="coerce"),
    # })

    # ==============================
    # Concatenação final
    # ==============================
    bilhetes_final = bilhetes.copy()
    # pd.concat(
    #     [bilhetes, marisa_ajustada],
    #     ignore_index=True
    # )

    # ==============================
    # Credenciamento
    # ==============================
    cred_filename = quote("Credenciamento.xlsx")
    cred_url = f"{github_base}/data/raw/{cred_filename}"
    cred_2025 = pd.read_excel(load_file_from_github(cred_url, headers), sheet_name="Staff", engine='openpyxl')
    artistico_2025 = pd.read_excel(load_file_from_github(cred_url, headers), sheet_name="Artistico", engine='openpyxl')
    desm_2024 = pd.read_excel(load_file_from_github(cred_url, headers), sheet_name="Desmontagem_2024", engine='openpyxl')
    
    # Normaliza os nomes das colunas
    cred_2025.columns = cred_2025.columns.str.strip().str.upper()
    artistico_2025.columns = artistico_2025.columns.str.strip().str.upper()
    desm_2024.columns = desm_2024.columns.str.strip().str.upper()
    
    # Processa artístico - transforma Função 1 e Função 2 em linhas separadas
    if not artistico_2025.empty:
        # Cria duas cópias do DataFrame artístico
        artistico_funcao1 = artistico_2025.copy()
        artistico_funcao2 = artistico_2025.copy()
        
        # Renomeia Função 1 para FUNÇÃO/CATEGORIA na primeira cópia
        if "FUNÇÃO 1" in artistico_funcao1.columns:
            artistico_funcao1["CATEGORIA"] = artistico_funcao1["FUNÇÃO 1"]
        
        # Renomeia Função 2 para FUNÇÃO/CATEGORIA na segunda cópia
        if "FUNÇÃO 2" in artistico_funcao2.columns:
            artistico_funcao2["CATEGORIA"] = artistico_funcao2["FUNÇÃO 2"]
        
        # Remove colunas Função 1 e Função 2 originais
        cols_to_drop = [col for col in ["FUNÇÃO 1", "FUNÇÃO 2"] if col in artistico_funcao1.columns]
        if cols_to_drop:
            artistico_funcao1 = artistico_funcao1.drop(columns=cols_to_drop)
            artistico_funcao2 = artistico_funcao2.drop(columns=cols_to_drop)
        
        # Filtra apenas linhas onde a função não é vazia
        if "CATEGORIA" in artistico_funcao1.columns:
            artistico_funcao1 = artistico_funcao1[artistico_funcao1["CATEGORIA"].notna() & (artistico_funcao1["CATEGORIA"] != "")]
        if "CATEGORIA" in artistico_funcao2.columns:
            artistico_funcao2 = artistico_funcao2[artistico_funcao2["CATEGORIA"].notna() & (artistico_funcao2["CATEGORIA"] != "")]
        
        # Concatena as duas versões
        artistico_processado = pd.concat([artistico_funcao1, artistico_funcao2], ignore_index=True)
        
        # Para artístico, usa NOME ou NOME COMPLETO como CPF se não houver CPF
        cpf_cols_artistico = [col for col in artistico_processado.columns if 'CPF' in col.upper()]
        if not cpf_cols_artistico:
            # Se não tem coluna CPF, cria uma usando NOME COMPLETO ou NOME
            if "NOME COMPLETO" in artistico_processado.columns:
                artistico_processado["FUNCIONÁRIOS - CPF"] = artistico_processado["NOME COMPLETO"]
            elif "NOME" in artistico_processado.columns:
                artistico_processado["FUNCIONÁRIOS - CPF"] = artistico_processado["NOME"]
            else:
                # Se não tem nem nome, usa índice
                artistico_processado["FUNCIONÁRIOS - CPF"] = "ARTISTICO_" + artistico_processado.index.astype(str)
        else:
            # Se tem CPF mas está vazio, preenche com NOME COMPLETO, NOME ou índice
            cpf_col = cpf_cols_artistico[0]
            # Primeiro tenta NOME COMPLETO
            if "NOME COMPLETO" in artistico_processado.columns:
                mask_vazio = artistico_processado[cpf_col].isna() | (artistico_processado[cpf_col] == '') | (artistico_processado[cpf_col] == 'nan') | (artistico_processado[cpf_col] == 'None')
                artistico_processado.loc[mask_vazio, cpf_col] = artistico_processado.loc[mask_vazio, "NOME COMPLETO"]
            # Depois tenta NOME
            if "NOME" in artistico_processado.columns:
                mask_vazio = artistico_processado[cpf_col].isna() | (artistico_processado[cpf_col] == '') | (artistico_processado[cpf_col] == 'nan') | (artistico_processado[cpf_col] == 'None')
                artistico_processado.loc[mask_vazio, cpf_col] = artistico_processado.loc[mask_vazio, "NOME"]
            # Por último, usa índice como fallback
            mask_vazio = artistico_processado[cpf_col].isna() | (artistico_processado[cpf_col] == '') | (artistico_processado[cpf_col] == 'nan') | (artistico_processado[cpf_col] == 'None')
            artistico_processado.loc[mask_vazio, cpf_col] = "ARTISTICO_" + artistico_processado.loc[mask_vazio].index.astype(str)
    else:
        artistico_processado = pd.DataFrame()
    
    # Concatena Staff com Artístico processado
    if not artistico_processado.empty:
        cred_2025 = pd.concat([cred_2025, artistico_processado], ignore_index=True)
    
    # Adiciona coluna de origem
    cred_2025["ORIGEM"] = "2025"
    desm_2024["ORIGEM"] = "Desmontagem 2024"
    
    # Ajusta ETAPA para artístico (quando estiver vazia ou nan)
    if "ETAPA" in cred_2025.columns:
        cred_2025["ETAPA"] = cred_2025["ETAPA"].astype(str)
        mask_etapa_vazia = cred_2025["ETAPA"].isin(['nan', 'None', 'NaN', '', '<NA>', 'nat'])
        cred_2025.loc[mask_etapa_vazia, "ETAPA"] = "ARTÍSTICO"
    
    # Processa dados de 2025
    if "DATA" in cred_2025.columns:
        cred_2025["DATA"] = pd.to_datetime(cred_2025["DATA"], errors="coerce")
    
    # Tratamento especial para colunas de CPF - 2025 (ANTES de converter para string)
    cpf_columns_2025 = [col for col in cred_2025.columns if 'CPF' in col.upper()]
    for col in cpf_columns_2025:
        if col in cred_2025.columns:
            # Converte para string
            cred_2025[col] = cred_2025[col].astype(str)
            
            # Substitui valores vazios/nulos pelo índice
            mask_vazio = cred_2025[col].isin(['nan', 'None', 'NaN', '', '<NA>', 'nat'])
            cred_2025.loc[mask_vazio, col] = "SEM_CPF_" + cred_2025.loc[mask_vazio].index.astype(str)
            
            # Formata CPFs numéricos com zeros à esquerda
            mask_numerico = cred_2025[col].str.isdigit() & (cred_2025[col].str.len() <= 11)
            cred_2025.loc[mask_numerico, col] = cred_2025.loc[mask_numerico, col].str.zfill(11)
    
    # Converte todas as colunas object para string para evitar erros do PyArrow - 2025
    for col in cred_2025.columns:
        if cred_2025[col].dtype == 'object' and col != 'DATA' and col not in cpf_columns_2025:
            cred_2025[col] = cred_2025[col].astype(str)
    
    # Adiciona informação de evento baseado na data - 2025
    if "TDL Event Date" in bilhetes_final.columns and "TDL Event" in bilhetes_final.columns:
        mapa_data_evento = (
            bilhetes_final[["TDL Event Date", "TDL Event"]]
            .drop_duplicates()
            .set_index("TDL Event Date")["TDL Event"]
            .to_dict()
        )
        
        if "DATA" in cred_2025.columns:
            cred_2025["EVENTO"] = cred_2025["DATA"].map(mapa_data_evento)
    
    # Processa dados de 2024
    if "DATA" in desm_2024.columns:
        desm_2024["DATA"] = pd.to_datetime(desm_2024["DATA"], errors="coerce")
    
    # Converte todas as colunas object para string para evitar erros do PyArrow - 2024
    for col in desm_2024.columns:
        if desm_2024[col].dtype == 'object' and col != 'DATA':
            desm_2024[col] = desm_2024[col].astype(str)
    
    # Tratamento especial para colunas de CPF - 2024
    cpf_columns_2024 = [col for col in desm_2024.columns if 'CPF' in col.upper()]
    for col in cpf_columns_2024:
        desm_2024[col] = desm_2024[col].replace(['nan', 'None', 'NaN', ''], None)
        desm_2024[col] = desm_2024[col].apply(
            lambda x: x.zfill(11) if x is not None and x not in ['nan', 'None', 'NaN', '', 'None'] else None
        )

    return bilhetes_final, cred_2025, desm_2024


@st.cache_data
def carregar_geojson_ras():
    """
    Carrega o GeoJSON oficial das Regiões Administrativas do Rio de Janeiro
    a partir da API da Prefeitura.
    """
    url = (
        "https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/"
        "Limites_administrativos/FeatureServer/3/query"
        "?where=1%3D1&outFields=*&f=geojson"
    )
    try:
        ra_gdf = gpd.read_file(url)
        # Converte para WGS84 (lat/lon)
        ra_gdf = ra_gdf.to_crs(4326)
        return ra_gdf
    except Exception as e:
        st.warning(f"Não foi possível carregar os limites das RAs: {e}")
        return None


@st.cache_data
def carregar_geojson_brasil():
    """
    Carrega o GeoJSON dos estados do Brasil.
    Usa dados do IBGE via URL pública.
    """
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    try:
        brasil_gdf = gpd.read_file(url)
        return brasil_gdf
    except Exception as e:
        st.warning(f"Não foi possível carregar o mapa do Brasil: {e}")
        return None


@st.cache_data
def carregar_geojson_municipios_rj():
    """
    Carrega o GeoJSON dos municípios do Estado do Rio de Janeiro.
    """
    # URL do GeoJSON dos municípios do RJ (IBGE)
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-33-mun.json"
    try:
        rj_gdf = gpd.read_file(url)
        # Converte para WGS84 se necessário
        if rj_gdf.crs and rj_gdf.crs.to_epsg() != 4326:
            rj_gdf = rj_gdf.to_crs(4326)
        return rj_gdf
    except Exception as e:
        st.warning(f"Não foi possível carregar o mapa dos municípios do RJ: {e}")
        return None


# ==============================
# App principal
# ==============================
def main():
    st.set_page_config(
        page_title="Dashboard Arena Jockey",
        layout="wide"
    )

    st.title("📊 Dashboard Arena Jockey")
    st.markdown("Versão inicial do painel de **Bilhetagem** e **Credenciamento**.")

    # Carrega dados
    bilhetes, cred_2025, cred_2024 = load_data()

    # Aba de navegação
    tab_bilhetagem, tab_credenciamento = st.tabs(["🎟 Bilhetagem", "👷 Credenciamento 2025"])

    # ==============================
    # ABA 1 – BILHETAGEM
    # ==============================
    with tab_bilhetagem:
        st.subheader("🎟 Análises de Bilhetagem")

        # Adiciona coluna de dia da semana
        if "TDL Event Date" in bilhetes.columns:
            bilhetes["dia_semana"] = bilhetes["TDL Event Date"].dt.day_name()
            
            # Traduz os dias da semana
            mapa_dia_bilhetagem = {
                "Monday": "Segunda",
                "Tuesday": "Terça",
                "Wednesday": "Quarta",
                "Thursday": "Quinta",
                "Friday": "Sexta",
                "Saturday": "Sábado",
                "Sunday": "Domingo",
            }
            bilhetes["dia_semana_label"] = bilhetes["dia_semana"].map(mapa_dia_bilhetagem)

        # Filtros - Linha 1
        col1, col2, col3 = st.columns(3)

        # Evento
        eventos = sorted(bilhetes["TDL Event"].dropna().unique())
        evento_sel = col1.multiselect("Evento", eventos)

        # Período
        if bilhetes["TDL Event Date"].notna().any():
            data_min = bilhetes["TDL Event Date"].min()
            data_max = bilhetes["TDL Event Date"].max()
            periodo = col2.date_input(
                "Período do evento",
                value=(data_min, data_max),
                min_value=data_min,
                max_value=data_max
            )
        else:
            periodo = None

        # Dia da Semana
        if "dia_semana_label" in bilhetes.columns:
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            dias_disponiveis = [d for d in dias_semana if d in bilhetes["dia_semana_label"].unique()]
            dia_semana_sel = col3.multiselect("Dia da Semana", dias_disponiveis)
        else:
            dia_semana_sel = []

        # Filtros - Linha 2
        col4, col5, col6 = st.columns(3)

        # Região Administrativa
        ras = sorted(bilhetes["RA"].dropna().unique())
        ra_sel = col6.multiselect("Região Administrativa", ras)
        
        # País
        pais_col = "TDL Customer Country"
        if pais_col in bilhetes.columns:
            paises = sorted(bilhetes[pais_col].dropna().unique())
            pais_sel = col4.multiselect("País", paises)
        else:
            pais_sel = []

        # Estado
        tipo_ingresso_col = "TDL Price Category"
        if tipo_ingresso_col in bilhetes.columns:
            tipo_ingressos = sorted(bilhetes[tipo_ingresso_col].dropna().unique())
            tipo_ingresso_sel = col5.multiselect("Tipo de Ingresso", tipo_ingressos)
        else:
            tipo_ingresso_sel = []

        # Aplica filtros
        df_b = bilhetes.copy()

        if evento_sel:
            df_b = df_b[df_b["TDL Event"].isin(evento_sel)]

        if periodo is not None and isinstance(periodo, (list, tuple)) and len(periodo) == 2:
            ini, fim = periodo
            df_b = df_b[
                (df_b["TDL Event Date"] >= pd.to_datetime(ini)) &
                (df_b["TDL Event Date"] <= pd.to_datetime(fim))
            ]

        if pais_sel and pais_col in df_b.columns:
            df_b = df_b[df_b[pais_col].isin(pais_sel)]

        if tipo_ingresso_sel and tipo_ingresso_col in df_b.columns:
            df_b = df_b[df_b[tipo_ingresso_col].isin(tipo_ingresso_sel)]

        if ra_sel:
            df_b = df_b[df_b["RA"].isin(ra_sel)]

        if dia_semana_sel and "dia_semana_label" in df_b.columns:
            df_b = df_b[df_b["dia_semana_label"].isin(dia_semana_sel)]

        st.markdown("#### Visão geral")
        col_a, col_b, col_c = st.columns(3)

        total_ingressos = df_b["TDL Sum Tickets (B+S-A)"].sum()
        total_receita = df_b["TDL Sum Ticket Net Price (B+S-A)"].sum()
        total_clientes = df_b["TDL Customer CPF"].nunique()

        col_a.metric("Total ingressos", int(total_ingressos))
        col_b.metric("Receita líquida (R$)", f"{total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col_c.metric("Clientes únicos", int(total_clientes))

        # Novas métricas
        st.markdown("---")
        col_d, col_e, col_f = st.columns(3)
        
        media_ingressos_por_cpf = total_ingressos / total_clientes if total_clientes > 0 else 0
        ticket_medio = total_receita / total_ingressos if total_ingressos > 0 else 0
        
        # Calcula clientes recorrentes (que foram a mais de 1 evento)
        if "TDL Event" in df_b.columns:
            clientes_recorrentes = df_b.groupby("TDL Customer CPF")["TDL Event"].nunique()
            qtd_recorrentes = (clientes_recorrentes > 1).sum()
            perc_recorrentes = (qtd_recorrentes / total_clientes * 100) if total_clientes > 0 else 0
        else:
            qtd_recorrentes = 0
            perc_recorrentes = 0
        
        col_d.metric("Média de ingressos por CPF", f"{media_ingressos_por_cpf:.2f}")
        col_e.metric("Ticket médio (R$)", f"{ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col_f.metric("Clientes recorrentes", f"{qtd_recorrentes} ({perc_recorrentes:.1f}%)")
        
        # Botão de download das métricas
        st.markdown("---")
        metricas_resumo = pd.DataFrame({
            "Métrica": [
                "Total de ingressos",
                "Receita líquida (R$)",
                "Clientes únicos",
                "Média de ingressos por CPF",
                "Ticket médio (R$)",
                "Clientes recorrentes (quantidade)",
                "Clientes recorrentes (%)"
            ],
            "Valor": [
                int(total_ingressos),
                f"{total_receita:,.2f}",
                int(total_clientes),
                f"{media_ingressos_por_cpf:.2f}",
                f"{ticket_medio:,.2f}",
                int(qtd_recorrentes),
                f"{perc_recorrentes:.1f}"
            ]
        })
        
        csv_metricas = metricas_resumo.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Download Métricas Gerais (CSV)",
            data=csv_metricas,
            file_name="metricas_bilhetagem.csv",
            mime="text/csv",
            use_container_width=True
        )

        # ==============================
        # Análise de Comportamento de Compra
        # ==============================
        st.markdown("---")
        # Análise de comportamento de compra (função modular)
        analise_comportamento_compra(df_b)

        # ==============================
        # Dados Demográficos
        # ==============================
        st.markdown("---")
        # Análise demográfica (função modular)
        analise_demografica(df_b)

        st.markdown("---")
        # Gráfico de vendas ao longo do tempo (função modular)
        grafico_vendas_ao_longo_do_tempo(df_b)

        st.markdown("#### Top Regiões Administrativas (Ingressos)")
        if not df_b.empty:
            por_ra = (
                df_b.groupby("RA")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
            )
            por_ra = por_ra[por_ra["RA"].notna()]
            # Calcula percentuais
            total_ra = por_ra["TDL Sum Tickets (B+S-A)"].sum()
            por_ra["Percentual"] = (por_ra["TDL Sum Tickets (B+S-A)"] / total_ra * 100).round(1)
            
            fig_ra = px.bar(
                por_ra,
                x="RA",
                y="TDL Sum Tickets (B+S-A)",
                labels={
                    "RA": "Região Administrativa",
                    "TDL Sum Tickets (B+S-A)": "Ingressos"
                },
                title="Ingressos por Região Administrativa",
                color="TDL Sum Tickets (B+S-A)",
                color_continuous_scale="Blues",
                text=por_ra["Percentual"].apply(lambda x: f"{x}%")
            )
            fig_ra.update_traces(textposition='outside')
            fig_ra.update_layout(height=450, showlegend=False)
            st.plotly_chart(fig_ra, use_container_width=True)
        
        with st.expander("📊 Ver dados da tabela"):
            por_ra_display = por_ra[["RA", "TDL Sum Tickets (B+S-A)", "Percentual"]].copy()
            por_ra_display.columns = ["Região Administrativa", "Ingressos", "Percentual (%)"]
            st.dataframe(por_ra_display, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📍 Análises Geográficas")

        # ==============================
        # Mapa do Brasil
        # ==============================
        # Mapa do Brasil (função modular)
        mapa_brasil(df_b, carregar_geojson_brasil)

        # ==============================
        # Mapa do Estado do Rio de Janeiro
        # ==============================
        # Mapa do Estado do RJ (função modular)
        mapa_estado_rj(df_b, carregar_geojson_municipios_rj)

        # Mapa das RAs da capital (função modular)
        mapa_ras_capital(df_b, carregar_geojson_ras)

        # Gráfico de bairros por tipo de ingresso (função modular)
        grafico_bairros_por_tipo_ingresso(df_b)

        # Top 10 Bairros
        st.markdown("#### Top 10 Bairros por Total de Ingressos")
        if "bairro_google_norm" in df_b.columns:
            top_bairros = (
                df_b[df_b["bairro_google_norm"].notna()]
                .groupby("bairro_google_norm")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
                .head(10)
            )
            
            # Calcula percentuais em relação ao total geral
            total_geral_ingressos = df_b["TDL Sum Tickets (B+S-A)"].sum()
            top_bairros["Percentual"] = (top_bairros["TDL Sum Tickets (B+S-A)"] / total_geral_ingressos * 100).round(1)
            
            # Layout com gráfico e tabela lado a lado
            col_grafico, col_tabela = st.columns([2, 1])
            
            with col_grafico:
                fig_top_bairros = px.bar(
                    top_bairros,
                    x="bairro_google_norm",
                    y="TDL Sum Tickets (B+S-A)",
                    labels={
                        "bairro_google_norm": "Bairro",
                        "TDL Sum Tickets (B+S-A)": "Total de Ingressos"
                    },
                    title="Top 10 Bairros",
                    text=top_bairros["Percentual"].apply(lambda x: f"{x}%"),
                    color="TDL Sum Tickets (B+S-A)",
                    color_continuous_scale="Blues"
                )
                fig_top_bairros.update_traces(textposition='outside')
                fig_top_bairros.update_layout(
                    xaxis={'categoryorder':'total descending'},
                    height=500,
                    showlegend=False
                )
                st.plotly_chart(fig_top_bairros, use_container_width=True)
            
            with col_tabela:
                # Formata para exibição
                top_bairros_display = top_bairros.copy()
                top_bairros_display.columns = ["Bairro", "Total de Ingressos", "Percentual (%)"]
                top_bairros_display["Total de Ingressos"] = top_bairros_display["Total de Ingressos"].astype(int)
                top_bairros_display.index = range(1, len(top_bairros_display) + 1)
                
                st.dataframe(top_bairros_display, use_container_width=True, height=500)
            
            # Botão de download
            csv_top_bairros = top_bairros_display.to_csv(index=True, encoding='utf-8-sig')
            st.download_button(
                label="📥 Download Top 10 Bairros (CSV)",
                data=csv_top_bairros,
                file_name="top_10_bairros.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("Coluna de bairro não disponível nos dados.")

        # Tabela
        st.markdown("#### Amostra dos dados de bilhetagem")
        st.dataframe(df_b)

    # ==============================
    # ABA 2 – CREDENCIAMENTO 2025
    # ==============================
    with tab_credenciamento:
        st.subheader("👷 Análises de Credenciamento 2025")

        cred = cred_2025.copy()

        # Cria coluna com dia da semana
        if "DATA" in cred.columns:
            cred["dia_semana"] = cred["DATA"].dt.day_name()

            # Traduz e ordena
            mapa_dia = {
                "Wednesday": "Quarta",
                "Thursday": "Quinta",
                "Friday": "Sexta",
                "Saturday": "Sábado",
                "Sunday": "Domingo",
                "Monday": "Segunda",
                "Tuesday": "Terça",
            }
            cred["dia_label"] = cred["dia_semana"].map(mapa_dia)

        # Filtros - Linha 1
        col1, col2, col3 = st.columns(3)

        # Etapa
        if "ETAPA" in cred.columns:
            etapas = sorted(cred["ETAPA"].dropna().unique())
            etapa_sel = col1.multiselect("Etapa", etapas)
        else:
            etapa_sel = []

        # Categoria
        if "CATEGORIA" in cred.columns:
            categorias = sorted(cred["CATEGORIA"].dropna().unique())
            cat_sel = col2.multiselect("Categoria", categorias)
        else:
            cat_sel = []

        # Empresa
        if "EMPRESA" in cred.columns:
            empresas = sorted(cred["EMPRESA"].dropna().unique())
            emp_sel = col3.multiselect("Empresa", empresas)
        else:
            emp_sel = []

        # Filtros - Linha 2
        col4, col5, col6 = st.columns(3)

        # Evento
        if "EVENTO" in cred.columns:
            eventos_cred = sorted([e for e in cred["EVENTO"].dropna().unique() if e != 'nan' and e != 'None'])
            evento_cred_sel = col4.multiselect("Evento", eventos_cred, key="evento_cred")
        else:
            evento_cred_sel = []

        # Origem (2025 ou Desmontagem 2024)
        if "ORIGEM" in cred.columns:
            origens = sorted(cred["ORIGEM"].dropna().unique())
            origem_sel = col5.multiselect("Ano/Evento", origens)
        else:
            origem_sel = []

        # Dia da Semana
        if "dia_label" in cred.columns:
            dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            dias_disponiveis = [d for d in dias_semana if d in cred["dia_label"].unique()]
            dia_semana_cred_sel = col6.multiselect("Dia da Semana", dias_disponiveis)
        else:
            dia_semana_cred_sel = []

        # Filtros - Linha 3
        col7, col8, col9 = st.columns(3)

        # Período de data
        if "DATA" in cred.columns and cred["DATA"].notna().any():
            data_min_cred = cred["DATA"].min()
            data_max_cred = cred["DATA"].max()
            periodo_cred = col7.date_input(
                "Período de credenciamento",
                value=(data_min_cred, data_max_cred),
                min_value=data_min_cred,
                max_value=data_max_cred,
                key="periodo_cred"
            )
        else:
            periodo_cred = None

        # Aplica filtros
        df_c = cred.copy()

        if etapa_sel and "ETAPA" in df_c.columns:
            df_c = df_c[df_c["ETAPA"].isin(etapa_sel)]
        if cat_sel and "CATEGORIA" in df_c.columns:
            df_c = df_c[df_c["CATEGORIA"].isin(cat_sel)]
        if emp_sel and "EMPRESA" in df_c.columns:
            df_c = df_c[df_c["EMPRESA"].isin(emp_sel)]
        if evento_cred_sel and "EVENTO" in df_c.columns:
            df_c = df_c[df_c["EVENTO"].isin(evento_cred_sel)]
        if origem_sel and "ORIGEM" in df_c.columns:
            df_c = df_c[df_c["ORIGEM"].isin(origem_sel)]
        if dia_semana_cred_sel and "dia_label" in df_c.columns:
            df_c = df_c[df_c["dia_label"].isin(dia_semana_cred_sel)]
        if periodo_cred is not None and isinstance(periodo_cred, (list, tuple)) and len(periodo_cred) == 2:
            ini_cred, fim_cred = periodo_cred
            df_c = df_c[
                (df_c["DATA"] >= pd.to_datetime(ini_cred)) &
                (df_c["DATA"] <= pd.to_datetime(fim_cred))
            ]

        # Métricas gerais
        st.markdown("#### Visão geral")
        col_a, col_b, col_c = st.columns(3)

        # Total de credenciamentos (total de registros)
        cpf_cols_cred = [col for col in df_c.columns if 'CPF' in col.upper()]
        total_credenciamentos = len(df_c)
        col_a.metric("Total de credenciamentos", int(total_credenciamentos))
        
        # Conta profissionais únicos por CPF
        if cpf_cols_cred:
            # Remove valores None/nan antes de contar
            cpf_unicos = df_c[df_c[cpf_cols_cred[0]].notna() & (df_c[cpf_cols_cred[0]] != 'None')][cpf_cols_cred[0]].nunique()
            col_b.metric("Profissionais únicos (CPF)", int(cpf_unicos))
        elif "CATEGORIA" in df_c.columns:
            total_categorias = df_c["CATEGORIA"].nunique()
            col_b.metric("Categorias únicas", int(total_categorias))
        
        if "EMPRESA" in df_c.columns:
            total_empresas = df_c["EMPRESA"].nunique()
            col_c.metric("Empresas envolvidas", int(total_empresas))

        # Análise de profissionais por categoria e dia
        if "CATEGORIA" in df_c.columns and "DATA" in df_c.columns:
            st.markdown("#### Profissionais por Categoria e Dia")
            
            # Conta profissionais por categoria e data
            cpf_col_cred = [col for col in df_c.columns if 'CPF' in col.upper()]
            if cpf_col_cred:
                # Filtra categorias válidas
                df_c_cat_dia = df_c[
                    df_c["CATEGORIA"].notna() & 
                    (df_c["CATEGORIA"] != 'nan') & 
                    (df_c["CATEGORIA"] != 'None')
                ]
                
                prof_por_cat_dia = (
                    df_c_cat_dia.groupby(["CATEGORIA", "DATA"])[cpf_col_cred[0]]
                    .count()
                    .reset_index()
                )
                prof_por_cat_dia.columns = ["Categoria", "Data", "Profissionais"]
                prof_por_cat_dia["Data"] = pd.to_datetime(prof_por_cat_dia["Data"]).dt.strftime("%d/%m/%Y")
                
                if not prof_por_cat_dia.empty:
                    # Cria tabela pivotada
                    tabela_cat_dia = prof_por_cat_dia.pivot(
                        index="Data",
                        columns="Categoria",
                        values="Profissionais"
                    ).fillna(0).astype(int)
                    
                    # Adiciona total por linha
                    tabela_cat_dia['Total'] = tabela_cat_dia.sum(axis=1)
                    
                    st.dataframe(tabela_cat_dia, use_container_width=True)
                    
                    with st.expander("📊 Ver gráfico"):
                        # Gráfico de barras empilhadas
                        prof_por_cat_dia_num = prof_por_cat_dia.copy()
                        prof_por_cat_dia_num["Data"] = pd.to_datetime(prof_por_cat_dia_num["Data"], format="%d/%m/%Y")
                        
                        # Calcula total por dia para mostrar no topo
                        total_por_dia_cat = prof_por_cat_dia_num.groupby("Data")["Profissionais"].sum().reset_index()
                        total_por_dia_cat.columns = ["Data", "Total"]
                        
                        fig_cat_dia = px.bar(
                            prof_por_cat_dia_num,
                            x="Data",
                            y="Profissionais",
                            color="Categoria",
                            barmode="stack",
                            labels={
                                "Data": "Data",
                                "Profissionais": "Profissionais",
                                "Categoria": "Categoria"
                            },
                            title="Profissionais por categoria e dia"
                        )
                        
                        # Adiciona anotações com o total no topo de cada barra
                        for _, row in total_por_dia_cat.iterrows():
                            fig_cat_dia.add_annotation(
                                x=row["Data"],
                                y=row["Total"],
                                text=f"{row['Total']:.0f}",
                                showarrow=False,
                                yshift=10,
                                font=dict(size=12, color="white", family="Arial Black"),
                                bgcolor="rgba(0,0,0,0.7)",
                                bordercolor="white",
                                borderwidth=1,
                                borderpad=3
                            )
                        
                        fig_cat_dia.update_layout(height=500)
                        st.plotly_chart(fig_cat_dia, use_container_width=True)
                else:
                    st.info("Não há dados de categorias mapeadas para o período selecionado.")
            
            st.markdown("---")
        
        st.markdown("#### (a) Total de profissionais por categoria")
        if not df_c.empty and "CATEGORIA" in df_c.columns and cpf_cols_cred:
            # Filtra NaN antes de agrupar
            df_c_cat = df_c[df_c["CATEGORIA"].notna() & (df_c["CATEGORIA"] != 'nan') & (df_c["CATEGORIA"] != 'None')]
            total_cat = (
                df_c_cat.groupby("CATEGORIA")[cpf_cols_cred[0]]
                .count()
                .reset_index()
            )
            total_cat.columns = ["CATEGORIA", "Total"]
            total_cat = total_cat[total_cat["CATEGORIA"].notna()]
            total_cat = total_cat.sort_values("Total", ascending=False)

            # Calcula percentuais
            total_geral = total_cat["Total"].sum()
            total_cat["Percentual"] = (total_cat["Total"] / total_geral * 100).round(1)
            
            fig_total = px.bar(
                total_cat,
                x="CATEGORIA",
                y="Total",
                labels={
                    "CATEGORIA": "Categoria",
                    "Total": "Total de profissionais"
                },
                title="Total de profissionais por categoria",
                text=total_cat["Percentual"].apply(lambda x: f"{x}%"),
                color="Total",
                color_continuous_scale="Blues"
            )
            
            fig_total.update_traces(textposition='outside')
            fig_total.update_layout(
                xaxis={'categoryorder':'total descending'},
                height=500,
                showlegend=False
            )
            
            st.plotly_chart(fig_total, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                total_cat_display = total_cat.copy()
                total_cat_display.columns = ["Categoria", "Total de Profissionais", "Percentual (%)"]
                st.dataframe(total_cat_display, hide_index=True, use_container_width=True)

        st.markdown("#### Número de Fornecedores por Categoria")
        if not df_c.empty and "CATEGORIA" in df_c.columns and "EMPRESA" in df_c.columns:
            # Filtra NaN antes de agrupar
            df_c_forn = df_c[df_c["CATEGORIA"].notna() & (df_c["CATEGORIA"] != 'nan') & (df_c["CATEGORIA"] != 'None') & 
                             df_c["EMPRESA"].notna() & (df_c["EMPRESA"] != 'nan') & (df_c["EMPRESA"] != 'None')]
            # Conta fornecedores únicos por categoria
            fornecedores_por_cat = (
                df_c_forn.groupby("CATEGORIA")["EMPRESA"]
                .nunique()
                .reset_index()
                .sort_values("EMPRESA", ascending=False)
            )
            fornecedores_por_cat.columns = ["Categoria", "Fornecedores"]
            fornecedores_por_cat = fornecedores_por_cat[fornecedores_por_cat["Categoria"].notna()]
            
            # Calcula percentuais
            total_fornecedores_graf = fornecedores_por_cat["Fornecedores"].sum()
            fornecedores_por_cat["Percentual"] = (fornecedores_por_cat["Fornecedores"] / total_fornecedores_graf * 100).round(1)
            
            fig_fornecedores = px.bar(
                fornecedores_por_cat,
                x="Categoria",
                y="Fornecedores",
                labels={
                    "Categoria": "Categoria",
                    "Fornecedores": "Número de Fornecedores"
                },
                title="Fornecedores únicos por categoria",
                text=fornecedores_por_cat["Percentual"].apply(lambda x: f"{x}%"),
                color="Fornecedores",
                color_continuous_scale="Blues"
            )
            
            fig_fornecedores.update_traces(textposition='outside')
            fig_fornecedores.update_layout(
                xaxis={'categoryorder':'total descending'},
                height=500,
                showlegend=False
            )
            
            st.plotly_chart(fig_fornecedores, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                st.dataframe(fornecedores_por_cat, hide_index=True, use_container_width=True)

        st.markdown("#### (b) Total de profissionais por categoria em cada dia do evento")
        if not df_c.empty and "dia_label" in df_c.columns and "CATEGORIA" in df_c.columns and cpf_cols_cred:
            # Filtra apenas os dias do evento (qua a dom) e remove NaN
            dias_evento = ["Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            df_c_evento = df_c[
                df_c["dia_label"].isin(dias_evento) & 
                df_c["CATEGORIA"].notna() & 
                (df_c["CATEGORIA"] != 'nan') & 
                (df_c["CATEGORIA"] != 'None')
            ]
            
            if not df_c_evento.empty:
                total_cat_dia = (
                    df_c_evento.groupby(["dia_label", "CATEGORIA"])[cpf_cols_cred[0]]
                    .count()
                    .reset_index()
                )
                total_cat_dia.columns = ["dia_label", "CATEGORIA", "Total"]
                total_cat_dia = total_cat_dia[total_cat_dia["dia_label"].notna() & total_cat_dia["CATEGORIA"].notna()]

                # Ordena dias na sequência desejada
                ordem_dias = ["Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                total_cat_dia["dia_label"] = pd.Categorical(
                    total_cat_dia["dia_label"], categories=ordem_dias, ordered=True
                )
                total_cat_dia = total_cat_dia.sort_values("dia_label")

                # Calcula total por dia
                total_por_dia = total_cat_dia.groupby("dia_label")["Total"].sum().reset_index()
                total_por_dia.columns = ["dia_label", "Total_Dia"]
                
                # Calcula percentual de cada dia em relação ao total geral
                total_geral = total_por_dia["Total_Dia"].sum()
                total_por_dia["Percentual_Dia"] = (total_por_dia["Total_Dia"] / total_geral * 100).round(1)
                
                fig_total = px.bar(
                    total_cat_dia,
                    x="dia_label",
                    y="Total",
                    color="CATEGORIA",
                    barmode="stack",
                    labels={
                        "dia_label": "Dia da Semana",
                        "Total": "Total de profissionais",
                        "CATEGORIA": "Categoria"
                    },
                    title="Total de profissionais por categoria em cada dia do evento"
                )
                
                # Adiciona anotações com percentual no topo de cada barra
                for _, row in total_por_dia.iterrows():
                    fig_total.add_annotation(
                        x=row["dia_label"],
                        y=row["Total_Dia"],
                        text=f"{row['Percentual_Dia']:.1f}%<br>(n={row['Total_Dia']:.0f})",
                        showarrow=False,
                        yshift=15,
                        font=dict(size=11, color="white", family="Arial")
                    )
                
                fig_total.update_layout(height=500, yaxis_title="Percentual (%)")
                st.plotly_chart(fig_total, use_container_width=True)
                
                with st.expander("📊 Ver dados da tabela"):
                    # Cria tabela pivotada para melhor visualização
                    tabela_total_dia = total_cat_dia.pivot(index="dia_label", columns="CATEGORIA", values="Total").fillna(0)
                    tabela_total_dia = tabela_total_dia.astype(int)
                    st.dataframe(tabela_total_dia, use_container_width=True)
            else:
                st.info("Não há dados para os dias do evento (quarta a domingo).")

        st.markdown("#### Distribuição por dia da semana")
        if not df_c.empty and "dia_label" in df_c.columns and cpf_cols_cred:
            # Filtra NaN antes de agrupar
            df_c_dia = df_c[df_c["dia_label"].notna() & (df_c["dia_label"] != 'nan') & (df_c["dia_label"] != 'None')]
            profissionais_por_dia = (
                df_c_dia.groupby("dia_label")[cpf_cols_cred[0]]
                .count()
                .reset_index()
            )
            profissionais_por_dia.columns = ["dia_label", "Total"]
            profissionais_por_dia = profissionais_por_dia[profissionais_por_dia["dia_label"].notna()]
            
            # Ordena os dias
            ordem_todos_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            profissionais_por_dia["dia_label"] = pd.Categorical(
                profissionais_por_dia["dia_label"], categories=ordem_todos_dias, ordered=True
            )
            profissionais_por_dia = profissionais_por_dia.sort_values("dia_label")
            
            # Calcula percentuais
            total_dias = profissionais_por_dia["Total"].sum()
            profissionais_por_dia["Percentual"] = (profissionais_por_dia["Total"] / total_dias * 100).round(1)
            
            fig_dia = px.bar(
                profissionais_por_dia,
                x="dia_label",
                y="Total",
                labels={
                    "dia_label": "Dia da Semana",
                    "Total": "Total de profissionais"
                },
                title="Total de profissionais por dia da semana",
                text=profissionais_por_dia["Percentual"].apply(lambda x: f"{x}%")
            )
            fig_dia.update_traces(textposition='outside')
            st.plotly_chart(fig_dia, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                profissionais_por_dia_display = profissionais_por_dia[["dia_label", "Total", "Percentual"]].copy()
                profissionais_por_dia_display.columns = ["Dia da Semana", "Total de Profissionais", "Percentual (%)"]
                st.dataframe(profissionais_por_dia_display, hide_index=True, use_container_width=True)

        st.markdown("#### Amostra dos dados de credenciamento")
        
        # Seleciona as colunas principais para exibição
        colunas_exibir = []
        colunas_possiveis = ["DATA", "NOME", "CATEGORIA", "EMPRESA", "ETAPA", "EVENTO", "ORIGEM"]
        
        for col in colunas_possiveis:
            if col in df_c.columns:
                colunas_exibir.append(col)
        
        # Adiciona coluna CPF se existir
        if cpf_cols_cred:
            colunas_exibir.insert(1, cpf_cols_cred[0])
        
        # Remove valores 'nan', 'None' das colunas string para melhor visualização
        df_c_display = df_c[colunas_exibir].copy()
        for col in df_c_display.columns:
            if df_c_display[col].dtype == 'object':
                df_c_display[col] = df_c_display[col].replace(['nan', 'None'], '')
        
        st.dataframe(df_c_display, use_container_width=True)

if __name__ == "__main__":
    main()
