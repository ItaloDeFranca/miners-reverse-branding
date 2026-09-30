---
name: miners-reverse-branding
description: Clona um site inteiro (HTML renderizado, CSS, JS, imagens, fontes) para uma pasta pronta para deploy + um .zip com o nome do domínio, e depois extrai dele um design system completo — tokens de cor, tipografia, espaçamento, raios, sombras, grade, breakpoints, todos os componentes com variantes e um guia de uso, entregues como tokens.json, tokens.css, components.css, styleguide.html navegável e DESIGN-SYSTEM.md. Use sempre que o usuário quiser clonar, baixar, espelhar, "grabbar", extrair ou fazer backup de um site, migrar um site para outra hospedagem, ou extrair/recriar/documentar o design system, identidade visual, guia de estilo, paleta, tipografia ou componentes de um site existente a partir de uma URL — mesmo que ele só diga "pega o visual desse site" ou "quero o estilo do site X".
---

# Miners Reverse Branding

Duas etapas, nesta ordem: **clonar** o site (deploy-ready + zip) e **extrair o design system** dele.
O clone vem primeiro porque é o backup fiel e porque a lista de páginas que ele descobre define quais
páginas analisar na segunda etapa.

Se o usuário pedir só uma das etapas, faça só aquela. Clone apenas sites que o usuário tem direito de
copiar (dele, do cliente, ou referência para estudo interno); se o pedido for claramente republicar o
site de terceiros como se fosse próprio, pergunte antes.

## Layout de saída

Pasta base: a que o usuário indicar; senão, o diretório de trabalho atual.

```
<base>/
├── <dominio>/                    clone navegável, pronto para subir em qualquer host estático
├── <dominio>.zip                 o mesmo clone compactado
└── <dominio>-design-system/
    ├── DESIGN-SYSTEM.md          manual de uso (o entregável principal para humanos)
    ├── styleguide.html           página navegável com tokens, grade e componentes renderizados
    ├── tokens.json               fonte da verdade dos tokens
    ├── tokens.css                variáveis CSS + classes de texto e grade (gerado)
    ├── components.css            classes .ds-* dos componentes (usa só var(--...))
    ├── components.json           catálogo de componentes e variantes
    ├── raw-extraction.json       dados brutos medidos (evidência)
    ├── assets/                   logos, ícones e imagens usados pelos componentes
    └── screenshots/              páginas inteiras e recortes dos componentes originais
```

## Etapa 0 — ambiente

```bash
SKILL=<caminho desta skill>
PY=$(bash "$SKILL/scripts/setup.sh")
```

Cria (uma vez) um venv em `~/.venvs/miners-reverse-branding` com Playwright e Chromium e imprime o python a
usar. Use sempre `$PY` nos passos seguintes; o Python do sistema costuma não ter Playwright e o
Homebrew bloqueia `pip install` global.

## Etapa 1 — clonar

```bash
cd <base> && $PY "$SKILL/scripts/grabber.py" <url> <max_paginas> .
```

`max_paginas` padrão 20; para sites institucionais pequenos isso cobre tudo. O script navega em
largura pelos links internos, rola cada página para disparar lazy-load, salva o HTML já renderizado
e todo asset do mesmo domínio que o navegador pediu. No fim, uma passada de "completar" reescreve as
URLs absolutas em HTML, CSS, JS e JSON (inclusive as escapadas `https:\/\/site`) para caminhos da
raiz e baixa o que esses arquivos referenciam mas o navegador não carregou em 1440px: outros tamanhos
do `srcset`, fundos usados só no mobile, fontes de ícone, `url()` de CSS. Depois gera o zip.
Redirecionamentos de host (sem www → www) são tratados como o mesmo site.

Verifique o resultado antes de seguir:
- `ls <dominio>/` tem `index.html` e as pastas de assets
- conte os `.html` salvos e compare com o que o script reportou
- assets de CDN de terceiros (Google Fonts, cdn.jsdelivr, imagens em S3/Cloudflare) **não** são
  baixados; o HTML continua apontando para eles. Informe isso ao usuário quando existirem, porque o
  clone depende deles estarem no ar.
- Teste o clone servido localmente: `cd <dominio> && $PY -m http.server 8000`, abra com Playwright
  nas larguras 1440 e 390 e registre respostas 404 e requisições ao domínio original. Zero das duas
  é o critério de clone independente. Links usam caminhos da raiz (`/css/...`), então abrir o
  `index.html` direto do Finder quebra estilos; precisa de servidor.

## Etapa 2 — medir o design

Escolha de 3 a 6 páginas representativas a partir do clone (home, uma página interna de conteúdo,
contato/formulário, listagem se houver). Monte as URLs vivas correspondentes e rode:

```bash
$PY "$SKILL/scripts/extract_design.py" <dominio>-design-system <url1> <url2> ...
```

Use as URLs vivas, não o clone: fontes e imagens de CDN só carregam no original, e as medições de
tipografia dependem delas.

O script produz `raw-extraction.json` com frequências de cores (texto, fundo, borda), fontes, tamanhos,
pesos, espaçamentos, gaps, raios, sombras, transições, max-widths de containers, elementos em grid,
variáveis CSS de `:root`, `@font-face`, media queries e, para cada família de componente, até 6
variantes únicas com estilo computado, HTML de origem e screenshot.

