import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

import os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
df = pd.read_pickle(D+'stations.pkl')
dv = pd.read_pickle(D+'vars.pkl')
dt = pd.read_pickle(D+'tesis.pkl')

# order
RORD = {'Arica y Parinacota': 0, 'Tarapacá': 1, 'Antofagasta': 2, 'Atacama': 3}
df['_r'] = df['Región'].map(RORD)
df = df.sort_values(['_r', 'Red', 'Latitud'], ascending=[True, True, False]).drop(columns='_r')
# re-number IDs in final order and propagate
remap = {old: f'N-{i+1:04d}' for i, old in enumerate(df['ID'])}
df['ID'] = df['ID'].map(remap)
dv['ID'] = dv['ID'].map(remap)
dt['ID catálogo'] = dt['ID catálogo'].apply(lambda s: ', '.join(remap[x.strip()] for x in s.split(',') if x.strip()))
dv['_k'] = dv['ID'].str[2:].astype(int)
dv = dv.sort_values(['_k', 'Variable']).drop(columns='_k')

F = 'Arial'
HFILL = PatternFill('solid', fgColor='1F3A5F')
HFONT = Font(name=F, bold=True, color='FFFFFF', size=10)
BFONT = Font(name=F, size=10)
thin = Side(style='thin', color='D0D7E2')

wb = Workbook()

def write_table(ws, frame, name, widths, wrap_cols=()):
    cols = list(frame.columns)
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=1, column=j, value=c)
        cell.font = HFONT; cell.fill = HFILL
        cell.alignment = Alignment(vertical='center', wrap_text=True)
    for i, row in enumerate(frame.itertuples(index=False), 2):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v): v = None
            if v is not None and hasattr(v, 'item'): v = v.item()
            cell = ws.cell(row=i, column=j, value=v)
            cell.font = BFONT
            cell.alignment = Alignment(vertical='top', wrap_text=cols[j-1] in wrap_cols)
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = 'C2'
    ref = f'A1:{get_column_letter(len(cols))}{len(frame)+1}'
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name='TableStyleLight9', showRowStripes=True)
    ws.add_table(t)

# ---------- Léame ----------
ws = wb.active; ws.title = 'Léame'
ws.column_dimensions['A'].width = 34; ws.column_dimensions['B'].width = 110
r = 1
def put(a, b='', bold=False, size=10, color=None):
    global r
    ws.cell(row=r, column=1, value=a).font = Font(name=F, bold=True if b else bold, size=size, color=color)
    c = ws.cell(row=r, column=2, value=b); c.font = Font(name=F, size=10); c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.cell(row=r, column=1).alignment = Alignment(vertical='top', wrap_text=True)
    r += 1

put('Catálogo de estaciones meteorológicas – Norte de Chile (Arica y Parinacota a Atacama)', bold=True, size=14, color='1F3A5F')
put('Metadatos compilados al 28-10-2026. No incluye los datos, solo la información de estaciones y mediciones.', size=10)
r += 1
put('Contenido', bold=True, size=12, color='1F3A5F')
put('Estaciones', 'Una fila por estación: red, propietario, códigos, coordenadas (WGS84, grados decimales), altitud, tipo, variables medidas, altura de sensores, primer y último año con datos, estado operativo y fuente.')
put('Variables y periodos', 'Una fila por estación y variable (o por variable y altura de sensor, en torres): periodo disponible, cobertura y altura del sensor cuando la fuente la informa. Se filtra por la columna ID.')
put('Resumen', 'Conteo de estaciones por red, región y estado (fórmulas sobre la hoja Estaciones).')
put('Estaciones tesis', 'Correspondencia entre los códigos usados en la tesis WRF-Antofagasta y las estaciones del catálogo.')
put('Fuentes', 'Origen de cada red y cómo se obtuvo la información.')
r += 1
put('Estado operativo', bold=True, size=12, color='1F3A5F')
for k, v in [
    ('Operativa', 'DMC/SACLIM: con datos en las últimas 24 h. CEAZA-Met: última lectura en octubre 2026. DGA: precipitación con datos hasta 2025 o 2026 en la base CR2.'),
    ('Operativa (en línea)', 'SINCA: la ficha indica recepción de datos en línea.'),
    ('Probablemente operativa', 'DMC/SACLIM: sin datos en las últimas 24 h, pero con datos en 2025–2026.'),
    ('Nueva (2026)', 'Estación incorporada a SACLIM en 2026 (p. ej. red CODELCO, nuevas INIA) aún sin inventario de datos publicado.'),
    ('Sin datos recientes', 'Últimos datos entre 2019 y 2024; puede ser cierre o rezago en la actualización de la base.'),
    ('Inactiva / cerrada', 'Sin datos desde antes de 2019 o campaña de medición terminada (Ministerio de Energía).'),
    ('Sin información', 'La fuente no publica inventario ni fecha del último dato.')]:
    put(k, v)
