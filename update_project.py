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
    
    # Formatted rating
    try:
        nota_f = f'{float(nota):.1f}'
    except:
        nota_f = '5.0'

    # Badge logic
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

print(f'Total de eletricistas carregados: {len(electricians)}')

# ── Generate Network Cards HTML ─────────────────────────────
cards_html = []
for el in electricians:
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
          <a class="btn-network-site" href="sites/{el['slug']}.html" title="Acessar página de {el['name']}">
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
    cards_html.append(card)

network_cards_joined = '\n'.join(cards_html)

network_section_html = f'''<!-- ══════════════════════════════════════════════════════════
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
{network_cards_joined}
    </div>

    <div class="network-empty" id="networkEmpty" style="display: none;">
      <i class="ph-fill ph-warning-circle" aria-hidden="true"></i>
      <h4>Nenhum eletricista encontrado para esta busca</h4>
      <p>Tente buscar por outro termo ou clique em "Todas as Cidades".</p>
    </div>
  </div>
</section>
'''

# ── Network CSS ─────────────────────────────────────────────
network_css = '''
/* ── Rede Regional de Eletricistas ───────────────────────── */
.network-section {
  padding: clamp(4.5rem, 7.5vw, 7rem) 0;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--bg-subtle) 60%, transparent);
}
.network-controls {
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
  margin-bottom: 2.8rem;
}
.city-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: center;
}
.city-tab {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-full);
  padding: 0.55rem 1.15rem;
  font-family: var(--font-body);
  font-size: 13.5px;
  font-weight: 600;
  color: var(--soft);
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.15s ease;
  white-space: nowrap;
}
.city-tab:hover {
  color: var(--ink);
  border-color: var(--amber);
  transform: translateY(-1px);
}
.city-tab.active {
  background: var(--amber);
  color: #000000;
  border-color: var(--amber);
  font-weight: 700;
  box-shadow: 0 2px 10px rgba(245, 158, 11, 0.35);
}
.network-search-box {
  position: relative;
  display: flex;
  align-items: center;
  max-width: 580px;
  width: 100%;
}
.network-search-box i {
  position: absolute;
  left: 1.1rem;
  color: var(--muted);
  font-size: 1.15rem;
  pointer-events: none;
}
.network-search-box input {
  width: 100%;
  padding: 0.85rem 5.5rem 0.85rem 2.8rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  font-family: var(--font-body);
  font-size: 14.5px;
  color: var(--ink);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.network-search-box input:focus {
  outline: none;
  border-color: var(--amber);
  box-shadow: 0 0 0 3px var(--amber-tint);
}
.network-search-count {
  position: absolute;
  right: 1rem;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  pointer-events: none;
}

.network-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}
@media (min-width: 640px) {
  .network-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 1.6rem;
  }
}
@media (min-width: 1024px) {
  .network-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 1.8rem;
  }
}

.network-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1.6rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1.1rem;
  box-shadow: var(--shadow-subtle);
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
.network-card:hover {
  transform: translateY(-3px);
  border-color: rgba(245, 158, 11, 0.4);
  box-shadow: var(--shadow-card);
}
.network-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.network-city-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 12px;
  font-weight: 600;
  color: var(--soft);
}
.network-city-tag i { color: var(--amber); font-size: 0.95rem; }
.network-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: var(--r-full);
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  color: var(--ink);
  letter-spacing: 0.02em;
}
.network-card-title {
  font-family: var(--font-heading);
  font-size: 16.5px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.3;
}
.network-rating-strip {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 12.5px;
}
.network-stars {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--amber);
  font-weight: 700;
}
.network-reviews-count { color: var(--muted); }
.network-card-desc {
  font-size: 13.5px;
  color: var(--soft);
  line-height: 1.6;
  flex-grow: 1;
}
.network-card-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.btn-network-site, .btn-network-wa {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  min-height: 42px;
  padding: 0.55rem 0.85rem;
  border-radius: var(--r-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
  white-space: nowrap;
}
.btn-network-site {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  color: var(--ink);
}
.btn-network-site:hover {
  background: var(--card-hover);
  border-color: var(--border-focus);
  color: var(--amber);
}
.btn-network-wa {
  background: var(--wa);
  border: 1px solid var(--wa);
  color: #ffffff;
}
.btn-network-wa:hover {
  background: var(--wa-hover);
}
.btn-network-wa .svg-wa {
  width: 1.1em;
  height: 1.1em;
  fill: #ffffff;
}
.network-empty {
  text-align: center;
  padding: 4rem 1.5rem;
  color: var(--soft);
}
.network-empty i { font-size: 2.8rem; color: var(--amber); margin-bottom: 0.8rem; display: inline-block; }
.network-empty h4 { font-size: 18px; color: var(--ink); margin-bottom: 0.4rem; }
'''

