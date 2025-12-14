import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import json
import numpy as np
import unicodedata


def get_plotly_config(escala=2):
    """Retorna configuração otimizada para gráficos Plotly"""
    return {
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'grafico_arena_jockey',
            'height': 1080,
            'width': 1920,
            'scale': escala
        },
        'displayModeBar': True,
        'displaylogo': False
    }


def get_font_sizes(escala=2):
    """Retorna tamanhos de fonte base aumentados"""
    return {
        'title': 24,
        'axis': 18,
        'tick': 16,
        'legend': 16,
        'annotation': 16
    }


def remover_acentos(texto):
    """Remove acentos de uma string"""
    if pd.isna(texto):
        return texto
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])


def mapa_brasil(df_b, carregar_geojson_brasil_func, escala=2):
    """Exibe mapa do Brasil com distribuição de ingressos por estado"""
    st.markdown("#### 🗺️ Distribuição de Ingressos no Brasil")
    
    # Verifica se há coluna de país
    if "TDL Customer Country" in df_b.columns:
        # Filtra apenas Brasil
        df_brasil = df_b[(df_b["TDL Customer Country"] == "Brasil") | (df_b["TDL Customer Country"] == "Brazil")].copy()
        
        if not df_brasil.empty and "uf_google" in df_brasil.columns:
            # Agrupa por UF
            por_estado = (
                df_brasil.groupby("uf_google")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
            )
            por_estado = por_estado[por_estado["uf_google"].notna()]
            por_estado.columns = ["UF", "Ingressos"]
            
            if not por_estado.empty:
                # Carrega GeoJSON do Brasil
                brasil_gdf = carregar_geojson_brasil_func()
                
                if brasil_gdf is not None:
                    # Normaliza nomes das UFs
                    por_estado["UF"] = por_estado["UF"].str.upper().str.strip()
                    
                    # Mapeamento de nomes de estados para siglas (caso necessário)
                    mapa_estados = {
                        "ACRE": "AC", "ALAGOAS": "AL", "AMAPÁ": "AP", "AMAZONAS": "AM",
                        "BAHIA": "BA", "CEARÁ": "CE", "DISTRITO FEDERAL": "DF", "ESPÍRITO SANTO": "ES",
                        "GOIÁS": "GO", "MARANHÃO": "MA", "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS",
                        "MINAS GERAIS": "MG", "PARÁ": "PA", "PARAÍBA": "PB", "PARANÁ": "PR",
                        "PERNAMBUCO": "PE", "PIAUÍ": "PI", "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN",
                        "RIO GRANDE DO SUL": "RS", "RONDÔNIA": "RO", "RORAIMA": "RR", "SANTA CATARINA": "SC",
                        "SÃO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO"
                    }
                    
                    # Se a coluna tem nomes completos, converte para siglas
                    if por_estado["UF"].str.len().max() > 2:
                        por_estado["UF"] = por_estado["UF"].map(mapa_estados).fillna(por_estado["UF"])
                    
                    # Verifica qual campo usar no GeoJSON
                    if "sigla" in brasil_gdf.columns:
                        merge_col = "sigla"
                    elif "UF" in brasil_gdf.columns:
                        merge_col = "UF"
                    elif "name" in brasil_gdf.columns:
                        merge_col = "name"
                        # Cria coluna de sigla a partir do nome
                        brasil_gdf["sigla"] = brasil_gdf["name"].map({v: k for k, v in {
                            "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
                            "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
                            "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
                            "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
                            "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
                            "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
                            "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"
                        }.items()})
                        merge_col = "sigla"
                    else:
                        merge_col = brasil_gdf.columns[0]
                    
                    # Merge dos dados
                    brasil_com_dados = brasil_gdf.merge(
                        por_estado,
                        left_on=merge_col,
                        right_on="UF",
                        how="left"
                    )
                    brasil_com_dados["Ingressos"] = brasil_com_dados["Ingressos"].fillna(0)
                    
                    # Remove colunas datetime antes de converter para JSON
                    brasil_para_mapa = brasil_com_dados.copy()
                    for col in brasil_para_mapa.columns:
                        if pd.api.types.is_datetime64_any_dtype(brasil_para_mapa[col]):
                            brasil_para_mapa = brasil_para_mapa.drop(columns=[col])
                    
                    # Normaliza os valores usando raiz quadrada para melhor distribuição visual
                    brasil_para_mapa["Ingressos_Normalizado"] = np.sqrt(brasil_para_mapa["Ingressos"])
                    
                    # Converte para GeoJSON
                    geojson_brasil = json.loads(brasil_para_mapa.to_json())
                    
                    # Cria o mapa
                    fig_brasil = px.choropleth_mapbox(
                        brasil_para_mapa,
                        geojson=geojson_brasil,
                        locations=brasil_com_dados.index,
                        color="Ingressos_Normalizado",
                        hover_name=merge_col,
                        hover_data={
                            "Ingressos": ":,.0f",
                            "Ingressos_Normalizado": False
                        },
                        color_continuous_scale="Viridis",
                        mapbox_style="open-street-map",
                        center={"lat": -14.235, "lon": -51.925},
                        zoom=3,
                        labels={
                            "Ingressos_Normalizado": "Distribuição (normalizado)",
                            "Ingressos": "Total de Ingressos"
                        },
                        title="Distribuição de ingressos vendidos por estado (escala normalizada)"
                    )
                    
                    fonts = get_font_sizes(escala)
                    fig_brasil.update_layout(
                        height=600,
                        margin={"r":0,"t":40,"l":0,"b":0},
                        title_font_size=fonts['title'],
                        font_size=fonts['tick']
                    )
                    
                    st.plotly_chart(fig_brasil, use_container_width=True, config=get_plotly_config(escala))
                    
                    # Tabela com dados
                    with st.expander("📊 Ver dados por estado"):
                        por_estado_display = por_estado.sort_values("Ingressos", ascending=False)
                        total_brasil = por_estado_display["Ingressos"].sum()
                        por_estado_display["Percentual (%)"] = (por_estado_display["Ingressos"] / total_brasil * 100).round(1)
                        st.dataframe(por_estado_display, hide_index=True, use_container_width=True)
                else:
                    st.info("Não foi possível carregar o mapa do Brasil.")
            else:
                st.info("Não há dados de UF disponíveis para criar o mapa do Brasil.")
        elif not df_brasil.empty:
            # Se não tem UF, mostra ao menos os países
            st.info("Coluna 'uf_google' não encontrada na base de dados. Adicione informações de estado/UF para visualizar o mapa do Brasil.")
            
            # Mostra distribuição por país como alternativa
            por_pais = (
                df_b.groupby("TDL Customer Country")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
            )
            por_pais = por_pais[por_pais["TDL Customer Country"].notna()]
            por_pais.columns = ["País", "Ingressos"]
            
            total_pais = por_pais["Ingressos"].sum()
            por_pais["Percentual (%)"] = (por_pais["Ingressos"] / total_pais * 100).round(1)
            
            fig_pais = px.bar(
                por_pais.head(10),
                x="País",
                y="Ingressos",
                text=por_pais.head(10)["Percentual (%)"].apply(lambda x: f"{x}%"),
                title="Top 10 Países - Ingressos vendidos",
                color="Ingressos",
                color_continuous_scale="Blues"
            )
            fonts = get_font_sizes(escala)
            fig_pais.update_traces(textposition='outside', textfont_size=fonts['annotation'])
            fig_pais.update_layout(
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick']
            )
            st.plotly_chart(fig_pais, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver todos os países"):
                st.dataframe(por_pais, hide_index=True, use_container_width=True)


def mapa_estado_rj(df_b, carregar_geojson_municipios_rj_func, escala=2):
    """Exibe mapa do Estado do Rio de Janeiro com distribuição por município"""
    st.markdown("#### 🗺️ Distribuição de Ingressos no Estado do Rio de Janeiro")
    
    if "uf_google" in df_b.columns and "cidade_google_norm" in df_b.columns:
        # Filtra apenas RJ
        df_rj = df_b[df_b["uf_google"].str.upper() == "RJ"].copy()
        
        if not df_rj.empty:
            # Agrupa por cidade
            por_cidade = (
                df_rj.groupby("cidade_google_norm")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
            )
            por_cidade = por_cidade[por_cidade["cidade_google_norm"].notna()]
            por_cidade.columns = ["Cidade", "Ingressos"]
            
            if not por_cidade.empty:
                # Carrega GeoJSON dos municípios do RJ
                rj_gdf = carregar_geojson_municipios_rj_func()
                
                if rj_gdf is not None:
                    # Normaliza nomes das cidades (remove acentos)
                    por_cidade["Cidade_Norm"] = por_cidade["Cidade"].apply(remover_acentos).str.upper().str.strip()
                    
                    # Identifica o campo de nome no GeoJSON
                    nome_field = None
                    for field in ["name", "nome", "NM_MUN", "NOME_MUN", "municipio"]:
                        if field in rj_gdf.columns:
                            nome_field = field
                            break
                    
                    if nome_field:
                        # Normaliza nomes do GeoJSON (remove acentos)
                        rj_gdf["nome_normalizado"] = rj_gdf[nome_field].apply(remover_acentos).str.upper().str.strip()
                        
                        # Merge dos dados
                        rj_com_dados = rj_gdf.merge(
                            por_cidade,
                            left_on="nome_normalizado",
                            right_on="Cidade_Norm",
                            how="left"
                        )
                        rj_com_dados["Ingressos"] = rj_com_dados["Ingressos"].fillna(0)
                        
                        # Remove colunas datetime
                        rj_para_mapa = rj_com_dados.copy()
                        for col in rj_para_mapa.columns:
                            if pd.api.types.is_datetime64_any_dtype(rj_para_mapa[col]):
                                rj_para_mapa = rj_para_mapa.drop(columns=[col])
                        
                        # Normaliza valores para melhor visualização
                        rj_para_mapa["Ingressos_Normalizado"] = np.sqrt(rj_para_mapa["Ingressos"])
                        
                        # Converte para GeoJSON
                        geojson_rj = json.loads(rj_para_mapa.to_json())
                        
                        # Cria o mapa
                        fig_rj = px.choropleth_mapbox(
                            rj_para_mapa,
                            geojson=geojson_rj,
                            locations=rj_para_mapa.index,
                            color="Ingressos_Normalizado",
                            hover_name="nome_normalizado",
                            hover_data={
                                "Ingressos": ":,.0f",
                                "Ingressos_Normalizado": False
                            },
                            color_continuous_scale="YlOrRd",
                            mapbox_style="open-street-map",
                            center={"lat": -22.5, "lon": -42.8},
                            zoom=7.5,
                            labels={
                                "Ingressos_Normalizado": "Distribuição (normalizado)",
                                "Ingressos": "Total de Ingressos"
                            },
                            title="Distribuição de ingressos por município no Estado do Rio de Janeiro"
                        )
                        
                        fonts = get_font_sizes(escala)
                        fig_rj.update_layout(
                            height=600,
                            margin={"r":0,"t":40,"l":0,"b":0},
                            title_font_size=fonts['title'],
                            font_size=fonts['tick']
                        )
                        
                        st.plotly_chart(fig_rj, use_container_width=True, config=get_plotly_config(escala))
                        
                        # Tabela com dados
                        with st.expander("📊 Ver dados por município"):
                            por_cidade_display = por_cidade.sort_values("Ingressos", ascending=False)
                            total_rj = por_cidade_display["Ingressos"].sum()
                            por_cidade_display["Percentual (%)"] = (por_cidade_display["Ingressos"] / total_rj * 100).round(1)
                            st.dataframe(por_cidade_display, hide_index=True, use_container_width=True)
                    else:
                        st.warning("O GeoJSON dos municípios não contém um campo de nome reconhecido.")
                else:
                    st.info("Não foi possível carregar o mapa dos municípios do RJ.")
            else:
                st.info("Não há dados de cidades do RJ disponíveis.")
        else:
            st.info("Não há dados de ingressos para o estado do Rio de Janeiro.")
    else:
        st.info("Colunas 'uf_google' e/ou 'cidade_google_norm' não encontradas para criar o mapa do RJ.")


def mapa_ras_capital(df_b, carregar_geojson_ras_func, escala=2):
    """Exibe mapa das Regiões Administrativas da capital do RJ"""
    st.markdown("#### Mapa Oficial - Ingressos por Região Administrativa")
    if not df_b.empty and "RA" in df_b.columns:
        # Carrega os limites oficiais das RAs
        ra_gdf = carregar_geojson_ras_func()
        
        if ra_gdf is not None:
            # Agrupa ingressos por RA
            por_ra_mapa = (
                df_b.groupby("RA")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
            )
            por_ra_mapa = por_ra_mapa[por_ra_mapa["RA"].notna()]
            
            # Mapeamento direto das RAs
            if "nomera" in ra_gdf.columns:
                # Merge direto com os dados
                ra_com_dados = ra_gdf.merge(
                    por_ra_mapa,
                    left_on="nomera",
                    right_on="RA",
                    how="left"
                )
                
                # Se não houver matches, tenta normalizar os nomes
                if ra_com_dados["TDL Sum Tickets (B+S-A)"].isna().all():
                    
                    # Normaliza os nomes das RAs na base
                    por_ra_mapa["RA_norm"] = por_ra_mapa["RA"].str.upper().str.strip()
                    
                    # Normaliza os nomes no GeoJSON
                    ra_gdf["nomera_norm"] = ra_gdf["nomera"].str.upper().str.strip()
                    
                    # Tenta merge com nomes normalizados
                    ra_com_dados = ra_gdf.merge(
                        por_ra_mapa,
                        left_on="nomera_norm",
                        right_on="RA_norm",
                        how="left"
                    )
                
                # Preenche valores ausentes com 0
                ra_com_dados["TDL Sum Tickets (B+S-A)"] = ra_com_dados["TDL Sum Tickets (B+S-A)"].fillna(0)
                
                # Remove RAs sem dados para melhor visualização
                ra_com_dados_filtrado = ra_com_dados[ra_com_dados["TDL Sum Tickets (B+S-A)"] > 0]
                
                if not ra_com_dados_filtrado.empty:
                    # Remove colunas datetime
                    ra_para_mapa = ra_com_dados.copy()
                    for col in ra_para_mapa.columns:
                        if pd.api.types.is_datetime64_any_dtype(ra_para_mapa[col]):
                            ra_para_mapa = ra_para_mapa.drop(columns=[col])
                    
                    # Normaliza valores usando raiz quadrada para melhor distribuição visual
                    ra_para_mapa["Ingressos_Normalizado"] = np.sqrt(ra_para_mapa["TDL Sum Tickets (B+S-A)"])
                    
                    # Converte para GeoJSON
                    geojson_data = json.loads(ra_para_mapa.to_json())
                    
                    # Cria o mapa choropleth
                    fig_mapa_ra_oficial = px.choropleth_mapbox(
                        ra_para_mapa,
                        geojson=geojson_data,
                        locations=ra_para_mapa.index,
                        color="Ingressos_Normalizado",
                        hover_name="nomera",
                        hover_data={
                            "TDL Sum Tickets (B+S-A)": ":,.0f",
                            "Ingressos_Normalizado": False
                        },
                        color_continuous_scale="YlOrRd",
                        mapbox_style="open-street-map",
                        center={"lat": -22.9068, "lon": -43.1729},
                        zoom=9.5,
                        labels={
                            "Ingressos_Normalizado": "Distribuição (normalizado)",
                            "TDL Sum Tickets (B+S-A)": "Ingressos"
                        },
                        title="Distribuição de ingressos por Região Administrativa (escala normalizada)"
                    )
                    
                    fonts = get_font_sizes(escala)
                    fig_mapa_ra_oficial.update_layout(
                        height=600,
                        margin={"r":0,"t":40,"l":0,"b":0},
                        title_font_size=fonts['title'],
                        font_size=fonts['tick']
                    )
                    
                    st.plotly_chart(fig_mapa_ra_oficial, use_container_width=True, config=get_plotly_config(escala))
                    
                    # Mostra tabela com dados
                    with st.expander("📊 Ver dados detalhados por RA"):
                        tabela_ra = por_ra_mapa.sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
                        tabela_ra_display = tabela_ra[["RA", "TDL Sum Tickets (B+S-A)"]].copy()
                        tabela_ra_display.columns = ["Região Administrativa", "Ingressos"]
                        
                        # Adiciona percentual
                        total_ra_tabela = tabela_ra_display["Ingressos"].sum()
                        tabela_ra_display["Percentual (%)"] = (tabela_ra_display["Ingressos"] / total_ra_tabela * 100).round(1)
                        
                        st.dataframe(tabela_ra_display, hide_index=True, use_container_width=True)
                else:
                    st.warning("Não foi possível mapear as RAs da base de dados com as RAs oficiais. Verifique os nomes na seção de debug acima.")
            else:
                st.warning("O GeoJSON das RAs não contém o campo esperado 'nomera'.")
        else:
            st.info("Não foi possível carregar os limites oficiais das Regiões Administrativas.")


def grafico_bairros_por_tipo_ingresso(df_b, escala=2):
    """Exibe gráfico de bairros por tipo de ingresso"""
    st.markdown("#### Bairros por Tipo de Ingresso")
    bairro_col = "bairro_google_norm"
    tipo_ingresso_col = "TDL Price Category"
    
    if not df_b.empty and bairro_col in df_b.columns and tipo_ingresso_col in df_b.columns:
        # Agrupa por bairro e tipo de ingresso
        bairro_tipo = (
            df_b.groupby([bairro_col, tipo_ingresso_col])["TDL Sum Tickets (B+S-A)"]
            .sum()
            .reset_index()
        )
        bairro_tipo = bairro_tipo[bairro_tipo[bairro_col].notna() & bairro_tipo[tipo_ingresso_col].notna()]
        
        # Filtra apenas os top 15 bairros por volume total
        top_bairros_nomes = (
            df_b.groupby(bairro_col)["TDL Sum Tickets (B+S-A)"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .index.tolist()
        )
        
        bairro_tipo_top = bairro_tipo[bairro_tipo[bairro_col].isin(top_bairros_nomes)]
        
        if not bairro_tipo_top.empty:
            # Calcula percentuais por bairro
            total_por_bairro = bairro_tipo_top.groupby(bairro_col)["TDL Sum Tickets (B+S-A)"].transform('sum')
            bairro_tipo_top["Percentual"] = (bairro_tipo_top["TDL Sum Tickets (B+S-A)"] / total_por_bairro * 100).round(1)
            
            fig_bairro_tipo = px.bar(
                bairro_tipo_top,
                x=bairro_col,
                y="TDL Sum Tickets (B+S-A)",
                color=tipo_ingresso_col,
                barmode="stack",
                labels={
                    bairro_col: "Bairro",
                    "TDL Sum Tickets (B+S-A)": "Ingressos",
                    tipo_ingresso_col: "Tipo de Ingresso"
                },
                title="Top 15 Bairros por Tipo de Ingresso",
                text=bairro_tipo_top["Percentual"].apply(lambda x: f"{x}%")
            )
            
            fonts = get_font_sizes(escala)
            fig_bairro_tipo.update_traces(textposition='inside', textfont_size=fonts['annotation'])
            fig_bairro_tipo.update_layout(
                xaxis={'categoryorder':'total descending'},
                height=500,
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick'],
                legend_font_size=fonts['legend']
            )
            
            st.plotly_chart(fig_bairro_tipo, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver dados da tabela"):
                # Cria tabela pivotada para melhor visualização
                tabela_bairro_tipo = bairro_tipo_top.pivot(index=bairro_col, columns=tipo_ingresso_col, values="TDL Sum Tickets (B+S-A)").fillna(0)
                tabela_bairro_tipo = tabela_bairro_tipo.astype(int)
                # Adiciona total por bairro
                tabela_bairro_tipo['Total'] = tabela_bairro_tipo.sum(axis=1)
                tabela_bairro_tipo = tabela_bairro_tipo.sort_values('Total', ascending=False)
                st.dataframe(tabela_bairro_tipo, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir o gráfico de bairros por tipo de ingresso.")