r += 1
put('Advertencias', bold=True, size=12, color='1F3A5F')
for k, v in [
    ('Altura de sensores', 'Informada por la fuente en CEAZA-Met y en las torres del Ministerio de Energía. En DMC/INIA se deduce del elemento registrado (\"Viento a 10 m\" / \"Viento a 2 m\"); la altura de T/HR no se publica (estándar OMM 1.5–2 m).'),
    ('Periodos DGA', 'Se calcularon año a año desde la base CR2 (Explorador Climático), que solo incluye precipitación y temperaturas extremas diarias. Las estaciones DGA pueden medir otras variables no incluidas en esa base.'),
    ('Duplicados', 'Las estaciones DGA que también figuran en SACLIM se fusionaron en una sola fila (se anota el código SACLIM). La estación INIA de Vallenar (CEAZA-Met INIA65) se fusionó con CE Huasco (SACLIM 280021).'),
    ('SINCA', 'Solo se listan las estaciones de calidad del aire que el SINCA marca con parámetros meteorológicos; la ficha pública no detalla cuáles ni sus periodos.'),
    ('No incluido', 'Redes privadas sin publicación abierta (mineras, generadoras, SQM), estaciones de observatorios fuera de SACLIM (archivo propio de ESO/ALMA) y datos AMDAR/satelitales, salvo la mención en la estación de radiosondeo de Antofagasta.'),
    ('Coordenadas', 'Tal como las publica cada fuente. Se marcan en Notas los casos dudosos detectados.')]:
    put(k, v)

# ---------- Estaciones ----------
ws = wb.create_sheet('Estaciones')
cols = ['ID', 'Nombre', 'Red', 'Propietario', 'Código', 'Código OMM / OACI', 'Región', 'Latitud', 'Longitud',
        'Altitud (m)', 'Tipo', 'Zona', 'Variables', 'Altura sensores', 'Inicio datos', 'Fin datos', 'Estado',
        'Criterio estado', 'Operador', 'Fuente metadatos', 'Notas']
write_table(ws, df[cols], 'Estaciones', [9, 32, 34, 16, 12, 14, 18, 10, 10, 10, 30, 13, 45, 45, 9, 9, 18, 40, 26, 40, 60],
            wrap_cols=('Variables', 'Altura sensores', 'Notas', 'Criterio estado', 'Red'))
for row in ws.iter_rows(min_row=2, min_col=8, max_col=9):
    for c in row: c.number_format = '0.0000'
for row in ws.iter_rows(min_row=2, min_col=10, max_col=10):
    for c in row: c.number_format = '#,##0'

# ---------- Variables ----------
ws = wb.create_sheet('Variables y periodos')
write_table(ws, dv[['ID', 'Nombre', 'Red', 'Código', 'Región', 'Variable', 'Desde', 'Hasta', 'Cobertura (%)', 'Altura sensor (m)', 'Fuente']],
            'Variables', [9, 32, 34, 12, 18, 38, 12, 12, 12, 12, 40], wrap_cols=('Red',))

# ---------- Resumen ----------
ws = wb.create_sheet('Resumen')
reds = sorted(df['Red'].unique(), key=lambda x: -len(df[df['Red'] == x]))
estados = ['Operativa', 'Operativa (en línea)', 'Probablemente operativa', 'Nueva (2026)', 'Sin datos recientes', 'Inactiva / cerrada', 'Sin información']
regs = ['Arica y Parinacota', 'Tarapacá', 'Antofagasta', 'Atacama']
ws['A1'] = 'Estaciones por red y estado'; ws['A1'].font = Font(name=F, bold=True, size=12, color='1F3A5F')
hdr = ['Red'] + estados + ['Total']
for j, h in enumerate(hdr, 1):
    c = ws.cell(row=2, column=j, value=h); c.font = HFONT; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
