import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


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
    """Retorna tamanhos de fonte base aumentados proporcionalmente à escala"""
    # Multiplica diretamente pela escala para fontes maiores na exportação
    return {
        'title': int(20 * escala),
        'axis': int(16 * escala),
        'tick': int(14 * escala),
        'legend': int(14 * escala),
        'annotation': int(14 * escala)
    }



def analise_clusters_clientes(df_b, escala=2):
    """
    Realiza análise de cluster dos clientes baseada em comportamento de compra,
    valor de ingressos e tipos de ingresso.
    """
    st.markdown("### 🎯 Análise de Clusters de Clientes")
    st.markdown("Segmentação de clientes baseada em comportamento de compra, valor gasto e preferências")
    
    if df_b.empty or "TDL Customer CPF" not in df_b.columns:
        st.info("Não há dados disponíveis para análise de clusters.")
        return
    
    # Filtra eventos excluídos da análise
    if "TDL Event" in df_b.columns:
        df_b = df_b[df_b["TDL Event"] != "O BAILE DA MÚSICA BRASILEIRA COM CORDAO DO BOITATA E CONVIDADOS"].copy()
    
    # Prepara os dados
    df_analise = df_b[df_b["TDL Customer CPF"].notna()].copy()
    
    # Identifica ingressos solidários
    if "TDL Ticket Type" in df_analise.columns:
        mask_solidario = df_analise["TDL Ticket Type"].str.upper().str.contains("SOLIDÁRIO", na=False)
    else:
        mask_solidario = pd.Series([False] * len(df_analise), index=df_analise.index)
    
    # Agrupa por cliente
    features_clientes = df_analise.groupby("TDL Customer CPF").agg({
        "TDL Sum Tickets (B+S-A)": "sum",  # Total de ingressos comprados
        "TDL Sum Ticket Net Price (B+S-A)": ["sum", "mean"],  # Valor total e médio gasto
        "TDL Event": "nunique"  # Número de eventos diferentes
    }).reset_index()
    
    # Renomeia colunas
    features_clientes.columns = ["CPF", "Total_Ingressos", "Valor_Total", "Ticket_Medio", "Num_Eventos"]
    
    # Adiciona informação se comprou ingresso solidário
    if "TDL Ticket Type" in df_analise.columns:
        solidarios = df_analise[mask_solidario].groupby("TDL Customer CPF")["TDL Sum Tickets (B+S-A)"].sum().reset_index(name="Ingressos_Solidarios")
        features_clientes = features_clientes.merge(solidarios, left_on="CPF", right_on="TDL Customer CPF", how="left")
        features_clientes["Ingressos_Solidarios"] = features_clientes["Ingressos_Solidarios"].fillna(0)
        if "TDL Customer CPF" in features_clientes.columns:
            features_clientes = features_clientes.drop("TDL Customer CPF", axis=1)
    else:
        features_clientes["Ingressos_Solidarios"] = 0
    
    # Remove outliers extremos (top 1% em valor total)
    threshold_valor = features_clientes["Valor_Total"].quantile(0.99)
    features_clientes_filtered = features_clientes[features_clientes["Valor_Total"] <= threshold_valor].copy()
    
    if len(features_clientes_filtered) < 10:
        st.warning("Dados insuficientes para análise de clusters.")
        return
    
    # Seleciona features para clustering
    X = features_clientes_filtered[["Total_Ingressos", "Valor_Total", "Ticket_Medio", "Num_Eventos", "Ingressos_Solidarios"]].copy()
    
    # Normaliza os dados
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determina número ótimo de clusters usando método do cotovelo
    st.markdown("#### 📈 Determinação do Número Ótimo de Clusters")
    
    col_cotovelo, col_info = st.columns([2, 1])
    
    with col_cotovelo:
        inertias = []
        K_range = range(2, min(11, len(features_clientes_filtered) // 10))
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(X_scaled)
            inertias.append(kmeans.inertia_)
        
        fig_cotovelo = go.Figure()
        fig_cotovelo.add_trace(go.Scatter(
            x=list(K_range),
            y=inertias,
            mode='lines+markers',
            marker=dict(size=10, color='blue'),
            line=dict(width=2)
        ))
        
        fonts = get_font_sizes(escala)
        fig_cotovelo.update_layout(
            title="Método do Cotovelo para Determinar K Ótimo",
            xaxis_title="Número de Clusters (K)",
            yaxis_title="Inércia (Soma dos Quadrados Intra-Cluster)",
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            height=400
        )
        
        st.plotly_chart(fig_cotovelo, use_container_width=True, config=get_plotly_config(escala))
    
    with col_info:
        st.markdown("#### ℹ️ Sobre o Método")
        st.write("O **método do cotovelo** ajuda a identificar o número ideal de clusters.")
        st.write("Procure pelo 'cotovelo' no gráfico - o ponto onde a taxa de redução da inércia diminui significativamente.")
    
    # Permite ao usuário escolher o número de clusters
    n_clusters = st.slider(
        "Selecione o número de clusters:",
        min_value=2,
        max_value=min(10, len(features_clientes_filtered) // 10),
        value=4,
        help="Baseie-se no gráfico do cotovelo acima para escolher o melhor valor"
    )
    
    # Aplica K-means com o número escolhido
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    features_clientes_filtered["Cluster"] = kmeans.fit_predict(X_scaled)
    
    # Aplica PCA para visualização 2D
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    features_clientes_filtered["PC1"] = X_pca[:, 0]
    features_clientes_filtered["PC2"] = X_pca[:, 1]
    
    # Visualização dos clusters
    st.markdown("---")
    st.markdown("#### 🎨 Visualização dos Clusters")
    
    col_viz1, col_viz2 = st.columns(2)
    
    fonts = get_font_sizes(escala)
    
    with col_viz1:
        # Gráfico PCA
        fig_pca = px.scatter(
            features_clientes_filtered,
            x="PC1",
            y="PC2",
            color="Cluster",
            title="Clusters de Clientes (Visualização PCA)",
            labels={"PC1": "Componente Principal 1", "PC2": "Componente Principal 2"},
            color_continuous_scale="Viridis",
            hover_data=["Total_Ingressos", "Valor_Total", "Ticket_Medio"]
        )
        
        fig_pca.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            height=500
        )
        
        st.plotly_chart(fig_pca, use_container_width=True, config=get_plotly_config(escala))
    
    with col_viz2:
        # Gráfico Valor Total vs Total de Ingressos
        fig_scatter = px.scatter(
            features_clientes_filtered,
            x="Total_Ingressos",
            y="Valor_Total",
            color="Cluster",
            title="Valor Total vs Quantidade de Ingressos por Cluster",
            labels={"Total_Ingressos": "Total de Ingressos", "Valor_Total": "Valor Total (R$)"},
            color_continuous_scale="Viridis",
            hover_data=["Ticket_Medio", "Num_Eventos"]
        )
        
        fig_scatter.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            height=500
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True, config=get_plotly_config(escala))
    
    # Análise detalhada de cada cluster
    st.markdown("---")
    st.markdown("#### 📊 Características dos Clusters")
    
    # Calcula estatísticas por cluster
    cluster_stats = features_clientes_filtered.groupby("Cluster").agg({
        "CPF": "count",
        "Total_Ingressos": ["mean", "median", "sum"],
        "Valor_Total": ["mean", "median", "sum"],
        "Ticket_Medio": ["mean", "median"],
        "Num_Eventos": ["mean", "median"],
        "Ingressos_Solidarios": ["sum", "mean"]
    }).round(2)
    
    # Renomeia colunas do MultiIndex
    cluster_stats.columns = [
        "Quantidade_Clientes",
        "Media_Ingressos", "Mediana_Ingressos", "Total_Ingressos_Cluster",
        "Media_Valor_Total", "Mediana_Valor_Total", "Total_Valor_Cluster",
        "Media_Ticket_Medio", "Mediana_Ticket_Medio",
        "Media_Num_Eventos", "Mediana_Num_Eventos",
        "Total_Solidarios", "Media_Solidarios_por_Cliente"
    ]
    
    cluster_stats = cluster_stats.reset_index()
    
    # Cria nomes descritivos para os clusters baseados nas características
    def nomear_cluster(row):
        if row["Media_Valor_Total"] > cluster_stats["Media_Valor_Total"].quantile(0.75):
            if row["Media_Num_Eventos"] > 1.5:
                return f"Cluster {row['Cluster']}: VIPs Recorrentes"
            else:
                return f"Cluster {row['Cluster']}: Alto Valor"
        elif row["Media_Ingressos"] > cluster_stats["Media_Ingressos"].quantile(0.75):
            return f"Cluster {row['Cluster']}: Compradores em Grupo"
        elif row["Media_Solidarios_por_Cliente"] > 0.5:
            return f"Cluster {row['Cluster']}: Solidários"
        elif row["Media_Num_Eventos"] > cluster_stats["Media_Num_Eventos"].median():
            return f"Cluster {row['Cluster']}: Fãs Frequentes"
        else:
            return f"Cluster {row['Cluster']}: Ocasionais"
    
    cluster_stats["Nome_Cluster"] = cluster_stats.apply(nomear_cluster, axis=1)
    
    # Exibe cards com informações de cada cluster
    num_cols = min(n_clusters, 3)
    clusters_rows = [cluster_stats.iloc[i:i+num_cols] for i in range(0, len(cluster_stats), num_cols)]
    
    for row_clusters in clusters_rows:
        cols = st.columns(len(row_clusters))
        for idx, (_, cluster_info) in enumerate(row_clusters.iterrows()):
            with cols[idx]:
                st.markdown(f"### {cluster_info['Nome_Cluster']}")
                st.metric("Clientes", f"{int(cluster_info['Quantidade_Clientes']):,}".replace(",", "."))
                st.metric("Ingressos Médios", f"{cluster_info['Media_Ingressos']:.1f}")
                st.metric("Ticket Médio", f"R$ {cluster_info['Media_Ticket_Medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                st.metric("Eventos Médios", f"{cluster_info['Media_Num_Eventos']:.1f}")
                
                if cluster_info['Total_Solidarios'] > 0:
                    st.write(f"🤝 **Solidários:** {int(cluster_info['Total_Solidarios'])} ingressos")
    
    # Tabela detalhada
    st.markdown("---")
    st.markdown("#### 📋 Tabela Detalhada dos Clusters")
    
    # Formata a tabela para exibição
    cluster_display = cluster_stats.copy()
    cluster_display["Quantidade_Clientes"] = cluster_display["Quantidade_Clientes"].astype(int)
    cluster_display["Total_Ingressos_Cluster"] = cluster_display["Total_Ingressos_Cluster"].astype(int)
    cluster_display["Total_Solidarios"] = cluster_display["Total_Solidarios"].astype(int)
    
    # Seleciona colunas principais
    cols_exibir = [
        "Nome_Cluster", "Quantidade_Clientes", "Media_Ingressos",
        "Media_Ticket_Medio", "Media_Num_Eventos", "Total_Solidarios"
    ]
    
    cluster_display_final = cluster_display[cols_exibir].copy()
    cluster_display_final.columns = [
        "Cluster", "Clientes", "Ingressos Médios",
        "Ticket Médio (R$)", "Eventos Médios", "Ingressos Solidários"
    ]
    
    st.dataframe(cluster_display_final, hide_index=True, use_container_width=True)
    
    # Gráfico de barras comparativo
    st.markdown("---")
    st.markdown("#### 📊 Comparação entre Clusters")
    
    fonts = get_font_sizes(escala)
    
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        # Comparação de valor total por cluster
        fig_valor = px.bar(
            cluster_stats,
            x="Nome_Cluster",
            y="Total_Valor_Cluster",
            title="Receita Total por Cluster",
            labels={"Nome_Cluster": "Cluster", "Total_Valor_Cluster": "Receita Total (R$)"},
            color="Total_Valor_Cluster",
            color_continuous_scale="Blues"
        )
        
        fig_valor.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            showlegend=False,
            height=400,
            coloraxis_colorbar=dict(
                tickfont=dict(size=fonts['tick'])
            )
        )
        
        st.plotly_chart(fig_valor, use_container_width=True, config=get_plotly_config(escala))
    
    with col_comp2:
        # Comparação de quantidade de clientes
        fig_qtd = px.bar(
            cluster_stats,
            x="Nome_Cluster",
            y="Quantidade_Clientes",
            title="Quantidade de Clientes por Cluster",
            labels={"Nome_Cluster": "Cluster", "Quantidade_Clientes": "Número de Clientes"},
            color="Quantidade_Clientes",
            color_continuous_scale="Greens"
        )
        
        fig_qtd.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            showlegend=False,
            height=400,
            coloraxis_colorbar=dict(
                tickfont=dict(size=fonts['tick'])
            )
        )
        
        st.plotly_chart(fig_qtd, use_container_width=True, config=get_plotly_config(escala))
    
    # Gráfico de radar para comparar perfis
    st.markdown("---")
    st.markdown("#### 🕸️ Perfil dos Clusters (Gráfico Radar)")
    
    fonts = get_font_sizes(escala)
    
    # Normaliza as métricas para o gráfico radar (0-100)
    metricas_radar = cluster_stats[["Nome_Cluster", "Media_Ingressos", "Media_Ticket_Medio", "Media_Num_Eventos"]].copy()
    
    for col in ["Media_Ingressos", "Media_Ticket_Medio", "Media_Num_Eventos"]:
        max_val = metricas_radar[col].max()
        if max_val > 0:
            metricas_radar[f"{col}_norm"] = (metricas_radar[col] / max_val * 100).round(1)
        else:
            metricas_radar[f"{col}_norm"] = 0
    
    fig_radar = go.Figure()
    
    categorias = ["Ingressos Médios", "Ticket Médio", "Eventos Médios"]
    
    for _, row in metricas_radar.iterrows():
        valores = [
            row["Media_Ingressos_norm"],
            row["Media_Ticket_Medio_norm"],
            row["Media_Num_Eventos_norm"]
        ]
        
        fig_radar.add_trace(go.Scatterpolar(
            r=valores,
            theta=categorias,
            fill='toself',
            name=row["Nome_Cluster"]
        ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        title="Comparação de Perfis dos Clusters (Normalizado 0-100)",
        title_font_size=fonts['title'],
        legend_font_size=fonts['legend'],
        height=500
    )
    
    st.plotly_chart(fig_radar, use_container_width=True, config=get_plotly_config(escala))
    
    # Exporta dados dos clusters
    st.markdown("---")
    features_clientes_filtered["Nome_Cluster"] = features_clientes_filtered["Cluster"].map(
        dict(zip(cluster_stats["Cluster"], cluster_stats["Nome_Cluster"]))
    )
    
    csv_clusters = features_clientes_filtered[["CPF", "Nome_Cluster", "Total_Ingressos", "Valor_Total", "Ticket_Medio", "Num_Eventos"]].to_csv(index=False, encoding='utf-8-sig')
    
    st.download_button(
        label="📥 Download Análise de Clusters (CSV)",
        data=csv_clusters,
        file_name="analise_clusters_clientes.csv",
        mime="text/csv",
        use_container_width=True
    )


def analise_clusters_geograficos(df_b, escala=2):
    """
    Realiza análise de cluster baseada em localização geográfica (bairro e cidade).
    Identifica regiões de maior concentração e padrões geográficos de consumo.
    """
    st.markdown("### 📍 Análise de Clusters Geográficos")
    st.markdown("Segmentação por localização: identifica regiões com maior concentração de público")
    
    if df_b.empty:
        st.info("Não há dados disponíveis para análise.")
        return
    
    # Filtra eventos excluídos da análise
    if "TDL Event" in df_b.columns:
        df_b = df_b[df_b["TDL Event"] != "O BAILE DA MÚSICA BRASILEIRA COM CORDAO DO BOITATA E CONVIDADOS"].copy()
    
    # Verifica disponibilidade dos campos geográficos
    tem_bairro = "bairro_google_norm" in df_b.columns or "bairro_google" in df_b.columns
    tem_cidade = "cidade_google" in df_b.columns
    
    if not tem_bairro and not tem_cidade:
        st.warning("Dados geográficos (bairro_google/cidade_google) não disponíveis.")
        return
    
    # Prepara campo de bairro
    campo_bairro = "bairro_google_norm" if "bairro_google_norm" in df_b.columns else "bairro_google"
    
    # Opção de análise
    tipo_analise = st.radio(
        "Selecione o tipo de análise:",
        ["Bairros (Rio de Janeiro)", "Cidades (Estado/País)"],
        horizontal=True
    )
    
    if tipo_analise == "Bairros (Rio de Janeiro)" and tem_bairro:
        analise_clusters_bairros(df_b, campo_bairro, escala)
    elif tipo_analise == "Cidades (Estado/País)" and tem_cidade:
        analise_clusters_cidades(df_b, escala)
    else:
        st.warning(f"Dados não disponíveis para {tipo_analise}.")


def analise_clusters_bairros(df_b, campo_bairro, escala=2):
    """Análise de clusters por bairros do Rio de Janeiro"""
    st.markdown("#### 🏘️ Análise por Bairros")
    
    # Filtra apenas dados com bairro informado
    df_bairros = df_b[df_b[campo_bairro].notna()].copy()
    
    if df_bairros.empty:
        st.info("Não há dados de bairros disponíveis.")
        return
    
    # Agrupa por bairro
    bairros_stats = df_bairros.groupby(campo_bairro).agg({
        "TDL Sum Tickets (B+S-A)": "sum",
        "TDL Sum Ticket Net Price (B+S-A)": "sum",
        "TDL Customer CPF": "nunique",
        "TDL Event": "nunique"
    }).reset_index()
    
    bairros_stats.columns = ["Bairro", "Total_Ingressos", "Receita_Total", "Clientes_Unicos", "Eventos_Diferentes"]
    
    # Calcula métricas derivadas
    bairros_stats["Ticket_Medio"] = (bairros_stats["Receita_Total"] / bairros_stats["Total_Ingressos"]).round(2)
    bairros_stats["Ingressos_por_Cliente"] = (bairros_stats["Total_Ingressos"] / bairros_stats["Clientes_Unicos"]).round(2)
    
    # Remove bairros com poucos dados (menos de 5 ingressos)
    bairros_stats = bairros_stats[bairros_stats["Total_Ingressos"] >= 5].copy()
    
    # Remove valores inválidos (NaN, inf, -inf)
    bairros_stats = bairros_stats.replace([np.inf, -np.inf], np.nan)
    bairros_stats = bairros_stats.dropna(subset=["Ticket_Medio", "Ingressos_por_Cliente"])
    
    if len(bairros_stats) < 5:
        st.warning("Dados insuficientes para análise de clusters de bairros.")
        return
    
    # Prepara dados para clustering
    X = bairros_stats[["Total_Ingressos", "Ticket_Medio", "Ingressos_por_Cliente"]].copy()
    
    # Normaliza
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determina número de clusters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Método do cotovelo
        max_k = min(8, len(bairros_stats) // 5)
        if max_k >= 2:
            inertias = []
            K_range = range(2, max_k + 1)
            
            for k in K_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(X_scaled)
                inertias.append(kmeans.inertia_)
            
            fig_cotovelo = go.Figure()
            fig_cotovelo.add_trace(go.Scatter(
                x=list(K_range),
                y=inertias,
                mode='lines+markers',
                marker=dict(size=10, color='orange'),
                line=dict(width=2)
            ))
            
            fonts = get_font_sizes(escala)
            fig_cotovelo.update_layout(
                title="Método do Cotovelo - Clusters de Bairros",
                xaxis_title="Número de Clusters (K)",
                yaxis_title="Inércia",
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick'],
                height=400
            )
            st.plotly_chart(fig_cotovelo, use_container_width=True, config=get_plotly_config(escala))
    
    with col2:
        st.markdown("#### 💡 Interpretação")
        st.write("Clusters de bairros agrupam regiões com:")
        st.write("- Padrões similares de consumo")
        st.write("- Ticket médio semelhante")
        st.write("- Comportamento de compra similar")
    
    # Slider para escolher número de clusters
    n_clusters = st.slider(
        "Número de clusters de bairros:",
        min_value=2,
        max_value=max_k if max_k >= 2 else 3,
        value=min(4, max_k) if max_k >= 2 else 3,
        key="slider_bairros"
    )
    
    # Aplica K-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    bairros_stats["Cluster"] = kmeans.fit_predict(X_scaled)
    
    # Nomeia clusters
    def nomear_cluster_bairro(row, stats_df):
        if row["Ticket_Medio"] > stats_df["Ticket_Medio"].quantile(0.75):
            return f"Cluster {row['Cluster']}: Premium"
        elif row["Total_Ingressos"] > stats_df["Total_Ingressos"].quantile(0.75):
            return f"Cluster {row['Cluster']}: Alto Volume"
        elif row["Ingressos_por_Cliente"] > stats_df["Ingressos_por_Cliente"].quantile(0.75):
            return f"Cluster {row['Cluster']}: Grupos Grandes"
        else:
            return f"Cluster {row['Cluster']}: Padrão"
    
    bairros_stats["Nome_Cluster"] = bairros_stats.apply(lambda row: nomear_cluster_bairro(row, bairros_stats), axis=1)
    
    # Visualizações
    st.markdown("---")
    st.markdown("#### 📊 Visualização dos Clusters de Bairros")
    
    fonts = get_font_sizes(escala)
    
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        # Scatter: Total de Ingressos vs Ticket Médio
        fig_scatter = px.scatter(
            bairros_stats,
            x="Total_Ingressos",
            y="Ticket_Medio",
            color="Nome_Cluster",
            size="Clientes_Unicos",
            hover_data=["Bairro"],
            title="Bairros: Volume vs Ticket Médio",
            labels={"Total_Ingressos": "Total de Ingressos", "Ticket_Medio": "Ticket Médio (R$)"}
        )
        
        fig_scatter.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            height=450
        )
        st.plotly_chart(fig_scatter, use_container_width=True, config=get_plotly_config(escala))
    
    with col_viz2:
        # Top 10 bairros por cluster
        top_bairros_cluster = bairros_stats.nlargest(10, "Total_Ingressos")
        
        fig_top = px.bar(
            top_bairros_cluster,
            x="Bairro",
            y="Total_Ingressos",
            color="Nome_Cluster",
            title="Top 10 Bairros por Volume",
            labels={"Bairro": "Bairro", "Total_Ingressos": "Ingressos"}
        )
        
        fig_top.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            xaxis_tickangle=-45,
            height=450
        )
        st.plotly_chart(fig_top, use_container_width=True, config=get_plotly_config(escala))
    
    # Estatísticas por cluster
    st.markdown("---")
    st.markdown("#### 📋 Características dos Clusters de Bairros")
    
    cluster_summary = bairros_stats.groupby("Nome_Cluster").agg({
        "Bairro": "count",
        "Total_Ingressos": ["sum", "mean"],
        "Receita_Total": "sum",
        "Ticket_Medio": "mean",
        "Clientes_Unicos": "sum"
    }).round(2)
    
    cluster_summary.columns = ["Qtd_Bairros", "Total_Ingressos", "Media_Ingressos", "Receita_Total", "Ticket_Medio", "Total_Clientes"]
    cluster_summary = cluster_summary.reset_index()
    
    # Exibe cards
    cols = st.columns(min(n_clusters, 3))
    for idx, (_, cluster_info) in enumerate(cluster_summary.iterrows()):
        with cols[idx % 3]:
            st.markdown(f"**{cluster_info['Nome_Cluster']}**")
            st.metric("Bairros", int(cluster_info['Qtd_Bairros']))
            st.metric("Total Ingressos", f"{int(cluster_info['Total_Ingressos']):,}".replace(",", "."))
            st.metric("Ticket Médio", f"R$ {cluster_info['Ticket_Medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.metric("Clientes", f"{int(cluster_info['Total_Clientes']):,}".replace(",", "."))
    
    # Tabela de bairros por cluster
    with st.expander("🔍 Ver lista completa de bairros por cluster"):
        for cluster_name in bairros_stats["Nome_Cluster"].unique():
            st.markdown(f"**{cluster_name}**")
            bairros_cluster = bairros_stats[bairros_stats["Nome_Cluster"] == cluster_name][["Bairro", "Total_Ingressos", "Ticket_Medio"]].sort_values("Total_Ingressos", ascending=False)
            st.dataframe(bairros_cluster, hide_index=True, use_container_width=True)
    
    # Download
    csv_bairros = bairros_stats.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download Clusters de Bairros (CSV)",
        data=csv_bairros,
        file_name="clusters_geograficos_bairros.csv",
        mime="text/csv",
        use_container_width=True
    )


