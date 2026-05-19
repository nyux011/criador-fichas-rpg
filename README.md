# Criador de Fichas — One-shot de Terror Investigativo

Mini aplicação Streamlit para que jogadores criem fichas de personagem em um sistema D20 simplificado e exportem um PDF estilo dossiê confidencial.

## Estrutura

```
criador-fichas-rpg/
├── app.py              # Interface Streamlit
├── ficha_pdf.py        # Geração do PDF (ReportLab, em memória)
├── regras.py           # Constantes do sistema, validação e cálculos derivados
├── requirements.txt    # Dependências
├── README.md
└── assets/             # Pasta opcional para imagens / logos / fundos
```

## Rodar localmente

1. Garanta Python 3.10+ instalado.
2. Crie um ambiente virtual (recomendado):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instale as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

4. Execute:

   ```powershell
   streamlit run app.py
   ```

5. O Streamlit abrirá automaticamente o navegador em `http://localhost:8501`.

## Hospedar no Streamlit Community Cloud

1. Crie um repositório no GitHub contendo o conteúdo da pasta `criador-fichas-rpg/` (incluindo `requirements.txt`).
2. Acesse <https://share.streamlit.io> e clique em **New app**.
3. Selecione o repositório, branch e arquivo principal `app.py`.
4. Confirme o deploy. O Streamlit instalará as dependências do `requirements.txt` automaticamente.
5. Compartilhe a URL gerada com seus jogadores.

> Nenhuma variável de ambiente é necessária — a aplicação não usa banco, autenticação ou serviços externos.

## Personalizar o visual do PDF

Toda a estética do PDF está concentrada em [ficha_pdf.py](ficha_pdf.py). Para ajustar:

- **Paleta:** edite as constantes `COR_FUNDO_HEADER`, `COR_DESTAQUE`, `COR_CARIMBO`, `COR_TEXTO`, etc. no topo do arquivo. Aceitam `colors.HexColor("#xxxxxx")` ou `colors.Color(r, g, b, alpha=...)`.
- **Carimbo "CONFIDENCIAL":** ajuste em `_desenhar_carimbo()` o ângulo (`c.rotate`), a fonte ou troque a string.
- **Cabeçalho da página:** edite `_desenhar_cabecalho_pagina()` para mudar título, subtítulo, altura ou para incluir um logotipo via `c.drawImage("assets/logo.png", x, y, width, height)` (requer Pillow).
- **Tabelas de atributos / perícias:** funções `_desenhar_tabela_atributos`, `_desenhar_pericias` e `_desenhar_derivados` controlam tamanhos, fontes e cores das células.
- **Layout de seções narrativas:** veja a tupla `campos_narrativos` dentro de `gerar_pdf_ficha()` e o helper `_bloco_multilinha()` (parâmetro `linhas` controla quantas pautas aparecem por campo).
- **Margens/folha:** constantes `MARGEM_X`, `MARGEM_TOPO`, `MARGEM_BASE`. O tamanho da página vem de `pagesizes.A4` — pode trocar por `LETTER` se preferir.

Se quiser usar imagens/logos no fundo, descomente o uso da pasta `assets/` e instale Pillow (`pip install Pillow`) — a importação no `ficha_pdf.py` é opcional.

## Notas do sistema

- **Atributos:** 7 pontos · mín 0 · máx 3 (Físico, Mental, Relação, Conhecimento).
- **Perícias:** 10 pontos · mín 0 · máx 2 (15 perícias agrupadas por categoria).
- **Saúde calculada:**
  - Vitalidade = 10 + Físico × 3
  - Resistência = 8 + Físico + Mental
  - Iniciativa = Físico + Mental
- **Teste padrão:** 1d20 + Atributo + Perícia vs Dificuldade.

A validação acontece em tempo real e o botão de PDF só libera o download quando a ficha está completa e dentro dos limites.
