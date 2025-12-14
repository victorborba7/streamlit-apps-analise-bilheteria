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


def analise_demografica(df_b, escala=2):
    """Exibe análises demográficas dos clientes"""
    st.markdown("### 👥 Perfil Demográfico dos Clientes")
    
    col_demo1, col_demo2 = st.columns(2)
    
    with col_demo1:
        st.markdown("#### Distribuição por Gênero")
        if "TDL Customer Salutation" in df_b.columns:
            # Mapeia os valores para português ANTES de contar
            mapa_genero = {
                "Mr": "Masculino",
                "Ms": "Feminino",
                "Sr": "Masculino",
                "Sr.": "Masculino",
                "Sra": "Feminino",
                "Sra.": "Feminino",
                "- no TDL data available -": "Não informado"
            }
            df_b_genero = df_b.copy()
            df_b_genero["Gênero"] = df_b_genero["TDL Customer Salutation"].map(mapa_genero).fillna("Não informado")
            
            # Agora agrupa por gênero já mapeado
            genero_count = df_b_genero.groupby("Gênero")["TDL Sum Tickets (B+S-A)"].sum().reset_index()
            genero_count.columns = ["Gênero", "Quantidade"]
            genero_count = genero_count[genero_count["Gênero"].notna()].sort_values("Quantidade", ascending=False)
            
            fig_genero = px.pie(
                genero_count,
                values="Quantidade",
                names="Gênero",
                title="Ingressos por Gênero",
                hole=0.4
            )
            fonts = get_font_sizes(escala)
            fig_genero.update_layout(
                title_font_size=fonts['title'],
                legend_font_size=fonts['legend'],
                font_size=fonts['annotation']
            )
            st.plotly_chart(fig_genero, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver dados da tabela"):
                st.dataframe(genero_count, hide_index=True, use_container_width=True)
        else:
            st.info("Dados de gênero não disponíveis na base de dados.")
    
    with col_demo2:
        st.markdown("#### Distribuição por Faixa Etária")
        if "Faixa Etária" in df_b.columns:
            idade_count = df_b["Faixa Etária"].value_counts().sort_index().reset_index()
            idade_count.columns = ["Faixa Etária", "Quantidade"]
            idade_count = idade_count[idade_count["Faixa Etária"].notna()]
            
            # Calcula percentuais
            total_idade = idade_count["Quantidade"].sum()
            idade_count["Percentual"] = (idade_count["Quantidade"] / total_idade * 100).round(1)
            
            fig_idade = px.bar(
                idade_count,
                x="Faixa Etária",
                y="Quantidade",
                labels={"Faixa Etária": "Idade", "Quantidade": "Ingressos"},
                title="Ingressos por Faixa Etária",
                text=idade_count["Percentual"].apply(lambda x: f"{x}%")
            )
            fonts = get_font_sizes(escala)
            fig_idade.update_traces(textposition='outside', textfont_size=fonts['annotation'])
            fig_idade.update_layout(
                title_font_size=fonts['title'],
                xaxis_title_font_size=fonts['axis'],
                yaxis_title_font_size=fonts['axis'],
                xaxis_tickfont_size=fonts['tick'],
                yaxis_tickfont_size=fonts['tick']
            )
            st.plotly_chart(fig_idade, use_container_width=True, config=get_plotly_config(escala))
            
            with st.expander("📊 Ver dados da tabela"):
                st.dataframe(idade_count, hide_index=True, use_container_width=True)
        else:
            st.info("Dados de faixa etária não disponíveis na base de dados.")
    
    # Cruzamento de dados demográficos
    if "TDL Customer Salutation" in df_b.columns and "Faixa Etária" in df_b.columns:
        st.markdown("#### Distribuição por Gênero e Faixa Etária")
        
        # Prepara os dados
        df_demo = df_b[["TDL Customer Salutation", "Faixa Etária", "TDL Sum Tickets (B+S-A)"]].copy()
        
        # Mapeia gênero
        mapa_genero = {
            "Mr": "Masculino",
            "Ms": "Feminino",
            "Sr": "Masculino",
            "Sr.": "Masculino",
            "Sra": "Feminino",
            "Sra.": "Feminino",
            "- no TDL data available -": "Não informado"
        }
        df_demo["Gênero"] = df_demo["TDL Customer Salutation"].map(mapa_genero).fillna("Não informado")
        
        cruzamento = (
            df_demo.groupby(["Faixa Etária", "Gênero"])["TDL Sum Tickets (B+S-A)"]
            .sum()
            .reset_index()
        )
        cruzamento = cruzamento[cruzamento["Faixa Etária"].notna() & cruzamento["Gênero"].notna()]
        
        # Calcula percentuais por grupo
        total_por_faixa = cruzamento.groupby("Faixa Etária")["TDL Sum Tickets (B+S-A)"].transform('sum')
        cruzamento["Percentual"] = (cruzamento["TDL Sum Tickets (B+S-A)"] / total_por_faixa * 100).round(1)
        
        fig_cruzamento = px.bar(
            cruzamento,
            x="Faixa Etária",
            y="TDL Sum Tickets (B+S-A)",
            color="Gênero",
            barmode="group",
            labels={
                "Faixa Etária": "Idade",
                "TDL Sum Tickets (B+S-A)": "Ingressos",
                "Gênero": "Gênero"
            },
            title="Distribuição de ingressos por gênero e faixa etária",
            text=cruzamento["Percentual"].apply(lambda x: f"{x}%")
        )
        fonts = get_font_sizes(escala)
        fig_cruzamento.update_traces(textposition='outside', textfont_size=fonts['annotation'])
        fig_cruzamento.update_layout(
            title_font_size=fonts['title'],
            xaxis_title_font_size=fonts['axis'],
            yaxis_title_font_size=fonts['axis'],
            xaxis_tickfont_size=fonts['tick'],
            yaxis_tickfont_size=fonts['tick'],
            legend_font_size=fonts['legend']
        )
        st.plotly_chart(fig_cruzamento, use_container_width=True, config=get_plotly_config(escala))
        
        with st.expander("📊 Ver dados da tabela"):
            # Cria tabela pivotada para melhor visualização
            tabela_cruzamento = cruzamento.pivot_table(
                index="Faixa Etária", 
                columns="Gênero", 
                values="TDL Sum Tickets (B+S-A)", 
                aggfunc='sum'
            ).fillna(0)
            tabela_cruzamento = tabela_cruzamento.astype(int)
            st.dataframe(tabela_cruzamento, use_container_width=True)