# ── Network JS ──────────────────────────────────────────────
network_js = '''
// ── Filtro da Rede Regional de Eletricistas ──
(function() {
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
      const cardCity = card.getAttribute('data-city');
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
      searchTerm = e.target.value.trim().toLowerCase();
      filterCards();
    });
  }
})();
'''

# ── Update index.html ───────────────────────────────────────
with open(index_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add Network CSS before </style>
if '.network-section' not in html:
    html = html.replace('</style>', f'{network_css}\n</style>')

# 2. Add Network section before #duvidas
if 'id="rede"' not in html:
    html = html.replace('<!-- ══════════════════════════════════════════════════════════\n     FAQ COM PALAVRAS-CHAVE DO GOOGLE',
                        f'{network_section_html}\n<!-- ══════════════════════════════════════════════════════════\n     FAQ COM PALAVRAS-CHAVE DO GOOGLE')

# 3. Add Network JS before </script>
if 'networkSearchInput' not in html:
    html = html.replace('</script>\n</body>', f'{network_js}\n</script>\n</body>')

# 4. Add header navigation link to #rede
if 'href="#rede"' not in html:
    # In footer links:
    html = html.replace('<a href="#sobre">Sobre</a>', '<a href="#sobre">Sobre</a>\n      <a href="#rede">Rede Regional</a>')

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('index.html atualizado com a seção da Rede Regional (50 eletricistas)!')

# ── Update and Run generate_sites.py ────────────────────────
# Clean output_sites_dir of stale html files
for item in os.listdir(output_sites_dir):
    if item.endswith('.html'):
        os.remove(os.path.join(output_sites_dir, item))
print('Limpeza de arquivos HTML antigos em sites/ concluída.')

# Sync images
if os.path.exists(imgs_src_dir):
    shutil.copytree(imgs_src_dir, imgs_dest_dir, dirs_exist_ok=True)
print('Sincronização de imagens para sites/imgs/ concluída.')

# Regenerate all 50 sites and create clean folder per electrician
template_content = html

# We create a banner back link in the template for sub-sites
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

for el in electricians:
    sub_html = template_content

    # Adapt name and city
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

    # 1. Save sites/<slug>.html
    site_file = os.path.join(output_sites_dir, f'{el["slug"]}.html')
    with open(site_file, 'w', encoding='utf-8') as f:
        f.write(sub_html)

    # 2. Save <slug>/index.html for clean URL raphaelolima.com/<slug>
    folder_dir = os.path.join(base_dir, el['slug'])
    os.makedirs(folder_dir, exist_ok=True)
    clean_url_html = sub_html.replace('src="imgs/', 'src="../imgs/')
    clean_url_html = clean_url_html.replace('href="favicon.ico"', 'href="../favicon.ico"')
    clean_url_html = clean_url_html.replace('href="imgs/', 'href="../imgs/')
    clean_url_file = os.path.join(folder_dir, 'index.html')
    with open(clean_url_file, 'w', encoding='utf-8') as f:
        f.write(clean_url_html)

print(f'Sucesso: 50 sites gerados em sites/ e 50 pastas para URLs limpas (raphaelolima.com/<nome-do-eletricista>)!')

# ── Create CNAME file for raphaelolima.com ───────────────────
cname_path = os.path.join(base_dir, 'CNAME')
with open(cname_path, 'w', encoding='utf-8') as f:
    f.write('raphaelolima.com\n')
print('Arquivo CNAME com raphaelolima.com criado com sucesso!')

# ── Create .gitignore ───────────────────────────────────────
gitignore_path = os.path.join(base_dir, '.gitignore')
with open(gitignore_path, 'w', encoding='utf-8') as f:
    f.write('''# Sistema e temporarios
*.log
.playwright-mcp/
__pycache__/
*.pyc

# Arquivos temporarios de captura
FireShot*.png
FireShot*.pdf
''')
print('Arquivo .gitignore criado com sucesso!')
