"""Extracción de artículos de la Ley 1801 de 2016 desde la base documental del Senado.

BASE DE REFERENCIA PARA WILDER (Fase 1). NO es el pipeline oficial del corpus:
fue escrita para sacar rápido 10 artículos de muestra (corpus/muestra/) y sirve
como punto de partida, no como solución final. Limitaciones conocidas:
  - La vigencia es una sola etiqueta por artículo (la fuente la marca por numeral).
  - Los encabezados de libro/título/capítulo se detectan con heurísticas.
  - Solo extrae los artículos listados en SEL; no procesa los 243.

Uso:
    python extraer_senado.py <carpeta> <salida.json> <marcas.json>

  <carpeta>      debe contener la subcarpeta "senado/" con las 6 páginas HTML
                 descargadas de secretariasenado.gov.co/senado/basedoc/:
                 ley_1801_2016.html y ley_1801_2016_pr001.html ... _pr005.html
                 (codificación ISO-8859-1).
  <salida.json>  corpus de salida (id, ubicacion, epigrafe, texto, vigencia, tema).
  <marcas.json>  marcas editoriales de la fuente que justifican cada vigencia.
"""
import sys, re, html, json
from pathlib import Path
sp = Path(sys.argv[1])
files = ['ley_1801_2016.html'] + [f'ley_1801_2016_pr00{i}.html' for i in range(1, 6)]
raw = []
for f in files:
    t = (sp / 'senado' / f).read_bytes().decode('latin-1')
    t = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', '', t)
    t = re.sub(r'(?i)</t[dh]>', ' | ', t)
    t = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>|</li>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    raw.append(html.unescape(t))
full = '\n'.join(raw)
full = re.sub(r'[ \t\xa0]+', ' ', full)
lines = [l.strip() for l in full.split('\n')]
lines = [l for l in lines if l]

NOISE = {'Notas de Vigencia', 'Jurisprudencia Vigencia', 'Legislación Anterior', 'Notas del Editor',
         'Resumen de Notas de Vigencia', 'Jurisprudencia', 'Concordancias', 'Siguiente', 'Anterior'}
art_re = re.compile(r'^ART[ÍI]CULO (\d+)o?\.\s*(.*)$')
lib_re = re.compile(r'^LIBRO (PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO)\.?$')
tit_re = re.compile(r'^T[ÍI]TULO ([IVXL]+)\.?$')
cap_re = re.compile(r'^CAP[ÍI]TULO ([IVXL]+)\.?$')

# Locate start (first ARTÍCULO 1) and walk
arts = {}
state = {'libro': None, 'titulo': None, 'capitulo': None}
backup = dict(state)
cur = None
pending = None  # heading name collection: (key, number)
def is_heading(l): return bool(lib_re.match(l) or tit_re.match(l) or cap_re.match(l) or art_re.match(l))
started = False
for l in lines:
    if not started:
        if art_re.match(l) and art_re.match(l).group(1) == '1':
            started = True
        else:
            # track headings before art 1
            pass
    m = lib_re.match(l)
    if m: backup = dict(state); pending = ['libro', m.group(1), []]; state['titulo'] = state['capitulo'] = None; cur = None; continue
    m = tit_re.match(l)
    if m: backup = dict(state); pending = ['titulo', m.group(1), []]; state['capitulo'] = None; cur = None; continue
    m = cap_re.match(l)
    if m: backup = dict(state); pending = ['capitulo', m.group(1), []]; cur = None; continue
    m = art_re.match(l)
    if m:
        if pending is not None and not pending[2]: state = dict(backup)
        pending = None
        n = int(m.group(1))
        cur = n
        if n not in arts:
            arts[n] = {'ubic': dict(state), 'lines': [m.group(2)]}
        else:
            cur = None
        continue
    if pending is not None and cur is None:
        if re.match(r'(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO)', l) or l in NOISE or l.startswith('<') or '|' in l or l != l.upper() or re.search(r'\d', l): continue
        pending[2].append(l)
        kind = {'libro': 'Libro', 'titulo': 'Título', 'capitulo': 'Capítulo'}[pending[0]]
        num = pending[1].capitalize() if pending[0] == 'libro' else pending[1]
        nm = ' '.join(pending[2]).strip().capitalize()
        state[pending[0]] = f'{kind} {num}. {nm}'
        continue
    if cur is not None:
        arts[cur]['lines'].append(l)
    # lines before a heading's name but after article: ignore
# fix: heading name collection must stop after article start (handled by cur) 

def clean(lines):
    out = []
    for l in lines:
        if l in NOISE: continue
        l = re.sub(r'<[^<>]*>', '', l)
        l = re.sub(r'\s+', ' ', l).strip()
        if not l: continue
        if l.startswith('|') and out: out[-1] += ' ' + l; continue
        out.append(l)
    return out

def split_epigrafe(first):
    first = re.sub(r'<[^<>]*>', '', first).strip() if first.startswith('<') else first
    m = re.match(r'^([^a-z.<]+?)\.(?:\s|$|<)', first)
    return (m.group(1).strip(), first[m.end():].strip()) if m else (first.strip(), '')

def vigencia(raw_lines):
    j = '\n'.join(raw_lines)
    marks = re.findall(r'<[^<>]*>', j)
    head = ' '.join(re.findall(r'<[^<>]*>', raw_lines[0])) if raw_lines else ''
    if re.search(r'Art[íi]culo INEXEQUIBLE', head, re.I): return 'inexequible', marks
    if re.search(r'Art[íi]culo CONDICIONALMENTE exequible', head, re.I): return 'exequible_condicionado', marks
    if re.search(r'(modificad|adicionad)o? (por|en cumplimiento)', j, re.I): return 'modificado', marks
    return 'vigente', marks

SEL = {
 173: ('Medidas correctivas', 'Medidas correctivas'),
 180: ('Multas', 'Tipos de multa'),
 218: ('Orden de comparendo', 'Comparendo'),
 139: ('Definición del espacio público', 'Espacio público'),
 140: ('Cuidado e integridad del espacio público', 'Consumo de sustancias en espacio público'),
 124: ('Tenencia de animales', 'Animales potencialmente peligrosos'),
 163: ('Ingreso a inmueble sin orden escrita', 'Ingreso a domicilio'),
 198: ('Autoridades de policía', 'Autoridades de policía'),
 222: ('Proceso verbal inmediato', 'Proceso verbal inmediato'),
 183: ('No pago de multas', 'No pago de multas'),
}
out = []; report = []
for n, (_, tema) in SEL.items():
    a = arts[n]
    ep, resto = split_epigrafe(a['lines'][0])
    body_lines = ([resto] if resto else []) + a['lines'][1:]
    vig, marks = vigencia(a['lines'])
    body = clean(body_lines)
    out.append({
        'id': f'art-{n}',
        'ubicacion': {'libro': a['ubic']['libro'], 'titulo': a['ubic']['titulo'],
                      'capitulo': a['ubic']['capitulo'], 'articulo': f'Artículo {n}'},
        'epigrafe': ep, 'texto': '\n'.join(body), 'vigencia': vig, 'tema': tema})
    report.append((n, vig, marks))
out.sort(key=lambda a: int(a['id'][4:]))
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
Path(sys.argv[3]).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
print(len(arts))
