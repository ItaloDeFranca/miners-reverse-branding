# Formato de tokens.json e components.json

`build_styleguide.py` lê estes dois arquivos. Siga os nomes de chave exatamente: o script gera as
variáveis CSS a partir deles, e o styleguide quebra em silêncio se uma chave vier com outro nome.

## tokens.json

Toda folha é um objeto `{ "value": ..., "usage": "..." }`. `usage` é opcional, mas é o que torna o
design system utilizável: diga onde o token aparece no site ("fundo do header e CTAs principais").

```json
{
  "meta": {
    "name": "Pelion",
    "source": "https://www.pelion.com.br",
    "extractedAt": "2026-09-30",
    "language": "pt-BR",
    "fontsImport": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"
  },
  "color": {
    "brand":    { "primary": { "value": "#0B3D91", "usage": "CTAs, links, destaques" },
                  "primary-hover": { "value": "#082E6D" },
                  "secondary": { "value": "#F5A623" } },
    "text":     { "primary": { "value": "#111827" }, "secondary": { "value": "#4B5563" }, "inverse": { "value": "#FFFFFF" } },
    "surface":  { "page": { "value": "#FFFFFF" }, "muted": { "value": "#F3F4F6" }, "dark": { "value": "#0A0A0A" } },
    "border":   { "default": { "value": "#E5E7EB" } },
    "feedback": { "success": { "value": "#16A34A" }, "error": { "value": "#DC2626" } }
  },
  "typography": {
    "fontFamily": { "heading": { "value": "'Inter', sans-serif" }, "body": { "value": "'Inter', sans-serif" } },
    "fontWeight": { "regular": { "value": 400 }, "semibold": { "value": 600 }, "bold": { "value": 700 } },
    "scale": {
      "display": { "fontFamily": "heading", "fontSize": "64px", "mobileFontSize": "40px", "lineHeight": "1.1",
                   "fontWeight": 700, "letterSpacing": "-0.02em", "usage": "Título do hero", "sample": "Texto real do site" },
      "h1": { "...": "..." }, "h2": {}, "h3": {}, "body-lg": {}, "body": {}, "small": {}, "overline": { "textTransform": "uppercase" }
    }
  },
  "spacing":    { "1": { "value": "4px" }, "2": { "value": "8px" }, "3": { "value": "12px" }, "4": { "value": "16px" }, "6": { "value": "24px" }, "8": { "value": "32px" } },
  "radius":     { "sm": { "value": "4px" }, "md": { "value": "8px" }, "lg": { "value": "16px" }, "full": { "value": "9999px" } },
  "shadow":     { "sm": { "value": "0 1px 2px rgba(0,0,0,.06)" }, "md": { "value": "0 8px 24px rgba(0,0,0,.08)", "usage": "cards" } },
  "grid": {
    "container": { "value": "1200px" }, "columns": { "value": 12 }, "gutter": { "value": "24px" },
    "margin": { "value": "24px" }, "mobileColumns": { "value": 4 }, "gutter-mobile": { "value": "16px" },
    "mobileBreakpoint": { "value": "768px" }
  },
  "breakpoint": { "sm": { "value": "640px" }, "md": { "value": "768px" }, "lg": { "value": "1024px" }, "xl": { "value": "1280px" } },
  "motion":     { "duration-fast": { "value": "150ms" }, "duration-base": { "value": "250ms" }, "easing": { "value": "cubic-bezier(.4,0,.2,1)" } }
}
```

Variáveis geradas (prefixo por seção): `color` → `--color-brand-primary`; `typography.fontFamily` →
`--font-family-heading`; `fontWeight` → `--font-weight-bold`; `spacing` → `--space-4`; `radius` →
`--radius-md`; `shadow` → `--shadow-md`; `grid` → `--grid-gutter`; `motion` → `--motion-easing`.
Cada item de `typography.scale` vira a classe `.ds-text-<nome>` e as variáveis `--text-<nome>-size`,
`-line-height`, `-weight`, `-tracking`, `-family`.

O styleguide usa `--font-family-body` e `--color-text-primary` como base da área onde os
componentes são renderizados, então mantenha essas duas chaves.

Classes de grade geradas: `.ds-container`, `.ds-grid`, `.ds-col-1` … `.ds-col-<columns>`. Abaixo de
`mobileBreakpoint` a grade passa a `mobileColumns` e spans maiores que isso ocupam a linha inteira.

## components.json

```json
{
  "components": [
    {
      "name": "Botão",
      "slug": "button",
      "category": "Ações",
      "description": "Dispara a ação principal da seção. Um primário por bloco.",
      "variants": [
        { "name": "Primário", "html": "<a class=\"ds-btn ds-btn--primary\" href=\"#\">Fale com um especialista</a>" },
        { "name": "Secundário", "html": "<a class=\"ds-btn ds-btn--secondary\" href=\"#\">Saiba mais</a>", "note": "sobre fundo claro" }
      ],
      "usage": { "do": ["Verbo no infinitivo ou imperativo"], "dont": ["Dois primários lado a lado"] },
      "reference_screenshot": "screenshots/comp-www-pelion-com-br-button-0.png"
    }
  ]
}
```

`html` é renderizado ao vivo no styleguide, então use só classes `.ds-*` definidas em
`components.css` (que tira todo valor de design de `var(--...)` de tokens.css). Nada de classes do site
original: o objetivo é um sistema reaproveitável, não uma cópia do CSS deles. `reference_screenshot`
é relativo à pasta do design system.