## Etapa 3 — curar os tokens

Esta é a parte que exige julgamento. Os números brutos têm ruído: cores de widgets de terceiros,
paddings de 13px de um plugin, 40 tons de cinza quase iguais. Leia `raw-extraction.json` e olhe os
screenshots das páginas (Read nas imagens) para entender a hierarquia visual antes de nomear.

1. **Cores**: agrupe tons próximos (diferença imperceptível → mesmo token). Identifique a primária pela
   cor dos CTAs e links, não só pela frequência — o branco do fundo sempre ganha em frequência.
   Variáveis em `cssVariables` (`:root`) e `scopedCssVariables` (tema com escopo, como
   `.elementor-kit-5`) são a intenção declarada do designer, mas confirme que aparecem na tela:
   construtores de página (Elementor, Divi, Webflow) deixam paletas padrão de instalação que o site
   nunca usa.
2. **Tipografia**: família de título e de corpo, escala a partir de `typeScale` (h1..h6, p, small) +
   tamanhos frequentes. Registre `mobileFontSize` comparando com o bloco `mobile`.
3. **Espaçamento**: detecte a base (4 ou 8) e monte a escala com os valores que aparecem de fato;
   arredonde os quebrados.
4. **Grade**: container = max-width mais frequente entre 960 e 1440px; colunas e gutter a partir de
   `grids` e `gaps`; breakpoints a partir de `mediaQueries` (os valores de `max-width`/`min-width`).
5. Escreva `tokens.json` exatamente no formato de `references/tokens-schema.md` — leia esse arquivo
   agora. Inclua `usage` em todo token relevante; é o que transforma uma paleta em sistema.

## Etapa 4 — componentes

Leia `references/components-checklist.md`. Para cada família em `raw-extraction.json → components`
(e cada item do checklist presente no site):

- Escreva as classes em `components.css`. Todo valor de design (cor, fonte, tamanho de texto,
  espaçamento, raio, sombra, duração) vem de `var(--...)` de tokens.css, para que trocar um token
  mude o sistema inteiro. Literais estruturais são aceitáveis: larguras em %, `1px` de borda,
  valores dentro de `@media` (variáveis não funcionam ali), `url()` de imagens. Nomeie em BEM com
  prefixo `ds-` (`.ds-btn`, `.ds-btn--primary`, `.ds-card__title`). Inclua `:hover`,
  `:focus-visible` e `:disabled` onde se aplica.
- Imagens que os componentes usam (logo, ícones, fotos de hero) vão para `<dominio>-design-system/assets/`,
  copiadas do clone, para o design system funcionar sozinho. Confira o tipo real com `file`:
  servidores costumam entregar WebP com extensão `.png`/`.jpg`; renomeie a cópia.
- Registre em `components.json` nome, categoria, descrição, variantes com HTML de exemplo usando
  textos reais do site, faça/evite, e o screenshot original de referência.
- Inclua também 2 a 4 **padrões de seção** (hero, grade de benefícios, CTA final, rodapé) como
  componentes da categoria "Padrões de seção", montados com `.ds-container` + `.ds-grid`.

Compare cada componente recriado com o screenshot original. O teste é: lado a lado, alguém
reconheceria que é o mesmo site?

## Etapa 5 — gerar e documentar

```bash
$PY "$SKILL/scripts/build_styleguide.py" <dominio>-design-system
```

Gera `tokens.css` e `styleguide.html`. Nunca edite `tokens.css` à mão: mude `tokens.json` e rode de
novo.

Depois escreva `DESIGN-SYSTEM.md` seguindo `references/design-system-md-template.md`, no idioma do
usuário (padrão PT-BR). Ele precisa ter um exemplo de página mínima completa que funcione só com
tokens.css + components.css.

## Etapa 6 — verificar

Tire screenshot do styleguide e olhe:

```bash
cd <dominio>-design-system && ($PY -m http.server 8799 --bind 127.0.0.1 >/dev/null 2>&1 &) && sleep 1 && $PY - <<'EOF'
import asyncio
from playwright.async_api import async_playwright
async def m():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1440, "height": 900})
        await pg.goto("http://127.0.0.1:8799/styleguide.html")
        await pg.wait_for_timeout(800); await pg.screenshot(path="screenshots/_styleguide.png", full_page=True)
        await pg.set_viewport_size({"width": 390, "height": 844}); await pg.screenshot(path="screenshots/_styleguide-mobile.png", full_page=True)
        await b.close()
asyncio.run(m())
EOF
pkill -f "http.server 8799"
```

Sirva por HTTP, não `file://`: com `file://` o Chromium bloqueia `mask-image` e fontes com URL
relativa, e os ícones somem da captura sem estarem quebrados de verdade. Leia as duas imagens. Procure: componentes sem estilo (classe inexistente em components.css), fonte
caindo para a do sistema (faltou `fontsImport`), cores que não batem com o site, grade não virando no
mobile. Corrija e rode a etapa 5 de novo até ficar fiel.

## Entrega

Resuma para o usuário: caminhos do clone, do zip e do design system; quantas páginas foram clonadas;
dependências externas que o clone ainda tem; a paleta e as fontes em uma linha; quantos componentes
foram documentados; e o que foi inferido em vez de medido (estados de hover, componentes ausentes).
