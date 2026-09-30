# miners-reverse-branding

Skill para Claude Code que faz engenharia reversa da marca de um site a partir da URL. Primeiro clona
o site inteiro numa pasta pronta para deploy, com um `.zip` que leva o nome do domínio. Depois extrai
dele um design system completo: tokens, grade, componentes e o manual de uso.

## O que ela entrega

```
<dominio>/                    clone navegável, sem dependência do site original
<dominio>.zip                 o mesmo clone compactado
<dominio>-design-system/
├── DESIGN-SYSTEM.md          manual de uso, com página de exemplo pronta
├── styleguide.html           cores, tipografia, grade e componentes renderizados
├── tokens.json / tokens.css  cores, fontes, escala tipográfica, espaçamento, raios, sombras, grade, breakpoints
├── components.css / .json    componentes .ds-* com variantes, estados e faça/evite
├── assets/                   logos, ícones e imagens usados pelos componentes
└── screenshots/              páginas originais e recortes de cada componente
```

## Instalação

Clone dentro da pasta de skills do Claude Code, global ou de um projeto:

```bash
git clone https://github.com/ItaloDeFranca/miners-reverse-branding ~/.claude/skills/miners-reverse-branding
# ou, só para um projeto:
git clone https://github.com/ItaloDeFranca/miners-reverse-branding .claude/skills/miners-reverse-branding
```

Requisito: Python 3.10+. Na primeira execução, `scripts/setup.sh` cria um ambiente em
`~/.venvs/miners-reverse-branding` com Playwright e Chromium. Não precisa instalar nada à mão.

## Uso

Peça em linguagem natural no Claude Code:

- "Extrai o site https://exemplo.com.br e cria o design system"
- "Clona esse site e me dá o zip"
- "Quero o design system do site X: cores, fontes, grade e componentes"

A skill segue seis etapas: preparar o ambiente, clonar, medir o design nas páginas vivas, curar os
tokens, recriar os componentes e gerar o styleguide. No fim ela verifica o resultado por screenshot,
no desktop e no celular, antes de entregar.

## Scripts (uso direto, sem o Claude)

```bash
PY=$(bash scripts/setup.sh)
$PY scripts/grabber.py https://exemplo.com.br 20 ./saida          # clone + zip (20 = máx. de páginas)
$PY scripts/extract_design.py ./saida/ds https://exemplo.com.br/  # medições brutas + screenshots
$PY scripts/build_styleguide.py ./saida/ds                        # tokens.json + components.json → tokens.css + styleguide.html
```

`build_styleguide.py` espera `tokens.json` e `components.json` no formato de
`references/tokens-schema.md`. A curadoria entre a medição e esse formato é a parte que o Claude faz.

## Limitações

- Formulários e buscas do clone não funcionam, porque dependem do backend do site original.
- Assets de CDNs de terceiros (Google Fonts, por exemplo) continuam apontando para o CDN.
- Estados de hover, foco e erro que o site não mostra são inferidos e ficam marcados como "derivado".
- Use em sites seus, de clientes ou como referência de estudo interno.
