import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import FormulaRule

import os
V = os.path.dirname(os.path.abspath(__file__)) + '/'
df = pd.read_pickle(V+'st.pkl'); dp = pd.read_pickle(V+'pr.pkl')
RO = {'DMC': 0, 'INIA / Agromet': 1, 'Armada (DIRECTEMAR)': 2, 'Armada – SERVIMET (vía Agromet)': 2, 'ESO (vía DMC)': 3,
      'SINCA (calidad del aire)': 4, 'DGA': 5, 'CEAZA-Met': 6, 'Ministerio de Energía (campaña eólica y solar)': 7}
OPO = {'Sí': 0, 'Probable': 1, 'Sin información': 2, 'No': 3}
df['_r'] = df['Red'].map(RO); df['_o'] = df['Operativa'].map(OPO)
df = df.sort_values(['_r', 'Latitud'], ascending=[True, False]).reset_index(drop=True)
df['ID'] = [f'E-{i+1:03d}' for i in range(len(df))]
idmap = dict(zip(df['_key'], df['ID']))
dp['ID'] = dp['_key'].map(idmap)
dp = dp.merge(df[['_key', 'Nombre', 'Red', 'Operativa']], on='_key')
dp['_n'] = dp['ID'].str[2:].astype(int)
dp['_t'] = dp['Tipo'].map({'Calidad del aire': 0, 'Meteorológico': 1})
dp = dp.sort_values(['_n', '_t', 'Parámetro']).reset_index(drop=True)
def fmtd(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    s = str(v)
    return s if len(s) > 4 else int(s)
dp['Desde'] = dp['Desde'].map(fmtd); dp['Hasta'] = dp['Hasta'].map(fmtd)

F = 'Arial'
HF = Font(name=F, bold=True, color='FFFFFF', size=10); HFILL = PatternFill('solid', fgColor='1F3A5F')
BF = Font(name=F, size=10)
wb = Workbook()

def table(ws, frame, name, widths, wrap=()):
    cols = list(frame.columns)
    for j, c in enumerate(cols, 1):
        x = ws.cell(row=1, column=j, value=c); x.font = HF; x.fill = HFILL; x.alignment = Alignment(wrap_text=True, vertical='center')
    for i, row in enumerate(frame.itertuples(index=False), 2):
        for j, v in enumerate(row, 1):
            if isinstance(v, float) and pd.isna(v): v = None
            if v is not None and hasattr(v, 'item'): v = v.item()
            x = ws.cell(row=i, column=j, value=v); x.font = BF; x.alignment = Alignment(vertical='top', wrap_text=cols[j-1] in wrap)
    for j, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 32; ws.freeze_panes = 'C2'
    t = Table(displayName=name, ref=f'A1:{get_column_letter(len(cols))}{len(frame)+1}')
    t.tableStyleInfo = TableStyleInfo(name='TableStyleLight9', showRowStripes=True); ws.add_table(t)
    return cols

def color_op(ws, col, n):
    L = get_column_letter(col); rng = f'{L}2:{L}{n+1}'
    for val, c in [('Sí', 'D7F0DF'), ('Probable', 'FCEFD2'), ('No', 'EDEFF2'), ('Sin información', 'EDEFF2')]:
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'{L}2="{val}"'], fill=PatternFill('solid', fgColor=c)))

# ---------------- Léame
ws = wb.active; ws.title = 'Léame'
ws.column_dimensions['A'].width = 30; ws.column_dimensions['B'].width = 112
r = 1
def put(a, b='', size=10, bold=False, color=None):
    global r
    x = ws.cell(row=r, column=1, value=a); x.font = Font(name=F, bold=bold or bool(b), size=size, color=color); x.alignment = Alignment(vertical='top', wrap_text=True)
    y = ws.cell(row=r, column=2, value=b); y.font = BF; y.alignment = Alignment(vertical='top', wrap_text=True)
    r += 1
