import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import BytesIO
from urllib.parse import quote


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
    bilhetes_filename = quote("base_unificada_arena_marisa_RA.xlsx")
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
    cred_filename = quote("CREDENCIAMENTO_Planilha_AC.xlsx")
    cred_url = f"{github_base}/data/raw/{cred_filename}"
    cred_2025 = pd.read_excel(load_file_from_github(cred_url, headers), sheet_name="GERAL 2025", header=4, engine='openpyxl')
    desm_2024 = pd.read_excel(load_file_from_github(cred_url, headers), sheet_name="Desmontagem 2024", header=2, engine='openpyxl')
    
    # Normaliza os nomes das colunas
    cred_2025.columns = cred_2025.columns.str.strip().str.upper()
    desm_2024.columns = desm_2024.columns.str.strip().str.upper()
    
    # Garante que ambas as planilhas tenham a coluna QTD
    # Se não tiver QTD, conta cada linha como 1 profissional
    if "QTD" not in cred_2025.columns:
        cred_2025["QTD"] = 1
    if "QTD" not in desm_2024.columns:
        desm_2024["QTD"] = 1
    
    # Adiciona coluna de origem
    cred_2025["ORIGEM"] = "2025"
    desm_2024["ORIGEM"] = "Desmontagem 2024"
    
    # Concatena os dados de credenciamento
    cred = pd.concat([cred_2025, desm_2024], ignore_index=True)

    if "DATA" in cred.columns:
        cred["DATA"] = pd.to_datetime(cred["DATA"], errors="coerce")
    
    # Converte todas as colunas object para string para evitar erros do PyArrow
    # Exceto colunas numéricas e de data
    for col in cred.columns:
        if cred[col].dtype == 'object' and col != 'DATA':
            cred[col] = cred[col].astype(str)
    
    # Tratamento especial para colunas de CPF no credenciamento
    cpf_columns = [col for col in cred.columns if 'CPF' in col.upper()]
    for col in cpf_columns:
        # Remove valores inválidos
        cred[col] = cred[col].replace(['nan', 'None', 'NaN', ''], None)
        # Preenche com zeros à esquerda para ter 11 dígitos
        cred[col] = cred[col].apply(
            lambda x: x.zfill(11) if x is not None and x not in ['nan', 'None', 'NaN', '', 'None'] else None
        )
    
    # Adiciona informação de evento baseado na data do credenciamento
    # Cria mapeamento entre datas e eventos a partir da bilhetagem
    if "TDL Event Date" in bilhetes_final.columns and "TDL Event" in bilhetes_final.columns:
        mapa_data_evento = (
            bilhetes_final[["TDL Event Date", "TDL Event"]]
            .drop_duplicates()
            .set_index("TDL Event Date")["TDL Event"]
            .to_dict()
        )
        
        # Mapeia evento baseado na data
        if "DATA" in cred.columns:
            cred["EVENTO"] = cred["DATA"].map(mapa_data_evento)

    return bilhetes_final, cred


