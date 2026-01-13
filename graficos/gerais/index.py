import streamlit as st
import pandas as pd
import plotly.express as px


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


def grafico_vendas_ao_longo_do_tempo(df_b, escala=2):
    """Exibe gráfico de linha mostrando ingressos vendidos ao longo do tempo"""
    st.markdown("#### Ingressos ao longo do tempo")
    if not df_b.empty:
        vendas_por_dia = (
            df_b.groupby("TDL Event Date")["TDL Sum Tickets (B+S-A)"]
            .sum()
            .reset_index()
        )
        vendas_por_dia = vendas_por_dia[vendas_por_dia["TDL Event Date"].notna()]
        fig_tempo = px.line(
            vendas_por_dia,
            x="TDL Event Date",
            y="TDL Sum Tickets (B+S-A)",
            labels={
                "TDL Event Date": "Data",
                "TDL Sum Tickets (B+S-A)": "Ingressos"
            },
            title="Ingressos vendidos por dia"
        )
        fonts = get_font_sizes(escala)
        fig_tempo.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick']
        )
        st.plotly_chart(fig_tempo, use_container_width=True, config=get_plotly_config(escala))
        
        with st.expander("📊 Ver dados da tabela"):
            vendas_por_dia_display = vendas_por_dia.copy()
            vendas_por_dia_display["TDL Event Date"] = vendas_por_dia_display["TDL Event Date"].dt.strftime("%d/%m/%Y")
            vendas_por_dia_display.columns = ["Data", "Ingressos"]
            st.dataframe(vendas_por_dia_display, hide_index=True, use_container_width=True)


