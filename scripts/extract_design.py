"""
extract_design.py — coleta a matéria-prima de um design system a partir de páginas renderizadas.

  python extract_design.py <pasta_saida> <url> [<url> ...]

Grava em <pasta_saida>/:
  raw-extraction.json      cores, fontes, escala tipográfica, espaçamentos, raios, sombras,
                           breakpoints, containers, grades, variáveis CSS e componentes
  screenshots/page-*.png   página inteira (desktop 1440 e mobile 390)
  screenshots/comp-*.png   recorte de cada variante de componente encontrada

É matéria-prima: valores contados por frequência. A curadoria (nomear, agrupar, descartar ruído)
é feita depois, gerando tokens.json.
"""
import asyncio, json, os, re, sys
from collections import Counter
from playwright.async_api import async_playwright

OUT = sys.argv[1]
URLS = sys.argv[2:]
SHOTS = os.path.join(OUT, "screenshots")
os.makedirs(SHOTS, exist_ok=True)

# Seletores de cada família de componente. A ordem importa: o primeiro que casar "reivindica" o elemento.
COMPONENTS = {
    "button": "button, [role=button], input[type=submit], input[type=button], a[class*=btn], a[class*=button], a[class*=Button], a[class*=cta]",
    "input": "input[type=text], input[type=email], input[type=tel], input[type=search], input[type=password], input[type=number], input:not([type])",
    "textarea": "textarea",
    "select": "select",
    "checkbox_radio": "input[type=checkbox], input[type=radio]",
    "form": "form",
    "navbar": "header, nav, [class*=navbar], [class*=header]:not(html):not(body):not(main)",
    "footer": "footer, [class*=footer]:not(html):not(body):not(main)",
    "hero": "main > section:first-of-type, [class*=hero], [class*=banner]",
    "card": "[class*=card], [class*=Card], article",
    "badge": ":is([class*=badge], [class*=tag], [class*=chip], [class*=pill], [class*=label]):not(label):not(form):not(svg):not(:has(form, input, svg, img))",
    "accordion": "details, [class*=accordion], [class*=faq] [aria-expanded]",
    "tabs": "[role=tablist], [class*=tabs]",
    "testimonial": "[class*=testimonial], [class*=depoimento], blockquote",
    "table": "table",
    "link": "main a:not([class*=btn]):not([class*=button])",
    "icon": "svg",
    "image": "img",
    "divider": "hr",
    "list": "main ul, main ol",
}

