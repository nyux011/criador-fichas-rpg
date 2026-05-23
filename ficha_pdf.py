"""Geração do PDF da ficha em estética de dossiê confidencial.

O PDF é montado em memória (BytesIO) usando ReportLab, sem dependência
de imagens externas. A paleta é sombria (preto/grafite/vermelho discreto),
as seções aparecem em caixas com cabeçalho escuro e há um carimbo
diagonal "CONFIDENCIAL" levemente translúcido no fundo.
"""

from __future__ import annotations

from io import BytesIO
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas

from regras import (
    ATRIBUTOS,
    PERICIAS_POR_GRUPO,
    calcular_derivados,
)

# ---------------------------------------------------------------------------
# Paleta e medidas
# ---------------------------------------------------------------------------

COR_FUNDO_HEADER = colors.HexColor("#1a1a1a")
COR_TEXTO_HEADER = colors.HexColor("#f4f4f4")
COR_BORDA = colors.HexColor("#2b2b2b")
COR_TEXTO = colors.HexColor("#111111")
COR_LABEL = colors.HexColor("#444444")
COR_LINHA_FINA = colors.HexColor("#888888")
COR_DESTAQUE = colors.HexColor("#7a0a0a")

MARGEM_X = 18 * mm
MARGEM_TOPO = 18 * mm
MARGEM_BASE = 18 * mm

LARGURA, ALTURA = A4


# ---------------------------------------------------------------------------
# Helpers de desenho
# ---------------------------------------------------------------------------


def _desenhar_cabecalho_pagina(c: Canvas, titulo: str, subtitulo: str) -> float:
    """Desenha o cabeçalho do topo da página e retorna a coordenada Y livre.

    Args:
        c: Canvas ReportLab.
        titulo: Texto principal do cabeçalho.
        subtitulo: Texto secundário (ex.: nome do arquivo/caso).

    Returns:
        Coordenada Y abaixo do cabeçalho, pronta para o conteúdo.
    """
    altura_header = 22 * mm
    y_top = ALTURA - MARGEM_TOPO
    c.setFillColor(COR_FUNDO_HEADER)
    c.rect(MARGEM_X, y_top - altura_header, LARGURA - 2 * MARGEM_X, altura_header, fill=1, stroke=0)

    c.setFillColor(COR_TEXTO_HEADER)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGEM_X + 6 * mm, y_top - 9 * mm, titulo)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(MARGEM_X + 6 * mm, y_top - 15 * mm, subtitulo)

    # Faixa fina vermelha como detalhe.
    c.setFillColor(COR_DESTAQUE)
    c.rect(MARGEM_X, y_top - altura_header - 1.2, LARGURA - 2 * MARGEM_X, 1.2, fill=1, stroke=0)

    return y_top - altura_header - 5 * mm


def _desenhar_rodape(c: Canvas, numero_pagina: int) -> None:
    """Desenha o rodapé com numeração e selo discreto.

    Args:
        c: Canvas ReportLab.
        numero_pagina: Número da página atual.
    """
    c.setFillColor(COR_LABEL)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGEM_X, MARGEM_BASE - 8, "Arquivo de uso restrito · Investigação em andamento")
    c.drawRightString(
        LARGURA - MARGEM_X,
        MARGEM_BASE - 8,
        f"Página {numero_pagina}",
    )


def _titulo_secao(c: Canvas, y: float, texto: str) -> float:
    """Desenha um cabeçalho de seção (faixa escura) e retorna o novo Y.

    Args:
        c: Canvas ReportLab.
        y: Coordenada Y onde a seção começa.
        texto: Título da seção.

    Returns:
        Coordenada Y abaixo da faixa, pronta para o conteúdo.
    """
    altura = 7 * mm
    c.setFillColor(COR_FUNDO_HEADER)
    c.rect(MARGEM_X, y - altura, LARGURA - 2 * MARGEM_X, altura, fill=1, stroke=0)
    c.setFillColor(COR_TEXTO_HEADER)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGEM_X + 4 * mm, y - altura + 2.2 * mm, texto.upper())
    return y - altura - 4 * mm


