from graphviz import Digraph
import os

# ============ DIAGRAMA 3 - PIPELINE DE PRONOSTICO ============
# Documenta la parte del MODELO para el paper.
# Flujo: datos -> features -> AutoGluon (walk-forward) -> cuantiles -> API

g = Digraph('pipeline', format='png')
g.attr(rankdir='LR', bgcolor='white', fontname='Arial', labelloc='t',
        label='Pipeline de pronostico probabilistico de generacion FV - Nomyra',
        fontsize='16')
g.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='10')

# Fuentes de datos
with g.subgraph(name='cluster_fuentes') as s:
    s.attr(label='Fuentes de datos', style='rounded', color='#0d3b3b', fontname='Arial')
    s.node('meteo', 'Covariables\nmeteorologicas\n(Open-Meteo / OpenWeather)', fillcolor='#E6F1FB')
    s.node('hist', 'Historico de\ngeneracion\n(COES / ERA5-Land)', fillcolor='#E6F1FB')

# Procesamiento
g.node('etl', 'ETL + limpieza\nresolucion 15 min\nvalidacion temporal', fillcolor='#FAEEDA')
g.node('feat', 'Ingenieria de\ncaracteristicas\n(features)', fillcolor='#FAEEDA')

# Modelo
with g.subgraph(name='cluster_modelo') as s:
    s.attr(label='Modelo', style='rounded,filled', fillcolor='#EAF3DE', color='#3B6D11', fontname='Arial')
    s.node('automl', 'AutoGluon TimeSeries\nWeightedEnsemble\n(walk-forward backtesting)', fillcolor='#C0DD97')
    s.node('cuant', 'Pronostico por\ncuantiles (probabilistico)\nnMAE 3.98%', fillcolor='#C0DD97')

# Salida
g.node('api', 'API REST\n(FastAPI)\nJSON day-ahead', fillcolor='#CECBF6')
g.node('disp', 'Dispositivo\nNomyra en sitio\n(consume por WiFi)', fillcolor='#E1F5EE')

g.edge('meteo', 'etl')
g.edge('hist', 'etl')
g.edge('etl', 'feat')
g.edge('feat', 'automl')
g.edge('automl', 'cuant')
g.edge('cuant', 'api')
g.edge('api', 'disp', label='pronostico D+1')

archivo = g.render("4_pipeline_pronostico_nomyra", cleanup=True)

print("Diagrama generado correctamente.")
print("Archivo generado:", archivo)
print("Carpeta actual:", os.getcwd())