COLLECT_JS = r"""
(components) => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    // Fora da tela (links "pular para o conteúdo", menus fechados) conta como invisível
    const off = r.right <= 0 || r.bottom <= 0 || r.left >= document.documentElement.scrollWidth || (s.clip && s.clip !== 'auto') || s.clipPath === 'inset(50%)';
    return r.width > 1 && r.height > 1 && !off && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0; };
  const all = [...document.querySelectorAll('body *')].filter(vis);
  const bump = (o, k, n = 1) => { if (k && k !== 'none' && k !== 'normal' && k !== 'auto') o[k] = (o[k] || 0) + n; };
  const colors = {text: {}, background: {}, border: {}}, fonts = {}, sizes = {}, weights = {}, lineHeights = {},
        spacing = {}, gaps = {}, radius = {}, shadows = {}, transitions = {}, maxWidths = {};
  const grids = [], flexRows = {};
  for (const el of all) {
    const s = getComputedStyle(el);
    const area = Math.min(el.getBoundingClientRect().width * el.getBoundingClientRect().height, 200000);
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText) { bump(colors.text, s.color); bump(fonts, s.fontFamily); bump(sizes, s.fontSize); bump(weights, s.fontWeight); bump(lineHeights, s.lineHeight); }
    if (s.backgroundColor !== 'rgba(0, 0, 0, 0)') bump(colors.background, s.backgroundColor, 1 + Math.round(area / 20000));
    if (parseFloat(s.borderTopWidth) > 0) bump(colors.border, s.borderTopColor);
    for (const p of ['paddingTop','paddingRight','paddingBottom','paddingLeft','marginTop','marginBottom']) if (parseFloat(s[p]) > 0) bump(spacing, s[p]);
    if (s.rowGap && s.rowGap !== 'normal' && parseFloat(s.rowGap) > 0) bump(gaps, s.rowGap);
    if (s.columnGap && s.columnGap !== 'normal' && parseFloat(s.columnGap) > 0) bump(gaps, s.columnGap);
    if (parseFloat(s.borderTopLeftRadius) > 0) bump(radius, s.borderTopLeftRadius);
    bump(shadows, s.boxShadow);
    if (s.transitionDuration !== '0s') bump(transitions, s.transitionDuration + ' ' + s.transitionTimingFunction);
    if (s.maxWidth !== 'none' && s.maxWidth.endsWith('px')) bump(maxWidths, s.maxWidth);
    if (s.display.includes('grid') && grids.length < 40) grids.push({selector: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0,2).join('.') : ''), columns: s.gridTemplateColumns, gap: s.gap, children: el.children.length, width: Math.round(el.getBoundingClientRect().width)});
    if (s.display.includes('flex') && s.flexDirection.startsWith('row') && el.children.length >= 3) bump(flexRows, `${el.children.length} itens, gap ${s.columnGap}`);
  }
  // Escala tipográfica por tag semântica
  const typeScale = {};
  for (const tag of ['h1','h2','h3','h4','h5','h6','p','a','li','small','label','button','blockquote','span']) {
    const el = [...document.querySelectorAll(tag)].find(e => vis(e) && e.textContent.trim().length > 1);
    if (!el) continue;
    const s = getComputedStyle(el);
    typeScale[tag] = {fontFamily: s.fontFamily, fontSize: s.fontSize, fontWeight: s.fontWeight, lineHeight: s.lineHeight,
                      letterSpacing: s.letterSpacing, textTransform: s.textTransform, color: s.color, sample: el.textContent.trim().slice(0, 60)};
  }
  // Variáveis CSS, @font-face e media queries das folhas de estilo acessíveis
  const cssVars = {}, scopedVars = {}, fontFaces = new Set(), media = {};
  const walk = rules => { for (const r of rules) {
    if (r.style && r.selectorText) {
      const vars = [...r.style].filter(p => p.startsWith('--'));
      // :root/html/body = intenção global declarada. Outros seletores (ex.: .elementor-kit-5, [data-theme])
      // também podem carregar a paleta do tema, então guardamos à parte.
      const target = /(^|,)\s*(:root|html|body)\s*($|,)/.test(r.selectorText) ? cssVars
                   : (vars.length >= 3 && Object.keys(scopedVars).length < 25 ? (scopedVars[r.selectorText.slice(0, 80)] ||= {}) : null);
      if (target) for (const p of vars.slice(0, 80)) target[p] = r.style.getPropertyValue(p).trim();
    }
    if (r.type === 5) fontFaces.add((r.style.getPropertyValue('font-family') + ' ' + r.style.getPropertyValue('font-weight')).trim());
    if (r.media) { bump(media, r.media.mediaText); if (r.cssRules) walk(r.cssRules); }
  }};
  let blocked = 0;
  for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch (e) { blocked++; } }
  // Componentes: variantes únicas por assinatura de estilo
  const claimed = new Set(), comps = {};
  const pick = ['display','color','backgroundColor','backgroundImage','fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','textTransform',
                'paddingTop','paddingRight','paddingBottom','paddingLeft','borderTopWidth','borderTopStyle','borderTopColor','borderTopLeftRadius','boxShadow','gap','height','width','maxWidth'];
  for (const [name, sel] of Object.entries(components)) {
    let els; try { els = [...document.querySelectorAll(sel)].filter(vis); } catch (e) { continue; }
    const variants = {};
    for (const el of els) {
      if (claimed.has(el)) continue;
      const s = getComputedStyle(el);
      const style = Object.fromEntries(pick.map(k => [k, s[k]]));
      const sig = [style.color, style.backgroundColor, style.backgroundImage.slice(0, 40), style.fontSize, style.fontWeight, style.borderTopWidth, style.borderTopColor, style.borderTopLeftRadius, style.paddingTop, style.paddingLeft].join('|');
      if (!variants[sig]) {
        const id = `${name}-${Object.keys(variants).length}`;
        el.setAttribute('data-ds-probe', id);
        variants[sig] = {id, count: 0, tag: el.tagName.toLowerCase(), classes: typeof el.className === 'string' ? el.className : '',
                         text: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 80), style,
                         html: el.outerHTML.replace(/\s+/g, ' ').slice(0, 1200),
                         box: {w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height)}};
      }
      variants[sig].count++;
      claimed.add(el);
    }
    const list = Object.values(variants).sort((a, b) => b.count - a.count).slice(0, 6);
    if (list.length) comps[name] = {total: els.length, variants: list};
  }
  const top = (o, n = 24) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, n);
  return {
    title: document.title, lang: document.documentElement.lang,
    colors: {text: top(colors.text), background: top(colors.background), border: top(colors.border, 12)},
    fonts: top(fonts, 8), fontSizes: top(sizes), fontWeights: top(weights, 10), lineHeights: top(lineHeights, 12),
    typeScale, spacing: top(spacing, 30), gaps: top(gaps, 15), radius: top(radius, 12), shadows: top(shadows, 10),
    transitions: top(transitions, 8), maxWidths: top(maxWidths, 12), grids, flexRows: top(flexRows, 10),
    cssVariables: cssVars, scopedCssVariables: scopedVars, fontFaces: [...fontFaces], mediaQueries: top(media, 30), blockedStylesheets: blocked,
    components: comps,
  };
}
"""


