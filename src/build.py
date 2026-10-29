import math, re, json
import pandas as pd
from pyproj import Transformer

import os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
FECHA = '28-10-2026'

# ---------------- helpers ----------------
def region_from(lat, lon):
    if lat > -19.22:
        return 'Tarapacá' if (lat < -19.05 and lon > -69.5) else 'Arica y Parinacota'
    if lat > -21.45:
        if lat < -21.15 and lon > -68.9: return 'Antofagasta'
        return 'Tarapacá'
    if lat > -26.0: return 'Antofagasta'
    if lat > -29.35: return 'Atacama'
    return 'Coquimbo'

VARNAME = {
    'T': 'Temperatura del aire', 'HR': 'Humedad relativa / punto de rocío', 'P': 'Presión atmosférica',
    'PP': 'Precipitación', 'NIEVE': 'Nieve', 'V2': 'Viento (vel./dir.)', 'V10': 'Viento (vel./dir.)',
    'RAD': 'Radiación solar global', 'SOL': 'Heliofanía (horas de sol)', 'UV': 'Radiación UV',
    'TSUELO': 'Temperatura de suelo', 'ET': 'Evapotranspiración / evaporación',
    'NUB': 'Nubosidad, visibilidad y tiempo presente', 'RS': 'Perfiles verticales (radiosondeo)',
}
ORDER = list(dict.fromkeys(VARNAME.values()))

def parse_vars(s):
    out = []
    for tok in (s or '').split():
        k, v = tok.split(':')
        a, b = v.split('-')
        out.append((k, int(a), int(b)))
    return out

def hav(a, b, c, d):
    R = 6371; p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))

stations = []   # dicts
varrows = []    # long format

def add_var(st, var, desde, hasta, cob=None, altura=None, fuente=None):
    varrows.append({'ID': st['ID'], 'Red': st['Red'], 'Código': st['Código'], 'Nombre': st['Nombre'],
                    'Región': st['Región'], 'Variable': var, 'Desde': desde, 'Hasta': hasta,
                    'Cobertura (%)': cob, 'Altura sensor (m)': altura, 'Fuente': fuente or st['Fuente metadatos']})

