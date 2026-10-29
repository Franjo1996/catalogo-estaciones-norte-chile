import re, math
import pandas as pd
from pyproj import Transformer

import os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
V = B + 'v2/'
LATN, LATS = -19.95, -27.30
HOY = '28-10-2026'

def inside(lat): return LATS <= lat <= LATN
def hav(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
    return 2*6371*math.asin(math.sqrt(h))
def region(lat, lon):
    if lat > -21.45:
        return 'Antofagasta' if (lat < -21.15 and lon > -68.9) else 'Tarapacá'
    if lat > -26.0: return 'Antofagasta'
    return 'Atacama'

ST, PR = [], []
def station(**k):
    k.setdefault('Notas', ''); ST.append(k); return k
def param(st, tipo, par, desde, hasta, res, alt='', tec='', cob=None, acc=''):
    PR.append({'_key': st['_key'], 'Tipo': tipo, 'Parámetro': par, 'Altura sensor': alt, 'Resolución más fina': res,
               'Desde': desde, 'Hasta': hasta, 'Cobertura (%)': cob, 'Técnica / instrumento': tec, 'Acceso a datos': acc})

# ------------------------------------------------------------------ DMC / SACLIM
dmc = {}
for fn in ['dmc_part1.csv', 'dmc_part2.csv']:
    for l in open(B+fn, encoding='utf-8'):
        f = l.rstrip('\n').split(';')
        if len(f) < 17: continue
        dmc[f[0]] = dict(code=f[0], omm=f[1], oaci=f[2], name=f[3], lat=float(f[4]), lon=float(f[5]), alt=float(f[6]),
                         prop=f[7], fc=f[8], tipo={'A': 'Automática', 'C': 'Convencional', 'M': 'Mixta'}[f[9]], clas=f[10],
                         oper=f[15], op24=f[16] == '1')
elems = {}
for l in open(V+'dmc_elems.txt', encoding='utf-8'):
    c, e = l.strip().split('|')
    elems[c] = [(int(x.split(':')[0]), *map(int, x.split(':')[1].split('-'))) for x in e.split(',')]

# element -> (parameter label, kind) ; kind: 'auto' sensor, 'obs' observer/METAR, 'rs' sounding, 'day' daily product
EL = {26: ('Temperatura del aire', 'auto'), 42: ('Temperatura del aire', 'auto'), 43: ('Temperatura del aire', 'auto'),
      44: ('Temperatura del aire', 'auto'), 45: ('Temperatura del aire', 'auto'),
      66: ('Humedad relativa', 'auto'), 67: ('Temperatura de punto de rocío', 'auto'), 23: ('Temperatura de bulbo húmedo', 'obs'),
      64: ('Presión atmosférica (QFE/QFF/QNH)', 'auto'), 65: ('Presión atmosférica (QFE/QFF/QNH)', 'auto'), 70: ('Presión atmosférica (QFE/QFF/QNH)', 'auto'),
      1: ('Tendencia barométrica', 'obs'),
      173: ('Precipitación', 'auto'), 57: ('Precipitación', 'auto'), 60: ('Precipitación', 'auto'), 55: ('Precipitación', 'auto'),
      28: ('Viento (dirección y velocidad)', 'auto'), 149: ('Viento (dirección y velocidad)', 'auto'), 150: ('Viento (dirección y velocidad)', 'auto'),
      20: ('Racha de viento', 'auto'), 29: ('Variación de la dirección del viento', 'obs'), 83: ('Cizalladura del viento', 'obs'),
      89: ('Radiación solar global', 'auto'), 90: ('Radiación solar global', 'auto'),
      94: ('Radiación UV (índice UV / irradiancia eritémica)', 'auto'), 96: ('Radiación UV (índice UV / irradiancia eritémica)', 'auto'),
      95: ('Radiación UV-B', 'auto'), 50: ('Heliofanía (horas de sol)', 'day'), 93: ('Heliofanía (horas de sol)', 'auto'),
      152: ('Evapotranspiración', 'day'), 52: ('Evaporación de bandeja', 'day'),
      11: ('Temperatura de suelo', 'auto'), 151: ('Temperatura de suelo', 'auto'),
      4: ('Nubosidad (cantidad, tipo, altura)', 'obs'), 5: ('Nubosidad (cantidad, tipo, altura)', 'obs'),
      6: ('Nubosidad (cantidad, tipo, altura)', 'obs'), 7: ('Nubosidad (cantidad, tipo, altura)', 'obs'),
      30: ('Visibilidad', 'obs'), 32: ('Visibilidad', 'obs'), 163: ('Visibilidad', 'obs'), 164: ('Visibilidad', 'obs'),
      27: ('Visibilidad', 'obs'), 84: ('Visibilidad', 'obs'),
      33: ('Tiempo presente y pasado', 'obs'), 34: ('Tiempo presente y pasado', 'obs'), 40: ('Tiempo presente y pasado', 'obs'),
      21: ('Tiempo presente y pasado', 'obs'), 10: ('Estado del suelo', 'obs'),
      86: ('Perfiles verticales (radiosondeo)', 'rs'), 189: ('Perfiles verticales (radiosondeo)', 'rs')}

ACC_DMC = 'climatologia.meteochile.gob.cl (datos minutarios EMA: registro gratuito; horarios/diarios libres)'
ACC_AGRO = 'agrometeorologia.cl (horario, diario; libre)'

def dmc_res(s, kind, par):
    auto = s['tipo'] in ('Automática', 'Mixta')
    if kind == 'rs': return 'Diaria (sondeo 12 UTC)'
    if kind == 'obs': return 'Horaria (METAR/SYNOP)' if s['tipo'] != 'Automática' or s['prop'] == 'DMC' else 'Horaria'
    if kind == 'day': return 'Diaria'
    if s['prop'] == 'INIA': return 'Horaria'
    if par.startswith('Heliofanía') or par.startswith('Radiación UV'): return 'Horaria'
    if par.startswith('Radiación solar global') and s['prop'] == 'DMC': return '10 minutos (producto DMC); 1 min en datos EMA'
    if s['prop'] in ('DMC',) and auto: return '1 minuto'
    if s['prop'] in ('DIRECTEMAR',): return 'Horaria (observación sinóptica)'
    if s['prop'] == 'ESO': return 'Horaria (vía DMC)'
    if not auto: return 'Diaria / sinóptica'
    return 'Horaria'

# Agromet
agro = []
for l in open(V+'agromet.txt', encoding='utf-8'):
    f = l.rstrip('\n').split('|')
    agro.append(dict(id=f[0], name=f[1], inst=f[2], lat=float(f[3]), lon=float(f[4]), alt=float(f[5]), com=f[6], status=f[7],
                     dias=int(f[8]), vars=f[9].split()))
for a in agro: a['used'] = False

dga_saclim_unmatched = []
for c, s in dmc.items():
    if not inside(s['lat']): continue
    if s['prop'] == 'DGA':
        dga_saclim_unmatched.append(s); continue
    el = elems.get(c, [])
    el15 = [e for e in el if e[2] >= 2015]
    # agromet match
    am = None
    for a in agro:
        if not a['used'] and hav(s['lat'], s['lon'], a['lat'], a['lon']) < 1.0 and (a['inst'] in s['prop'] or (a['inst'] == 'MMA-DMC' and s['prop'] == 'DMC')):
            am = a; a['used'] = True; break
    if not el15 and not (am and am['status'] == 'en línea'):
        continue
    last = max([e[2] for e in el15], default=None)
    first = min([e[1] for e in el15], default=None)
    if s['op24'] or (am and am['status'] == 'en línea'):
        est, crit = 'Sí', 'Datos en las últimas 24 h (' + ('SACLIM' if s['op24'] else '') + (' y ' if s['op24'] and am else '') + ('Agromet "en línea"' if am else '') + f', {HOY})'
    elif last and last >= 2026:
        est, crit = 'Sí', f'Datos en {last} en SACLIM, sin transmisión en las últimas 24 h'
    elif last and last >= 2025:
        est, crit = 'Probable', f'Últimos datos en SACLIM: {last}'
    else:
        est, crit = 'No', f'Últimos datos en SACLIM: {last}'
    red = {'DMC': 'DMC', 'INIA': 'INIA / Agromet', 'ESO': 'ESO (vía DMC)', 'DIRECTEMAR': 'Armada (DIRECTEMAR)'}.get(s['prop'], s['prop'])
    notas = []
    if c == '230001': notas.append('Única estación de radiosondeo del norte (OMM 85442). La DMC también publica perfiles AMDAR de aeronaves en Antofagasta.')
    if s['prop'] == 'ESO': notas.append('Integrada a SACLIM en 2026; ESO mantiene su propio archivo de condiciones ambientales del observatorio.')
    if am and am['inst'] != 'INIA': notas.append(f"También publicada en Agromet (id {am['id']}).")
    if s['prop'] == 'INIA': notas.append(f"Agromet id {am['id']}." if am else '')
    if first and first < 2015 and last and last >= 2015: pass
    k = station(_key='DMC'+c, Nombre=s['name'], Red=red, Propietario=s['prop'], Código=c,
                **{'Código OMM / OACI': ' / '.join(x for x in [s['omm'], s['oaci']] if x)},
                Región=region(s['lat'], s['lon']), Latitud=s['lat'], Longitud=s['lon'], **{'Altitud (m)': s['alt']},
                Tipo='Meteorológica', Instalación=f"{s['tipo']} – {s['clas']}",
                **{'Operativa': est, 'Criterio operatividad': crit, 'Fuente metadatos': f'https://climatologia.meteochile.gob.cl/application/informacion/fichaDeEstacion/{c}',
                   'Acceso a datos': ACC_AGRO if s['prop'] == 'INIA' else ACC_DMC, 'Notas': ' '.join(x for x in notas if x)})
    # params
    agg = {}
    for eid, a, b in el:
        if eid not in EL: continue
        lab, kind = EL[eid]
        if b < 2015: continue
        alt = ''
        if eid in (28, 149): alt = '10 m'
        if eid == 150: alt = '2 m'
        if eid == 11: alt = '-0.10 m'
        if eid == 151: alt = '-0.05 m'
        key = (lab, alt if lab.startswith('Viento') or lab.startswith('Temperatura de suelo') else '')
        g = agg.setdefault(key, [a, b, kind])
        g[0] = min(g[0], a); g[1] = max(g[1], b)
        if kind == 'auto': g[2] = 'auto'
    for (lab, alt), (a, b, kind) in agg.items():
        res = dmc_res(s, kind, lab)
        if lab == 'Precipitación' and s['prop'] == 'INIA' and any(e[0] == 55 for e in el): res = 'Horaria (15 min en SACLIM 2010–2016)'
        param(k, 'Meteorológico', lab, a, b, res, alt=alt, acc=k['Acceso a datos'])

# Agromet stations not in SACLIM (SERVIMET, etc.)
VMAP = {'TA': 'Temperatura del aire', 'HR': 'Humedad relativa', 'PP': 'Precipitación', 'VV': 'Viento (dirección y velocidad)',
        'DV': 'Viento (dirección y velocidad)', 'RD': 'Radiación solar global'}
for a in agro:
    if a['used'] or not inside(a['lat']): continue
    vs = list(dict.fromkeys(VMAP[v.split('-')[0]] for v in a['vars'] if v.split('-')[0] in VMAP))
    if not vs and a['inst'] == 'SERVIMET':
        vs = list(dict.fromkeys(VMAP.values())); a['nota'] = 'Fuera de línea en Agromet; variables según el resto de la red SERVIMET.'
    est = 'Sí' if a['status'] == 'en línea' else 'No'
    k = station(_key='AGRO'+a['id'], Nombre=a['name'], Red='Armada – SERVIMET (vía Agromet)' if a['inst'] == 'SERVIMET' else a['inst'],
                Propietario='Armada de Chile (SERVIMET)' if a['inst'] == 'SERVIMET' else a['inst'], Código=f"Agromet {a['id']}",
                **{'Código OMM / OACI': ''}, Región=region(a['lat'], a['lon']), Latitud=a['lat'], Longitud=a['lon'],
                **{'Altitud (m)': a['alt']}, Tipo='Meteorológica', Instalación='Automática',
                **{'Operativa': est, 'Criterio operatividad': f"Agromet: '{a['status']}' ({HOY}); {a['dias']} días con datos",
                   'Fuente metadatos': 'https://agrometeorologia.cl', 'Acceso a datos': ACC_AGRO,
                   'Notas': ('Estación nueva: registro corto (desde 2025–2026). ' if a['dias'] < 400 else '') + a.get('nota', '')})
    y0 = 2026 if a['dias'] < 300 else 2025
    for v in vs:
        param(k, 'Meteorológico', v, y0, 2026 if est == 'Sí' else None, 'Horaria', acc=ACC_AGRO)

# ------------------------------------------------------------------ DGA (CR2) + SACLIM DGA
dga = []
for l in open(B+'dga_cr2.csv', encoding='utf-8'):
    f = l.strip().split(';')
    if len(f) < 8: continue
    v = {}
    for tok in f[7].split():
        m = re.match(r'(\w+):(\d{4})-(\d{4})\((\d+)%\)', tok)
        v[m.group(1)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    dga.append(dict(code=f[0], name=f[1], lat=float(f[2]), lon=float(f[3]), alt=float(f[4]) if f[4] else None, v=v))
ACC_DGA = 'DGA: BNA (snia.mop.gob.cl, diaria oficial) y transmisión satelital en línea (horaria); CR2 Explorador Climático (diaria)'
for g in dga:
    if not inside(g['lat']): continue
    last = max(x[1] for x in g['v'].values())
    if last < 2015: continue
    sm = next((s for s in dga_saclim_unmatched if hav(s['lat'], s['lon'], g['lat'], g['lon']) < 3), None)
    if sm: dga_saclim_unmatched.remove(sm)
    est, crit = ('Probable', f'Datos hasta {last} en la base CR2 (actualizada hasta 2025)') if last >= 2025 else ('No', f'Últimos datos en la base CR2: {last}')
    k = station(_key='DGA'+g['code'], Nombre=g['name'], Red='DGA', Propietario='DGA', Código=g['code'],
                **{'Código OMM / OACI': ''}, Región=region(g['lat'], g['lon']), Latitud=g['lat'], Longitud=g['lon'],
                **{'Altitud (m)': g['alt']}, Tipo='Meteorológica', Instalación='Automática – DGA' if sm else 'Meteorológica DGA',
                **{'Operativa': est, 'Criterio operatividad': crit, 'Fuente metadatos': 'https://explorador.cr2.cl' + (f' ; SACLIM {sm["code"]}' if sm else ''),
                   'Acceso a datos': ACC_DGA,
                   'Notas': 'Las estaciones automáticas DGA miden típicamente precipitación, temperatura y humedad relativa (registro cada 30–60 min, transmisión horaria); la base pública consolidada solo ofrece precipitación y temperaturas extremas diarias.'})
    names = {'PP': 'Precipitación', 'TX': 'Temperatura del aire (máx./mín. diaria)', 'TN': 'Temperatura del aire (máx./mín. diaria)'}
    agg = {}
    for kk, (a, b, c) in g['v'].items():
        if b < 2015: continue
        lab = names[kk]; x = agg.setdefault(lab, [a, b, c]); x[0] = min(x[0], a); x[1] = max(x[1], b); x[2] = min(x[2], c)
    for lab, (a, b, c) in agg.items():
        param(k, 'Meteorológico', lab, a, b, 'Diaria (base consolidada); horaria en línea', cob=c, acc=ACC_DGA)
for s in dga_saclim_unmatched:
    if s['fc'][-4:] < '2012': continue
    k = station(_key='DMC'+s['code'], Nombre=s['name'], Red='DGA', Propietario='DGA', Código=f"SACLIM {s['code']}",
                **{'Código OMM / OACI': ''}, Región=region(s['lat'], s['lon']), Latitud=s['lat'], Longitud=s['lon'],
                **{'Altitud (m)': s['alt']}, Tipo='Meteorológica', Instalación='Automática – DGA',
                **{'Operativa': 'Sin información', 'Criterio operatividad': f"Alta en SACLIM {s['fc']}; sin inventario de datos público",
                   'Fuente metadatos': f"https://climatologia.meteochile.gob.cl/application/informacion/fichaDeEstacion/{s['code']}",
                   'Acceso a datos': ACC_DGA,
                   'Notas': 'Estación automática DGA sin datos en las bases públicas revisadas; consultar a la DGA (probablemente precipitación, red de alerta de quebradas).'})
    param(k, 'Meteorológico', 'Precipitación (probable; a confirmar con DGA)', int(s['fc'][-4:]), None, 'Horaria (transmisión satelital)', acc=ACC_DGA)

# ------------------------------------------------------------------ SINCA
tr = Transformer.from_crs('EPSG:32719', 'EPSG:4326', always_xy=True)
AQN = {'MP2.5': 'MP2,5', 'MP 2,5 (MP 2,5 - μg/m3)': 'MP2,5', 'MP10': 'MP10', 'MP10disc': 'MP10 (gravimétrico, muestras de 24 h)',
       'SO2': 'SO2', 'NO': 'NO', 'NO2': 'NO2', 'NOX': 'NOx', 'CO': 'CO', 'O3': 'O3', 'Pb': 'Plomo (Pb) en MP10', 'As': 'Arsénico (As) en MP10', 'Cu': 'Cobre (Cu) en MP10'}
MTN = {'RadGlobal': 'Radiación solar global', 'HR': 'Humedad relativa', 'T': 'Temperatura del aire', 'WDIR': 'Viento – dirección',
       'WSPD': 'Viento – velocidad', 'P': 'Presión atmosférica', 'PP': 'Precipitación'}
ACC_SINCA = 'sinca.mma.gob.cl (series horarias descargables, libre)'
cur = None; stn = []
for l in open(V+'sinca_params.txt', encoding='utf-8'):
    f = l.rstrip('\n').split('|')
    if f[0] == 'S':
        cur = dict(id=f[1], n=f[2], com=f[3], prop=f[4], oper=f[5], E=float(f[6]), N=float(f[7]), ini=f[8], rec=f[9], p=[]); stn.append(cur)
    else:
        cur['p'].append(dict(kind=f[1], code=f[2], freq=f[3], alt=f[4], d0=f[5], d1=f[6], h0=f[7], tec=f[8]))
for s in stn:
    lon, lat = tr.transform(s['E'], s['N'])
    if not inside(lat): continue
    ps = [p for p in s['p'] if p['d1'][:4].isdigit() and int(p['d1'][:4]) >= 2015]
    if not ps: continue
    last = max(p['d1'] for p in ps)
    if last >= '2026-10-01': est, crit = 'Sí', f'Último dato {last} (SINCA)'
    elif last >= '2026-01-01': est, crit = 'Probable', f'Último dato {last} (SINCA); sin datos en las últimas semanas'
    else: est, crit = 'No', f'Último dato {last} (SINCA)'
    kinds = {p['kind'] for p in ps}
    tipo = 'Calidad del aire + meteorología' if kinds == {'aq', 'met'} else ('Calidad del aire' if 'aq' in kinds else 'Meteorológica')
    notas = []
    if s['id'] == '68': notas.append('Las coordenadas UTM publicadas coinciden con Hospital del Cobre (Calama); probable error de la ficha.')
    notas.append(f"Inicio de operación reportado {s['ini']}; recepción de datos: {s['rec']}.")
    k = station(_key='SINCA'+s['id'], Nombre=f"{s['n']} ({s['com']})", Red='SINCA (calidad del aire)', Propietario=s['prop'],
                Código=f"SINCA {s['id']}", **{'Código OMM / OACI': ''}, Región=region(lat, lon), Latitud=round(lat, 5), Longitud=round(lon, 5),
                **{'Altitud (m)': None}, Tipo=tipo, Instalación=f"Monitoreo continuo – operador {s['oper']}",
                **{'Operativa': est, 'Criterio operatividad': crit, 'Fuente metadatos': f"https://sinca.mma.gob.cl/index.php/estacion/index/id/{s['id']}",
                   'Acceso a datos': ACC_SINCA, 'Notas': ' '.join(notas)})
    for p in ps:
        if p['kind'] == 'aq':
            name = AQN.get(p['code'], p['code'])
            res = 'Diaria (muestra de 24 h)' if 'disc' in p['code'] or p['code'] in ('Pb', 'As', 'Cu') else 'Horaria'
            d0 = p['d0']
            if p['h0'] and p['h0'][:4].isdigit() and p['h0'] < d0 and p['h0'] > '1995': d0 = p['h0']
            param(k, 'Calidad del aire', name, d0, p['d1'], res, tec=p['tec'], acc=ACC_SINCA)
        else:
            name = MTN.get(p['code'], p['code'])
            alt = '' if p['alt'] in ('S/I', 'No definido') else p['alt']
            param(k, 'Meteorológico', name, p['d0'], p['d1'], 'Horaria', alt=alt or 'No informada', tec=p['tec'], acc=ACC_SINCA)

# ------------------------------------------------------------------ CEAZA (SALH, CNPP)
for l in open(B+'ceaza.txt', encoding='utf-8'):
    if l.startswith('#'): continue
    f = l.strip().split('|')
    if len(f) < 9: continue
    code, name, lat, lon, alt, p1, p2, prov, sens = f
    lat, lon = float(lat), float(lon)
    if not inside(lat) or p2[:4] < '2015': continue
    k = station(_key='CEAZA'+code, Nombre=name, Red='CEAZA-Met', Propietario='CEAZA' + (' / IEB' if 'IEB' in name else ''), Código=code,
                **{'Código OMM / OACI': ''}, Región=region(lat, lon), Latitud=lat, Longitud=lon, **{'Altitud (m)': float(alt)},
                Tipo='Meteorológica', Instalación='Automática',
                **{'Operativa': 'No', 'Criterio operatividad': f'Última lectura {p2} (CEAZA-Met)', 'Fuente metadatos': 'https://www.ceazamet.cl',
                   'Acceso a datos': 'ceazamet.cl (servicio web, horaria con mín./prom./máx.; libre)', 'Notas': ''})
    for x in sens.split(';'):
        n, h = x.strip().split('@')
        param(k, 'Meteorológico', n, p1, p2, 'Horaria (mín./prom./máx.)', alt=h, acc='ceazamet.cl')

# ------------------------------------------------------------------ Ministerio de Energía
VN = {'vels': 'Viento – velocidad', 'velB': 'Viento – velocidad (anemómetro secundario)', 'dirv': 'Viento – dirección',
      'temp': 'Temperatura del aire', 'hrel': 'Humedad relativa', 'pres': 'Presión atmosférica', 'rglb': 'Radiación solar global',
      'rglb_ta': 'Radiación global (seguidor solar)', 'rdif_ta': 'Radiación difusa (seguidor solar)', 'rdni_ta': 'Radiación directa normal (seguidor solar)',
      'rdif': 'Radiación difusa', 'rdni': 'Radiación directa normal', 'rnet': 'Radiación neta', 'rglb_ref': 'Radiación global (sensor de referencia)'}
for l in open(B+'minenergia.csv', encoding='utf-8'):
    f = l.strip().split(';')
    if len(f) < 10: continue
    code, name, lat, lon, alt, status, ini, fin, grp, com = f[:10]
    vv = f[10] if len(f) > 10 else ''
    lat, lon = float(lat), float(lon)
    if not inside(lat) or fin[:4] < '2015' or not vv: continue
    tipo = {'eolo/20m': 'Torre de prospección eólica 20 m', 'eolo/80m': 'Torre de medición eólica 110 m', 'solar/giz': 'Estación de monitoreo solar',
            'solar/cordero': 'Sitio de monitoreo solar'}.get(grp, grp)
    k = station(_key='MEN'+code, Nombre=name, Red='Ministerio de Energía (campaña eólica y solar)', Propietario='Ministerio de Energía',
                Código=code, **{'Código OMM / OACI': ''}, Región=region(lat, lon), Latitud=lat, Longitud=lon, **{'Altitud (m)': float(alt)},
                Tipo='Meteorológica', Instalación=tipo,
                **{'Operativa': 'No', 'Criterio operatividad': f'Campaña terminada: última observación {fin}', 'Fuente metadatos': 'http://walker.dgf.uchile.cl/Mediciones/',
                   'Acceso a datos': 'walker.dgf.uchile.cl/Mediciones (10 min; libre)', 'Notas': ''})
    for tok in vv.split():
        kk, h = tok.split('@')
        if kk not in VN: continue
        for hh in h.split('/'):
            param(k, 'Meteorológico', VN[kk], ini, fin, '10 minutos', alt=f'{hh} m', acc='walker.dgf.uchile.cl')

# ------------------------------------------------------------------ Radiosonda / AMDAR as separate rows
k = station(_key='RS85442', Nombre='Radiosonda Antofagasta (Cerro Moreno)', Red='DMC', Propietario='DMC', Código='OMM 85442',
            **{'Código OMM / OACI': '85442 / SCFA'}, Región='Antofagasta', Latitud=-23.45361, Longitud=-70.44528, **{'Altitud (m)': 139},
            Tipo='Perfiles verticales', Instalación='Radiosondeo',
            **{'Operativa': 'Sí', 'Criterio operatividad': 'Vuelos registrados en 2026 (SACLIM)', 'Fuente metadatos': 'https://climatologia.meteochile.gob.cl/application/informacion/fichaDeEstacion/230001',
               'Acceso a datos': 'climatologia.meteochile.gob.cl (productos RadioSondas); también Univ. of Wyoming / IGRA', 'Notas': 'Mismo sitio que la estación de superficie Cerro Moreno.'})
for p in ['Temperatura', 'Humedad relativa / punto de rocío', 'Viento (dirección y velocidad)', 'Altura geopotencial / presión']:
    param(k, 'Meteorológico', p + ' (perfil)', 1981, 2026, '1 sondeo diario (12 UTC)', acc=k['Acceso a datos'])
k = station(_key='AMDAR', Nombre='AMDAR – aeronaves en aeropuertos de Antofagasta, Calama e Iquique', Red='DMC', Propietario='DMC / aerolíneas',
            Código='AMDAR', **{'Código OMM / OACI': 'SCFA, SCCF, SCDA'}, Región='Antofagasta', Latitud=-23.45361, Longitud=-70.44528,
            **{'Altitud (m)': None}, Tipo='Perfiles verticales', Instalación='Observaciones de aeronaves en ascenso y descenso',
            **{'Operativa': 'Sí', 'Criterio operatividad': 'Producto AMDAR mensual vigente en el portal DMC', 'Fuente metadatos': 'https://climatologia.meteochile.gob.cl/application/requerimiento/producto/RE1017',
               'Acceso a datos': 'climatologia.meteochile.gob.cl (Datos AMDAR; registro gratuito)', 'Notas': 'Frecuencia irregular, según vuelos. Coordenadas: aeropuerto Cerro Moreno como referencia.'})
for p in ['Temperatura (perfil)', 'Viento (perfil)']:
    param(k, 'Meteorológico', p, None, 2026, 'Por vuelo (irregular)', acc=k['Acceso a datos'])

df = pd.DataFrame(ST); dp = pd.DataFrame(PR)
# derived station columns
def summarize(g, tipo):
    x = g[g['Tipo'] == tipo]['Parámetro'].tolist()
    return '; '.join(dict.fromkeys(x))
rows = []
for _, s in df.iterrows():
    g = dp[dp['_key'] == s['_key']]
    ys = [int(str(v)[:4]) for v in g['Desde'] if v is not None and str(v)[:4].isdigit()]
    ye = [int(str(v)[:4]) for v in g['Hasta'] if v is not None and str(v)[:4].isdigit()]
    res = list(dict.fromkeys(g['Resolución más fina']))
    order = ['1 minuto', '10 minutos', 'Horaria']
    best = next((r for o in order for r in res if r.startswith(o)), res[0] if res else '')
    rows.append({'Parámetros meteorológicos': summarize(g, 'Meteorológico'), 'Parámetros calidad del aire': summarize(g, 'Calidad del aire'),
                 'Resolución más fina': best, 'Primer dato': min(ys) if ys else None, 'Último dato': max(ye) if ye else None})
df = pd.concat([df, pd.DataFrame(rows)], axis=1)
df['Cubre 2015–2026'] = df.apply(lambda r: 'Sí' if (r['Primer dato'] or 9999) <= 2015 and (r['Último dato'] or 0) >= 2026 else 'Parcial', axis=1)
df.to_pickle(V+'st.pkl'); dp.to_pickle(V+'pr.pkl')
print(len(df), len(dp))
print(df.groupby('Red').size()); print(df.groupby('Operativa').size()); print(df.groupby('Tipo').size())
print(df[df['Red'] == 'INIA / Agromet'][['Nombre', 'Notas']].to_string())