def slug(url):
    return re.sub(r"[^a-z0-9]+", "-", url.lower().split("://")[-1]).strip("-")[:60] or "home"


async def scroll(page):
    await page.evaluate("""async () => {
        for (let i = 0; i < 40; i++) { window.scrollBy(0, innerHeight); await new Promise(r => setTimeout(r, 150)); }
        window.scrollTo(0, 0);
    }""")


async def main():
    result = {"pages": {}}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for url in URLS:
            print("›", url)
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print("  ✗", e.__class__.__name__)
                await page.close()
                continue
            await scroll(page)
            data = await page.evaluate(COLLECT_JS, COMPONENTS)
            s = slug(url)
            await page.screenshot(path=os.path.join(SHOTS, f"page-{s}-desktop.png"), full_page=True)
            # Recorte de cada variante de componente (limitado para não explodir o disco)
            for name, comp in data["components"].items():
                for v in comp["variants"][:4]:
                    el = await page.query_selector(f'[data-ds-probe="{v["id"]}"]')
                    if not el or v["box"]["w"] * v["box"]["h"] > 1440 * 1600:
                        continue
                    path = os.path.join(SHOTS, f"comp-{s}-{v['id']}.png")
                    try:
                        await el.screenshot(path=path, timeout=5000)
                        v["screenshot"] = os.path.relpath(path, OUT)
                    except Exception:
                        pass
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.wait_for_timeout(600)
            data["mobile"] = await page.evaluate("""() => ({
                bodyFontSize: getComputedStyle(document.body).fontSize,
                h1: (() => { const h = document.querySelector('h1'); return h ? getComputedStyle(h).fontSize : null; })(),
                hasHamburger: !![...document.querySelectorAll('button, [class*=menu], [class*=burger], [class*=toggle]')]
                    .find(e => e.getBoundingClientRect().width > 0 && e.getBoundingClientRect().width < 80),
                overflowX: document.documentElement.scrollWidth > innerWidth,
            })""")
            await page.screenshot(path=os.path.join(SHOTS, f"page-{s}-mobile.png"), full_page=True)
            result["pages"][url] = data
            await page.close()
        await browser.close()

    # Agregado entre páginas: soma as frequências para facilitar a curadoria
    agg = {}
    for key in ["fontSizes", "spacing", "radius", "shadows", "fonts", "gaps", "maxWidths"]:
        c = Counter()
        for d in result["pages"].values():
            c.update(dict(d[key]))
        agg[key] = c.most_common(30)
    for kind in ["text", "background", "border"]:
        c = Counter()
        for d in result["pages"].values():
            c.update(dict(d["colors"][kind]))
        agg[f"colors_{kind}"] = c.most_common(24)
    result["aggregate"] = agg

    with open(os.path.join(OUT, "raw-extraction.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    n = sum(len(d["components"]) for d in result["pages"].values())
    print(f"✓ {len(result['pages'])} páginas analisadas, {n} famílias de componentes → {OUT}/raw-extraction.json")


asyncio.run(main())