def obter_coordenadas_bairros():
    """
    Retorna um dicionário com as coordenadas (lat, lon) aproximadas
    dos principais bairros do Rio de Janeiro.
    """
    return {
        # Zona Sul
        "Copacabana": (-22.9711, -43.1822),
        "Ipanema": (-22.9838, -43.2047),
        "Leblon": (-22.9840, -43.2237),
        "Botafogo": (-22.9479, -43.1828),
        "Flamengo": (-22.9323, -43.1751),
        "Laranjeiras": (-22.9367, -43.1888),
        "Catete": (-22.9265, -43.1777),
        "Glória": (-22.9206, -43.1764),
        "Humaitá": (-22.9512, -43.1942),
        "Urca": (-22.9498, -43.1656),
        "Leme": (-22.9651, -43.1691),
        "Lagoa": (-22.9703, -43.2051),
        "Jardim Botânico": (-22.9662, -43.2244),
        "Gávea": (-22.9794, -43.2336),
        "São Conrado": (-23.0078, -43.2677),
        "Vidigal": (-22.9928, -43.2326),
        "Rocinha": (-22.9881, -43.2490),
        
        # Centro
        "Centro": (-22.9035, -43.1773),
        "Lapa": (-22.9142, -43.1795),
        "Santa Teresa": (-22.9204, -43.1901),
        "Cinelândia": (-22.9097, -43.1755),
        "Castelo": (-22.9058, -43.1736),
        "Saúde": (-22.8950, -43.1829),
        "Gamboa": (-22.8979, -43.1897),
        "Santo Cristo": (-22.8959, -43.1960),
        "Caju": (-22.8806, -43.2124),
        "Cidade Nova": (-22.9118, -43.2075),
        
        # Zona Norte
        "Tijuca": (-22.9213, -43.2314),
        "Vila Isabel": (-22.9166, -43.2485),
        "Grajaú": (-22.9191, -43.2611),
        "Andaraí": (-22.9265, -43.2488),
        "Maracanã": (-22.9121, -43.2302),
        "Alto da Boa Vista": (-22.9587, -43.2716),
        "Praça da Bandeira": (-22.9072, -43.2177),
        "São Cristóvão": (-22.8999, -43.2223),
        "Mangueira": (-22.9052, -43.2396),
        "Benfica": (-22.8971, -43.2391),
        "Sampaio": (-22.9187, -43.2808),
        "Engenho Novo": (-22.9030, -43.2683),
        "Riachuelo": (-22.9094, -43.2630),
        "Rocha": (-22.9217, -43.2441),
        "Todos os Santos": (-22.9078, -43.2823),
        "Méier": (-22.9025, -43.2785),
        "Cachambi": (-22.8968, -43.2732),
        "Engenho de Dentro": (-22.9014, -43.2946),
        "Lins de Vasconcelos": (-22.9164, -43.2757),
        "Abolição": (-22.8919, -43.2912),
        "Água Santa": (-22.9109, -43.3010),
        "Encantado": (-22.8989, -43.2892),
        "Piedade": (-22.9006, -43.3047),
        "Pilares": (-22.8857, -43.2995),
        "Inhaúma": (-22.8847, -43.2789),
        "Del Castilho": (-22.8838, -43.2676),
        "Maria da Graça": (-22.8863, -43.2607),
        "Tomás Coelho": (-22.8802, -43.2954),
        "Jacaré": (-22.8916, -43.2490),
        "Jacarezinho": (-22.8861, -43.2559),
        "Complexo do Alemão": (-22.8638, -43.2632),
        "Higienópolis": (-22.8676, -43.3126),
        "Bonsucesso": (-22.8663, -43.2518),
        "Ramos": (-22.8468, -43.2455),
        "Olaria": (-22.8455, -43.2640),
        "Penha": (-22.8413, -43.2796),
        "Penha Circular": (-22.8350, -43.2901),
        "Brás de Pina": (-22.8316, -43.2896),
        "Cordovil": (-22.8274, -43.3057),
        "Parada de Lucas": (-22.8175, -43.3182),
        "Vigário Geral": (-22.8181, -43.3314),
        "Jardim América": (-22.8063, -43.3274),
        "Vila da Penha": (-22.8388, -43.3094),
        "Vista Alegre": (-22.8288, -43.3241),
        "Irajá": (-22.8317, -43.3323),
        "Colégio": (-22.8240, -43.3413),
        "Vicente de Carvalho": (-22.8471, -43.3170),
        "Vila Kosmos": (-22.8506, -43.2988),
        "Madureira": (-22.8715, -43.3363),
        "Oswaldo Cruz": (-22.8572, -43.3461),
        "Bento Ribeiro": (-22.8665, -43.3614),
        "Marechal Hermes": (-22.8764, -43.3675),
        "Rocha Miranda": (-22.8483, -43.3526),
        "Turiaçu": (-22.8329, -43.3542),
        "Cascadura": (-22.8848, -43.3305),
        "Campinho": (-22.8824, -43.3447),
        "Quintino Bocaiuva": (-22.8866, -43.3204),
        "Cavalcanti": (-22.8787, -43.3104),
        "Engenheiro Leal": (-22.8673, -43.3036),
        "Honório Gurgel": (-22.8528, -43.3374),
        "Guadalupe": (-22.8445, -43.3665),
        "Acari": (-22.8262, -43.3424),
        "Costa Barros": (-22.8114, -43.3563),
        "Pavuna": (-22.8066, -43.3714),
        "Anchieta": (-22.8239, -43.3962),
        "Parque Anchieta": (-22.8170, -43.3858),
        "Ricardo de Albuquerque": (-22.8356, -43.3867),
        "Coelho Neto": (-22.8237, -43.3577),
        
        # Zona Oeste
        "Barra da Tijuca": (-23.0052, -43.3153),
        "Recreio dos Bandeirantes": (-23.0257, -43.4618),
        "Jacarepaguá": (-22.9327, -43.3659),
        "Freguesia": (-22.9320, -43.3404),
        "Pechincha": (-22.9243, -43.3554),
        "Taquara": (-22.9205, -43.3679),
        "Tanque": (-22.9133, -43.3629),
        "Praça Seca": (-22.8999, -43.3496),
        "Vila Valqueire": (-22.8844, -43.3653),
        "Curicica": (-22.9655, -43.3623),
        "Camorim": (-22.9735, -43.4172),
        "Vargem Grande": (-22.9872, -43.4962),
        "Vargem Pequena": (-22.9979, -43.4683),
        "Anil": (-22.9463, -43.3413),
        "Gardênia Azul": (-22.9454, -43.3565),
        "Cidade de Deus": (-22.9451, -43.3616),
        "Itanhangá": (-23.0032, -43.3399),
        "Joá": (-23.0134, -43.2889),
        "Grumari": (-23.0445, -43.5227),
        "Bangu": (-22.8781, -43.4619),
        "Senador Camará": (-22.8645, -43.4877),
        "Gericinó": (-22.8734, -43.4394),
        "Padre Miguel": (-22.8772, -43.4558),
        "Realengo": (-22.8821, -43.4345),
        "Campo dos Afonsos": (-22.8863, -43.4116),
        "Magalhães Bastos": (-22.8931, -43.4082),
        "Vila Militar": (-22.8635, -43.3943),
        "Deodoro": (-22.8556, -43.3829),
        "Jardim Sulacap": (-22.8900, -43.4875),
        "Campo Grande": (-22.9067, -43.5563),
        "Senador Vasconcelos": (-22.8787, -43.6398),
        "Inhoaíba": (-22.9214, -43.5767),
        "Cosmos": (-22.9191, -43.6081),
        "Santíssimo": (-22.9029, -43.5937),
        "Santa Cruz": (-22.9193, -43.6853),
        "Paciência": (-22.8800, -43.6614),
        "Sepetiba": (-22.9750, -43.7080),
        "Guaratiba": (-23.0547, -43.6010),
        "Barra de Guaratiba": (-23.0752, -43.5726),
        "Pedra de Guaratiba": (-23.0895, -43.6304),
    }


