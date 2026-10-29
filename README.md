# Catálogo de estaciones meteorológicas y de calidad del aire – Norte de Chile

Metadatos de estaciones de observación (no los datos) compilados el **28-10-2026** desde fuentes públicas.

## Versión actual: Iquique a Caldera (v2)

- **Dominio:** 19,95°S a 27,30°S, de la costa a la frontera (Tarapacá sur, Antofagasta y Atacama norte).
- **Periodo:** estaciones con al menos un parámetro con datos entre 2015 y la fecha.
- **Variables:** meteorológicas (superficie y perfiles verticales) y de calidad del aire (MP10, MP2,5, SO₂, NO, NO₂, NOx, CO, O₃, metales).
- **171 estaciones**, **793 filas de parámetros**: cada fila trae resolución más fina, periodo, altura de sensor y estado operativo.

| Archivo | Contenido |
|---|---|
| `data/Catalogo_estaciones_Iquique_Caldera.xlsx` | Planilla completa: Léame, Estaciones, Parámetros, Resumen y Fuentes |
| `data/estaciones_iquique_caldera.csv` | Hoja Estaciones (UTF-8) |
| `data/parametros_iquique_caldera.csv` | Hoja Parámetros (UTF-8) |
| `mapa/index.html` | Mapa interactivo autocontenido con filtros por red, estado, tipo y resolución |

### Resolución temporal más fina por red

| Red | Resolución | Acceso |
|---|---|---|
| DMC (estaciones automáticas) | 1 minuto | climatologia.meteochile.gob.cl (registro gratuito) |
| Ministerio de Energía (torres y estaciones solares) | 10 minutos | walker.dgf.uchile.cl/Mediciones |
| SINCA, INIA/Agromet, Armada (SERVIMET), CEAZA-Met | Horaria | sinca.mma.gob.cl, agrometeorologia.cl, ceazamet.cl |
| DGA | Horaria en línea; diaria en la base consolidada | snia.mop.gob.cl, explorador.cr2.cl |
| Radiosonda Antofagasta (OMM 85442) | 1 sondeo diario (12 UTC) | climatologia.meteochile.gob.cl |

### Estado operativo

- **Sí:** datos en las últimas 24 h o en el mes en curso.
- **Probable:** datos hasta 2025 o mediados de 2026 sin confirmación reciente. La base CR2 de la DGA llega a 2025.
- **No:** estación cerrada, campaña terminada o parámetros discontinuados.
- **Sin información:** estaciones DGA del catastro DMC sin datos en las bases públicas.

### Limitaciones

- **DGA:** la base pública solo trae precipitación y temperaturas extremas diarias; el resto de las variables horarias debe confirmarse con la DGA.
- **Altura de sensores:** publicada por SINCA, CEAZA-Met y Ministerio de Energía. En DMC/INIA se deduce del elemento (viento 10 m o 2 m).
- **Copiapó (27,37°S)** queda fuera del dominio por pocos kilómetros.

## Versión anterior: Arica a Atacama (v1)

`data/Catalogo_estaciones_norte_Chile.xlsx` y sus CSV `*_v1.csv`: 458 estaciones meteorológicas de todas las épocas, sin calidad del aire.

## Reproducir

```bash
pip install pandas openpyxl pyproj
python src/v2/build_v2.py     # une las fuentes
python src/v2/xlsx_v2.py      # genera la planilla en src/v2/
python src/v2/make_map_v2.py  # genera mapa/index.html
```

Los archivos de entrada en `src/` (`dmc_*.csv`, `dga_cr2.csv`, `sinca*.txt`, `agromet.txt`, `ceaza.txt`, `minenergia.csv`) son extractos de los portales listados abajo, tomados el 28-10-2026. `src/build.py` y `src/xlsx_build.py` generan la versión v1.

## Fuentes

- DMC – SACLIM: https://climatologia.meteochile.gob.cl
- Agromet (INIA – Red Agroclimática Nacional): https://agrometeorologia.cl
- SINCA – Ministerio del Medio Ambiente: https://sinca.mma.gob.cl
- CR2 – Explorador Climático (datos DGA): https://explorador.cr2.cl
- DGA – Información Oficial Hidrometeorológica: https://snia.mop.gob.cl/BNAConsultas/reportes
- CEAZA-Met: https://www.ceazamet.cl
- Ministerio de Energía – Campaña de medición eólica y solar: http://walker.dgf.uchile.cl/Mediciones/
- Contornos del mapa: Natural Earth vía world-atlas