put('Catálogo de estaciones meteorológicas y de calidad del aire – Iquique a Caldera', size=14, bold=True, color='1F3A5F')
put('Metadatos al 28-10-2026. No incluye datos, solo información de estaciones, parámetros y disponibilidad.')
r += 1
put('Criterios', size=12, bold=True, color='1F3A5F')
put('Dominio', 'Latitud entre 19.95°S (al norte de Iquique y Alto Hospicio) y 27.30°S (incluye Caldera y el aeródromo Desierto de Atacama), desde la costa hasta la frontera. Copiapó (27.37°S) queda fuera por pocos kilómetros; se puede agregar si se requiere.')
put('Periodo', 'Estaciones con al menos un parámetro con datos entre 2015 y la fecha. En "Parámetros" se listan solo los parámetros con datos en ese periodo; las columnas Desde/Hasta muestran el registro completo de cada uno (puede empezar antes de 2015). La columna "Cubre 2015–2026" indica si la estación tiene datos desde 2015 o antes hasta 2026.')
put('Variables', 'Meteorológicas (superficie y perfiles verticales) y de calidad del aire (MP10, MP2,5, SO2, NO, NO2, NOx, CO, O3 y metales en material particulado).')
put('Resolución temporal', 'La más fina disponible públicamente según cada red: DMC (estaciones automáticas) 1 minuto, con descarga para usuarios registrados (gratis); Ministerio de Energía 10 minutos; SINCA, INIA/Agromet, SERVIMET y CEAZA-Met horaria; DGA horaria en línea y diaria en la base consolidada; radiosonda 1 sondeo diario (12 UTC).')
r += 1
put('Columna "Operativa"', size=12, bold=True, color='1F3A5F')
put('Sí', 'Con datos en las últimas 24 h o en el mes en curso (SACLIM, Agromet "en línea", último dato SINCA en octubre de 2026).')
put('Probable', 'Datos hasta 2025 o hasta mediados de 2026, sin confirmación de transmisión reciente. En la DGA, la base CR2 llega a 2025, por lo que las estaciones con datos hasta 2025 se marcan como probables.')
put('No', 'Sin datos recientes: estación cerrada, campaña terminada o parámetros discontinuados.')
put('Sin información', 'Estaciones DGA registradas en el catastro de la DMC sin datos en las bases públicas revisadas.')
r += 1
put('Hojas', size=12, bold=True, color='1F3A5F')
put('Estaciones', 'Una fila por estación: red, propietario, códigos, coordenadas WGS84, altitud, tipo, parámetros meteorológicos y de calidad del aire, resolución más fina, primer y último dato, si cubre 2015–2026, estado operativo, acceso a los datos y notas.')
put('Parámetros', 'Una fila por estación y parámetro (y altura de sensor cuando corresponde): resolución, desde, hasta, cobertura, técnica o instrumento y acceso. Se relaciona con Estaciones por la columna ID.')
put('Resumen', 'Conteos por red, tipo y estado (fórmulas sobre la hoja Estaciones).')
put('Fuentes', 'Origen de la información de cada red.')
r += 1
put('Advertencias', size=12, bold=True, color='1F3A5F')
for a, b in [
    ('Altura de sensores', 'Publicada por SINCA, CEAZA-Met y Ministerio de Energía. En DMC/INIA se deduce del elemento (viento a 10 m o 2 m; temperatura de suelo a 5 y 10 cm). En el resto se indica "No informada".'),
    ('DGA', 'La base pública consolidada solo trae precipitación y temperaturas extremas diarias. Las estaciones automáticas DGA miden típicamente precipitación, temperatura y humedad relativa y transmiten cada hora; el detalle por estación debe confirmarse con la DGA.'),
    ('SINCA', 'Fechas de primer y último registro según la ficha de cada estación. Algunos parámetros meteorológicos figuran sin altura. Las fichas SINCA solo muestran parámetros con datos publicados.'),
    ('Duplicados', 'Estaciones INIA y DMC que aparecen tanto en SACLIM como en Agromet se presentan en una sola fila.'),
    ('No incluido', 'Redes privadas sin publicación (mineras, puertos, generadoras fuera del SINCA) y archivos propios de observatorios (ESO, ALMA) más allá de lo que publica la DMC.')]:
    put(a, b)

# ---------------- Estaciones
ws = wb.create_sheet('Estaciones')
cols = ['ID', 'Nombre', 'Red', 'Propietario', 'Código', 'Código OMM / OACI', 'Región', 'Latitud', 'Longitud', 'Altitud (m)', 'Tipo',
        'Instalación', 'Parámetros meteorológicos', 'Parámetros calidad del aire', 'Resolución más fina', 'Primer dato', 'Último dato',
        'Cubre 2015–2026', 'Operativa', 'Criterio operatividad', 'Acceso a datos', 'Fuente metadatos', 'Notas']
table(ws, df[cols], 'Estaciones', [8, 30, 24, 24, 13, 14, 15, 10, 10, 10, 20, 26, 46, 30, 22, 9, 9, 11, 11, 36, 36, 36, 50],
      wrap=('Parámetros meteorológicos', 'Parámetros calidad del aire', 'Notas', 'Criterio operatividad', 'Acceso a datos', 'Instalación', 'Nombre', 'Propietario'))
for row in ws.iter_rows(min_row=2, min_col=8, max_col=9):
    for c in row: c.number_format = '0.0000'
for row in ws.iter_rows(min_row=2, min_col=10, max_col=10):
    for c in row: c.number_format = '#,##0'
color_op(ws, cols.index('Operativa')+1, len(df))

# ---------------- Parámetros
ws = wb.create_sheet('Parámetros')
pc = ['ID', 'Nombre', 'Red', 'Tipo', 'Parámetro', 'Altura sensor', 'Resolución más fina', 'Desde', 'Hasta', 'Cobertura (%)', 'Técnica / instrumento', 'Operativa', 'Acceso a datos']
table(ws, dp[pc], 'Parametros', [8, 30, 24, 16, 38, 12, 26, 12, 12, 11, 30, 11, 40], wrap=('Nombre', 'Parámetro', 'Acceso a datos'))
color_op(ws, pc.index('Operativa')+1, len(dp))

