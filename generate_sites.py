import csv
import json
import os
import re
import shutil
import unicodedata

base_dir = r'C:\Users\rapha\Downloads\site-template'
csv_path = os.path.join(base_dir, 'Planilha de Prospecção - academia - eletricista - Página1.csv')
index_path = os.path.join(base_dir, 'index.html')
output_sites_dir = os.path.join(base_dir, 'sites')
imgs_src_dir = os.path.join(base_dir, 'imgs')
imgs_dest_dir = os.path.join(output_sites_dir, 'imgs')

CITY_SLUGS = {
    'São José dos Campos': 'sjc',
    'Jacareí': 'jacarei',
    'Taubaté': 'taubate',
    'Pindamonhangaba': 'pinda',
    'Guaratinguetá': 'guaratingueta',
    'Caçapava': 'cacapava'
}

CITY_SIGLAS = {
    'São José dos Campos': 'SJC',
    'Jacareí': 'JCA',
    'Taubaté': 'TBT',
    'Pindamonhangaba': 'PIND',
    'Guaratinguetá': 'GTA',
    'Caçapava': 'CCP'
}

def ascii_only(value):
    return unicodedata.normalize('NFKD', value or '').encode('ASCII', 'ignore').decode('ASCII').strip()

def clean_phone(phone):
    return ascii_only(phone or '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

def wa_number(phone):
    digits = clean_phone(phone)
    if digits.startswith('55'): return digits
    if len(digits) >= 10: return '55' + digits
    return digits

def text_number(phone):
    digits = clean_phone(phone)
    if digits.startswith('55') and len(digits) >= 12: digits = digits[2:]
    if len(digits) == 11: return f'({digits[:2]}) {digits[2:7]}-{digits[7:]}'
    elif len(digits) == 10: return f'({digits[:2]}) {digits[2:6]}-{digits[6:]}'
    elif len(digits) >= 11:
        local = digits[-11:]
        return f'({local[:2]}) {local[2:7]}-{local[7:]}'
    return phone or '(12) 99999-9999'

def slugify(name, city, used_slugs):
    base = ascii_only(name) or 'cliente'
    words = [w for w in base.split() if w.isalnum()]
    city_slug = CITY_SLUGS.get(city, 'regiao')
    if len(words) >= 2:
        slug = f'{words[0].lower()}-{words[1].lower()}-{city_slug}'
    else:
        slug = f'{words[0].lower()}-{city_slug}' if words else f'cliente-{city_slug}'
    if slug in used_slugs:
        suffix = 2
        while f'{slug}-{suffix}' in used_slugs: suffix += 1
        slug = f'{slug}-{suffix}'
    used_slugs.add(slug)
    return slug

# Read CSV
raw = open(csv_path, 'rb').read()
clients = None
for enc in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
    try:
        text = raw.decode(enc)
        if '\ufffd' not in text:
            clients = list(csv.DictReader(text.splitlines()))
            break
    except:
        pass
if not clients:
    clients = list(csv.DictReader(raw.decode('latin-1', errors='replace').splitlines()))

# Sincronização de imagens
os.makedirs(output_sites_dir, exist_ok=True)
if os.path.exists(imgs_src_dir):
    shutil.copytree(imgs_src_dir, imgs_dest_dir, dirs_exist_ok=True)

# Limpeza de HTMLs antigos
for item in os.listdir(output_sites_dir):
    if item.endswith('.html'):
        os.remove(os.path.join(output_sites_dir, item))

with open(index_path, 'r', encoding='utf-8') as f:
    template = f.read()

subsite_banner = '''<!-- Barra Superior de Navegação da Rede Regional -->
<div class="network-breadcrumb-bar" style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); padding: 0.6rem 0; font-size: 13px;">
  <div class="wrap" style="display: flex; align-items: center; justify-content: space-between;">
    <a href="../index.html#rede" style="display: inline-flex; align-items: center; gap: 0.5rem; color: var(--soft); text-decoration: none; font-weight: 600;">
      <i class="ph-bold ph-arrow-left" aria-hidden="true"></i>
      <span>Voltar para a Rede Regional (50 Eletricistas no Vale do Paraíba)</span>
    </a>
    <span style="font-size: 12px; color: var(--muted); display: none; @media(min-width:600px){display:inline;}">raphaelolima.com</span>
  </div>
</div>
'''

used_slugs = set()
count = 0

for client in clients:
    name = client['Nome do Profissional / Empresa']
    city = client['Cidade']
    phone = client['Telefone / WhatsApp']
    reviews = ascii_only(client['Avaliações'] or '0')
    nota = client['Nota'] or '5.0'
    obs = client['Observações Comerciais'] or ''
    if not name or not city: continue

    slug = slugify(name, city, used_slugs)
    sigla = CITY_SIGLAS.get(city, city[:3].upper())
    wa = wa_number(phone)
    tel = text_number(phone)

    try:
        nota_f = f'{float(nota):.1f}'
    except:
        nota_f = '5.0'

    html = template
    display_name = name
    first_name = name.split()[0] if name.split() else name

    html = html.replace('Lupercio Neto', display_name)
    html = html.replace('Lupercio', first_name)

    city_replacements = [
        ('Eletricista em São José dos Campos (SJC) 24h', f'Eletricista em {city} 24h'),
        ('Eletricista em São José dos Campos (SJC)', f'Eletricista em {city}'),
        ('Eletricista em São José dos Campos', f'Eletricista em {city}'),
        ('em São José dos Campos', f'em {city}'),
        ('de São José dos Campos', f'de {city}'),
        ('São José dos Campos (SJC)', f'{city} ({sigla})'),
        ('São José dos Campos', city),
        ('Eletricista SJC 24 Horas', f'Eletricista {sigla} 24 Horas'),
        ('Eletricista SJC 24h', f'Eletricista {sigla} 24h'),
        ('Eletricista SJC', f'Eletricista {sigla}'),
        ('no Google SJC', f'no Google {sigla}'),
        ('SJC', sigla),
    ]
    for old, new in city_replacements:
        html = html.replace(old, new)

    html = html.replace('(12) 99999-9999', tel)
    html = html.replace('5512999999999', wa)
    html = html.replace('+5512999999999', f'+{wa}')
    html = html.replace('129999999999', wa[2:])

    html = html.replace('54 avaliações reais', f'{reviews} avaliações reais')
    html = html.replace('54 clientes', f'{reviews} clientes')
    html = html.replace('auditada por 54', f'auditada por {reviews}')
    html = html.replace('5.0 <span class="acc">★</span>', f'{nota_f} <span class="acc">★</span>')
    html = html.replace('>5.0<', f'>{nota_f}<')

    # Breadcrumb bar
    html = html.replace('<body>', f'<body>\n{subsite_banner}', 1)

    # 1. Arquivo em sites/<slug>.html
    filename = f'{slug}.html'
    filepath = os.path.join(output_sites_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    # 2. Pasta para URL limpa: raphaelolima.com/<slug>
    folder_dir = os.path.join(base_dir, slug)
    os.makedirs(folder_dir, exist_ok=True)
    clean_url_html = html.replace('src="imgs/', 'src="../imgs/')
    clean_url_html = clean_url_html.replace('href="favicon.ico"', 'href="../favicon.ico"')
    clean_url_html = clean_url_html.replace('href="imgs/', 'href="../imgs/')
    with open(os.path.join(folder_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(clean_url_html)

    count += 1
    print(f'Gerado: {filename} e pasta /{slug}/')

print(f'\nTotal de {count} sites e pastas gerados com sucesso!')
