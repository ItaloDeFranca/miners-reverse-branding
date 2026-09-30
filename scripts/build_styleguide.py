"""
build_styleguide.py — transforma tokens.json + components.json + components.css em
tokens.css e styleguide.html (navegável, sem dependências).

  python build_styleguide.py <pasta_design_system>

A pasta precisa conter tokens.json e components.json (formato em references/tokens-schema.md).
components.css é opcional, mas é onde vivem as classes .ds-* dos componentes.
"""
import html, json, os, re, sys, unicodedata

DS = sys.argv[1]
tokens = json.load(open(os.path.join(DS, "tokens.json"), encoding="utf-8"))
comps = json.load(open(os.path.join(DS, "components.json"), encoding="utf-8")).get("components", [])
meta = tokens.get("meta", {})

PREFIX = {"color": "color", "spacing": "space", "radius": "radius", "shadow": "shadow",
          "grid": "grid", "breakpoint": "breakpoint", "motion": "motion", "zIndex": "z"}


def kebab(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()  # "Ações" → "acoes"
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"([a-z])([A-Z])", r"\1-\2", str(s)).lower()).strip("-")


def flatten(node, path):
    """Folhas são objetos com 'value'. Devolve [(var, value, usage, path)]."""
    out = []
    for k, v in node.items():
        if isinstance(v, dict) and "value" in v:
            out.append(("--" + "-".join(kebab(p) for p in path + [k]), v["value"], v.get("usage", ""), path + [k]))
        elif isinstance(v, dict):
            out += flatten(v, path + [k])
    return out


# ---------- tokens.css ----------
lines, groups = [], {}
for section, prefix in PREFIX.items():
    if section in tokens:
        items = flatten(tokens[section], [prefix])
        groups[section] = items
        lines += [f"  {n}: {v};" for n, v, _, _ in items]
typo = tokens.get("typography", {})
for key, prefix in (("fontFamily", "font-family"), ("fontWeight", "font-weight")):
    items = flatten(typo.get(key, {}), [prefix])
    groups[key] = items
    lines += [f"  {n}: {v};" for n, v, _, _ in items]

scale = typo.get("scale", {})
for name, t in scale.items():
    n = kebab(name)
    fam = t.get("fontFamily")
    if fam:
        lines.append(f"  --text-{n}-family: {'var(--font-family-' + kebab(fam) + ')' if fam in typo.get('fontFamily', {}) else fam};")
    for prop, css in (("fontSize", "size"), ("lineHeight", "line-height"), ("fontWeight", "weight"), ("letterSpacing", "tracking")):
        if prop in t:
            lines.append(f"  --text-{n}-{css}: {t[prop]};")

bps = {k: v["value"] for k, v in tokens.get("breakpoint", {}).items()}
grid = {k: v["value"] for k, v in tokens.get("grid", {}).items()}
mobile_bp = grid.get("mobileBreakpoint") or bps.get("md") or "768px"
cols = int(grid.get("columns", 12))
mcols = int(grid.get("mobileColumns", 4))

css = ["/* Gerado por build_styleguide.py a partir de tokens.json. Edite tokens.json, não este arquivo. */",
       ":root {", *lines, "}", ""]
for name, t in scale.items():
    n = kebab(name)
    rule = [f".ds-text-{n} {{"]
    if t.get("fontFamily"):
        rule.append(f"  font-family: var(--text-{n}-family);")
    for prop, cssn, var in (("fontSize", "font-size", "size"), ("lineHeight", "line-height", "line-height"),
                            ("fontWeight", "font-weight", "weight"), ("letterSpacing", "letter-spacing", "tracking")):
        if prop in t:
            rule.append(f"  {cssn}: var(--text-{n}-{var});")
    if t.get("textTransform"):
        rule.append(f"  text-transform: {t['textTransform']};")
    css += rule + ["}"]
css += ["",
        ".ds-container { width: 100%; max-width: var(--grid-container); margin-inline: auto; padding-inline: var(--grid-margin, 16px); box-sizing: border-box; }",
        f".ds-grid {{ display: grid; grid-template-columns: repeat({cols}, minmax(0, 1fr)); gap: var(--grid-gutter, 24px); }}",
        *[f".ds-col-{i} {{ grid-column: span {i}; }}" for i in range(1, cols + 1)],
        f"@media (max-width: {mobile_bp}) {{",
        *[f"  .ds-col-{i} {{ grid-column: 1 / -1; }}" for i in range(mcols + 1, cols + 1)],
        f"  .ds-grid {{ grid-template-columns: repeat({mcols}, minmax(0, 1fr)); gap: var(--grid-gutter-mobile, var(--grid-gutter, 16px)); }}",
        *[f"  .ds-text-{kebab(n)} {{ font-size: {t['mobileFontSize']}; }}" for n, t in scale.items() if t.get("mobileFontSize")],
        "}"]
