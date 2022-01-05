import streamlit as st
import pandas as pd
import geopandas as gpd
import datetime
import urllib
from geopy.geocoders import Nominatim
import plotly.graph_objects as go
from streamlit_folium import folium_static
import folium

st.title('Film Permits in Chicago')

st.markdown("""
            This application uses public data to count the number of filming
            permits issued in each ward between two given dates. Please select
            the start and end date below.
            """)
sd = st.date_input("Start Date:",
                   datetime.datetime(2021, 1, 1),
                   datetime.datetime(2016,1,1))
                   
ed = st.date_input("End Date:",
                   min_value=datetime.datetime(2017, 1, 1))

def get_data(start,end):
    start_date = start.strftime('%Y-%m-%dT%H:%M:%S')
    end_date = end.strftime('%Y-%m-%dT%H:%M:%S')
    
    endpoint = 'https://data.cityofchicago.org/resource/c2az-nhru.csv?'
    query = "$where=applicationissueddate between '{}' and '{}'".format(start_date, end_date)
    qquery = urllib.parse.quote(query, '=&?$')
    limit = '&$limit=50000'
    milestone = '&currentmilestone=Complete'
    url = endpoint+qquery+milestone+limit
    film_permits = pd.read_csv(url)
    
    return film_permits

perm_data = get_data(sd,ed)
perm_data = perm_data.drop_duplicates(subset=['APPLICATIONNUMBER'])

gdf_permits = gpd.GeoDataFrame(perm_data,geometry=gpd.points_from_xy(perm_data.LONGITUDE,perm_data.LATITUDE))

geojson_file = 'https://data.cityofchicago.org/resource/k9yb-bpqx.geojson'
wards = gpd.read_file(geojson_file)
wards = wards.rename(columns={'ward':'Ward'})

gdf_permits = gdf_permits.set_crs(epsg=4326)

sjoined_permits = gdf_permits.sjoin(wards,how="inner",predicate='within')

grouped_permits = sjoined_permits.groupby("Ward").size()
df = grouped_permits.to_frame().reset_index()
df.columns = ['Ward', 'Permit Count']

wards = wards.merge(df,how='left',on='Ward').fillna(0).sort_values('Ward')

permit_wards = wards[['Ward','Permit Count']].copy()

permit_wards['Ward'] = permit_wards['Ward'].astype(int)
permit_wards['Permit Count'] = permit_wards['Permit Count'].astype(int)
permit_wards = permit_wards.sort_values('Ward')
output_csv = permit_wards.to_csv(index=False)

fig = go.Figure(data=[go.Table(
    header=dict(values=['Ward','Number of Permits Issued'],
                fill_color='paleturquoise',
                align='center'),
    cells=dict(values=[permit_wards['Ward'],permit_wards['Permit Count']],
               fill_color='lavender',
               align='center'))
    ])

fig.update_traces(cells_font_size = 15)
fig.update_traces(cells_height = 30)
fig.update_traces(header_font_size = 18)
fig.update_layout(margin=dict(l=0,
                              r=0,
                              b=0,
                              t=0
                              )
                  )

address = 'Chicago, Illinois'

geolocator = Nominatim(user_agent="chi_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude

# create map of Chicago using latitude and longitude values
map_chicago = folium.Map(location=[latitude, longitude], zoom_start=10)

folium.Choropleth(geo_data = geojson_file,
                  name = "choropleth",
                  data = wards,
                  columns = ['ward','Permit Count'],
                  key_on = 'feature.properties.ward',
                  fill_color = 'YlOrRd',
                  fill_opacity = 0.6,
                  line_opacity = 1,
                  legend_name = 'Number of Film Permits',
                  highlight=True).add_to(map_chicago)

style_function = lambda x: {'fillColor': '#ffffff',
                           'color':'#000000',
                           'fillOpacity': 0.1,
                           'weight': 0.1}

folium.GeoJson(wards,style_function=style_function,
               tooltip=folium.features.GeoJsonTooltip(fields=['ward','Permit Count'],aliases=['Ward','Number of Permits'])).add_to(map_chicago)

st.write("")
st.plotly_chart(fig,use_container_width=True)
col1, col2, col3, col4, col5 = st.columns(5)
with col3:
    st.download_button(
        label='Download CSV',
        data=output_csv,
        file_name='output.csv',
        mime='text/csv')
    
folium_static(map_chicago)
