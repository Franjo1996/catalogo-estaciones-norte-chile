"""Genera mapa/index.html a partir de st_final.pkl / pr_final.pkl (salida de xlsx_v2.py)."""
import os, json
import pandas as pd
V = os.path.dirname(os.path.abspath(__file__)) + '/'
ROOT = os.path.dirname(os.path.dirname(V.rstrip('/'))) + '/'
df = pd.read_pickle(V+'st_final.pkl'); dp = pd.read_pickle(V+'pr_final.pkl')
K = {'DMC': 'DMC', 'INIA / Agromet': 'INIA', 'Armada (DIRECTEMAR)': 'ARM', 'Armada – SERVIMET (vía Agromet)': 'ARM', 'ESO (vía DMC)': 'ESO',
     'SINCA (calidad del aire)': 'SINCA', 'DGA': 'DGA', 'CEAZA-Met': 'CEAZA', 'Ministerio de Energía (campaña eólica y solar)': 'MINEN'}
S = {'Sí': 'op', 'Probable': 'prob', 'No': 'off', 'Sin información': 'unk'}
nz = lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else v
out = []
for _, r in df.iterrows():
    g = dp[dp.ID == r.ID]
    out.append(dict(id=r.ID, n=r.Nombre, k=K[r.Red], red=r.Red, p=r.Propietario, c=r['Código'], o=r['Código OMM / OACI'], reg=r['Región'],
                    la=round(r.Latitud, 5), lo=round(r.Longitud, 5), z=None if pd.isna(r['Altitud (m)']) else int(r['Altitud (m)']), t=r.Tipo,
                    res=r['Resolución más fina'], i=None if pd.isna(r['Primer dato']) else int(r['Primer dato']),
                    f=None if pd.isna(r['Último dato']) else int(r['Último dato']), cov=r['Cubre 2015–2026'], e=r.Operativa, s=S[r.Operativa],
                    cr=r['Criterio operatividad'], acc=r['Acceso a datos'], u=r['Fuente metadatos'].split(' ; ')[0], no=r.Notas,
                    ps=[[p.Tipo[0], p['Parámetro'], nz(p['Altura sensor']) or '', p['Resolución más fina'], str(nz(p.Desde) or ''), str(nz(p.Hasta) or '')] for _, p in g.iterrows()]))
t = open(V+'map_template_v2.html', encoding='utf-8').read()
html = t.replace('__STATIONS__', json.dumps(out, ensure_ascii=False, separators=(',', ':'))).replace('__BASE__', open(V+'../base.json', encoding='utf-8').read())
os.makedirs(ROOT+'mapa', exist_ok=True)
open(ROOT+'mapa/index.html', 'w', encoding='utf-8').write(html)
print('mapa/index.html', len(out), 'estaciones')