open(os.path.join(DS, "tokens.css"), "w", encoding="utf-8").write("\n".join(css) + "\n")


# ---------- styleguide.html ----------
def rgb(v):
    v = v.strip()
    m = re.match(r"#([0-9a-f]{3}|[0-9a-f]{6})$", v, re.I)
    if m:
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"rgba?\((\d+)[, ]+(\d+)[, ]+(\d+)", v)
    return tuple(int(x) for x in m.groups()) if m else None


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


e = html.escape
sections, nav = [], []


def section(sid, title, body, intro=""):
    nav.append(f'<a href="#{sid}">{e(title)}</a>')
    sections.append(f'<section class=sg-section id="{sid}"><h2 class=sg-h2>{e(title)}</h2>{f"<p class=intro>{intro}</p>" if intro else ""}{body}</section>')


# Cores
if groups.get("color"):
    by_group = {}
    for n, v, u, p in groups["color"]:
        by_group.setdefault(" / ".join(p[1:-1]) or "cores", []).append((n, v, u, p[-1]))
    body = ""
    for g, items in by_group.items():
        body += f"<h3 class=sg-h3>{e(g.title())}</h3><div class=swatches>"
        for n, v, u, label in items:
            c = rgb(str(v))
            badge = ""
            if c:
                cw, cb = contrast(c, (255, 255, 255)), contrast(c, (0, 0, 0))
                badge = f'<span class=aa>branco {cw:.1f}:1 · preto {cb:.1f}:1</span>'
                ink = "#fff" if cw >= cb else "#000"
            else:
                ink = "#000"
            body += (f'<div class=swatch><div class=chip style="background:var({n});color:{ink}">Aa</div>'
                     f'<b>{e(label)}</b><code>{e(str(v))}</code><code>var({n})</code>{badge}<small>{e(u)}</small></div>')
        body += "</div>"
    section("cores", "Cores", body, "Contraste AA exige 4.5:1 para texto normal e 3:1 para texto grande (≥ 24px ou 18.66px bold).")

# Tipografia
if scale or groups.get("fontFamily"):
    body = "<div class=fams>" + "".join(
        f'<div><span style="font-family:var({n});font-size:40px">Aa Bb Çç 123</span><b>{e(p[-1])}</b><code>{e(str(v))}</code><small>{e(u)}</small></div>'
        for n, v, u, p in groups.get("fontFamily", [])) + "</div>"
    body += "<table class='sg-table scale'><tr><th>Estilo</th><th>Amostra</th><th>Especificação</th><th>Uso</th></tr>"
    for name, t in scale.items():
        spec = " · ".join(str(t[k]) for k in ("fontSize", "lineHeight", "fontWeight", "letterSpacing") if k in t)
        if t.get("mobileFontSize"):
            spec += f" <br><small>mobile: {e(str(t['mobileFontSize']))}</small>"
        body += (f'<tr><td><code>.ds-text-{kebab(name)}</code></td><td><div class="ds-text-{kebab(name)}">{e(t.get("sample", "O rápido design system"))}</div></td>'
                 f'<td>{spec}</td><td><small>{e(t.get("usage", ""))}</small></td></tr>')
    section("tipografia", "Tipografia", body + "</table>")

# Espaçamento, raio, sombra
if groups.get("spacing"):
    body = "".join(f'<div class=space><code>var({n})</code><span style="width:var({n})"></span><small>{e(str(v))} {e(u)}</small></div>'
                   for n, v, u, _ in groups["spacing"])
    section("espacamento", "Espaçamento", body)
if groups.get("radius") or groups.get("shadow"):
    body = "<div class=boxes>" + "".join(f'<div style="border-radius:var({n})" class=box><code>var({n})</code><small>{e(str(v))}</small></div>' for n, v, _, _ in groups.get("radius", []))
    body += "".join(f'<div style="box-shadow:var({n})" class="box sh"><code>var({n})</code><small>{e(u)}</small></div>' for n, v, u, _ in groups.get("shadow", [])) + "</div>"
    section("superficies", "Raios e sombras", body)

