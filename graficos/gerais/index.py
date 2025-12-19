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
