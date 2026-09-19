from graphviz import Digraph
import os

# ============ DIAGRAMA 2 - MÁQUINA DE ESTADOS DEL FIRMWARE ============
# Documenta la operación, incluida la resiliencia OFFLINE (modo isla),
# parte central de la novedad reivindicada.

g = Digraph('estados', format='png')

g.attr(
    rankdir='TB',
    bgcolor='white',
    fontname='Arial',
    labelloc='t',
    label='Máquina de estados del firmware embebido - Medidor Nomyra',
    fontsize='16'
)

g.attr(
    'node',
    shape='box',
    style='rounded,filled',
    fontname='Arial',
    fontsize='11'
)

# Estado inicial
g.node(
    'init',
    'Inicio / Arranque',
    shape='circle',
    fillcolor='#D3D1C7',
    width='0.4',
    fontsize='9'
)

# Estados principales
g.node(
    'mide',
    'MIDIENDO\nLee ADE7758 por SPI aislado\nActualiza buffer 24 h en microSD\nMuestra en OLED',
    fillcolor='#E1F5EE'
)

g.node(
    'solicita',
    'SOLICITANDO PRONÓSTICO\n(Disparo diario ~19:00)\nConsulta API en nube por WiFi',
    fillcolor='#FAEEDA'
)

g.node(
    'muestra',
    'MOSTRANDO\nPresenta pronóstico D+1\n(Mediana + banda) en OLED\nGuarda pronóstico en caché',
    fillcolor='#E6F1FB'
)

g.node(
    'gestiona',
    'GESTIONANDO CARGAS\nActiva/desactiva relé según\npronóstico y medición',
    fillcolor='#CECBF6'
)

# Estado de resiliencia
g.node(
    'isla',
    'MODO ISLA (OFFLINE)\nSin conectividad\nSigue midiendo\nUsa el último pronóstico en caché\nMantiene buffer local',
    fillcolor='#F7C1C1'
)

# Transiciones
g.edge('init', 'mide')
g.edge('mide', 'solicita', label='Hora del pronóstico')
g.edge('solicita', 'muestra', label='Respuesta OK')
g.edge('muestra', 'gestiona', label='Pronóstico vigente')
g.edge('gestiona', 'mide', label='Ciclo continuo')

# Transiciones de resiliencia
g.edge(
    'solicita',
    'isla',
    label='Sin WiFi / Timeout',
    color='#A32D2D',
    fontcolor='#A32D2D'
)

g.edge(
    'isla',
    'gestiona',
    label='Usa pronóstico\ncacheado',
    color='#A32D2D',
    fontcolor='#A32D2D'
)

g.edge(
    'isla',
    'mide',
    label='Conexión\nrestablecida',
    color='#1D9E75',
    fontcolor='#0F6E56'
)

# Guardar diagrama
archivo = g.render("3_estados_firmware_nomyra", cleanup=True)

print("Diagrama generado correctamente.")
print("Archivo:", archivo)
print("Carpeta:", os.getcwd())