def _quebrar_texto(texto: str, fonte: str, tamanho: float, largura_max: float) -> list[str]:
    """Quebra um texto em linhas que cabem dentro de largura_max.

    Args:
        texto: Texto a quebrar.
        fonte: Nome da fonte ReportLab (ex.: 'Helvetica').
        tamanho: Tamanho em pontos.
        largura_max: Largura máxima disponível em pontos.

    Returns:
        Lista de linhas, cada uma dentro do limite de largura.
    """
    if not texto:
        return ["—"]
    palavras = texto.split()
    linhas: list[str] = []
    linha_atual = ""
    for palavra in palavras:
        tentativa = (linha_atual + " " + palavra).strip()
        if stringWidth(tentativa, fonte, tamanho) <= largura_max:
            linha_atual = tentativa
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)
    return linhas or ["—"]


def _campo_texto(c: Canvas, x: float, y: float, largura: float, label: str, valor: str) -> float:
    """Desenha um par label + valor com quebra automática de linha.

    Args:
        c: Canvas.
        x: X inicial.
        y: Y inicial.
        largura: Largura total do campo.
        label: Etiqueta.
        valor: Valor preenchido.

    Returns:
        Coordenada Y após o campo (para posicionar o próximo elemento).
    """
    c.setFillColor(COR_LABEL)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x, y, label.upper())
    c.setStrokeColor(COR_LINHA_FINA)
    c.setLineWidth(0.4)
    c.line(x, y - 1.5, x + largura, y - 1.5)
    c.setFillColor(COR_TEXTO)
    c.setFont("Helvetica", 10)
    altura_linha = 4 * mm
    linhas = _quebrar_texto(valor, "Helvetica", 10, largura)
    for i, linha in enumerate(linhas):
        c.drawString(x, y - 9 - i * altura_linha, linha)
    return y - 9 - (len(linhas) - 1) * altura_linha - 6 * mm


def _bloco_multilinha(
    c: Canvas,
    x: float,
    y: float,
    largura: float,
    label: str,
    valor: str,
    linhas: int = 3,
) -> float:
    """Desenha um campo narrativo em caixa com quebra automática de texto.

    Args:
        c: Canvas.
        x: X inicial.
        y: Y inicial.
        largura: Largura do bloco.
        label: Etiqueta exibida acima da caixa.
        valor: Texto a inserir.
        linhas: Número mínimo de linhas da caixa (garante espaço mesmo vazio).

    Returns:
        Coordenada Y após o bloco.
    """
    PADDING_X = 3 * mm
    PADDING_Y = 2.5 * mm
    ALTURA_LINHA = 4.5 * mm

    c.setFillColor(COR_LABEL)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x, y, label.upper())
    y -= 3

    texto = valor.strip() if valor else ""
    linhas_texto: list[str] = []
    if texto:
        largura_interna = largura - 2 * PADDING_X
        palavras = texto.split()
        linha_atual = ""
        for palavra in palavras:
            tentativa = (linha_atual + " " + palavra).strip()
            if stringWidth(tentativa, "Helvetica", 9.5) <= largura_interna:
                linha_atual = tentativa
            else:
                if linha_atual:
                    linhas_texto.append(linha_atual)
                linha_atual = palavra
        if linha_atual:
            linhas_texto.append(linha_atual)

    num_linhas = max(linhas, len(linhas_texto))
    altura_caixa = num_linhas * ALTURA_LINHA + 2 * PADDING_Y

    c.setStrokeColor(COR_BORDA)
    c.setFillColor(colors.white)
    c.setLineWidth(0.5)
    c.rect(x, y - altura_caixa, largura, altura_caixa, fill=1, stroke=1)

    if linhas_texto:
        c.setFillColor(COR_TEXTO)
        c.setFont("Helvetica", 9.5)
        for i, linha in enumerate(linhas_texto):
            y_linha = y - PADDING_Y - (i + 1) * ALTURA_LINHA + 1.5
            c.drawString(x + PADDING_X, y_linha, linha)

    return y - altura_caixa - 3 * mm


def _desenhar_tabela_atributos(
    c: Canvas, y: float, atributos: Dict[str, int]
) -> float:
    """Desenha tabela com os 4 atributos principais.

    Args:
        c: Canvas.
        y: Y inicial.
        atributos: Dicionário {nome: valor}.

    Returns:
        Coordenada Y após a tabela.
    """
    n = len(ATRIBUTOS)
    largura_total = LARGURA - 2 * MARGEM_X
    largura_celula = largura_total / n
    altura_celula = 16 * mm

    for i, nome in enumerate(ATRIBUTOS):
        x = MARGEM_X + i * largura_celula
        # Caixa.
        c.setStrokeColor(COR_BORDA)
        c.setLineWidth(0.6)
        c.rect(x, y - altura_celula, largura_celula, altura_celula, fill=0, stroke=1)
        # Faixa do label.
        c.setFillColor(COR_FUNDO_HEADER)
        c.rect(x, y - 5 * mm, largura_celula, 5 * mm, fill=1, stroke=0)
        c.setFillColor(COR_TEXTO_HEADER)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(x + largura_celula / 2, y - 5 * mm + 1.4 * mm, nome.upper())
        # Valor.
        c.setFillColor(COR_TEXTO)
        c.setFont("Helvetica-Bold", 18)
        valor = str(atributos.get(nome, 0))
        c.drawCentredString(
            x + largura_celula / 2, y - altura_celula + 4 * mm, valor
        )

    return y - altura_celula - 5 * mm