for i, red in enumerate(reds, 3):
    ws.cell(row=i, column=1, value=red).font = BFONT
    for j, e in enumerate(estados, 2):
        L = get_column_letter(j)
        ws.cell(row=i, column=j, value=f'=COUNTIFS(Estaciones!$C:$C,$A{i},Estaciones!$Q:$Q,{L}$2)').font = BFONT
    ws.cell(row=i, column=len(hdr), value=f'=SUM(B{i}:{get_column_letter(len(hdr)-1)}{i})').font = Font(name=F, bold=True)
tr_ = 3 + len(reds)
ws.cell(row=tr_, column=1, value='Total').font = Font(name=F, bold=True)
for j in range(2, len(hdr)+1):
    L = get_column_letter(j)
    ws.cell(row=tr_, column=j, value=f'=SUM({L}3:{L}{tr_-1})').font = Font(name=F, bold=True)
r0 = tr_ + 3
ws.cell(row=r0-1, column=1, value='Estaciones por región y estado').font = Font(name=F, bold=True, size=12, color='1F3A5F')
for j, h in enumerate(['Región'] + estados + ['Total'], 1):
    c = ws.cell(row=r0, column=j, value=h); c.font = HFONT; c.fill = HFILL; c.alignment = Alignment(wrap_text=True, vertical='center')
for i, rg in enumerate(regs, r0+1):
    ws.cell(row=i, column=1, value=rg).font = BFONT
    for j, e in enumerate(estados, 2):
        L = get_column_letter(j)
        ws.cell(row=i, column=j, value=f'=COUNTIFS(Estaciones!$G:$G,$A{i},Estaciones!$Q:$Q,{L}${r0})').font = BFONT
    ws.cell(row=i, column=len(hdr), value=f'=SUM(B{i}:{get_column_letter(len(hdr)-1)}{i})').font = Font(name=F, bold=True)
ws.column_dimensions['A'].width = 60
for j in range(2, len(hdr)+1): ws.column_dimensions[get_column_letter(j)].width = 14
ws.row_dimensions[2].height = 32; ws.row_dimensions[r0].height = 32

# ---------- Tesis ----------
ws = wb.create_sheet('Estaciones tesis')
write_table(ws, dt, 'Tesis', [12, 14, 52, 18, 18, 22])

# ---------- Fuentes ----------
ws = wb.create_sheet('Fuentes')
src = pd.DataFrame([
    ['DMC – SACLIM (catastro y fichas de estación)', 'DMC, DGA, INIA, FDF, CODELCO, ESO, USACH, Armada', 'Buscador de estaciones (regiones XV, I, II, III, todas las estaciones) y ficha de cada estación: coordenadas, tipo, clasificación, elementos asignados con año desde/hasta. Estado según filtro "datos en las últimas 24 horas".', 'https://climatologia.meteochile.gob.cl/application/informacion/buscadorEstaciones/RE2001'],
    ['CR2 – Explorador Climático', 'DGA', 'Porcentaje de días con datos por año (1940–2026) de precipitación, Tmáx y Tmín diarias; de ahí se obtiene primer/último año y cobertura.', 'https://explorador.cr2.cl'],
    ['CEAZA-Met – servicio web', 'CEAZA-Met (provincias de Atacama y estaciones del norte)', 'Lista de estaciones (primera y última lectura) y lista de sensores con altura.', 'https://www.ceazamet.cl'],
    ['Ministerio de Energía – Campaña de medición eólica y solar', 'Torres eólicas 20–110 m y estaciones solares', 'Catálogo de sitios (meta/siteinfo.json) con coordenadas, fechas y variables por altura.', 'http://walker.dgf.uchile.cl/Mediciones/'],
    ['SINCA – Ministerio del Medio Ambiente', 'Estaciones de calidad del aire con parámetros meteorológicos', 'Listado por región (filtro estaciones meteorológicas) y ficha de estación (propietario, operador, UTM, inicio de operación, tipo de recepción).', 'https://sinca.mma.gob.cl'],
], columns=['Fuente', 'Redes cubiertas', 'Qué se extrajo', 'URL'])
write_table(ws, src, 'Fuentes', [40, 40, 80, 60], wrap_cols=('Qué se extrajo', 'Redes cubiertas'))

wb.save(D+'Catalogo_estaciones_norte_Chile.xlsx')
df.to_pickle(D+'stations_final.pkl')
print('ok', len(df), len(dv))
