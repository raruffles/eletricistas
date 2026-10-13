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

# Build list of 50 electricians
used = set()
electricians = []
city_counts = {}

for c in clients:
    name = c['Nome do Profissional / Empresa']
    city = c['Cidade']
    phone = c['Telefone / WhatsApp']
    nota = c['Nota'] or '5.0'
    reviews = ascii_only(c['Avaliações'] or '0')
    obs = c['Observações Comerciais'] or ''
    if not name or not city: continue
    slug = slugify(name, city, used)
    city_code = CITY_SLUGS.get(city, 'outros')
    city_counts[city_code] = city_counts.get(city_code, 0) + 1

    try:
        nota_f = f'{float(nota):.1f}'
    except:
        nota_f = '5.0'

    obs_lower = obs.lower()
    if '24h' in obs_lower:
        badge = 'Plantão 24h'
    elif 'nr10' in obs_lower:
        badge = 'NR-10'
    elif 'industrial' in obs_lower or 'comercial' in obs_lower:
        badge = 'Comercial & Ind.'
    elif 'solar' in obs_lower:
        badge = 'Energia Solar'
    elif 'liderança' in obs_lower:
        badge = 'Top Avaliações'
    else:
        badge = 'Credenciado'

    electricians.append({
        'name': name,
        'city': city,
        'city_code': city_code,
        'slug': slug,
        'wa': wa_number(phone),
        'tel': text_number(phone),
        'nota': nota_f,
        'reviews': reviews,
        'obs': obs or 'Atendimento elétrico profissional residencial e comercial.',
        'badge': badge,
        'link_google': c.get('Link Google') or '',
        'link_maps': c.get('Link Google Maps') or ''
    })

print(f'Eletricistas carregados: {len(electricians)}')

# ── Function to build Cards HTML with specified link prefix ──
def build_cards_html(link_mode='root'):
    cards = []
    for el in electricians:
        if link_mode == 'root':
            # From root index.html to clean URL folder
            site_link = f"{el['slug']}/"
        elif link_mode == 'subfolder':
            # From clean URL subfolder ../{slug}/
            site_link = f"../{el['slug']}/"
        elif link_mode == 'sites_html':
            # Inside sites/ directory
            site_link = f"{el['slug']}.html"

        card = f'''      <article class="network-card" data-city="{el['city_code']}" data-search="{el['name'].lower()} {el['city'].lower()} {el['obs'].lower()} {el['badge'].lower()}">
        <div class="network-card-header">
          <div class="network-city-tag">
            <i class="ph-fill ph-map-pin" aria-hidden="true"></i>
            <span>{el['city']}</span>
          </div>
          <span class="network-badge">{el['badge']}</span>
        </div>
        <h3 class="network-card-title">{el['name']}</h3>
        <div class="network-rating-strip">
          <span class="network-stars"><i class="ph-fill ph-star" aria-hidden="true"></i> {el['nota']}</span>
          <span class="network-reviews-count">{el['reviews']} avaliações no Google</span>
        </div>
        <p class="network-card-desc">{el['obs']}</p>
        <div class="network-card-actions">
          <a class="btn-network-site" href="{site_link}" title="Acessar página de {el['name']}">
            <span>Ver Página</span>
            <i class="ph-bold ph-arrow-right" aria-hidden="true"></i>
          </a>
          <a class="btn-network-wa" href="https://wa.me/{el['wa']}?text=Ol%C3%A1%2C+vi+seu+perfil+na+Rede+Regional+de+Eletricistas+e+gostaria+de+um+or%C3%A7amento" target="_blank" rel="noopener noreferrer" aria-label="WhatsApp {el['name']}">
            <svg class="svg-wa" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91C2.13 13.66 2.59 15.36 3.45 16.86L2.05 22L7.3 20.62C8.75 21.41 10.38 21.83 12.04 21.83C17.5 21.83 21.95 17.38 21.95 11.92C21.95 9.27 20.92 6.78 19.05 4.91C17.18 3.03 14.69 2 12.04 2ZM12.04 3.67C14.24 3.67 16.31 4.53 17.87 6.08C19.42 7.64 20.28 9.71 20.28 11.92C20.28 16.46 16.59 20.16 12.04 20.16C10.59 20.16 9.17 19.78 7.92 19.04L7.62 18.86L4.5 19.68L5.33 16.64L5.13 16.32C4.33 15.04 3.8 13.5 3.8 11.91C3.8 7.37 7.5 3.67 12.04 3.67ZM8.97 7.42C8.76 7.42 8.51 7.5 8.3 7.73C8.08 7.96 7.49 8.52 7.49 9.65C7.49 10.78 8.32 11.87 8.44 12.02C8.56 12.18 10.03 14.47 12.33 15.42C14.24 16.2 14.63 16.05 15.06 16.01C15.48 15.97 16.42 15.45 16.61 14.91C16.8 14.37 16.8 13.91 16.74 13.82C16.68 13.73 16.53 13.67 16.31 13.56C16.1 13.45 15.06 12.94 14.87 12.87C14.67 12.8 14.53 12.76 14.39 12.98C14.24 13.2 13.83 13.68 13.7 13.83C13.58 13.98 13.46 14 13.25 13.89C13.03 13.78 12.34 13.55 11.52 12.82C10.88 12.25 10.45 11.54 10.33 11.33C10.21 11.11 10.31 10.99 10.42 10.88C10.52 10.78 10.64 10.62 10.76 10.48C10.88 10.34 10.92 10.23 11 10.07C11.08 9.91 11.04 9.77 10.98 9.65C10.92 9.53 10.47 8.42 10.28 7.96C10.1 7.52 9.91 7.58 9.77 7.57L9.34 7.56C9.13 7.56 8.97 7.42 8.97 7.42Z"/>
            </svg>
            <span>WhatsApp</span>
          </a>
        </div>
      </article>'''
        cards.append(card)
    return '\n'.join(cards)