# Grade
if grid:
    demo = "".join(f'<div class="ds-col-1 gcell">{i}</div>' for i in range(1, cols + 1))
    spans = "".join(f'<div class="ds-col-{n} gcell">.ds-col-{n}</div>' for n in [c for c in (cols // 2, cols // 2, cols // 3, cols // 3, cols // 3) if c])
    half = f'    <div class="ds-col-{cols // 2}">…</div>'
    grid_snippet = "\n".join(['<div class="ds-container">', '  <div class="ds-grid">', half, half, "  </div>", "</div>"])
    table = "".join(f"<tr><td>{e(k)}</td><td><code>{e(str(v))}</code></td></tr>" for k, v in grid.items())
    table += "".join(f"<tr><td>breakpoint {e(k)}</td><td><code>{e(str(v))}</code></td></tr>" for k, v in bps.items())
    body = (f'<table class="sg-table kv">{table}</table><p>Redimensione a janela abaixo de <code>{e(mobile_bp)}</code> para ver a grade virar {mcols} colunas.</p>'
            f'<div class="ds-container gwrap"><div class=ds-grid>{demo}</div><div class=ds-grid style="margin-top:12px">{spans}</div></div>'
            f'<pre class=sg-pre><code>{e(grid_snippet)}</code></pre>')
    section("grade", "Grade e breakpoints", body)

# Motion
if groups.get("motion"):
    section("motion", "Movimento", "<table class='sg-table kv'>" + "".join(f"<tr><td><code>var({n})</code></td><td>{e(str(v))}</td><td><small>{e(u)}</small></td></tr>" for n, v, u, _ in groups["motion"]) + "</table>")

# Componentes
cats = {}
for c in comps:
    cats.setdefault(c.get("category", "Componentes"), []).append(c)
for cat, items in cats.items():
    body = ""
    for c in items:
        body += f'<article class=comp id="c-{kebab(c.get("slug", c["name"]))}"><h3 class=sg-h3>{e(c["name"])}</h3><p>{e(c.get("description", ""))}</p>'
        for v in c.get("variants", []):
            body += (f'<div class=variant><div class=vhead>{e(v.get("name", ""))}{" · <small>" + e(v["note"]) + "</small>" if v.get("note") else ""}</div>'
                     f'<div class=stage>{v["html"]}</div><details><summary>Código</summary><pre class=sg-pre><code>{e(v["html"])}</code></pre></details></div>')
        use = c.get("usage", {})
        if use.get("do") or use.get("dont"):
            body += ('<div class=dodont><div class=do><b>Faça</b><ul>' + "".join(f"<li>{e(x)}</li>" for x in use.get("do", [])) +
                     '</ul></div><div class=dont><b>Evite</b><ul>' + "".join(f"<li>{e(x)}</li>" for x in use.get("dont", [])) + "</ul></div></div>")
        if c.get("reference_screenshot"):
            body += f'<details><summary>Referência original do site</summary><img class=ref src="{e(c["reference_screenshot"])}" alt="Captura original de {e(c["name"])}"></details>'
        body += "</article>"
    section("cat-" + kebab(cat), cat, body)

fonts_link = f'<link rel="stylesheet" href="{e(meta["fontsImport"])}">' if meta.get("fontsImport") else ""
comp_css = '<link rel="stylesheet" href="components.css">' if os.path.exists(os.path.join(DS, "components.css")) else ""
page = f"""<!doctype html>
<html lang="{e(meta.get('language', 'pt-BR'))}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(meta.get('name', 'Design System'))} · Design System</title>
{fonts_link}<link rel="stylesheet" href="tokens.css">{comp_css}
<style>
  .sg-shell {{ font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, sans-serif; color: #1a1a1a; background: #f6f6f4; margin: 0; display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }}
  .sg-nav {{ position: sticky; top: 0; height: 100vh; overflow: auto; padding: 24px 16px; background: #fff; border-right: 1px solid #e4e4e0; box-sizing: border-box; }}
  .sg-nav a {{ display: block; padding: 6px 10px; color: #333; text-decoration: none; border-radius: 6px; }}
  .sg-nav a:hover {{ background: #f0f0ec; }}
  .sg-main {{ padding: 32px clamp(16px, 4vw, 56px); min-width: 0; }}
  .sg-section {{ background: #fff; border: 1px solid #e4e4e0; border-radius: 12px; padding: 28px; margin-bottom: 24px; }}
  .sg-h1 {{ font-size: 32px; margin: 0 0 4px; }} .sg-h2 {{ font-size: 22px; margin: 0 0 12px; }} .sg-h3 {{ font-size: 16px; margin: 20px 0 10px; }}
  .sg-shell code:where(:not(.stage *)) {{ font: 12px ui-monospace, Menlo, monospace; background: #f3f3f0; padding: 1px 5px; border-radius: 4px; }}
  .sg-pre {{ background: #16161a; color: #eaeaea; padding: 14px; border-radius: 8px; overflow: auto; }} .sg-pre code {{ background: none; color: inherit; }}
  .sg-shell small:where(:not(.stage *)), .intro {{ color: #666; }}
  .swatches {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 14px; }}
  .swatch {{ display: flex; flex-direction: column; gap: 3px; }} .swatch .chip {{ height: 84px; border-radius: 8px; border: 1px solid #0001; display: grid; place-items: center; font-size: 22px; font-weight: 600; }}
  .aa {{ font-size: 11px; color: #666; }}
  .fams {{ display: grid; gap: 16px; }} .fams > div {{ display: flex; flex-direction: column; gap: 4px; }}
  .sg-table {{ border-collapse: collapse; width: 100%; }} .sg-table td, .sg-table th {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
  .scale td:nth-child(2) {{ max-width: 520px; overflow: hidden; }}
  .space {{ display: grid; grid-template-columns: 160px auto 1fr; align-items: center; gap: 12px; margin: 6px 0; }} .space span {{ height: 14px; background: #7c5cff; border-radius: 3px; display: block; }}
  .boxes {{ display: flex; flex-wrap: wrap; gap: 18px; }} .box {{ width: 150px; height: 100px; background: #fff; border: 1px solid #ddd; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 4px; }} .box.sh {{ border-color: transparent; }}
  .gwrap {{ background: #7c5cff10; padding-block: 12px; }} .gcell {{ background: #7c5cff30; border: 1px dashed #7c5cff; font: 11px ui-monospace, monospace; padding: 10px 2px; text-align: center; overflow: hidden; }}
  .kv td:first-child {{ width: 220px; }}
  .comp {{ border-top: 1px solid #eee; padding-top: 8px; }} .comp:first-of-type {{ border-top: 0; }}
  .variant {{ border: 1px solid #e8e8e4; border-radius: 10px; margin: 12px 0; overflow: hidden; }}
  .vhead {{ font-size: 13px; font-weight: 600; padding: 8px 12px; background: #fafaf8; border-bottom: 1px solid #eee; }}
  .stage {{ padding: 24px; overflow: auto; font: 16px/1.5 var(--font-family-body, inherit); color: var(--color-text-primary, inherit); background: var(--color-surface-page, #fff); }} .variant details {{ padding: 0 12px 8px; }} .sg-shell summary:where(:not(.stage *)) {{ cursor: pointer; font-size: 13px; color: #555; padding: 6px 0; }}
  .dodont {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }} .do, .dont {{ padding: 10px 14px; border-radius: 8px; font-size: 14px; }} .do {{ background: #e9f7ee; }} .dont {{ background: #fdecec; }}
  .ref {{ max-width: 100%; border: 1px solid #ddd; border-radius: 6px; }}
  @media (max-width: 800px) {{ .sg-shell {{ grid-template-columns: 1fr; }} .sg-nav {{ position: static; height: auto; display: flex; flex-wrap: wrap; }} .dodont {{ grid-template-columns: 1fr; }} }}
</style></head>
<body class="sg-shell">
<nav class=sg-nav><b style="display:block;padding:0 10px 12px">{e(meta.get('name', 'Design System'))}</b>{''.join(nav)}</nav>
<main class=sg-main><header style="margin-bottom:24px"><h1 class=sg-h1>{e(meta.get('name', 'Design System'))}</h1>
<small>Extraído de {e(meta.get('source', ''))} em {e(meta.get('extractedAt', ''))}. Guia de uso completo em DESIGN-SYSTEM.md.</small></header>
{''.join(sections)}
</main></body></html>"""
open(os.path.join(DS, "styleguide.html"), "w", encoding="utf-8").write(page)
print(f"✓ tokens.css ({len(lines)} variáveis) e styleguide.html ({len(comps)} componentes) → {DS}")
