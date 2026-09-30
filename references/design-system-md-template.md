# Estrutura de DESIGN-SYSTEM.md

Escreva no idioma do usuário (padrão PT-BR). É o manual: alguém que nunca viu o site deve conseguir
construir uma página nova no mesmo estilo lendo só este arquivo. Use valores e nomes de token reais,
nunca placeholders.

```markdown
# <Nome> · Design System

Extraído de <url> em <data>. <1 parágrafo sobre a personalidade visual: o que define o site —
ex.: "azul-marinho sóbrio, muito respiro, tipografia geométrica pesada nos títulos">.

## Como usar
1. Importe as fontes (<link> exato) e os estilos: tokens.css e components.css
2. Estruture a página com .ds-container + .ds-grid
3. Use as classes .ds-text-* para texto e os componentes .ds-* abaixo
(inclua um exemplo de página mínima completa em HTML, 20–40 linhas)

## Princípios
3 a 5 regras observadas no site, cada uma com a evidência. Ex.: "Um único CTA laranja por dobra:
em todas as 6 páginas analisadas a cor secundária aparece só no botão principal."

## Cores
Tabela: token · valor · uso · contraste com branco/preto. Combinações aprovadas e proibidas.

## Tipografia
Famílias, escala (tabela com desktop/mobile), regras (ex.: máximo de 65 caracteres por linha).

## Espaçamento, raios e sombras
Escalas + quando usar cada nível.

## Grade e responsividade
Container, colunas, gutter, breakpoints e como o layout se reorganiza no mobile.

## Componentes
Para cada um: propósito, variantes, HTML de exemplo, estados, faça/evite.

## Padrões de seção
Hero, grade de benefícios, CTA, rodapé: HTML montado.

## Acessibilidade
Pares de cor que falham AA, tamanho mínimo de alvo de toque, foco visível.

## Limitações da extração
O que foi inferido (hover, estados) e o que não foi possível ler (CSS bloqueado por CORS, fontes
de terceiros).
```