# ── Function to build the entire Network Section ──
def build_network_section(link_mode='root'):
    cards_html = build_cards_html(link_mode)
    return f'''<!-- ══════════════════════════════════════════════════════════
     REDE REGIONAL DE ELETRICISTAS (50 CIDADES/PROFISSIONAIS)
══════════════════════════════════════════════════════════ -->
<section class="network-section" id="rede">
  <div class="wrap">
    <div class="sec-head">
      <div class="eyebrow"><span class="dot"></span> Rede Regional no Vale do Paraíba</div>
      <h2>Eletricistas Credenciados em 6 Cidades</h2>
      <p>
        Encontre profissionais qualificados em São José dos Campos, Jacareí, Taubaté, Caçapava, Guaratinguetá e Pindamonhangaba com atendimento ágil e sem intermediários:
      </p>
    </div>

    <!-- Filtros por Cidade & Barra de Pesquisa Rápida -->
    <div class="network-controls">
      <div class="city-tabs" role="tablist" aria-label="Filtrar por cidade">
        <button class="city-tab active" data-city="all" type="button">Todas ({len(electricians)})</button>
        <button class="city-tab" data-city="sjc" type="button">São José dos Campos ({city_counts.get('sjc', 0)})</button>
        <button class="city-tab" data-city="taubate" type="button">Taubaté ({city_counts.get('taubate', 0)})</button>
        <button class="city-tab" data-city="jacarei" type="button">Jacareí ({city_counts.get('jacarei', 0)})</button>
        <button class="city-tab" data-city="cacapava" type="button">Caçapava ({city_counts.get('cacapava', 0)})</button>
        <button class="city-tab" data-city="guaratingueta" type="button">Guaratinguetá ({city_counts.get('guaratingueta', 0)})</button>
        <button class="city-tab" data-city="pinda" type="button">Pindamonhangaba ({city_counts.get('pinda', 0)})</button>
      </div>

      <div class="network-search-box">
        <i class="ph-bold ph-magnifying-glass" aria-hidden="true"></i>
        <input type="text" id="networkSearchInput" placeholder="Buscar por nome, bairro ou especialidade (ex: 24h, NR-10)..." aria-label="Pesquisar eletricista">
        <span class="network-search-count" id="networkCount">{len(electricians)} de {len(electricians)}</span>
      </div>
    </div>

    <!-- Grid dos Cards -->
    <div class="network-grid" id="networkGrid">
{cards_html}
    </div>

    <div class="network-empty" id="networkEmpty" style="display: none;">
      <i class="ph-fill ph-warning-circle" aria-hidden="true"></i>
      <h4>Nenhum eletricista encontrado para esta busca</h4>
      <p>Tente buscar por outro termo ou clique em "Todas ({len(electricians)})".</p>
    </div>
  </div>
</section>
'''

network_js = '''
// ── Filtro Interativo da Rede Regional de Eletricistas ──
(function() {
  function initNetworkFilter() {
    const tabs = document.querySelectorAll('.city-tab');
    const searchInput = document.getElementById('networkSearchInput');
    const countEl = document.getElementById('networkCount');
    const emptyEl = document.getElementById('networkEmpty');
    const cards = document.querySelectorAll('.network-card');

    if (!cards.length) return;

    let activeCity = 'all';
    let searchTerm = '';

    function filterCards() {
      let visible = 0;
      cards.forEach(card => {
        const cardCity = card.getAttribute('data-city') || '';
        const cardSearch = (card.getAttribute('data-search') || '').toLowerCase();

        const matchesCity = activeCity === 'all' || cardCity === activeCity;
        const matchesSearch = !searchTerm || cardSearch.includes(searchTerm);

        if (matchesCity && matchesSearch) {
          card.style.display = '';
          visible++;
        } else {
          card.style.display = 'none';
        }
      });

      if (countEl) countEl.textContent = `${visible} de ${cards.length}`;
      if (emptyEl) emptyEl.style.display = visible === 0 ? 'block' : 'none';
    }

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeCity = tab.getAttribute('data-city');
        filterCards();
      });
    });

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchTerm = (e.target.value || '').trim().toLowerCase();
        filterCards();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNetworkFilter);
  } else {
    initNetworkFilter();
  }
})();
'''

