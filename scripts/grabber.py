"""
grabber.py — clona um site para uma pasta pronta para deploy.

  python grabber.py https://exemplo.com.br 20 [pasta_saida]   (20 = máximo de páginas)

Gera <pasta_saida>/<dominio>/ e <pasta_saida>/<dominio>.zip
"""
import asyncio, os, re, sys, shutil
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

URL = sys.argv[1]
if not urlparse(URL).path:
    URL += "/"  # "site.com" e "site.com/" são a mesma página
MAX_PAGINAS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
SAIDA = sys.argv[3] if len(sys.argv) > 3 else "."
DOMINIO = urlparse(URL).netloc
PASTA = os.path.join(SAIDA, DOMINIO.replace(":", "_"))
# Domínios tratados como "o mesmo site" (ex.: pelion.com.br e www.pelion.com.br após redirect)
DOMINIOS = {DOMINIO}
ORIGENS = {f"{urlparse(URL).scheme}://{DOMINIO}"}
ORIGEM_REAL = next(iter(ORIGENS))  # host que de fato serve o site (atualizado se houver redirect)
REF_HTML = re.compile(r"""(?:src|href|data-src|data-bg|poster)=["']([^"']+)["']|(?:srcset|data-srcset)=["']([^"']+)["']""")
REF_CSS = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""")


def caminho_local(url, pagina=False):
    path = urlparse(url).path or "/"
    if pagina and not os.path.splitext(path)[1]:
        path = path.rstrip("/") + "/index.html"
    return os.path.join(PASTA, path.lstrip("/"))


def salvar(caminho, dados):
    if caminho.endswith("/"):
        return
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(dados)


def reescrever_origens(texto):
    # Absolutas (https://site), escapadas em JSON (https:\/\/site) e protocol-relative (//site)
    for origem in ORIGENS:
        texto = texto.replace(origem, "").replace(origem.replace("/", "\\/"), "")
    for dominio in DOMINIOS:
        texto = texto.replace(f"//{dominio}/", "/")
    return texto


async def completar(request):
    """Reescreve URLs em HTML/CSS/JS salvos e baixa o que eles referenciam mas o navegador não pediu
    (outros tamanhos do srcset, fundos de breakpoints mobile, fontes de ícone, url() de CSS)."""
    baixados, tentados = 0, set()
    for _ in range(3):  # CSS recém-baixado pode referenciar mais fontes/imagens
        faltando = set()
        for raiz, _, arquivos in os.walk(PASTA):
            for nome in arquivos:
                local = os.path.join(raiz, nome)
                ext = os.path.splitext(nome)[1].lower()
                if ext not in (".html", ".htm", ".css", ".js", ".json"):
                    continue
                with open(local, encoding="utf-8", errors="ignore") as f:
                    texto = f.read()
                novo = reescrever_origens(texto)
                if novo != texto:
                    with open(local, "w", encoding="utf-8") as f:
                        f.write(novo)
                if ext in (".html", ".htm"):
                    refs = []
                    for simples, lista in REF_HTML.findall(novo):
                        refs += [simples] if simples else [c.strip().split(" ")[0] for c in lista.split(",")]
                elif ext == ".css":
                    refs = REF_CSS.findall(novo)
                else:
                    continue
                url_arquivo = ORIGEM_REAL + "/" + os.path.relpath(local, PASTA).replace(os.sep, "/")
                for ref in refs:
                    if not ref or ref.startswith(("data:", "#", "mailto:", "tel:", "javascript:")):
                        continue
                    alvo = urljoin(url_arquivo, ref.replace("\\/", "/")).split("#")[0].split("?")[0]
                    caminho = urlparse(alvo).path
                    ext_alvo = os.path.splitext(caminho)[1].lower()
                    if urlparse(alvo).netloc in DOMINIOS and ext_alvo and ext_alvo not in (".html", ".htm", ".php") \
                            and alvo not in tentados and not os.path.exists(caminho_local(alvo)):
                        faltando.add(alvo)
        if not faltando:
            break
        tentados |= faltando
        for alvo in sorted(faltando):
            try:
                r = await request.get(alvo, timeout=20000)
                if r.ok:
                    salvar(caminho_local(alvo), await r.body())
                    baixados += 1
            except Exception:
                pass
    return baixados


async def main():
    global ORIGEM_REAL
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 1. Tudo que o navegador baixar do domínio (css, js, imagens, fontes) é salvo
        async def ao_receber(resp):
            if urlparse(resp.url).netloc not in DOMINIOS or resp.status != 200:
                return
            if resp.request.resource_type == "document":
                return
            try:
                salvar(caminho_local(resp.url), await resp.body())
            except Exception:
                pass

        page.on("response", ao_receber)

        fila, vistos, feitas = [URL], {URL}, 0
        while fila and feitas < MAX_PAGINAS:
            url = fila.pop(0)
            print("›", url)
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print("  ✗", e.__class__.__name__)
                continue

            # Se a URL inicial redirecionou para outro host (www, https), adota-o como interno
            final = urlparse(page.url)
            if final.netloc not in DOMINIOS:
                DOMINIOS.add(final.netloc)
                ORIGEM_REAL = f"{final.scheme}://{final.netloc}"
                ORIGENS.add(ORIGEM_REAL)
                print("  ↪ redirecionado para", final.netloc)

            # 2. Rola até o fim para carregar imagens lazy
            await page.evaluate("""async () => {
                for (let i = 0; i < 40; i++) { window.scrollBy(0, innerHeight); await new Promise(r => setTimeout(r, 200)); }
                window.scrollTo(0, 0);
            }""")

            # 3. Salva o HTML já renderizado, trocando links absolutos por /caminho
            html = await page.content()
            for origem in ORIGENS:
                html = html.replace(origem, "")
            salvar(caminho_local(url, pagina=True), html.encode())
            feitas += 1

            # 4. Coloca os links internos na fila
            links = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for link in links:
                link = link.split("#")[0].split("?")[0]
                if urlparse(link).netloc in DOMINIOS and link not in vistos \
                        and os.path.splitext(urlparse(link).path)[1] in ("", ".html", ".htm"):
                    vistos.add(link)
                    fila.append(link)

        # 5. Completa o clone: URLs em CSS/JS/JSON e assets que só aparecem em outros breakpoints
        extras = await completar(page.request)
        print(f"  + {extras} assets referenciados baixados")

        await browser.close()

    shutil.make_archive(PASTA, "zip", PASTA)
    print(f"✓ {feitas} páginas → {PASTA}/ e {PASTA}.zip")


asyncio.run(main())