# ---------------- Resumen
ws = wb.create_sheet('Resumen')
reds = df.drop_duplicates('Red').sort_values('_r')['Red'].tolist()
est = ['Sí', 'Probable', 'No', 'Sin información']
ws['A1'] = 'Estaciones por red y estado operativo'; ws['A1'].font = Font(name=F, bold=True, size=12, color='1F3A5F')
hdr = ['Red'] + [f'Operativa: {e}' for e in est] + ['Total', 'Con calidad del aire']
for j, h in enumerate(hdr, 1):
    x = ws.cell(row=2, column=j, value=h); x.font = HF; x.fill = HFILL; x.alignment = Alignment(wrap_text=True, vertical='center')
for i, red in enumerate(reds, 3):
    ws.cell(row=i, column=1, value=red).font = BF
    for j, e in enumerate(est, 2):
        ws.cell(row=i, column=j, value=f'=COUNTIFS(Estaciones!$C:$C,$A{i},Estaciones!$S:$S,"{e}")').font = BF
    ws.cell(row=i, column=6, value=f'=SUM(B{i}:E{i})').font = Font(name=F, bold=True)
    ws.cell(row=i, column=7, value=f'=COUNTIFS(Estaciones!$C:$C,$A{i},Estaciones!$K:$K,"Calidad*")').font = BF
t = 3 + len(reds)
ws.cell(row=t, column=1, value='Total').font = Font(name=F, bold=True)
for j in range(2, 8):
    L = get_column_letter(j); ws.cell(row=t, column=j, value=f'=SUM({L}3:{L}{t-1})').font = Font(name=F, bold=True)
r0 = t + 3
ws.cell(row=r0-1, column=1, value='Parámetros por tipo y resolución').font = Font(name=F, bold=True, size=12, color='1F3A5F')
ress = ['1 minuto', '10 minutos', 'Horaria', 'Diaria']
for j, h in enumerate(['Tipo'] + ress + ['Total filas'], 1):
    x = ws.cell(row=r0, column=j, value=h); x.font = HF; x.fill = HFILL
for i, tp in enumerate(['Meteorológico', 'Calidad del aire'], r0+1):
    ws.cell(row=i, column=1, value=tp).font = BF
    for j, rs in enumerate(ress, 2):
        ws.cell(row=i, column=j, value=f'=COUNTIFS(Parámetros!$D:$D,$A{i},Parámetros!$G:$G,"{rs}*")').font = BF
    ws.cell(row=i, column=6, value=f'=COUNTIFS(Parámetros!$D:$D,$A{i})').font = Font(name=F, bold=True)
ws.column_dimensions['A'].width = 46
for j in range(2, 8): ws.column_dimensions[get_column_letter(j)].width = 15
ws.row_dimensions[2].height = 32

# ---------------- Fuentes
ws = wb.create_sheet('Fuentes')
src = pd.DataFrame([
    ['DMC – SACLIM', 'DMC, INIA, ESO, Armada, DGA (catastro)', 'Catastro y fichas de estación: coordenadas, elementos con año desde/hasta, estado en las últimas 24 h. Producto "Datos minutarios" para EMA.', 'https://climatologia.meteochile.gob.cl'],
    ['Agromet (INIA – Red Agroclimática Nacional)', 'INIA, DMC, Armada (SERVIMET)', 'Listado de estaciones, estado "en línea" y variables publicadas; consultas horarias y diarias.', 'https://agrometeorologia.cl'],
    ['SINCA – Ministerio del Medio Ambiente', 'Estaciones de calidad del aire públicas y de empresas', 'Fichas de estación: parámetros contaminantes y meteorológicos con primer/último registro, frecuencia, altura y técnica.', 'https://sinca.mma.gob.cl'],
    ['CR2 – Explorador Climático', 'DGA', 'Disponibilidad diaria por año de precipitación y temperaturas extremas (1940–2026).', 'https://explorador.cr2.cl'],
    ['DGA – BNA y red en línea', 'DGA', 'Reportes meteorológicos oficiales (diarios); transmisión satelital horaria.', 'https://snia.mop.gob.cl/BNAConsultas/reportes'],
    ['CEAZA-Met', 'CEAZA', 'Servicio web: sensores con altura, primera y última lectura; series horarias.', 'https://www.ceazamet.cl'],
    ['Ministerio de Energía – Campaña de medición eólica y solar', 'Torres y estaciones solares', 'Catálogo de sitios con variables por altura y fechas; datos de 10 minutos.', 'http://walker.dgf.uchile.cl/Mediciones/'],
], columns=['Fuente', 'Redes', 'Qué se extrajo', 'URL'])
table(ws, src, 'Fuentes', [40, 36, 80, 50], wrap=('Qué se extrajo', 'Redes'))

wb.save(V+'Catalogo_estaciones_Iquique_Caldera.xlsx')
df.to_pickle(V+'st_final.pkl'); dp.to_pickle(V+'pr_final.pkl')
print('ok', len(df), len(dp))