def analise_clusters_cidades(df_b, escala=2):
    """Análise de clusters por cidades"""
    st.markdown("#### 🌆 Análise por Cidades")
    
    # Filtra apenas dados com cidade informada
    df_cidades = df_b[df_b["cidade_google"].notna()].copy()
    
    if df_cidades.empty:
        st.info("Não há dados de cidades disponíveis.")
        return
    
    # Agrupa por cidade
    cidades_stats = df_cidades.groupby("cidade_google").agg({
        "TDL Sum Tickets (B+S-A)": "sum",
        "TDL Sum Ticket Net Price (B+S-A)": "sum",
        "TDL Customer CPF": "nunique",
        "TDL Event": "nunique"
    }).reset_index()
    
    cidades_stats.columns = ["Cidade", "Total_Ingressos", "Receita_Total", "Clientes_Unicos", "Eventos_Diferentes"]
    
    # Calcula métricas derivadas
    cidades_stats["Ticket_Medio"] = (cidades_stats["Receita_Total"] / cidades_stats["Total_Ingressos"]).round(2)
    cidades_stats["Ingressos_por_Cliente"] = (cidades_stats["Total_Ingressos"] / cidades_stats["Clientes_Unicos"]).round(2)
    
    # Remove cidades com poucos dados (menos de 10 ingressos)
    cidades_stats = cidades_stats[cidades_stats["Total_Ingressos"] >= 10].copy()
    
    # Remove valores inválidos (NaN, inf, -inf)
    cidades_stats = cidades_stats.replace([np.inf, -np.inf], np.nan)
    cidades_stats = cidades_stats.dropna(subset=["Ticket_Medio", "Ingressos_por_Cliente"])
    
    if len(cidades_stats) < 5:
        st.warning("Dados insuficientes para análise de clusters de cidades.")
        return
    
    # Prepara dados para clustering
    X = cidades_stats[["Total_Ingressos", "Ticket_Medio", "Ingressos_por_Cliente"]].copy()
    
    # Normaliza
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determina número de clusters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Método do cotovelo
        max_k = min(8, len(cidades_stats) // 5)
        if max_k >= 2:
            inertias = []
            K_range = range(2, max_k + 1)
            
            for k in K_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(X_scaled)
                inertias.append(kmeans.inertia_)
            
            fig_cotovelo = go.Figure()
            fig_cotovelo.add_trace(go.Scatter(
                x=list(K_range),
                y=inertias,
                mode='lines+markers',
                marker=dict(size=10, color='green'),
                line=dict(width=2)
            ))
            
            fonts = get_font_sizes(escala)
            fig_cotovelo.update_layout(
                title="Método do Cotovelo - Clusters de Cidades",
                xaxis_title="Número de Clusters (K)",
                yaxis_title="Inércia",
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick'],
                height=400
            )
            st.plotly_chart(fig_cotovelo, use_container_width=True, config=get_plotly_config(escala))
    
    with col2:
        st.markdown("#### 💡 Interpretação")
        st.write("Clusters de cidades identificam:")
        st.write("- Mercados regionais similares")
        st.write("- Potencial de expansão")
        st.write("- Padrões de consumo por região")
    
    # Slider para escolher número de clusters
    n_clusters = st.slider(
        "Número de clusters de cidades:",
        min_value=2,
        max_value=max_k if max_k >= 2 else 3,
        value=min(4, max_k) if max_k >= 2 else 3,
        key="slider_cidades"
    )
    
    # Aplica K-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cidades_stats["Cluster"] = kmeans.fit_predict(X_scaled)
    
    # Nomeia clusters
    def nomear_cluster_cidade(row, stats_df):
        if row["Total_Ingressos"] > stats_df["Total_Ingressos"].quantile(0.75):
            return f"Cluster {row['Cluster']}: Mercado Principal"
        elif row["Ticket_Medio"] > stats_df["Ticket_Medio"].quantile(0.75):
            return f"Cluster {row['Cluster']}: Alto Valor"
        elif row["Total_Ingressos"] > stats_df["Total_Ingressos"].median():
            return f"Cluster {row['Cluster']}: Mercado Secundário"
        else:
            return f"Cluster {row['Cluster']}: Emergente"
    
    cidades_stats["Nome_Cluster"] = cidades_stats.apply(lambda row: nomear_cluster_cidade(row, cidades_stats), axis=1)
    
    # Visualizações
    st.markdown("---")
    st.markdown("#### 📊 Visualização dos Clusters de Cidades")
    
    fonts = get_font_sizes(escala)
    
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        # Scatter: Total de Ingressos vs Ticket Médio
        fig_scatter = px.scatter(
            cidades_stats,
            x="Total_Ingressos",
            y="Ticket_Medio",
            color="Nome_Cluster",
            size="Clientes_Unicos",
            hover_data=["Cidade"],
            title="Cidades: Volume vs Ticket Médio",
            labels={"Total_Ingressos": "Total de Ingressos", "Ticket_Medio": "Ticket Médio (R$)"}
        )
        
        fig_scatter.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            height=450
        )
        st.plotly_chart(fig_scatter, use_container_width=True, config=get_plotly_config(escala))
    
    with col_viz2:
        # Top 15 cidades por cluster
        top_cidades_cluster = cidades_stats.nlargest(15, "Total_Ingressos")
        
        fig_top = px.bar(
            top_cidades_cluster,
            x="Cidade",
            y="Total_Ingressos",
            color="Nome_Cluster",
            title="Top 15 Cidades por Volume",
            labels={"Cidade": "Cidade", "Total_Ingressos": "Ingressos"}
        )
        
        fig_top.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            xaxis_tickangle=-45,
            height=450
        )
        st.plotly_chart(fig_top, use_container_width=True, config=get_plotly_config(escala))
    
    # Estatísticas por cluster
    st.markdown("---")
    st.markdown("#### 📋 Características dos Clusters de Cidades")
    
    cluster_summary = cidades_stats.groupby("Nome_Cluster").agg({
        "Cidade": "count",
        "Total_Ingressos": ["sum", "mean"],
        "Receita_Total": "sum",
        "Ticket_Medio": "mean",
        "Clientes_Unicos": "sum"
    }).round(2)
    
    cluster_summary.columns = ["Qtd_Cidades", "Total_Ingressos", "Media_Ingressos", "Receita_Total", "Ticket_Medio", "Total_Clientes"]
    cluster_summary = cluster_summary.reset_index()
    
    # Exibe cards
    cols = st.columns(min(n_clusters, 3))
    for idx, (_, cluster_info) in enumerate(cluster_summary.iterrows()):
        with cols[idx % 3]:
            st.markdown(f"**{cluster_info['Nome_Cluster']}**")
            st.metric("Cidades", int(cluster_info['Qtd_Cidades']))
            st.metric("Total Ingressos", f"{int(cluster_info['Total_Ingressos']):,}".replace(",", "."))
            st.metric("Ticket Médio", f"R$ {cluster_info['Ticket_Medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            st.metric("Clientes", f"{int(cluster_info['Total_Clientes']):,}".replace(",", "."))
    
    # Tabela de cidades por cluster
    with st.expander("🔍 Ver lista completa de cidades por cluster"):
        for cluster_name in cidades_stats["Nome_Cluster"].unique():
            st.markdown(f"**{cluster_name}**")
            cidades_cluster = cidades_stats[cidades_stats["Nome_Cluster"] == cluster_name][["Cidade", "Total_Ingressos", "Ticket_Medio", "Clientes_Unicos"]].sort_values("Total_Ingressos", ascending=False)
            st.dataframe(cidades_cluster, hide_index=True, use_container_width=True)
    
    # Download
    csv_cidades = cidades_stats.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download Clusters de Cidades (CSV)",
        data=csv_cidades,
        file_name="clusters_geograficos_cidades.csv",
        mime="text/csv",
        use_container_width=True
    )
