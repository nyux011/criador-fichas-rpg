"""Regras do sistema simplificado D20 para a one-shot de terror investigativo.

Centraliza constantes (atributos, perícias, limites) e funções puras de
validação e cálculo de atributos derivados. É consumido por `app.py` para
validação em tempo real e por `ficha_pdf.py` para gerar o relatório final.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constantes do sistema
# ---------------------------------------------------------------------------

ATRIBUTOS: Tuple[str, ...] = ("Físico", "Mental", "Relação", "Conhecimento")

PONTOS_ATRIBUTOS: int = 7
ATRIBUTO_MIN: int = 0
ATRIBUTO_MAX: int = 3

# Perícias agrupadas por categoria — a ordem é preservada na ficha e no PDF.
PERICIAS_POR_GRUPO: Dict[str, Tuple[str, ...]] = {
    "Habilidades Físicas": ("Atletismo", "Furtividade", "Luta", "Pontaria"),
    "Habilidades Mentais": ("Percepção", "Investigação", "Intuição", "Vontade"),
    "Conhecimentos Gerais": (
        "Medicina",
        "Tecnologia",
        "Criminalística",
        "Cultura Geral",
    ),
    "Conhecimentos Específicos": ("Ocultismo", "Submundo", "Psicologia"),
}

PERICIAS: Tuple[str, ...] = tuple(
    p for grupo in PERICIAS_POR_GRUPO.values() for p in grupo
)

PONTOS_PERICIAS: int = 10
PERICIA_MIN: int = 0
PERICIA_MAX: int = 2


# ---------------------------------------------------------------------------
# Cálculos derivados
# ---------------------------------------------------------------------------

def calcular_vitalidade(fisico: int) -> int:
    """Calcula a Vitalidade do personagem.

    Args:
        fisico: Valor do atributo Físico.

    Returns:
        Vitalidade total: 10 + Físico * 3.
    """
    return 10 + fisico * 3


def calcular_resistencia(fisico: int, mental: int) -> int:
    """Calcula a Resistência do personagem.

    Args:
        fisico: Valor do atributo Físico.
        mental: Valor do atributo Mental.

    Returns:
        Resistência total: 8 + Físico + Mental.
    """
    return 8 + fisico + mental


def calcular_iniciativa(fisico: int, mental: int) -> int:
    """Calcula a Iniciativa do personagem.

    Args:
        fisico: Valor do atributo Físico.
        mental: Valor do atributo Mental.

    Returns:
        Iniciativa total: Físico + Mental.
    """
    return fisico + mental


def calcular_derivados(atributos: Dict[str, int]) -> Dict[str, int]:
    """Calcula todos os atributos derivados a partir dos atributos base.

    Args:
        atributos: Dicionário com os 4 atributos principais.

    Returns:
        Dicionário com Vitalidade, Resistência e Iniciativa.
    """
    fisico = atributos.get("Físico", 0)
    mental = atributos.get("Mental", 0)
    return {
        "Vitalidade": calcular_vitalidade(fisico),
        "Resistência": calcular_resistencia(fisico, mental),
        "Iniciativa": calcular_iniciativa(fisico, mental),
    }


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def validar_atributos(atributos: Dict[str, int]) -> List[str]:
    """Valida a distribuição de pontos entre atributos.

    Args:
        atributos: Dicionário {nome_atributo: valor}.

    Returns:
        Lista de mensagens de erro. Vazia se a distribuição estiver válida.
    """
    erros: List[str] = []
    for nome in ATRIBUTOS:
        valor = atributos.get(nome, 0)
        if valor < ATRIBUTO_MIN or valor > ATRIBUTO_MAX:
            erros.append(
                f"Atributo '{nome}' deve estar entre {ATRIBUTO_MIN} e {ATRIBUTO_MAX}."
            )
    total = sum(atributos.get(a, 0) for a in ATRIBUTOS)
    if total != PONTOS_ATRIBUTOS:
        diferenca = total - PONTOS_ATRIBUTOS
        if diferenca > 0:
            erros.append(
                f"Total de atributos é {total}; passou {diferenca} ponto(s)."
            )
        else:
            erros.append(
                f"Total de atributos é {total}; faltam {-diferenca} ponto(s)."
            )
    return erros


def validar_pericias(pericias: Dict[str, int]) -> List[str]:
    """Valida a distribuição de pontos entre perícias.

    Args:
        pericias: Dicionário {nome_pericia: valor}.

    Returns:
        Lista de mensagens de erro. Vazia se a distribuição estiver válida.
    """
    erros: List[str] = []
    for nome in PERICIAS:
        valor = pericias.get(nome, 0)
        if valor < PERICIA_MIN or valor > PERICIA_MAX:
            erros.append(
                f"Perícia '{nome}' deve estar entre {PERICIA_MIN} e {PERICIA_MAX}."
            )
    total = sum(pericias.get(p, 0) for p in PERICIAS)
    if total != PONTOS_PERICIAS:
        diferenca = total - PONTOS_PERICIAS
        if diferenca > 0:
            erros.append(
                f"Total de perícias é {total}; passou {diferenca} ponto(s)."
            )
        else:
            erros.append(
                f"Total de perícias é {total}; faltam {-diferenca} ponto(s)."
            )
    return erros


def validar_dados_basicos(nome_personagem: str, nome_jogador: str) -> List[str]:
    """Valida que os campos obrigatórios mínimos foram preenchidos.

    Args:
        nome_personagem: Nome do personagem.
        nome_jogador: Nome do jogador.

    Returns:
        Lista de mensagens de erro. Vazia se válido.
    """
    erros: List[str] = []
    if not nome_personagem or not nome_personagem.strip():
        erros.append("Nome do personagem é obrigatório.")
    if not nome_jogador or not nome_jogador.strip():
        erros.append("Nome do jogador é obrigatório.")
    return erros


def validar_ficha_completa(
    nome_personagem: str,
    nome_jogador: str,
    atributos: Dict[str, int],
    pericias: Dict[str, int],
) -> List[str]:
    """Validação consolidada da ficha inteira.

    Args:
        nome_personagem: Nome do personagem.
        nome_jogador: Nome do jogador.
        atributos: Dicionário de atributos.
        pericias: Dicionário de perícias.

    Returns:
        Lista de erros agregada. Vazia se a ficha estiver pronta para gerar PDF.
    """
    erros: List[str] = []
    erros.extend(validar_dados_basicos(nome_personagem, nome_jogador))
    erros.extend(validar_atributos(atributos))
    erros.extend(validar_pericias(pericias))
    return erros


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def normalizar_nome_arquivo(nome: str) -> str:
    """Normaliza um nome para uso seguro como nome de arquivo.

    Remove acentos, troca espaços por underscore e descarta caracteres
    especiais. Garante um fallback caso a string fique vazia.

    Args:
        nome: Texto livre informado pelo usuário.

    Returns:
        Slug seguro para uso em nome de arquivo.
    """
    if not nome:
        return "personagem"
    # Remove acentos via decomposição Unicode.
    sem_acentos = unicodedata.normalize("NFKD", nome)
    sem_acentos = sem_acentos.encode("ascii", "ignore").decode("ascii")
    sem_acentos = sem_acentos.strip().lower()
    # Substitui qualquer sequência de não-alfanuméricos por underscore.
    slug = re.sub(r"[^a-z0-9]+", "_", sem_acentos).strip("_")
    return slug or "personagem"