# ---------------- CR2 / DGA ----------------
dga = []
for l in open(D+'dga_cr2.csv', encoding='utf-8'):
    l = l.strip()
    if not l: continue
    f = l.split(';')
    v = {}
    for tok in f[7].split():
        m = re.match(r'(\w+):(\d{4})-(\d{4})\((\d+)%\)', tok)
        v[m.group(1)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    dga.append(dict(code=f[0], name=f[1], lat=float(f[2]), lon=float(f[3]), alt=float(f[4]) if f[4] else None, v=v, saclim=None))

# ---------------- DMC / SACLIM ----------------
dmc = []
for fn in ['dmc_part1.csv', 'dmc_part2.csv']:
    for l in open(D+fn, encoding='utf-8'):
        l = l.rstrip('\n')
        if not l: continue
        f = l.split(';')
        dmc.append(dict(code=f[0], omm=f[1], oaci=f[2], name=f[3], lat=float(f[4]), lon=float(f[5]), alt=float(f[6]),
                        prop=f[7], fc=f[8], tipo={'A': 'Automática', 'C': 'Convencional', 'M': 'Mixta'}[f[9]],
                        clas=f[10], zona=f[11], reg_dmc=f[12], metar=f[13], synop=f[14], oper=f[15], op24=f[16] == '1',
                        vars=parse_vars(f[17])))

# match SACLIM-DGA with CR2-DGA (same station in two catalogs)
for s in dmc:
    if s['prop'] != 'DGA': continue
    best = min(dga, key=lambda g: hav(s['lat'], s['lon'], g['lat'], g['lon']))
    if hav(s['lat'], s['lon'], best['lat'], best['lon']) < 3.0 and best['saclim'] is None:
        best['saclim'] = s
        s['merged'] = best['code']

ceaza_heights_inia65 = 'Temp./HR 2 m; viento 2 m; radiación 2 m; presión 2 m; pluviómetro 1.5 m (según CEAZA-Met, código INIA65)'

URL_DMC = 'https://climatologia.meteochile.gob.cl/application/informacion/fichaDeEstacion/'
nid = 0
def newid(prefix):
    global nid; nid += 1
    return f'{prefix}-{nid:04d}'

for s in dmc:
    if s.get('merged'): continue
    reg = region_from(s['lat'], s['lon'])
    if reg == 'Coquimbo' or s['lat'] < -29.35: continue
    red = {'DMC': 'DMC (Dirección Meteorológica de Chile)', 'INIA': 'INIA / Red Agroclimática Nacional (Agromet)',
           'DGA': 'DGA (Dirección General de Aguas)', 'FDF': 'FDF (Fundación para el Desarrollo Frutícola)',
           'CODELCO': 'CODELCO (vía DMC)', 'ESO': 'ESO (vía DMC)', 'USACH': 'USACH (vía DMC)',
           'DIRECTEMAR': 'Armada / DIRECTEMAR (vía DMC)'}.get(s['prop'], s['prop'])
    notas = []
    if s['reg_dmc'] != reg:
        notas.append(f"SACLIM la asigna a la región '{s['reg_dmc']}'; por coordenadas corresponde a {reg}.")
    if s['code'] == '270017':
        notas.append('Latitud en SACLIM (-28.976) parece errónea: el Tranque Lautaro está cerca de -27.98; verificar.')
    if s['code'] == '280021':
        notas.append('Misma estación que "Vallenar [INIA]" (INIA65) publicada por CEAZA-Met. ' + ceaza_heights_inia65 + '.')
    if s['metar'] == 'S': notas.append('Emite METAR.')
    if s['synop'] == 'S': notas.append('Emite SYNOP.')
    if s['code'] == '230001': notas.append('Estación de radiosondeo (OMM 85442): única estación de sondeo de la DMC en el norte. Recibe también datos AMDAR.')
    vs = [x for x in s['vars'] if not (x[0] == 'RS' and s['code'] != '230001')]
    last = max([b for _, _, b in vs], default=None)
    first = min([a for _, a, _ in vs], default=None)
    if s['op24']:
        est, crit = 'Operativa', f'Con datos en las últimas 24 h en SACLIM ({FECHA})'
    elif last and last >= 2025:
        est, crit = 'Probablemente operativa', f'Sin datos en las últimas 24 h, pero con datos hasta {last}'
    elif not vs and s['fc'].endswith('2026'):
        est, crit = 'Nueva (2026)', 'Incorporada a SACLIM en 2026; aún sin inventario de datos publicado'
    elif not vs:
        est, crit = 'Sin información', 'Sin inventario de datos en SACLIM'
    else:
        est, crit = 'Inactiva / cerrada', f'Últimos datos en SACLIM: {last}'
    alt_s = []
    if any(k == 'V10' for k, _, _ in vs): alt_s.append('Viento 10 m')
    if any(k == 'V2' for k, _, _ in vs): alt_s.append('Viento 2 m')
    if s['code'] == '280021': alt_s = ['Temp./HR 2 m', 'Viento 2 m', 'Radiación 2 m', 'Pluviómetro 1.5 m']
    st = {'ID': newid('N'), 'Red': red, 'Propietario': s['prop'], 'Código': s['code'],
          'Código OMM / OACI': ' / '.join([x for x in [s['omm'], s['oaci']] if x]),
          'Nombre': s['name'], 'Región': reg, 'Latitud': s['lat'], 'Longitud': s['lon'], 'Altitud (m)': s['alt'],
          'Tipo': f"{s['tipo']} – {s['clas']}", 'Zona': s['zona'],
          'Variables': '; '.join(sorted({VARNAME[k] for k, _, _ in vs}, key=ORDER.index)),
          'Altura sensores': '; '.join(alt_s) if alt_s else 'No informada (estándar OMM: T/HR 1.5–2 m)' if vs else '',
          'Inicio datos': first, 'Fin datos': last, 'Estado': est, 'Criterio estado': crit,
          'Operador': s['oper'], 'Fuente metadatos': URL_DMC + s['code'], 'Notas': ' '.join(notas)}
    stations.append(st)
    for k, a, b in vs:
        add_var(st, VARNAME[k] + (' 10 m' if k == 'V10' else ' 2 m' if k == 'V2' else ''), a, b,
                altura=10 if k == 'V10' else 2 if k == 'V2' else None)

# DGA from CR2
URL_CR2 = 'https://explorador.cr2.cl'
for g in dga:
    reg = region_from(g['lat'], g['lon'])
    if reg == 'Coquimbo': continue
    s = g['saclim']
    v = g['v']
    last = max(x[1] for x in v.values()); first = min(x[0] for x in v.values())
    if last >= 2025:
        est, crit = 'Operativa', f'Precipitación con datos hasta {last} en la base CR2/DGA'
    elif last >= 2019:
        est, crit = 'Sin datos recientes', f'Últimos datos en la base CR2: {last} (puede ser rezago de actualización)'
    else:
        est, crit = 'Inactiva / cerrada', f'Últimos datos en la base CR2: {last}'
    notas = ['Periodos según base de datos CR2 (Explorador Climático), que compila datos DGA; cobertura = % de días con dato dentro del periodo.']
    if s: notas.append(f"También registrada en SACLIM-DMC como '{s['name']}' (código {s['code']}, {s['tipo'].lower()}).")
    vars_ = []
    if 'PP' in v: vars_.append('Precipitación')
    if 'TX' in v or 'TN' in v: vars_.append('Temperatura máxima y mínima')
    st = {'ID': newid('N'), 'Red': 'DGA (Dirección General de Aguas)', 'Propietario': 'DGA', 'Código': g['code'],
          'Código OMM / OACI': '', 'Nombre': g['name'], 'Región': reg, 'Latitud': g['lat'], 'Longitud': g['lon'],
          'Altitud (m)': g['alt'], 'Tipo': ('Automática – ' if s else '') + 'Meteorológica DGA', 'Zona': s['zona'] if s else '',
          'Variables': '; '.join(vars_), 'Altura sensores': 'No informada', 'Inicio datos': first, 'Fin datos': last,
          'Estado': est, 'Criterio estado': crit, 'Operador': 'DGA',
          'Fuente metadatos': URL_CR2 + (' ; ' + URL_DMC + s['code'] if s else ''), 'Notas': ' '.join(notas)}
    stations.append(st)
    names = {'PP': 'Precipitación', 'TX': 'Temperatura máxima', 'TN': 'Temperatura mínima'}
    for k, (a, b, c) in v.items():
        add_var(st, names[k], a, b, cob=c, fuente='CR2 Explorador Climático (datos DGA)')

# ---------------- CEAZA-Met ----------------
for l in open(D+'ceaza.txt', encoding='utf-8'):
    if l.startswith('#') or not l.strip(): continue
    f = l.strip().split('|')
    code, name, lat, lon, alt, p1, p2, prov, sens = f
    if code == 'INIA65': continue  # duplicada con 280021
    lat, lon = float(lat), float(lon)
    reg = region_from(lat, lon)
    est = 'Operativa' if p2 >= '2026-10-01' else ('Sin datos recientes' if p2 >= '2026-01-01' else 'Inactiva / cerrada')
    sl = [x.strip() for x in sens.split(';')]
    vs = []
    hts = []
    for x in sl:
        n, h = x.split('@')
        vs.append(n); hts.append(f'{n} {h}')
    st = {'ID': newid('N'), 'Red': 'CEAZA-Met', 'Propietario': 'CEAZA' + (' / IEB' if 'IEB' in name else ''), 'Código': code,
          'Código OMM / OACI': '', 'Nombre': name, 'Región': reg, 'Latitud': lat, 'Longitud': lon, 'Altitud (m)': float(alt),
          'Tipo': 'Automática', 'Zona': '', 'Variables': '; '.join(dict.fromkeys(vs)), 'Altura sensores': '; '.join(hts),
          'Inicio datos': int(p1[:4]), 'Fin datos': int(p2[:4]), 'Estado': est,
          'Criterio estado': f'Primera lectura {p1}; última lectura {p2} (servicio web CEAZA-Met)', 'Operador': 'CEAZA',
          'Fuente metadatos': 'https://www.ceazamet.cl', 'Notas': ''}
    stations.append(st)
    for x in sl:
        n, h = x.split('@')
        add_var(st, n, p1, p2, altura=h.replace('m', ''), fuente='CEAZA-Met (GetListaSensores)')

# ---------------- Ministerio de Energía ----------------
VN = {'vels': 'Velocidad viento', 'velB': 'Velocidad viento (anemómetro secundario)', 'dirv': 'Dirección viento',
      'temp': 'Temperatura del aire', 'hrel': 'Humedad relativa', 'pres': 'Presión atmosférica',
      'rglb': 'Radiación global', 'rglb_ta': 'Radiación global (rastreador)', 'rdif_ta': 'Radiación difusa (rastreador)',
      'rdni_ta': 'Radiación directa normal (rastreador)', 'rdif': 'Radiación difusa', 'rdni': 'Radiación directa normal',
      'rnet': 'Radiación neta', 'rglb_ref': 'Radiación global (referencia)', 'rsoz': 'Radiación (sensor SOZ)',
      'tsoz': 'Temperatura sensor SOZ', 'temp_int': None, 'bvlt': None, 'tint': None}
for l in open(D+'minenergia.csv', encoding='utf-8'):
    if not l.strip(): continue
    f = l.strip().split(';')
    code, name, lat, lon, alt, status, ini, fin, grp, com = f[:10]
    vv = f[10] if len(f) > 10 else ''
    lat, lon = float(lat), float(lon)
    reg = region_from(lat, lon)
    if reg == 'Coquimbo' or com in ('La Higuera',): continue
    tipo = {'eolo/20m': 'Torre prospección eólica 20 m', 'eolo/80m': 'Torre de medición eólica (60–110 m)',
            'solar/giz': 'Estación de monitoreo solar', 'eolo/pnud': 'Torre eólica 20–30 m (proyecto PNUD)',
            'eolo/4reg': 'Torre eólica 20 m', 'solar/cordero': 'Sitio de monitoreo solar'}.get(grp, grp)
    hts, vnames = [], []
    for tok in vv.split():
        k, h = tok.split('@')
        if VN.get(k) is None: continue
        vnames.append(VN[k]); hts.append(f'{VN[k]} {h} m')
    finy = int(fin[:4])
    st = {'ID': newid('N'), 'Red': 'Ministerio de Energía – Campaña de medición eólica y solar (DGF U. de Chile / GIZ)',
          'Propietario': 'Ministerio de Energía', 'Código': code, 'Código OMM / OACI': '', 'Nombre': name, 'Región': reg,
          'Latitud': lat, 'Longitud': lon, 'Altitud (m)': float(alt), 'Tipo': tipo, 'Zona': '',
          'Variables': '; '.join(dict.fromkeys(vnames)), 'Altura sensores': '; '.join(hts),
          'Inicio datos': int(ini[:4]), 'Fin datos': finy, 'Estado': 'Inactiva / cerrada',
          'Criterio estado': f'Primera observación {ini}; última observación {fin} (catálogo walker.dgf.uchile.cl)',
          'Operador': 'DGF U. de Chile (por encargo del Ministerio de Energía)', 'Fuente metadatos': 'http://walker.dgf.uchile.cl/Mediciones/',
          'Notas': 'Datos promedio 10 min.' + (' Coordenadas redondeadas en la fuente.' if code in ('CHAJNANTOR', 'CALAMA', 'CANCHONES') else '')}
    stations.append(st)
    for tok in vv.split():
        k, h = tok.split('@')
        if VN.get(k) is None: continue
        for hh in h.split('/'):
            add_var(st, VN[k], ini, fin, altura=float(hh), fuente='walker.dgf.uchile.cl (meta/siteinfo)')

# ---------------- SINCA ----------------
tr = Transformer.from_crs('EPSG:32719', 'EPSG:4326', always_xy=True)
RG = {'XV': 'Arica y Parinacota', 'I': 'Tarapacá', 'II': 'Antofagasta', 'III': 'Atacama'}
for l in open(D+'sinca.csv', encoding='utf-8'):
    if not l.strip(): continue
    f = l.strip().split(';')
    R, sid, n, com, prop, conv, oper, E, N, huso, ini, rec = f[:12]
    lon, lat = tr.transform(float(E), float(N))
    est = 'Operativa (en línea)' if rec == 'en línea' else 'Sin información'
    st = {'ID': newid('N'), 'Red': 'SINCA (Ministerio del Medio Ambiente) – estación de calidad del aire con meteorología',
          'Propietario': prop, 'Código': f'SINCA-{sid}', 'Código OMM / OACI': '', 'Nombre': f'{n} ({com})', 'Región': RG[R],
          'Latitud': round(lat, 5), 'Longitud': round(lon, 5), 'Altitud (m)': None, 'Tipo': 'Automática – calidad del aire',
          'Zona': '', 'Variables': 'Parámetros meteorológicos (detalle no publicado en la ficha; típicamente viento, temperatura y humedad)',
          'Altura sensores': 'No informada', 'Inicio datos': int(ini[:4]), 'Fin datos': None, 'Estado': est,
          'Criterio estado': f'Recepción de datos: {rec} (ficha SINCA)', 'Operador': oper,
          'Fuente metadatos': f'https://sinca.mma.gob.cl/index.php/estacion/index/id/{sid}',
          'Notas': f'Coordenadas convertidas desde UTM huso {huso}S (WGS84). Inicio de operación reportado: {ini}.'}
    stations.append(st)

# ---------------- Thesis stations ----------------
tesis = [
    ('Costero', 'ALP', 'Altos La Portada (INIA)', '230024', 'Probable'),
    ('Costero', 'UCN', 'Universidad Católica del Norte, Antofagasta (DMC)', '230002', 'Probable'),
    ('Costero', 'LCH', 'La Chimba (DGA) – Quebrada La Chimba / Liceo La Chimba', '230008 / 230009', 'Por confirmar'),
    ('Norte', 'CSP', 'Caspana (INIA)', '220022', 'Por confirmar'),
    ('Norte', 'CLR', 'Calama Rural (INIA)', '220023', 'Por confirmar'),
    ('Norte', 'AEL', 'El Loa, Calama Ad. (DMC, SCCF)', '220002', 'Por confirmar'),
    ('Salar', 'SCR', 'Socaire (INIA)', '230020', 'Probable'),
    ('Salar', 'SPA', 'San Pedro de Atacama INIA', '220024', 'Por confirmar'),
    ('Salar', 'TDMC', 'Toconao (DMC, Red Básica)', '230004', 'Probable'),
    ('Salar', 'TINIA', 'Toconao (INIA)', '230019', 'Probable'),
    ('Salar', 'CMR', 'Camar (INIA)', '230023', 'Probable'),
]
for c in ['d01', 'd02', 'D02T2', 'd04', 'D04T3', 'd05a', 'd05b', 'd08', 'd09', 'D09T1', 'd10']:
    tesis.append(('Sur', c, 'Torre Ministerio de Energía ' + c, c, 'Coincide (mismo código)'))
bycode = {s['Código']: s for s in stations}
trows = []
for g, c, n, m, conf in tesis:
    ids = [bycode[x.strip()]['ID'] for x in m.split('/') if x.strip() in bycode]
    trows.append({'Grupo tesis': g, 'Código tesis': c, 'Estación probable en catálogo': n, 'Código en catálogo': m,
                  'ID catálogo': ', '.join(ids), 'Confianza': conf})

df = pd.DataFrame(stations)
dv = pd.DataFrame(varrows)
dt = pd.DataFrame(trows)
df.to_pickle(D+'stations.pkl'); dv.to_pickle(D+'vars.pkl'); dt.to_pickle(D+'tesis.pkl')
print(len(df), len(dv))
print(df.groupby(['Red']).size())
print(df.groupby(['Región']).size())
print(df.groupby(['Estado']).size())
print(df[df['Notas'].str.contains('SACLIM la asigna')][['Código', 'Nombre', 'Región', 'Notas']].to_string())
