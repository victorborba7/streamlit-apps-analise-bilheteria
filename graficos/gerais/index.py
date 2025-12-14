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
            fig_dist.update_traces(textposition='outside')
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
        st.plotly_chart(fig_recorrencia, use_container_width=True, config=get_plotly_config(escala))
        
        with st.expander("📊 Ver dados da tabela"):
            st.dataframe(dist_recorrencia, hide_index=True, use_container_width=True)