def _desenhar_pericias(
    c: Canvas, y: float, pericias: Dict[str, int]
) -> float:
    """Desenha as perícias agrupadas por categoria, em duas colunas.

    Args:
        c: Canvas.
        y: Y inicial.
        pericias: Dicionário {nome_pericia: valor}.

    Returns:
        Coordenada Y após o bloco.
    """
    largura_total = LARGURA - 2 * MARGEM_X
    largura_coluna = largura_total / 2 - 3 * mm
    x_esq = MARGEM_X
    x_dir = MARGEM_X + largura_coluna + 6 * mm

    # Distribui grupos entre as duas colunas para equilibrar.
    grupos = list(PERICIAS_POR_GRUPO.items())
    coluna_esq = grupos[:2]
    coluna_dir = grupos[2:]

    y_esq = _renderizar_coluna_pericias(c, x_esq, y, largura_coluna, coluna_esq, pericias)
    y_dir = _renderizar_coluna_pericias(c, x_dir, y, largura_coluna, coluna_dir, pericias)

    return min(y_esq, y_dir) - 2 * mm


def _renderizar_coluna_pericias(
    c: Canvas,
    x: float,
    y: float,
    largura: float,
    grupos,
    pericias: Dict[str, int],
) -> float:
    """Renderiza uma coluna de grupos de perícias.

    Args:
        c: Canvas.
        x: X inicial da coluna.
        y: Y inicial.
        largura: Largura da coluna.
        grupos: Lista de tuplas (nome_grupo, tupla_de_pericias).
        pericias: Dicionário com valores.

    Returns:
        Coordenada Y final após renderizar todos os grupos.
    """
    cursor_y = y
    for nome_grupo, lista in grupos:
        # Cabeçalho do grupo.
        c.setFillColor(COR_DESTAQUE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(x, cursor_y - 4, nome_grupo.upper())
        c.setStrokeColor(COR_DESTAQUE)
        c.setLineWidth(0.4)
        c.line(x, cursor_y - 6, x + largura, cursor_y - 6)
        cursor_y -= 14

        c.setFillColor(COR_TEXTO)
        c.setFont("Helvetica", 9.5)
        for pericia in lista:
            valor = pericias.get(pericia, 0)
            c.drawString(x + 2, cursor_y, pericia)
            c.setFont("Helvetica-Bold", 9.5)
            c.drawRightString(x + largura - 2, cursor_y, str(valor))
            c.setFont("Helvetica", 9.5)
            # Linha de base sutil.
            c.setStrokeColor(COR_LINHA_FINA)
            c.setLineWidth(0.2)
            c.line(x, cursor_y - 1.8, x + largura, cursor_y - 1.8)
            cursor_y -= 7.5 * mm
        cursor_y -= 4 * mm
    return cursor_y


def _desenhar_derivados(c: Canvas, y: float, derivados: Dict[str, int]) -> float:
    """Desenha o bloco de saúde calculada (Vitalidade, Resistência, Iniciativa).

    Args:
        c: Canvas.
        y: Y inicial.
        derivados: Dicionário com os 3 valores.

    Returns:
        Coordenada Y após o bloco.
    """
    nomes = ("Vitalidade", "Resistência", "Iniciativa")
    largura_total = LARGURA - 2 * MARGEM_X
    largura_celula = largura_total / 3
    altura_celula = 14 * mm

    for i, nome in enumerate(nomes):
        x = MARGEM_X + i * largura_celula
        c.setStrokeColor(COR_BORDA)
        c.setLineWidth(0.6)
        c.rect(x, y - altura_celula, largura_celula, altura_celula, fill=0, stroke=1)
        c.setFillColor(COR_DESTAQUE)
        c.rect(x, y - 4.5 * mm, largura_celula, 4.5 * mm, fill=1, stroke=0)
        c.setFillColor(COR_TEXTO_HEADER)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + largura_celula / 2, y - 4.5 * mm + 1.2 * mm, nome.upper())
        c.setFillColor(COR_TEXTO)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(
            x + largura_celula / 2, y - altura_celula + 3.5 * mm, str(derivados[nome])
        )

    return y - altura_celula - 5 * mm


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def gerar_pdf_ficha(
    dados_basicos: Dict[str, str],
    atributos: Dict[str, int],
    pericias: Dict[str, int],
    narrativa: Dict[str, str],
) -> BytesIO:
    """Gera o PDF da ficha em memória.

    Args:
        dados_basicos: Dicionário com 'nome_personagem' e 'nome_jogador'.
        atributos: Dicionário {nome_atributo: valor}.
        pericias: Dicionário {nome_pericia: valor}.
        narrativa: Dicionário com os campos narrativos preenchidos.

    Returns:
        Buffer BytesIO posicionado no início, contendo o PDF gerado.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle("Ficha de Personagem - Arquivo Confidencial")
    c.setAuthor("Sistema D20 Simplificado")

    nome_personagem = dados_basicos.get("nome_personagem", "").strip() or "Sem nome"
    nome_jogador = dados_basicos.get("nome_jogador", "").strip() or "—"

    derivados = calcular_derivados(atributos)

    # ---- Página 1 ---------------------------------------------------------
    y = _desenhar_cabecalho_pagina(
        c,
        "FICHA DE PERSONAGEM — ARQUIVO CONFIDENCIAL",
        "",
    )

    # Dados básicos
    y = _titulo_secao(c, y, "Dados Básicos")
    largura_meio = (LARGURA - 2 * MARGEM_X) / 2 - 3 * mm
    y = min(
        _campo_texto(c, MARGEM_X, y, largura_meio, "Nome do Personagem", nome_personagem),
        _campo_texto(c, MARGEM_X + largura_meio + 6 * mm, y, largura_meio, "Nome do Jogador", nome_jogador),
    )
    y = min(
        _campo_texto(c, MARGEM_X, y, largura_meio, "Conceito", narrativa.get("conceito", "")),
        _campo_texto(c, MARGEM_X + largura_meio + 6 * mm, y, largura_meio, "Profissão", narrativa.get("profissao", "")),
    )

    # Atributos
    y = _titulo_secao(c, y, "Atributos Principais")
    y = _desenhar_tabela_atributos(c, y, atributos)
    y -= 3 * mm

    # Saúde calculada
    y = _titulo_secao(c, y, "Saúde Calculada")
    y = _desenhar_derivados(c, y, derivados)
    y -= 3 * mm

    # Perícias
    y = _titulo_secao(c, y, "Perícias")
    y = _desenhar_pericias(c, y, pericias)

    _desenhar_rodape(c, 1)

    # ---- Página 2 ---------------------------------------------------------
    c.showPage()
    y = _desenhar_cabecalho_pagina(
        c,
        "DOSSIÊ NARRATIVO — ANEXO PSICOLÓGICO",
        "",
    )

    y = _titulo_secao(c, y, "Informações Narrativas")
    largura_full = LARGURA - 2 * MARGEM_X

    campos_narrativos = (
        ("Trauma ou Segredo", narrativa.get("trauma", "")),
        ("Ligação com o Caso", narrativa.get("ligacao", "")),
        ("Medo Pessoal", narrativa.get("medo", "")),
        ("Objetivo Pessoal", narrativa.get("objetivo", "")),
        ("Contato Importante", narrativa.get("contato", "")),
        ("Equipamento Inicial", narrativa.get("equipamento", "")),
        ("Anotações", narrativa.get("anotacoes", "")),
    )

    for label, valor in campos_narrativos:
        linhas = 4 if label in ("Equipamento Inicial", "Anotações") else 2
        y = _bloco_multilinha(c, MARGEM_X, y, largura_full, label, valor, linhas=linhas)
        y -= 4 * mm
        if y < MARGEM_BASE + 30 * mm:
            _desenhar_rodape(c, 2)
            c.showPage()
            y = _desenhar_cabecalho_pagina(
                c,
                "DOSSIÊ NARRATIVO — CONTINUAÇÃO",
                "",
            )
            y = _titulo_secao(c, y, "Informações Narrativas (cont.)")

    _desenhar_rodape(c, c.getPageNumber())

    c.save()
    buffer.seek(0)
    return buffer
