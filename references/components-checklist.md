# Checklist de componentes

Cubra tudo o que o site realmente usa. Se o site não tem um componente, não invente: registre a
ausência em DESIGN-SYSTEM.md ("o site não usa tabs"). Se o usuário pedir o conjunto completo mesmo
assim, derive os que faltam dos tokens e marque-os como "derivado, não presente no original".

## Fundação (sempre)
- Cores: marca, texto, superfícies, bordas, feedback (sucesso/erro/aviso), com contraste AA anotado
- Tipografia: famílias, pesos, escala completa (display → small/overline) com versão mobile
- Espaçamento: escala única, normalmente múltiplos de 4 ou 8. Arredonde valores quebrados (23px → 24px)
- Raios, sombras, bordas
- Grade: largura do container, colunas, gutter, margens laterais, comportamento mobile
- Breakpoints (das media queries em `raw-extraction.json`, não chutados)
- Movimento: durações e easings, se o site usa transição

## Componentes por categoria
| Categoria | Componentes | Estados a documentar |
|---|---|---|
| Ações | botão primário, secundário, ghost/link, ícone, tamanhos | hover, focus, disabled |
| Formulário | input, textarea, select, checkbox, radio, label, texto de ajuda, erro | focus, erro, disabled |
| Navegação | header/navbar, menu mobile, footer, breadcrumb, links | ativo, hover |
| Conteúdo | card, hero, seção com título, depoimento, lista de features, FAQ/accordion, tabela, estatística/número | — |
| Feedback | badge/tag, alerta, toast | variantes semânticas |
| Mídia | imagem com proporção, avatar, ícone, logo | — |
| Layout | container, grade, stack vertical, divisor | — |

Estados de hover não aparecem na extração estática. Infira pelo padrão do site (escurecer a cor
primária ~10%, sublinhar links) e deixe claro no guia que é inferência.

## Padrões de seção (templates de página)
Além de componentes atômicos, documente 2 a 4 padrões de seção recorrentes (hero, grade de
benefícios, bloco de CTA, rodapé) com o HTML montado sobre `.ds-container` + `.ds-grid`. É isso que
permite a alguém montar uma página nova no mesmo estilo.
