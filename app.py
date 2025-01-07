# Import Streamlit
import streamlit as st
import geopandas as gpd
import rasterio as rio
import folium
from streamlit_folium import folium_static
from streamlit_folium import st_folium

import plotly.express as px

# Configurar o layout para ser expansível
st.set_page_config(
    page_title="Sistema de crédito rural",
    layout="wide"  # Define o layout como 'wide' (modo largura total)
)
######################################################################################################
#######################################        FUNÇÔES         #######################################
######################################################################################################

# Definir a leitura em cache

@st.cache_data
def load_geodataframe(nome_tabela):

    # Caminho do Banco de Dados Geoespaciais
    bd_geopackage = './bd_campos_novos.gpkg'

    # Criar a SQL
    sql = f"SELECT * FROM {nome_tabela}"

    # Filtrar os dados a partir da SQL
    gdf = gpd.read_file(bd_geopackage, sql=sql)

    return gdf

def selecionar_car (gdf_area_imovel, gdf_reserva_legal, opcao):
    # Selecionar o CAR considerando selectbox
    area_imovel = gdf_area_imovel[gdf_area_imovel['cod_imovel'] == opcao]
    reserva_legal = gdf_reserva_legal[gdf_reserva_legal['cod_imovel'] == opcao]
    # Calcular o Bounding Box do polígono
    bounds = area_imovel.geometry.total_bounds
    minx, miny, maxx, maxy = bounds

    # Definir o centro do mapa com base no polígono selecionado
    centro_lat = (miny + maxy) / 2
    centro_lon = (minx + maxx) / 2

    return area_imovel, reserva_legal, centro_lat, centro_lon, miny, maxy, minx, maxx

######################################################################################################
#######################################        DADOS         #########################################
######################################################################################################
# Ler GeoDataFrame
ai_campos_novos = load_geodataframe('area_imovel')
rl_campos_novos = load_geodataframe('reserva_legal')
# Ler as áreas de Cobertura e Uso da Terra
ai_lulc = load_geodataframe('ai_lulc')
rl_lulc = load_geodataframe('rl_lulc')

# Obter as matrículas
matriculas = ai_campos_novos.cod_imovel.values.tolist()
# Obter as coordenadas centrais do GeoDataFrame
coords_centrais = ai_campos_novos.geometry.centroid.union_all().centroid.xy
# Obter as coordenadas centrais
longitude, latitude = coords_centrais[0][0], coords_centrais[1][0]

# Adicionar camada raster
with rio.open('./lulc.tif') as src:
   # Ler a imagem raster como Numpy
   img = src.read()
   # Obter as coordenadas do retângulo envolvente
   min_lon, min_lat, max_lon, max_lat = src.bounds
   # Organizar conforme o Folium
   bounds_orig = [[min_lat, min_lon], [max_lat, max_lon]]

######################################################################################################
#################################       TELA PRINCIPAL       #########################################
######################################################################################################

# Título do aplicativo
st.title("Sistema de crédito rural - Preserva+")
# Texto explicativo
st.write("Cálcula o valor em reais do crédito rural considerando o Cadastro Ambiental Rural.")


######################################################################################################
#######################################        SIDEBAR       #########################################
######################################################################################################
# Componentes na barra lateral
st.sidebar.title("Filtros")

# Seleção de opções com selectbox
opcao = st.sidebar.selectbox(
    "Selecione a matrícula:",  # Texto descritivo
    matriculas # Opções disponíveis
)

# Exibindo os resultados na página principal
st.write(f"Você escolheu: **{opcao}**")

# Selecionar o CAR de acordo com o selectbox do sidebar
area_imovel, reserva_legal, centro_lat, centro_lon, miny, maxy, minx, maxx = selecionar_car(ai_campos_novos,rl_campos_novos,opcao)



######################################################################################################
#######################################        MAPA       ############################################
######################################################################################################


# Inicializar o mapa Folium
mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=10)

# Adicionar a camada de Imóveis Rurais
folium.GeoJson(
    data=area_imovel,  # GeoDataFrame convertido diretamente em GeoJson
    name="Imóveis rurais",  # Nome da camada no LayerControl
    tooltip=folium.GeoJsonTooltip(  # Configurar tooltip
        fields=['des_condic'],  # Coluna(s) para mostrar no tooltip
        aliases=['Situação:'],  # Nomes amigáveis no tooltip
        localize=True
    ),
    style_function=lambda x: {
        'fillColor': 'none',  # Cor de preenchimento
        'color': 'black',       # Cor das bordas
        'weight': 1,            # Largura das bordas
        'fillOpacity': 0.6      # Opacidade do preenchimento
    }
).add_to(mapa)

# Verificar se Reserva Legal não está vazia
if not reserva_legal.empty:
    # Adicionar a camada de Reserva Legal
    folium.GeoJson(
        data=reserva_legal,  # GeoDataFrame convertido diretamente em GeoJson
        name="Reserva Legal",  # Nome da camada no LayerControl
        # Setup tooltip
        tooltip=folium.GeoJsonTooltip(  # Configurar tooltip
            fields=['cod_imovel','des_condic'],  # Coluna(s) para mostrar no tooltip
            aliases=['Matrícula','Situação:'],  # Nomes amigáveis no tooltip
            localize=True
        ),

        style_function=lambda x: {
            'fillColor': 'green',  # Cor de preenchimento
            'color': 'black',      # Cor das bordas
            'weight': 1,           # Largura das bordas
            'fillOpacity': 1     # Opacidade do preenchimento
        }
    ).add_to(mapa)