def analise_comportamento_compra(df_b, escala=2):
    """Exibe análises de comportamento de compra dos clientes"""
    st.markdown("### 🛒 Comportamento de Compra")
    
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        st.markdown("#### Distribuição de Ingressos por Cliente")
        if not df_b.empty:
            ingressos_por_cliente = (
                df_b[df_b["TDL Customer CPF"].notna()]
                .groupby("TDL Customer CPF")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
            )
            
            # Cria faixas de quantidade de ingressos
            ingressos_por_cliente["Faixa"] = pd.cut(
                ingressos_por_cliente["TDL Sum Tickets (B+S-A)"],
                bins=[0, 1, 2, 3, 5, 10, float('inf')],
                labels=["1 ingresso", "2 ingressos", "3 ingressos", "4-5 ingressos", "6-10 ingressos", "Mais de 10"]
            )
            
            dist_faixa = ingressos_por_cliente["Faixa"].value_counts().sort_index().reset_index()
            dist_faixa.columns = ["Faixa", "Quantidade de Clientes"]
            
            # Calcula percentuais
            total_clientes_dist = dist_faixa["Quantidade de Clientes"].sum()
            dist_faixa["Percentual"] = (dist_faixa["Quantidade de Clientes"] / total_clientes_dist * 100).round(1)
            
            fig_dist = px.bar(
                dist_faixa,
                x="Faixa",
                y="Quantidade de Clientes",
                labels={"Faixa": "Quantidade de Ingressos", "Quantidade de Clientes": "Clientes"},
                title="Quantos ingressos cada cliente comprou?",
                text=dist_faixa["Percentual"].apply(lambda x: f"{x}%")
            )
            fonts = get_font_sizes(escala)
            fig_dist.update_traces(textposition='outside', textfont_size=fonts['annotation'])
            fig_dist.update_layout(
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick']
            )
            st.plotly_chart(fig_dist, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver dados da tabela"):
                st.dataframe(dist_faixa, hide_index=True, use_container_width=True)
    
    with col_comp2:
        st.markdown("#### Top 10 Clientes (por quantidade de ingressos)")
        if not df_b.empty:
            top_clientes = (
                df_b[df_b["TDL Customer CPF"].notna()]
                .groupby("TDL Customer CPF")[["TDL Sum Tickets (B+S-A)", "TDL Sum Ticket Net Price (B+S-A)"]]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
                .head(10)
            )
            
            top_clientes["Receita (R$)"] = top_clientes["TDL Sum Ticket Net Price (B+S-A)"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            
            display_top = top_clientes[["TDL Customer CPF", "TDL Sum Tickets (B+S-A)", "Receita (R$)"]]
            display_top.columns = ["CPF", "Ingressos", "Receita Total"]
            st.dataframe(display_top, hide_index=True, use_container_width=True)
            
            # Expandir para mostrar detalhamento por dia da semana
            with st.expander("📊 Ver detalhamento por dia da semana"):
                if "dia_semana_label" in df_b.columns:
                    # Filtra apenas os top 10 CPFs
                    top_cpfs = top_clientes["TDL Customer CPF"].tolist()
                    df_top_detalhado = df_b[df_b["TDL Customer CPF"].isin(top_cpfs)]
                    
                    # Agrupa por CPF e dia da semana
                    detalhamento_dia = (
                        df_top_detalhado.groupby(["TDL Customer CPF", "dia_semana_label"])["TDL Sum Tickets (B+S-A)"]
                        .sum()
                        .reset_index()
                    )
                    
                    # Cria tabela pivotada
                    tabela_dia_semana = detalhamento_dia.pivot(
                        index="TDL Customer CPF",
                        columns="dia_semana_label",
                        values="TDL Sum Tickets (B+S-A)"
                    ).fillna(0).astype(int)
                    
                    # Ordena as colunas por dia da semana
                    ordem_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                    colunas_existentes = [dia for dia in ordem_dias if dia in tabela_dia_semana.columns]
                    tabela_dia_semana = tabela_dia_semana[colunas_existentes]
                    
                    # Adiciona coluna de total
                    tabela_dia_semana["Total"] = tabela_dia_semana.sum(axis=1)
                    
                    # Ordena por total descendente
                    tabela_dia_semana = tabela_dia_semana.sort_values("Total", ascending=False)
                    
                    st.dataframe(tabela_dia_semana, use_container_width=True)
                else:
                    st.info("Dados de dia da semana não disponíveis.")
    
    # Análise de recorrência
    st.markdown("#### Análise de Recorrência - Clientes em Múltiplos Eventos")
    if not df_b.empty and "TDL Event" in df_b.columns:
        eventos_por_cliente = (
            df_b[df_b["TDL Customer CPF"].notna()]
            .groupby("TDL Customer CPF")["TDL Event"]
            .nunique()
            .reset_index()
        )
        eventos_por_cliente.columns = ["CPF", "Eventos_Diferentes"]
        
        # Cria faixas
        eventos_por_cliente["Faixa_Eventos"] = eventos_por_cliente["Eventos_Diferentes"].apply(
            lambda x: f"{x} evento" if x == 1 else f"{x} eventos" if x <= 5 else "6+ eventos"
        )
        
        dist_recorrencia = eventos_por_cliente["Faixa_Eventos"].value_counts().reset_index()
        dist_recorrencia.columns = ["Eventos", "Clientes"]
        
        # Ordena as categorias
        ordem_eventos = ["1 evento", "2 eventos", "3 eventos", "4 eventos", "5 eventos", "6+ eventos"]
        dist_recorrencia["Eventos"] = pd.Categorical(dist_recorrencia["Eventos"], categories=ordem_eventos, ordered=True)
        dist_recorrencia = dist_recorrencia.sort_values("Eventos")
        
        fig_recorrencia = px.pie(
            dist_recorrencia,
            values="Clientes",
            names="Eventos",
            title="Distribuição de clientes por número de eventos diferentes frequentados",
            hole=0.4
        )
        fonts = get_font_sizes(escala)
        fig_recorrencia.update_layout(
            title_font_size=fonts['title'],
            legend_font_size=fonts['legend'],
            font_size=fonts['annotation']
        )
        st.plotly_chart(fig_recorrencia, use_container_width=True, config=get_plotly_config(escala))
        
        with st.expander("📊 Ver dados da tabela"):
            st.dataframe(dist_recorrencia, hide_index=True, use_container_width=True)


def analise_turismo_por_periodo(df_b, escala=2):
    """Analisa mudanças no perfil do público por período, identificando turistas nacionais e internacionais"""
    st.markdown("### 🌍 Análise de Turismo por Período")
    st.markdown("Identifica variações no perfil do público ao longo do tempo, destacando a presença de turistas")
    
    if df_b.empty or "TDL Event Date" not in df_b.columns:
        st.info("Não há dados disponíveis para análise.")
        return
    
    # Adiciona coluna de mês/ano
    df_analise = df_b.copy()
    df_analise["Mes_Ano"] = df_analise["TDL Event Date"].dt.to_period('M').astype(str)
    df_analise["Mes_Nome"] = df_analise["TDL Event Date"].dt.strftime('%B/%Y')
    
    # Mapeamento de meses em português
    meses_pt = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
        'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
        'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
        'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    for en, pt in meses_pt.items():
        df_analise["Mes_Nome"] = df_analise["Mes_Nome"].str.replace(en, pt)
    
    # Classifica origem: Rio de Janeiro, Outros Estados, Internacional
    def classificar_origem(row):
        # Usa uf_google se disponível, senão TDL Customer State
        estado = row.get("uf_google", row.get("TDL Customer State", ""))
        pais = row.get("TDL Customer Country", "")
        
        if pd.isna(pais) or pais == "":
            return "Não informado"
        
        if pais.upper() not in ["BRAZIL", "BRASIL", "BR"]:
            return "Internacional"
        
        if pd.isna(estado) or estado == "":
            return "Brasil - Estado não informado"
        
        if estado.upper() in ["RJ", "RIO DE JANEIRO"]:
            return "Rio de Janeiro"
        else:
            return "Outros Estados (Brasil)"
    
    df_analise["Origem_Classificada"] = df_analise.apply(classificar_origem, axis=1)
    
    # Agrupa por mês e origem
    evolucao = (
        df_analise.groupby(["Mes_Ano", "Mes_Nome", "Origem_Classificada"])["TDL Sum Tickets (B+S-A)"]
        .sum()
        .reset_index()
    )
    evolucao.columns = ["Mes_Ano", "Mes_Nome", "Origem", "Ingressos"]
    
    # Calcula percentuais por mês
    total_por_mes = evolucao.groupby("Mes_Ano")["Ingressos"].sum().reset_index()
    total_por_mes.columns = ["Mes_Ano", "Total_Mes"]
    evolucao = evolucao.merge(total_por_mes, on="Mes_Ano")
    evolucao["Percentual"] = (evolucao["Ingressos"] / evolucao["Total_Mes"] * 100).round(1)
    
    # Ordena por data
    evolucao = evolucao.sort_values("Mes_Ano")
    
    # Define cores para cada categoria
    cores_origem = {
        "Rio de Janeiro": "#1f77b4",
        "Outros Estados (Brasil)": "#ff7f0e",
        "Internacional": "#2ca02c",
        "Brasil - Estado não informado": "#d62728",
        "Não informado": "#9467bd"
    }
    
    # Gráfico 1: Evolução em valores absolutos
    st.markdown("#### 📊 Evolução do Público por Origem (Valores Absolutos)")
    fig_abs = px.bar(
        evolucao,
        x="Mes_Nome",
        y="Ingressos",
        color="Origem",
        title="Distribuição do Público por Origem ao Longo do Tempo",
        labels={"Mes_Nome": "Mês", "Ingressos": "Quantidade de Ingressos"},
        barmode="stack",
        color_discrete_map=cores_origem
    )
    
    fonts = get_font_sizes(escala)
    fig_abs.update_layout(
        title_font_size=fonts['title'],
        xaxis_title_font_size=fonts['axis'],
        yaxis_title_font_size=fonts['axis'],
        xaxis_tickfont_size=fonts['tick'],
        yaxis_tickfont_size=fonts['tick'],
        legend_font_size=fonts['legend'],
        height=500
    )
    st.plotly_chart(fig_abs, use_container_width=True, config=get_plotly_config(escala))
    
    # Gráfico 2: Evolução em percentuais
    st.markdown("#### 📈 Evolução do Público por Origem (Percentuais)")
    fig_perc = px.bar(
        evolucao,
        x="Mes_Nome",
        y="Percentual",
        color="Origem",
        title="Proporção do Público por Origem ao Longo do Tempo (%)",
        labels={"Mes_Nome": "Mês", "Percentual": "Percentual (%)"},
        barmode="stack",
        color_discrete_map=cores_origem,
        text=evolucao["Percentual"].apply(lambda x: f"{x:.1f}%" if x > 5 else "")
    )
    
    fig_perc.update_traces(textposition='inside', textfont_size=fonts['annotation'])
    fig_perc.update_layout(
        title_font_size=fonts['title'],
        xaxis_title_font_size=fonts['axis'],
        yaxis_title_font_size=fonts['axis'],
        xaxis_tickfont_size=fonts['tick'],
        yaxis_tickfont_size=fonts['tick'],
        legend_font_size=fonts['legend'],
        height=500,
        yaxis_range=[0, 100]
    )
    st.plotly_chart(fig_perc, use_container_width=True, config=get_plotly_config(escala))
    
    # Análise específica de dezembro
    dezembro_data = evolucao[evolucao["Mes_Nome"].str.contains("Dezembro")]
    if not dezembro_data.empty:
        st.markdown("---")
        st.markdown("#### 🎄 Análise Detalhada: Dezembro")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Métricas de turismo em dezembro
            turistas_nacionais = dezembro_data[dezembro_data["Origem"] == "Outros Estados (Brasil)"]["Ingressos"].sum()
            turistas_internacionais = dezembro_data[dezembro_data["Origem"] == "Internacional"]["Ingressos"].sum()
            publico_rj = dezembro_data[dezembro_data["Origem"] == "Rio de Janeiro"]["Ingressos"].sum()
            total_dezembro = dezembro_data["Ingressos"].sum()
            
            st.metric("Público do Rio de Janeiro", f"{int(publico_rj):,}".replace(",", "."))
            st.metric("Turistas Nacionais (outros estados)", f"{int(turistas_nacionais):,}".replace(",", "."))
            st.metric("Turistas Internacionais", f"{int(turistas_internacionais):,}".replace(",", "."))
            
            perc_turistas = ((turistas_nacionais + turistas_internacionais) / total_dezembro * 100) if total_dezembro > 0 else 0
            st.metric("% de Turistas (nacional + internacional)", f"{perc_turistas:.1f}%")
        
        with col2:
            # Gráfico de pizza para dezembro
            fig_dez = px.pie(
                dezembro_data,
                values="Ingressos",
                names="Origem",
                title="Distribuição do Público em Dezembro",
                hole=0.4,
                color="Origem",
                color_discrete_map=cores_origem
            )
            fig_dez.update_traces(textposition='auto', textinfo='percent+label', textfont_size=fonts['annotation'])
            fig_dez.update_layout(
                title_font_size=fonts['title'],
                legend_font_size=fonts['legend'],
                height=400
            )
            st.plotly_chart(fig_dez, use_container_width=True, config=get_plotly_config(escala))
    
    # Comparação entre meses
    st.markdown("---")
    st.markdown("#### 📋 Comparação Detalhada entre Meses")
    
    # Cria tabela pivotada
    tabela_comparacao = evolucao.pivot_table(
        index="Origem",
        columns="Mes_Nome",
        values="Percentual",
        fill_value=0
    ).round(1)
    
    # Adiciona linha de total de ingressos por mês
    total_linha = evolucao.groupby("Mes_Nome")["Total_Mes"].first()
    
    st.dataframe(tabela_comparacao, use_container_width=True)
    
    # Mostra total por mês
    st.markdown("**Total de Ingressos por Mês:**")
    total_display = total_linha.to_frame().T
    total_display.index = ["Total"]
    st.dataframe(total_display, use_container_width=True)
    
    # Top estados brasileiros (excluindo RJ)
    coluna_uf = "uf_google" if "uf_google" in df_analise.columns else "TDL Customer State"
    if coluna_uf in df_analise.columns:
        st.markdown("---")
        st.markdown("#### 🗺️ Top 10 Estados de Origem (excluindo RJ)")
        
        estados_outros = df_analise[
            (df_analise[coluna_uf].notna()) &
            (~df_analise[coluna_uf].str.upper().isin(["RJ", "RIO DE JANEIRO"]))
        ]
        
        if not estados_outros.empty:
            top_estados = (
                estados_outros.groupby(coluna_uf)["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
                .head(10)
            )
            top_estados.columns = ["Estado", "Ingressos_Val"]
            
            fig_estados = px.bar(
                top_estados,
                x="Estado",
                y="Ingressos_Val",
                title="Estados Brasileiros com Mais Turistas",
                labels={"Estado": "Estado", "Ingressos_Val": "Ingressos"},
                color="Ingressos_Val",
                color_continuous_scale="Oranges"
            )
            
            fig_estados.update_layout(
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick'],
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig_estados, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver dados da tabela"):
                top_estados_display = top_estados.copy()
                top_estados_display["Ingressos_Val"] = top_estados_display["Ingressos_Val"].astype(int)
                top_estados_display.columns = ["Estado", "Ingressos"]
                st.dataframe(top_estados_display, hide_index=True, use_container_width=True)
    
    # Top países (excluindo Brasil)
    if "TDL Customer Country" in df_analise.columns:
        st.markdown("---")
        st.markdown("#### 🌎 Top 10 Países de Origem (excluindo Brasil)")
        
        paises_outros = df_analise[
            (df_analise["TDL Customer Country"].notna()) &
            (~df_analise["TDL Customer Country"].str.upper().isin(["BRAZIL", "BRASIL", "BR"]))
        ]
        
        if not paises_outros.empty:
            top_paises = (
                paises_outros.groupby("TDL Customer Country")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
                .head(10)
            )
            
            fig_paises = px.bar(
                top_paises,
                x="TDL Customer Country",
                y="TDL Sum Tickets (B+S-A)",
                title="Países com Mais Turistas Internacionais",
                labels={"TDL Customer Country": "País", "TDL Sum Tickets (B+S-A)": "Ingressos"},
                color="TDL Sum Tickets (B+S-A)",
                color_continuous_scale="Greens"
            )
            
            fig_paises.update_layout(
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick'],
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig_paises, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver dados da tabela"):
                top_paises.columns = ["País", "Ingressos"]
                top_paises["Ingressos"] = top_paises["Ingressos"].astype(int)
                st.dataframe(top_paises, hide_index=True, use_container_width=True)
    
    # Botão de download
    csv_evolucao = evolucao.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download Análise Completa (CSV)",
        data=csv_evolucao,
        file_name="analise_turismo_por_periodo.csv",
        mime="text/csv",
        use_container_width=True
    )


def ranking_eventos_por_publico(df_b, escala=2):
    """Exibe ranking dos eventos ordenados por quantidade de público"""
    st.markdown("### 🏆 Ranking de Eventos por Público")
    
    if df_b.empty or "TDL Event" not in df_b.columns:
        st.info("Não há dados disponíveis para exibir o ranking.")
        return
    
    # Agrupa por evento e soma ingressos e receita
    ranking = (
        df_b[df_b["TDL Event"].notna()]
        .groupby("TDL Event")
        .agg({
            "TDL Sum Tickets (B+S-A)": "sum",
            "TDL Sum Ticket Net Price (B+S-A)": "sum",
            "TDL Customer CPF": "nunique"
        })
        .reset_index()
    )
    
    ranking.columns = ["Evento", "Total de Ingressos", "Receita Total (R$)", "Clientes Únicos"]
    ranking = ranking.sort_values("Total de Ingressos", ascending=False)
    
    # Calcula percentuais
    total_geral = ranking["Total de Ingressos"].sum()
    ranking["Percentual"] = (ranking["Total de Ingressos"] / total_geral * 100).round(1)
    
    # Calcula ticket médio
    ranking["Ticket Médio (R$)"] = (ranking["Receita Total (R$)"] / ranking["Total de Ingressos"]).round(2)
    
    # Layout com gráfico e métricas
    col_grafico, col_metricas = st.columns([2, 1])
    
    with col_grafico:
        # Cria gráfico de barras
        fig_ranking = px.bar(
            ranking,
            x="Total de Ingressos",
            y="Evento",
            orientation="h",
            title="Ranking de Eventos por Quantidade de Público",
            labels={"Total de Ingressos": "Ingressos Vendidos", "Evento": "Evento"},
            color="Total de Ingressos",
            color_continuous_scale="Blues",
            text=ranking["Percentual"].apply(lambda x: f"{x}%")
        )
        
        fonts = get_font_sizes(escala)
        fig_ranking.update_traces(textposition='outside', textfont_size=fonts['annotation'])
        fig_ranking.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            height=max(400, len(ranking) * 50),
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        st.plotly_chart(fig_ranking, use_container_width=True, config=get_plotly_config(escala))
    
    with col_metricas:
        st.markdown("#### 📊 Resumo Geral")
        st.metric("Total de Eventos", len(ranking))
        st.metric("Total de Ingressos", f"{int(total_geral):,}".replace(",", "."))
        st.metric("Receita Total", f"R$ {ranking['Receita Total (R$)'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        if len(ranking) > 0:
            evento_top = ranking.iloc[0]
            st.markdown("---")
            st.markdown("#### 🥇 Evento Líder")
            st.write(f"**{evento_top['Evento']}**")
            st.write(f"Ingressos: {int(evento_top['Total de Ingressos']):,}".replace(",", "."))
            st.write(f"Participação: {evento_top['Percentual']}%")
    
    # Tabela detalhada
    st.markdown("---")
    st.markdown("#### 📋 Detalhamento Completo")
    
    # Formata os valores para exibição
    ranking_display = ranking.copy()
    ranking_display["Total de Ingressos"] = ranking_display["Total de Ingressos"].astype(int)
    ranking_display["Receita Total (R$)"] = ranking_display["Receita Total (R$)"].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    ranking_display["Ticket Médio (R$)"] = ranking_display["Ticket Médio (R$)"].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    ranking_display["Percentual"] = ranking_display["Percentual"].apply(lambda x: f"{x}%")
    ranking_display.index = range(1, len(ranking_display) + 1)
    
    st.dataframe(ranking_display, use_container_width=True)
    
    # Botão de download
    csv_ranking = ranking_display.to_csv(index=True, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download Ranking Completo (CSV)",
        data=csv_ranking,
        file_name="ranking_eventos_publico.csv",
        mime="text/csv",
        use_container_width=True
    )


def grafico_pizza_tipo_ingresso_por_evento(df_b, escala=2):
    """Exibe gráfico de pizza para avaliar o percentual do tipo de ingresso comprado para cada evento"""
    st.markdown("### 🎫 Tipo de Ingresso por Evento")
    
    if df_b.empty:
        st.info("Não há dados disponíveis para exibir o gráfico.")
        return
    
    # Identifica a coluna de tipo de ingresso
    tipo_ingresso_col = None
    if "TDL Ticket Type" in df_b.columns:
        tipo_ingresso_col = "TDL Ticket Type"
    
    if tipo_ingresso_col is None or "TDL Event" not in df_b.columns:
        st.info("Dados de tipo de ingresso ou evento não disponíveis.")
        return
    
    # Obtém lista de eventos
    eventos = sorted(df_b["TDL Event"].dropna().unique())
    
    if len(eventos) == 0:
        st.info("Nenhum evento encontrado nos dados.")
        return
    
    # Permite ao usuário selecionar um evento específico ou ver todos
    evento_selecionado = st.selectbox(
        "Selecione um evento para análise:",
        ["Todos os eventos"] + list(eventos),
        key="select_evento_pizza"
    )
    
    # Filtra os dados conforme seleção
    if evento_selecionado == "Todos os eventos":
        df_filtrado = df_b.copy()
        titulo = "Distribuição de Tipos de Ingresso - Todos os Eventos"
    else:
        df_filtrado = df_b[df_b["TDL Event"] == evento_selecionado].copy()
        titulo = f"Distribuição de Tipos de Ingresso - {evento_selecionado}"
    
    # Agrupa por tipo de ingresso
    tipo_ingresso_count = (
        df_filtrado[df_filtrado[tipo_ingresso_col].notna()]
        .groupby(tipo_ingresso_col)["TDL Sum Tickets (B+S-A)"]
        .sum()
        .reset_index()
    )
    tipo_ingresso_count.columns = ["Tipo de Ingresso", "Quantidade"]
    tipo_ingresso_count = tipo_ingresso_count.sort_values("Quantidade", ascending=False)
    
    if tipo_ingresso_count.empty:
        st.info(f"Não há dados de tipo de ingresso disponíveis para {evento_selecionado}.")
        return
    
    # Calcula percentuais
    total = tipo_ingresso_count["Quantidade"].sum()
    tipo_ingresso_count["Percentual"] = (tipo_ingresso_count["Quantidade"] / total * 100).round(2)
    
    # Layout com duas colunas: gráfico e tabela
    col_grafico, col_tabela = st.columns([2, 1])
    
    with col_grafico:
        # Cria o gráfico de pizza
        fig_pizza = px.pie(
            tipo_ingresso_count,
            values="Quantidade",
            names="Tipo de Ingresso",
            title=titulo,
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fonts = get_font_sizes(escala)
        fig_pizza.update_traces(
            textposition='auto',
            textinfo='percent+label',
            textfont_size=fonts['annotation']
        )
        fig_pizza.update_layout(
            title_font_size=fonts['title'],
            legend_font_size=fonts['legend'],
            font_size=fonts['annotation'],
            height=500
        )
        
        st.plotly_chart(fig_pizza, use_container_width=True, config=get_plotly_config(escala))
    
    with col_tabela:
        # Exibe tabela com os dados
        tipo_ingresso_display = tipo_ingresso_count.copy()
        tipo_ingresso_display["Quantidade"] = tipo_ingresso_display["Quantidade"].astype(int)
        tipo_ingresso_display["Percentual"] = tipo_ingresso_display["Percentual"].apply(lambda x: f"{x}%")
        tipo_ingresso_display.index = range(1, len(tipo_ingresso_display) + 1)
        
        st.markdown("#### Detalhamento")
        st.dataframe(tipo_ingresso_display, use_container_width=True, height=500)
    
    # Botão de download
    csv_tipo_ingresso = tipo_ingresso_display.to_csv(index=True, encoding='utf-8-sig')
    st.download_button(
        label="📥 Download Dados (CSV)",
        data=csv_tipo_ingresso,
        file_name=f"tipo_ingresso_{evento_selecionado.replace(' ', '_').lower()}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Análise adicional: comparação entre eventos (se "Todos os eventos" estiver selecionado)
    if evento_selecionado == "Todos os eventos" and len(eventos) > 1:
        st.markdown("---")
        st.markdown("#### 📊 Comparação entre Eventos")
        
        # Cria tabela cruzada: eventos x tipos de ingresso
        comparacao = (
            df_b[df_b[tipo_ingresso_col].notna() & df_b["TDL Event"].notna()]
            .groupby(["TDL Event", tipo_ingresso_col])["TDL Sum Tickets (B+S-A)"]
            .sum()
            .reset_index()
        )
        comparacao.columns = ["Evento", "Tipo de Ingresso", "Quantidade"]
        
        # Cria gráfico de barras agrupadas
        fig_comparacao = px.bar(
            comparacao,
            x="Evento",
            y="Quantidade",
            color="Tipo de Ingresso",
            title="Distribuição de Tipos de Ingresso por Evento",
            labels={"Quantidade": "Ingressos", "Evento": "Evento"},
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fonts = get_font_sizes(escala)
        fig_comparacao.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend'],
            height=500
        )
        
        st.plotly_chart(fig_comparacao, use_container_width=True, config=get_plotly_config(escala))
        
        with st.expander("📊 Ver dados da comparação"):
            # Cria tabela pivotada para melhor visualização
            tabela_comparacao = comparacao.pivot(
                index="Evento",
                columns="Tipo de Ingresso",
                values="Quantidade"
            ).fillna(0).astype(int)
            
            # Adiciona coluna de total
            tabela_comparacao["Total"] = tabela_comparacao.sum(axis=1)
            
            # Ordena por total
            tabela_comparacao = tabela_comparacao.sort_values("Total", ascending=False)
            
            st.dataframe(tabela_comparacao, use_container_width=True)