def adicionar_regiao_administrativa(df_bilhete):
    """
    Aqui entra o mapeamento Bairro -> Região Administrativa (RA).
    Por enquanto, deixo como esqueleto com um dicionário vazio
    para depois você preencher com a tabela de mapeamento.
    """
    df = df_bilhete.copy()

    bairro_col = "WEB Customer Address Extension 3 - Bairro"
    if bairro_col not in df.columns:
        df["Região Administrativa"] = "Não informado"
        return df

    # Mapeamento de bairros do Rio de Janeiro para Regiões Administrativas
    bairro_para_ra = {
        # Zona Sul
        "Copacabana": "Zona Sul",
        "Ipanema": "Zona Sul",
        "Leblon": "Zona Sul",
        "Botafogo": "Zona Sul",
        "Flamengo": "Zona Sul",
        "Laranjeiras": "Zona Sul",
        "Catete": "Zona Sul",
        "Glória": "Zona Sul",
        "Humaitá": "Zona Sul",
        "Urca": "Zona Sul",
        "Leme": "Zona Sul",
        "Lagoa": "Zona Sul",
        "Jardim Botânico": "Zona Sul",
        "Gávea": "Zona Sul",
        "São Conrado": "Zona Sul",
        "Vidigal": "Zona Sul",
        "Rocinha": "Zona Sul",
        
        # Centro
        "Centro": "Centro",
        "Lapa": "Centro",
        "Santa Teresa": "Centro",
        "Cinelândia": "Centro",
        "Castelo": "Centro",
        "Saúde": "Centro",
        "Gamboa": "Centro",
        "Santo Cristo": "Centro",
        "Caju": "Centro",
        "Cidade Nova": "Centro",
        
        # Zona Norte
        "Tijuca": "Zona Norte",
        "Vila Isabel": "Zona Norte",
        "Grajaú": "Zona Norte",
        "Andaraí": "Zona Norte",
        "Maracanã": "Zona Norte",
        "Alto da Boa Vista": "Zona Norte",
        "Praça da Bandeira": "Zona Norte",
        "São Cristóvão": "Zona Norte",
        "Mangueira": "Zona Norte",
        "Benfica": "Zona Norte",
        "Sampaio": "Zona Norte",
        "Engenho Novo": "Zona Norte",
        "Riachuelo": "Zona Norte",
        "Rocha": "Zona Norte",
        "Todos os Santos": "Zona Norte",
        "Méier": "Zona Norte",
        "Cachambi": "Zona Norte",
        "Engenho de Dentro": "Zona Norte",
        "Lins de Vasconcelos": "Zona Norte",
        "Abolição": "Zona Norte",
        "Água Santa": "Zona Norte",
        "Encantado": "Zona Norte",
        "Piedade": "Zona Norte",
        "Pilares": "Zona Norte",
        "Inhaúma": "Zona Norte",
        "Del Castilho": "Zona Norte",
        "Maria da Graça": "Zona Norte",
        "Tomás Coelho": "Zona Norte",
        "Jacaré": "Zona Norte",
        "Jacarezinho": "Zona Norte",
        "Complexo do Alemão": "Zona Norte",
        "Higienópolis": "Zona Norte",
        "Bonsucesso": "Zona Norte",
        "Ramos": "Zona Norte",
        "Olaria": "Zona Norte",
        "Penha": "Zona Norte",
        "Penha Circular": "Zona Norte",
        "Brás de Pina": "Zona Norte",
        "Cordovil": "Zona Norte",
        "Parada de Lucas": "Zona Norte",
        "Vigário Geral": "Zona Norte",
        "Jardim América": "Zona Norte",
        "Vila da Penha": "Zona Norte",
        "Vista Alegre": "Zona Norte",
        "Irajá": "Zona Norte",
        "Colégio": "Zona Norte",
        "Vicente de Carvalho": "Zona Norte",
        "Vila Kosmos": "Zona Norte",
        "Madureira": "Zona Norte",
        "Oswaldo Cruz": "Zona Norte",
        "Bento Ribeiro": "Zona Norte",
        "Marechal Hermes": "Zona Norte",
        "Rocha Miranda": "Zona Norte",
        "Turiaçu": "Zona Norte",
        "Cascadura": "Zona Norte",
        "Campinho": "Zona Norte",
        "Quintino Bocaiuva": "Zona Norte",
        "Cavalcanti": "Zona Norte",
        "Engenheiro Leal": "Zona Norte",
        "Honório Gurgel": "Zona Norte",
        "Guadalupe": "Zona Norte",
        "Acari": "Zona Norte",
        "Costa Barros": "Zona Norte",
        "Pavuna": "Zona Norte",
        "Anchieta": "Zona Norte",
        "Parque Anchieta": "Zona Norte",
        "Ricardo de Albuquerque": "Zona Norte",
        "Coelho Neto": "Zona Norte",
        
        # Zona Oeste
        "Barra da Tijuca": "Zona Oeste",
        "Recreio dos Bandeirantes": "Zona Oeste",
        "Jacarepaguá": "Zona Oeste",
        "Freguesia": "Zona Oeste",
        "Pechincha": "Zona Oeste",
        "Taquara": "Zona Oeste",
        "Tanque": "Zona Oeste",
        "Praça Seca": "Zona Oeste",
        "Vila Valqueire": "Zona Oeste",
        "Curicica": "Zona Oeste",
        "Camorim": "Zona Oeste",
        "Vargem Grande": "Zona Oeste",
        "Vargem Pequena": "Zona Oeste",
        "Anil": "Zona Oeste",
        "Gardênia Azul": "Zona Oeste",
        "Cidade de Deus": "Zona Oeste",
        "Itanhangá": "Zona Oeste",
        "Joá": "Zona Oeste",
        "Grumari": "Zona Oeste",
        "Bangu": "Zona Oeste",
        "Senador Camará": "Zona Oeste",
        "Gericinó": "Zona Oeste",
        "Padre Miguel": "Zona Oeste",
        "Realengo": "Zona Oeste",
        "Campo dos Afonsos": "Zona Oeste",
        "Magalhães Bastos": "Zona Oeste",
        "Vila Militar": "Zona Oeste",
        "Deodoro": "Zona Oeste",
        "Jardim Sulacap": "Zona Oeste",
        "Campo Grande": "Zona Oeste",
        "Senador Vasconcelos": "Zona Oeste",
        "Inhoaíba": "Zona Oeste",
        "Cosmos": "Zona Oeste",
        "Santíssimo": "Zona Oeste",
        "Santa Cruz": "Zona Oeste",
        "Paciência": "Zona Oeste",
        "Sepetiba": "Zona Oeste",
        "Guaratiba": "Zona Oeste",
        "Barra de Guaratiba": "Zona Oeste",
        "Pedra de Guaratiba": "Zona Oeste",
    }

    df["Região Administrativa"] = (
        df[bairro_col]
        .map(bairro_para_ra)
        .fillna("RA não mapeada")
    )

    return df


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
    bilhetes, cred = load_data()

    # Aba de navegação
    tab_bilhetagem, tab_credenciamento = st.tabs(["🎟 Bilhetagem", "👷 Credenciamento"])

    # ==============================
    # ABA 1 – BILHETAGEM
    # ==============================
    with tab_bilhetagem:
        st.subheader("🎟 Análises de Bilhetagem")

        bilhetes = adicionar_regiao_administrativa(bilhetes)

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
        ras = sorted(bilhetes["Região Administrativa"].dropna().unique())
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
            df_b = df_b[df_b["Região Administrativa"].isin(ra_sel)]

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
        st.markdown("### 📊 Análise de Comportamento de Compra")
        
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            st.markdown("#### Distribuição de Ingressos por Cliente")
            if not df_b.empty:
                ingressos_por_cliente = (
                    df_b.groupby("TDL Customer CPF")["TDL Sum Tickets (B+S-A)"]
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
                
                fig_dist = px.bar(
                    dist_faixa,
                    x="Faixa",
                    y="Quantidade de Clientes",
                    labels={"Faixa": "Quantidade de Ingressos", "Quantidade de Clientes": "Clientes"},
                    title="Quantos ingressos cada cliente comprou?"
                )
                st.plotly_chart(fig_dist, use_container_width=True)
                
                with st.expander("📊 Ver dados da tabela"):
                    st.dataframe(dist_faixa, hide_index=True, use_container_width=True)
        
        with col_comp2:
            st.markdown("#### Top 10 Clientes (por quantidade de ingressos)")
            if not df_b.empty:
                top_clientes = (
                    df_b.groupby("TDL Customer CPF")[["TDL Sum Tickets (B+S-A)", "TDL Sum Ticket Net Price (B+S-A)"]]
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
                df_b.groupby("TDL Customer CPF")["TDL Event"]
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
            st.plotly_chart(fig_recorrencia, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                st.dataframe(dist_recorrencia, hide_index=True, use_container_width=True)

        # ==============================
        # Dados Demográficos
        # ==============================
        st.markdown("---")
        st.markdown("### 👥 Dados Demográficos")
        
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
                genero_count = genero_count.sort_values("Quantidade", ascending=False)
                
                fig_genero = px.pie(
                    genero_count,
                    values="Quantidade",
                    names="Gênero",
                    title="Ingressos por Gênero",
                    hole=0.4
                )
                st.plotly_chart(fig_genero, use_container_width=True)
                
                with st.expander("📊 Ver dados da tabela"):
                    st.dataframe(genero_count, hide_index=True, use_container_width=True)
            else:
                st.info("Dados de gênero não disponíveis na base de dados.")
        
        with col_demo2:
            st.markdown("#### Distribuição por Faixa Etária")
            if "Faixa Etária" in df_b.columns:
                idade_count = df_b["Faixa Etária"].value_counts().sort_index().reset_index()
                idade_count.columns = ["Faixa Etária", "Quantidade"]
                
                fig_idade = px.bar(
                    idade_count,
                    x="Faixa Etária",
                    y="Quantidade",
                    labels={"Faixa Etária": "Idade", "Quantidade": "Ingressos"},
                    title="Ingressos por Faixa Etária"
                )
                st.plotly_chart(fig_idade, use_container_width=True)
                
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
                title="Distribuição de ingressos por gênero e faixa etária"
            )
            st.plotly_chart(fig_cruzamento, use_container_width=True)
            
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

        st.markdown("---")
        st.markdown("### 📍 Análises Geográficas")

        st.markdown("#### Ingressos ao longo do tempo")
        if not df_b.empty:
            vendas_por_dia = (
                df_b.groupby("TDL Event Date")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
            )
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
            st.plotly_chart(fig_tempo, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                vendas_por_dia_display = vendas_por_dia.copy()
                vendas_por_dia_display["TDL Event Date"] = vendas_por_dia_display["TDL Event Date"].dt.strftime("%d/%m/%Y")
                vendas_por_dia_display.columns = ["Data", "Ingressos"]
                st.dataframe(vendas_por_dia_display, hide_index=True, use_container_width=True)

        st.markdown("#### Top Regiões Administrativas (Ingressos)")
        if not df_b.empty:
            por_ra = (
                df_b.groupby("Região Administrativa")["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
            )
            
            col_mapa_ra, col_bar_ra = st.columns([1, 1])
            
            with col_mapa_ra:
                # Mapa com coordenadas centrais de cada região administrativa
                coordenadas_ra = {
                    "Zona Sul": (-22.9711, -43.1822),
                    "Centro": (-22.9035, -43.1773),
                    "Zona Norte": (-22.9025, -43.2785),
                    "Zona Oeste": (-23.0052, -43.3153)
                }
                
                por_ra_mapa = por_ra[por_ra["Região Administrativa"].isin(coordenadas_ra.keys())].copy()
                por_ra_mapa["lat"] = por_ra_mapa["Região Administrativa"].map(lambda x: coordenadas_ra.get(x, (None, None))[0])
                por_ra_mapa["lon"] = por_ra_mapa["Região Administrativa"].map(lambda x: coordenadas_ra.get(x, (None, None))[1])
                por_ra_mapa = por_ra_mapa.dropna(subset=["lat", "lon"])
                
                if not por_ra_mapa.empty:
                    # Normaliza valores para o tamanho dos círculos
                    max_ingressos = por_ra_mapa["TDL Sum Tickets (B+S-A)"].max()
                    por_ra_mapa["size"] = (por_ra_mapa["TDL Sum Tickets (B+S-A)"] / max_ingressos) * 100 + 20
                    
                    fig_mapa_ra = px.scatter_mapbox(
                        por_ra_mapa,
                        lat="lat",
                        lon="lon",
                        size="size",
                        color="TDL Sum Tickets (B+S-A)",
                        hover_name="Região Administrativa",
                        hover_data={"TDL Sum Tickets (B+S-A)": True, "lat": False, "lon": False, "size": False},
                        color_continuous_scale="YlOrRd",
                        size_max=50,
                        zoom=9.5,
                        center={"lat": -22.9068, "lon": -43.1729},
                        mapbox_style="open-street-map",
                        labels={"TDL Sum Tickets (B+S-A)": "Ingressos"},
                        title="Mapa de Ingressos por Região Administrativa"
                    )
                    
                    fig_mapa_ra.update_layout(
                        height=450,
                        margin={"r":0,"t":40,"l":0,"b":0}
                    )
                    
                    st.plotly_chart(fig_mapa_ra, use_container_width=True)
                else:
                    st.info("Dados de região administrativa não disponíveis para o mapa.")
            
            with col_bar_ra:
                fig_ra = px.bar(
                    por_ra,
                    x="Região Administrativa",
                    y="TDL Sum Tickets (B+S-A)",
                    labels={
                        "Região Administrativa": "Região Administrativa",
                        "TDL Sum Tickets (B+S-A)": "Ingressos"
                    },
                    title="Ingressos por Região Administrativa",
                    color="TDL Sum Tickets (B+S-A)",
                    color_continuous_scale="Blues"
                )
                fig_ra.update_layout(height=450, showlegend=False)
                st.plotly_chart(fig_ra, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                por_ra_display = por_ra.copy()
                por_ra_display.columns = ["Região Administrativa", "Ingressos"]
                st.dataframe(por_ra_display, hide_index=True, use_container_width=True)

        st.markdown("#### Mapa de Calor - Ingressos por Bairro")
        bairro_col = "WEB Customer Address Extension 3 - Bairro"
        if not df_b.empty and bairro_col in df_b.columns:
            # Agrupa por bairro
            por_bairro = (
                df_b.groupby(bairro_col)["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
                .sort_values("TDL Sum Tickets (B+S-A)", ascending=False)
            )
            
            # Adiciona coordenadas
            coordenadas = obter_coordenadas_bairros()
            por_bairro["lat"] = por_bairro[bairro_col].map(lambda x: coordenadas.get(x, (None, None))[0])
            por_bairro["lon"] = por_bairro[bairro_col].map(lambda x: coordenadas.get(x, (None, None))[1])
            
            # Remove bairros sem coordenadas
            por_bairro = por_bairro.dropna(subset=["lat", "lon"])
            
            if not por_bairro.empty:
                # Cria o mapa de densidade
                fig_mapa = px.density_mapbox(
                    por_bairro,
                    lat="lat",
                    lon="lon",
                    z="TDL Sum Tickets (B+S-A)",
                    radius=15,
                    center={"lat": -22.9068, "lon": -43.1729},  # Centro do Rio
                    zoom=10,
                    mapbox_style="open-street-map",
                    hover_name=bairro_col,
                    hover_data={"TDL Sum Tickets (B+S-A)": True, "lat": False, "lon": False},
                    labels={"TDL Sum Tickets (B+S-A)": "Ingressos"},
                    title="Densidade de ingressos vendidos por bairro"
                )
                
                fig_mapa.update_layout(
                    height=600,
                    margin={"r":0,"t":40,"l":0,"b":0}
                )
                
                st.plotly_chart(fig_mapa, use_container_width=True)
                
                # Mostra top 10 bairros
                st.markdown("##### Top 10 Bairros")
                top_bairros = por_bairro.head(10)[[bairro_col, "TDL Sum Tickets (B+S-A)"]]
                top_bairros.columns = ["Bairro", "Ingressos"]
                st.dataframe(top_bairros, hide_index=True)
            else:
                st.info("Não há dados de bairros com coordenadas mapeadas para exibir no mapa.")

        st.markdown("#### Bairros por Tipo de Ingresso")
        bairro_col = "WEB Customer Address Extension 3 - Bairro"
        tipo_ingresso_col = "TDL Price Category"
        
        if not df_b.empty and bairro_col in df_b.columns and tipo_ingresso_col in df_b.columns:
            # Agrupa por bairro e tipo de ingresso
            bairro_tipo = (
                df_b.groupby([bairro_col, tipo_ingresso_col])["TDL Sum Tickets (B+S-A)"]
                .sum()
                .reset_index()
            )
            
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
                    title="Top 15 Bairros por Tipo de Ingresso"
                )
                
                fig_bairro_tipo.update_layout(
                    xaxis={'categoryorder':'total descending'},
                    height=500
                )
                
                st.plotly_chart(fig_bairro_tipo, use_container_width=True)
                
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

        # Tabela
        st.markdown("#### Amostra dos dados de bilhetagem")
        st.dataframe(df_b)

    # ==============================
    # ABA 2 – CREDENCIAMENTO
    # ==============================
    with tab_credenciamento:
        st.subheader("👷 Análises de Credenciamento")

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

        # Conta profissionais únicos por CPF (evita duplicatas)
        cpf_cols_cred = [col for col in df_c.columns if 'CPF' in col.upper()]
        if cpf_cols_cred:
            # Remove valores None/nan antes de contar
            cpf_unicos = df_c[df_c[cpf_cols_cred[0]].notna() & (df_c[cpf_cols_cred[0]] != 'None')][cpf_cols_cred[0]].nunique()
            col_a.metric("Profissionais únicos (CPF)", int(cpf_unicos))
        elif "QTD" in df_c.columns:
            total_profissionais = df_c["QTD"].sum()
            col_a.metric("Total de registros", int(total_profissionais))
        
        # Total de credenciamentos (soma de QTD)
        if "QTD" in df_c.columns:
            total_credenciamentos = df_c["QTD"].sum()
            col_b.metric("Total de credenciamentos", int(total_credenciamentos))
        elif "CATEGORIA" in df_c.columns:
            total_categorias = df_c["CATEGORIA"].nunique()
            col_b.metric("Categorias únicas", int(total_categorias))
        
        if "EMPRESA" in df_c.columns:
            total_empresas = df_c["EMPRESA"].nunique()
            col_c.metric("Empresas envolvidas", int(total_empresas))

        # Análise de profissionais por evento e dia
        if "EVENTO" in df_c.columns and "DATA" in df_c.columns:
            st.markdown("#### Profissionais por Evento e Dia")
            
            # Conta profissionais únicos por evento e data
            cpf_col_cred = [col for col in df_c.columns if 'CPF' in col.upper()]
            if cpf_col_cred:
                prof_por_evento_dia = (
                    df_c[df_c[cpf_col_cred[0]].notna() & (df_c[cpf_col_cred[0]] != 'None')]
                    .groupby(["EVENTO", "DATA"])[cpf_col_cred[0]]
                    .nunique()
                    .reset_index()
                )
                prof_por_evento_dia.columns = ["Evento", "Data", "Profissionais Únicos"]
                prof_por_evento_dia["Data"] = pd.to_datetime(prof_por_evento_dia["Data"]).dt.strftime("%d/%m/%Y")
                
                # Remove eventos None
                prof_por_evento_dia = prof_por_evento_dia[prof_por_evento_dia["Evento"].notna()]
                
                if not prof_por_evento_dia.empty:
                    # Cria tabela pivotada
                    tabela_evento_dia = prof_por_evento_dia.pivot(
                        index="Data",
                        columns="Evento",
                        values="Profissionais Únicos"
                    ).fillna(0).astype(int)
                    
                    # Adiciona total por linha
                    tabela_evento_dia['Total'] = tabela_evento_dia.sum(axis=1)
                    
                    st.dataframe(tabela_evento_dia, use_container_width=True)
                    
                    with st.expander("📊 Ver gráfico"):
                        # Gráfico de barras empilhadas
                        prof_por_evento_dia_num = prof_por_evento_dia.copy()
                        prof_por_evento_dia_num["Data"] = pd.to_datetime(prof_por_evento_dia_num["Data"], format="%d/%m/%Y")
                        
                        fig_evento_dia = px.bar(
                            prof_por_evento_dia_num,
                            x="Data",
                            y="Profissionais Únicos",
                            color="Evento",
                            barmode="stack",
                            labels={
                                "Data": "Data",
                                "Profissionais Únicos": "Profissionais",
                                "Evento": "Evento"
                            },
                            title="Profissionais únicos por evento e dia"
                        )
                        fig_evento_dia.update_layout(height=500)
                        st.plotly_chart(fig_evento_dia, use_container_width=True)
                else:
                    st.info("Não há dados de eventos mapeados para o período selecionado.")
            
            st.markdown("---")
        
        st.markdown("#### (a) Total de profissionais por categoria e etapa")
        if not df_c.empty and "CATEGORIA" in df_c.columns and "ETAPA" in df_c.columns and "QTD" in df_c.columns:
            total_cat_etapa = (
                df_c.groupby(["CATEGORIA", "ETAPA"])["QTD"]
                .sum()
                .reset_index()
            )

            fig_total = px.bar(
                total_cat_etapa,
                x="CATEGORIA",
                y="QTD",
                color="ETAPA",
                barmode="stack",
                labels={
                    "CATEGORIA": "Categoria",
                    "QTD": "Total de profissionais",
                    "ETAPA": "Etapa"
                },
                title="Total de profissionais por categoria e etapa (empilhado)"
            )
            
            fig_total.update_layout(
                xaxis={'categoryorder':'total descending'},
                height=500
            )
            
            st.plotly_chart(fig_total, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                # Cria tabela pivotada para melhor visualização
                tabela_cat_etapa = total_cat_etapa.pivot(index="CATEGORIA", columns="ETAPA", values="QTD").fillna(0)
                tabela_cat_etapa = tabela_cat_etapa.astype(int)
                tabela_cat_etapa['Total'] = tabela_cat_etapa.sum(axis=1)
                tabela_cat_etapa = tabela_cat_etapa.sort_values('Total', ascending=False)
                st.dataframe(tabela_cat_etapa, use_container_width=True)

        st.markdown("#### (b) Média de profissionais por categoria em cada dia do evento")
        if not df_c.empty and "dia_label" in df_c.columns and "CATEGORIA" in df_c.columns and "QTD" in df_c.columns:
            # Filtra apenas os dias do evento (qua a dom)
            dias_evento = ["Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            df_c_evento = df_c[df_c["dia_label"].isin(dias_evento)]
            
            if not df_c_evento.empty:
                media_cat_dia = (
                    df_c_evento.groupby(["dia_label", "CATEGORIA"])["QTD"]
                    .mean()
                    .reset_index()
                )

                # Ordena dias na sequência desejada
                ordem_dias = ["Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                media_cat_dia["dia_label"] = pd.Categorical(
                    media_cat_dia["dia_label"], categories=ordem_dias, ordered=True
                )
                media_cat_dia = media_cat_dia.sort_values("dia_label")

                fig_media = px.bar(
                    media_cat_dia,
                    x="dia_label",
                    y="QTD",
                    color="CATEGORIA",
                    barmode="stack",
                    labels={
                        "dia_label": "Dia da Semana",
                        "QTD": "Média de profissionais",
                        "CATEGORIA": "Categoria"
                    },
                    title="Média de profissionais por categoria em cada dia do evento"
                )
                
                fig_media.update_layout(height=500)
                st.plotly_chart(fig_media, use_container_width=True)
                
                with st.expander("📊 Ver dados da tabela"):
                    # Cria tabela pivotada para melhor visualização
                    tabela_media_dia = media_cat_dia.pivot(index="dia_label", columns="CATEGORIA", values="QTD").fillna(0)
                    tabela_media_dia = tabela_media_dia.round(2)
                    st.dataframe(tabela_media_dia, use_container_width=True)
            else:
                st.info("Não há dados para os dias do evento (quarta a domingo).")

        st.markdown("#### Distribuição por dia da semana")
        if not df_c.empty and "dia_label" in df_c.columns and "QTD" in df_c.columns:
            profissionais_por_dia = (
                df_c.groupby("dia_label")["QTD"]
                .sum()
                .reset_index()
            )
            
            # Ordena os dias
            ordem_todos_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            profissionais_por_dia["dia_label"] = pd.Categorical(
                profissionais_por_dia["dia_label"], categories=ordem_todos_dias, ordered=True
            )
            profissionais_por_dia = profissionais_por_dia.sort_values("dia_label")
            
            fig_dia = px.bar(
                profissionais_por_dia,
                x="dia_label",
                y="QTD",
                labels={
                    "dia_label": "Dia da Semana",
                    "QTD": "Total de profissionais"
                },
                title="Total de profissionais por dia da semana"
            )
            st.plotly_chart(fig_dia, use_container_width=True)
            
            with st.expander("📊 Ver dados da tabela"):
                profissionais_por_dia_display = profissionais_por_dia.copy()
                profissionais_por_dia_display.columns = ["Dia da Semana", "Total de Profissionais"]
                st.dataframe(profissionais_por_dia_display, hide_index=True, use_container_width=True)

        st.markdown("#### Amostra dos dados de credenciamento")
        st.dataframe(df_c)


if __name__ == "__main__":
    main()