# Adicionar o Numpy ao mapa
folium.raster_layers.ImageOverlay(
   image=img.transpose(1, 2, 0), # passar para banda, linha, coluna
   bounds=bounds_orig,
   opacity=0.6,
   name='LULC'
).add_to(mapa)

# Ajustar o mapa para os limites do polígono
mapa.fit_bounds([[miny, minx], [maxy, maxx]])

# Adicionar controle de camadas
folium.LayerControl().add_to(mapa)
# Exibir o mapa no Streamlit
#folium_static(mapa, width=700, height=500)
# Exibir mapa ajustando à largura da tela
st_folium(mapa, use_container_width=True, height=500)

######################################################################################################
#####################################        GRÁFICOS       ##########################################
######################################################################################################
# Selecionar o CAR - Tabela LULC - Área do imóvel
ai_lulc = ai_lulc[ai_lulc['matricula'] == opcao]
# Transformar o DataFrame para o formato longo (long format) usando melt
ai_lulc_melt = ai_lulc[['veg_nativa','antropizada','agua']].melt(var_name="Classes", value_name="Áreas(ha)")
# Transformar área para float
ai_lulc_melt['Áreas(ha)'] = ai_lulc_melt['Áreas(ha)'].astype(float)

# Selecionar o CAR - Tabela LULC - Reserva legal
rl_lulc = rl_lulc[rl_lulc['matricula'] == opcao]
# Transformar o DataFrame para o formato longo (long format) usando melt
rl_lulc_melt = rl_lulc[['veg_nativa','antropizada','agua']].melt(var_name="Classes", value_name="Áreas(ha)")
# Transformar área para float
rl_lulc_melt['Áreas(ha)'] = rl_lulc_melt['Áreas(ha)'].astype(float)

# Modificar os nomes das categorias
renomear_classes = {
    "veg_nativa": "Vegetação Nativa",
    "antropizada": "Área Antropizada",
    "agua": "Recursos Hídricos"
}
# Definir as cores personalizadas para cada categoria
cores_personalizadas = {
    "Vegetação Nativa": "#0d8d29",  # Verde
    "Área Antropizada": "rgb(225, 237, 54)",     # Amarelo
    "Recursos Hídricos": "rgb(52, 16, 214)"   # Azul
}

# Replace
ai_lulc_melt["Classes"] = ai_lulc_melt["Classes"].replace(renomear_classes)
rl_lulc_melt["Classes"] = rl_lulc_melt["Classes"].replace(renomear_classes)

# Criar o gráfico de barras com Plotly
fig_ai = px.bar(ai_lulc_melt, x="Classes", y= "Áreas(ha)", 
             color= "Classes",
             color_discrete_map=cores_personalizadas,
             title="Áreas do Uso e da Cobertura da Terra - Área do Imóvel",)


# Criar o gráfico de barras com Plotly
fig_rl = px.bar(rl_lulc_melt, x="Classes", y= "Áreas(ha)", 
             color= "Classes",
             color_discrete_map=cores_personalizadas,
             title="Áreas do Uso e da Cobertura da Terra - Reserva Legal",)



# Criar duas colunas no Streamlit
col1, col2 = st.columns(2)

# Exibir os gráficos nas colunas
with col1:
    st.plotly_chart(fig_ai, use_container_width=True)
    
with col2:
    st.plotly_chart(fig_rl, use_container_width=True)

######################################################################################################
#####################################        TABELAS       ###########################################
######################################################################################################
# Exibir os gráficos nas colunas

if not reserva_legal.empty:
    with col1:
        st.write('Tabela - Área do Imóvel')
        st.dataframe(area_imovel)
    with col2:    
        st.write('Tabela - Reserva Legal')
        st.dataframe(reserva_legal)
else:
    st.write('Tabela - Área do Imóvel')
    st.dataframe(area_imovel)
######################################################################################################
#####################################        SIDEBAR       ###########################################
######################################################################################################

# Situação do CAR
situacao_car = area_imovel.des_condic.values[0]

# Situação do CAR
if situacao_car != "Cancelado por decisao administrativa":
    # Verificar se Reserva Legal não está vazia
    if not reserva_legal.empty:

        # Exibindo os resultados na página principal
        st.sidebar.write(f"Situação: **{situacao_car}**")
        # Calcular o valor do crédtio para cada hectare com vegetação nativa (Área do Imóvel)
        total_credito_vgn_ai = float(ai_lulc.veg_nativa.values[0]) * 1000
        total_credito_ant_rl = float(rl_lulc.antropizada.values[0]) * 500
        # Multiplicar por 1000 reais
        st.sidebar.write(f"Esse CAR tem direito ao crédito rural:")
        st.sidebar.write(f"Valor do crédito rural para a vegetação nativa da Área do Imóvel é de  **{total_credito_vgn_ai} reais**")
        st.sidebar.write(f"Valor do crédito rural para a área antropizada da Reserva Legal é de  **{total_credito_ant_rl} reais**")
        st.sidebar.markdown(f'<p style="color:#32CD32;">Valor total do crédito rural: {total_credito_ant_rl+total_credito_vgn_ai} reais</p>',
                            unsafe_allow_html=True)

    else:

        st.sidebar.write(f"Esse CAR não possui Reserva legal declarada")
        st.sidebar.markdown( """<p style="color:#FF0000;">Esse CAR não tem direito ao crédito rural</p>""",
                            unsafe_allow_html=True)
else:
        st.sidebar.write(f"Esse CAR está 'Cancelado por decisão administrativa'")
        st.sidebar.markdown("""<p style="color:#FF0000;">Esse CAR não tem direito ao crédito rural</p>""",
                            unsafe_allow_html=True)