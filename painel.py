import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Dashboard Hidrológico", layout="wide")
st.title("🏗️ Dashboard Hidrológico para Engenharia - Matupá")

@st.cache_data
def carregar_dados():
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta_atual, '1054002_Chuvas.csv')
    
    df = pd.read_csv(caminho, sep=';', skiprows=14, decimal=',', encoding='latin-1')
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    
    chuva_cols = [f'Chuva{i:02d}' for i in range(1, 32)]
    df_long = df.melt(id_vars=['Data'], value_vars=chuva_cols, var_name='Dia', value_name='Chuva')
    df_long['Dia'] = df_long['Dia'].str.replace('Chuva', '').astype(int)
    
    def criar_data(row):
        try:
            return pd.Timestamp(year=row['Data'].year, month=row['Data'].month, day=row['Dia'])
        except:
            return pd.NaT

    df_long['Data_Completa'] = df_long.apply(criar_data, axis=1)
    df_clean = df_long.dropna(subset=['Data_Completa']).copy()
    
    df_clean['Ano'] = df_clean['Data_Completa'].dt.year
    df_clean['Mes'] = df_clean['Data_Completa'].dt.month
    df_clean['Ano_Mes'] = pd.to_datetime(df_clean['Ano'].astype(str) + '-' + df_clean['Mes'].astype(str).str.zfill(2) + '-01')
    
    return df_clean

try:
    df = carregar_dados()

    # --- BARRA LATERAL (FILTROS GERAIS) ---
    st.sidebar.title("⚙️ Filtros Gerais")
    st.sidebar.write("Aplica-se a todas as abas:")
    
    ano_min = int(df['Ano'].min())
    ano_max = int(df['Ano'].max())

    anos_selecionados = st.sidebar.slider(
        "Selecione o Período:", 
        min_value=ano_min, 
        max_value=ano_max, 
        value=(ano_max - 10, ano_max)
    )

    df_filtrado = df[(df['Ano'] >= anos_selecionados[0]) & (df['Ano'] <= anos_selecionados[1])].copy()

    # --- ABAS DO DASHBOARD ---
    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "📅 Visão Anual", 
        "📉 Visão Mensal", 
        "🌧️ Dias Chuvosos",
        "🔍 Detalhe Diário",
        "🚜 Janelas de Terraplenagem (Heatmap)"
    ])

    with aba1:
        st.subheader(f"Volume Total de Chuva por Ano ({anos_selecionados[0]} a {anos_selecionados[1]})")
        df_anual = df_filtrado.groupby('Ano')['Chuva'].sum().reset_index()
        fig1 = px.bar(df_anual, x='Ano', y='Chuva', labels={'Chuva': 'Precipitação (mm)'}, text_auto='.0f')
        fig1.update_xaxes(dtick=1)
        st.plotly_chart(fig1, use_container_width=True)

    with aba2:
        st.subheader("Volume Mensal (Visão Macro)")
        df_mensal = df_filtrado.groupby('Ano_Mes')['Chuva'].sum().reset_index()
        fig2 = px.bar(df_mensal, x='Ano_Mes', y='Chuva', labels={'Chuva': 'Precipitação (mm)'})
        fig2.update_xaxes(tickformat="%m/%Y") 
        st.plotly_chart(fig2, use_container_width=True)

    with aba3:
        st.subheader("Dias de chuva por mês (Impacto no Cronograma)")
        df_filtrado['Dia_Chuvoso'] = df_filtrado['Chuva'] > 0
        df_dias = df_filtrado.groupby('Ano_Mes')['Dia_Chuvoso'].sum().reset_index()
        fig3 = px.bar(df_dias, x='Ano_Mes', y='Dia_Chuvoso', labels={'Dia_Chuvoso': 'Nº de Dias Chuvosos'}, text_auto='.0f')
        fig3.update_xaxes(tickformat="%m/%Y")
        st.plotly_chart(fig3, use_container_width=True)

    with aba4:
        st.subheader("Analise o comportamento diário de um mês específico")
        col1, col2 = st.columns(2)
        with col1:
            ano_escolhido = st.selectbox("Escolha o Ano:", sorted(df['Ano'].unique(), reverse=True))
        with col2:
            mes_escolhido = st.selectbox("Escolha o Mês:", range(1, 13), format_func=lambda x: f"{x:02d}")
        
        df_mes_especifico = df[(df['Ano'] == ano_escolhido) & (df['Mes'] == mes_escolhido)].sort_values('Dia')
        
        if not df_mes_especifico.empty:
            max_chuva = df_mes_especifico['Chuva'].max()
            total_chuva = df_mes_especifico['Chuva'].sum()
            dias_com_chuva = (df_mes_especifico['Chuva'] > 0).sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Precipitação Total do Mês", f"{total_chuva:.1f} mm")
            c2.metric("Pico Máximo Diário", f"{max_chuva:.1f} mm")
            c3.metric("Dias Impraticáveis (Chuva > 0)", f"{dias_com_chuva} dias")

            fig4 = px.bar(df_mes_especifico, x='Dia', y='Chuva', 
                          title=f"Chuva Diária em {mes_escolhido:02d}/{ano_escolhido}",
                          labels={'Chuva': 'Precipitação (mm)', 'Dia': 'Dia'},
                          text_auto='.1f', color='Chuva', color_continuous_scale='Blues')
            fig4.update_xaxes(dtick=1)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("Não há dados registrados para este mês e ano.")

    # --- ABA 5 ATUALIZADA: MAPA DE CALOR FIXO ---
    with aba5:
        st.subheader("Mapa de Calor: Planejamento de Terraplenagem e Fundações")
        st.markdown("""
        **Regras de Cor (Absolutas e Fixas):** 🟢 **Verde:** Menos de 150 mm (Ideal)  
        🟡 **Amarelo:** De 150 mm a 400 mm (Atenção moderada)  
        🔴 **Vermelho:** Acima de 400 mm (Alto risco)
        """)

        df_heatmap = df_filtrado.groupby(['Ano', 'Mes'])['Chuva'].sum().reset_index()
        df_pivot = df_heatmap.pivot(index='Ano', columns='Mes', values='Chuva')
        df_pivot = df_pivot.sort_index(ascending=False)
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        # CRIANDO A ESCALA DE CORES FIXA
        # Considerando um teto visual de 500mm para os cálculos das cores:
        # 150/500 = 0.30 (30%)
        # 400/500 = 0.80 (80%)
        escala_fixa = [
            [0.0, "#00b050"],   # Início (0mm) - Verde
            [0.3, "#00b050"],   # Até 150mm - Verde
            [0.3, "#ffc000"],   # Passou de 150mm - Vira Amarelo
            [0.8, "#ffc000"],   # Até 400mm - Continua Amarelo
            [0.8, "#e20000"],   # Passou de 400mm - Vira Vermelho
            [1.0, "#e20000"]    # Até o infinito - Vermelho
        ]

        fig5 = px.imshow(
            df_pivot,
            labels=dict(x="Mês", y="Ano", color="Precipitação (mm)"),
            x=meses_nomes,
            y=df_pivot.index,
            text_auto='.0f',
            aspect="auto",
            color_continuous_scale=escala_fixa,
            range_color=[0, 500] # O SEGREDO ESTÁ AQUI: Trava a escala de 0 a 500
        )
        
        fig5.update_xaxes(side="top")
        fig5.update_layout(height=600)
        
        st.plotly_chart(fig5, use_container_width=True)

except Exception as e:
    st.error(f"Ocorreu um erro: {e}. Verifique o arquivo CSV.")