# 1. Update index.html
with open(index_path, 'r', encoding='utf-8') as f:
    index_html = f.read()

# Replace existing network section with fresh root-linked section
existing_section_pattern = re.compile(r'<!-- ═+\s+REDE REGIONAL DE ELETRICISTAS.*?</section>\n', re.DOTALL)
if existing_section_pattern.search(index_html):
    index_html = existing_section_pattern.sub(build_network_section('root'), index_html)
else:
    index_html = index_html.replace('<!-- ══════════════════════════════════════════════════════════\n     FAQ COM PALAVRAS-CHAVE DO GOOGLE',
                                    f"{build_network_section('root')}\n<!-- ══════════════════════════════════════════════════════════\n     FAQ COM PALAVRAS-CHAVE DO GOOGLE")

# Inject network_js before </body>
if 'initNetworkFilter' not in index_html:
    index_html = index_html.replace('</script>\n</body>', f'{network_js}\n</script>\n</body>')

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(index_html)
print('index.html atualizado e funcional com busca e filtros!')

# 2. Update all 50 Clean URL folders (/{slug}/index.html)
subsite_banner = '''<!-- Barra Superior de Navegação da Rede Regional -->
<div class="network-breadcrumb-bar" style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); padding: 0.6rem 0; font-size: 13px;">
  <div class="wrap" style="display: flex; align-items: center; justify-content: space-between;">
    <a href="../#rede" style="display: inline-flex; align-items: center; gap: 0.5rem; color: var(--soft); text-decoration: none; font-weight: 600;">
      <i class="ph-bold ph-arrow-left" aria-hidden="true"></i>
      <span>Voltar para a Rede Regional (50 Eletricistas no Vale do Paraíba)</span>
    </a>
    <span style="font-size: 12px; color: var(--muted); display: none; @media(min-width:600px){display:inline;}">raphaelolima.com</span>
  </div>
</div>
'''

# Pre-render subfolder network section and sites_html network section
subfolder_network_sec = build_network_section('subfolder')
sites_html_network_sec = build_network_section('sites_html')

for el in electricians:
    # Build sub-site template from updated index_html
    sub_html = index_html

    # Replace name and brand
    display_name = el['name']
    first_name = el['name'].split()[0] if el['name'].split() else el['name']
    if display_name.upper().startswith('ELETRICISTA') or display_name.upper().startswith('ELETRICA'):
        display_name = el['name']
        first_name = el['name']

    sub_html = sub_html.replace('Lupercio Neto', display_name)
    sub_html = sub_html.replace('Lupercio', first_name)

    # City string replacements
    city = el['city']
    sigla = CITY_SIGLAS.get(city, city[:3].upper())
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
        sub_html = sub_html.replace(old, new)

    # Phone replacements
    sub_html = sub_html.replace('(12) 99999-9999', el['tel'])
    sub_html = sub_html.replace('5512999999999', el['wa'])
    sub_html = sub_html.replace('+5512999999999', f'+{el["wa"]}')
    sub_html = sub_html.replace('129999999999', el['wa'][2:])

    # Ratings
    sub_html = sub_html.replace('54 avaliações reais', f'{el["reviews"]} avaliações reais')
    sub_html = sub_html.replace('54 clientes', f'{el["reviews"]} clientes')
    sub_html = sub_html.replace('auditada por 54', f'auditada por {el["reviews"]}')
    sub_html = sub_html.replace('5.0 <span class="acc">★</span>', f'{el["nota"]} <span class="acc">★</span>')
    sub_html = sub_html.replace('>5.0<', f'>{el["nota"]}<')

    # Add breadcrumb bar right after <body>
    sub_html = sub_html.replace('<body>', f'<body>\n{subsite_banner}', 1)

    # 1. Write clean URL subfolder index.html ({slug}/index.html)
    folder_dir = os.path.join(base_dir, el['slug'])
    os.makedirs(folder_dir, exist_ok=True)
    clean_sub_html = sub_html.replace('src="imgs/', 'src="../imgs/')
    clean_sub_html = clean_sub_html.replace('href="favicon.ico"', 'href="../favicon.ico"')
    clean_sub_html = clean_sub_html.replace('href="imgs/', 'href="../imgs/')
    # Replace network section with subfolder links (../{other_slug}/)
    clean_sub_html = existing_section_pattern.sub(subfolder_network_sec, clean_sub_html)

    clean_file = os.path.join(folder_dir, 'index.html')
    with open(clean_file, 'w', encoding='utf-8') as f:
        f.write(clean_sub_html)

    # 2. Write sites/{slug}.html
    sites_sub_html = existing_section_pattern.sub(sites_html_network_sec, sub_html)
    sites_file = os.path.join(output_sites_dir, f'{el["slug"]}.html')
    with open(sites_file, 'w', encoding='utf-8') as f:
        f.write(sites_sub_html)

print('Todos os 50 sites dedicados (clean URL e sites/) foram regenerados perfeitamente!')
