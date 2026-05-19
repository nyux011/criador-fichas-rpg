"""Interface Streamlit para criação da ficha de personagem.

Coordena entrada do usuário, validação em tempo real (delegada a `regras.py`)
e geração do PDF final (delegada a `ficha_pdf.py`). Mantém-se intencionalmente
simples: sem persistência, sem login, sem dependências além de Streamlit/ReportLab.
"""

from __future__ import annotations

import streamlit as st

from ficha_pdf import gerar_pdf_ficha
from regras import (
    ATRIBUTOS,
    ATRIBUTO_MAX,
    ATRIBUTO_MIN,
    PERICIAS_POR_GRUPO,
    PERICIA_MAX,
    PERICIA_MIN,
    PONTOS_ATRIBUTOS,
    PONTOS_PERICIAS,
    calcular_derivados,
    normalizar_nome_arquivo,
    validar_atributos,
    validar_ficha_completa,
    validar_pericias,
)

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Arquivo Confidencial — Ficha de Personagem",
    page_icon="🕯️",
    layout="wide",
)


def _aplicar_estilo() -> None:
    """Aplica um CSS leve para reforçar a estética de dossiê."""
    st.markdown(
        """
        <style>
            .main { background-color: #0f0f10; }
            h1, h2, h3, h4 { color: #f1e9d2 !important; letter-spacing: 0.5px; }
            .stMarkdown p, .stMarkdown li { color: #d8d4c7; }
            div[data-testid="stMetricValue"] { color: #f1e9d2; }
            .stButton > button {
                background-color: #7a0a0a;
                color: #f1e9d2;
                border: 1px solid #2b2b2b;
            }
            .stButton > button:hover { background-color: #5a0707; color: #fff; }
            .selo {
                border: 1px dashed #7a0a0a;
                padding: 8px 14px;
                color: #c8b994;
                display: inline-block;
                font-family: monospace;
                letter-spacing: 2px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------

def _renderizar_cabecalho() -> None:
    """Renderiza título, subtítulo e explicação do sistema."""
    st.markdown('<span class="selo">// ARQUIVO CONFIDENCIAL · USO INTERNO</span>', unsafe_allow_html=True)
    st.title("Ficha de Personagem — Dossiê do Investigador")
    st.subheader("One-shot de terror investigativo · Sistema D20 Simplificado")
    with st.expander("Como funciona o sistema (leia antes de preencher)", expanded=False):
        st.markdown(
            f"""
            **Teste padrão:** `1d20 + Atributo + Perícia` contra uma **Dificuldade** definida pelo mestre.

            **Atributos principais:** {", ".join(ATRIBUTOS)}.
            Distribua exatamente **{PONTOS_ATRIBUTOS} pontos** entre eles
            (mínimo {ATRIBUTO_MIN}, máximo {ATRIBUTO_MAX} por atributo).

            **Perícias:** distribua exatamente **{PONTOS_PERICIAS} pontos**
            (mínimo {PERICIA_MIN}, máximo {PERICIA_MAX} por perícia).

            **Atributos derivados** são calculados automaticamente:
            - Vitalidade = 10 + Físico × 3
            - Resistência = 8 + Físico + Mental
            - Iniciativa = Físico + Mental
            """
        )


# ---------------------------------------------------------------------------
# Seções do formulário
# ---------------------------------------------------------------------------

def _secao_dados_basicos() -> dict:
    """Renderiza inputs de identificação básica.

    Returns:
        Dicionário com nome do personagem e do jogador.
    """
    st.header("1 · Dados Básicos")
    col1, col2 = st.columns(2)
    with col1:
        nome_personagem = st.text_input("Nome do Personagem", max_chars=80)
    with col2:
        nome_jogador = st.text_input("Nome do Jogador", max_chars=80)
    return {
        "nome_personagem": nome_personagem,
        "nome_jogador": nome_jogador,
    }


def _secao_atributos() -> dict:
    """Renderiza inputs dos 4 atributos principais com feedback de pontos.

    Returns:
        Dicionário {nome_atributo: valor}.
    """
    st.header("2 · Atributos")
    st.caption(
        f"Distribua exatamente {PONTOS_ATRIBUTOS} pontos · mínimo {ATRIBUTO_MIN} · máximo {ATRIBUTO_MAX}."
    )
    cols = st.columns(len(ATRIBUTOS))
    atributos: dict = {}
    for col, nome in zip(cols, ATRIBUTOS):
        with col:
            atributos[nome] = st.number_input(
                nome,
                min_value=ATRIBUTO_MIN,
                max_value=ATRIBUTO_MAX,
                value=0,
                step=1,
                key=f"atributo_{nome}",
            )

    total = sum(atributos.values())
    restante = PONTOS_ATRIBUTOS - total
    col_a, col_b = st.columns(2)
    col_a.metric("Pontos usados", f"{total}/{PONTOS_ATRIBUTOS}")
    col_b.metric("Saldo", restante, delta=None)
    if restante > 0:
        st.warning(f"Faltam {restante} ponto(s) para distribuir.")
    elif restante < 0:
        st.error(f"Você passou {-restante} ponto(s) do limite.")
    else:
        st.success("Distribuição de atributos válida.")
    return atributos


def _secao_pericias() -> dict:
    """Renderiza inputs das 15 perícias agrupadas por categoria.

    Returns:
        Dicionário {nome_pericia: valor}.
    """
    st.header("3 · Perícias")
    st.caption(
        f"Distribua exatamente {PONTOS_PERICIAS} pontos · mínimo {PERICIA_MIN} · máximo {PERICIA_MAX}."
    )
    pericias: dict = {}
    for nome_grupo, lista in PERICIAS_POR_GRUPO.items():
        st.markdown(f"**{nome_grupo}**")
        cols = st.columns(len(lista))
        for col, pericia in zip(cols, lista):
            with col:
                pericias[pericia] = st.number_input(
                    pericia,
                    min_value=PERICIA_MIN,
                    max_value=PERICIA_MAX,
                    value=0,
                    step=1,
                    key=f"pericia_{pericia}",
                )

    total = sum(pericias.values())
    restante = PONTOS_PERICIAS - total
    col_a, col_b = st.columns(2)
    col_a.metric("Pontos usados", f"{total}/{PONTOS_PERICIAS}")
    col_b.metric("Saldo", restante)
    if restante > 0:
        st.warning(f"Faltam {restante} ponto(s) para distribuir.")
    elif restante < 0:
        st.error(f"Você passou {-restante} ponto(s) do limite.")
    else:
        st.success("Distribuição de perícias válida.")
    return pericias


def _secao_saude(atributos: dict) -> None:
    """Mostra os atributos derivados calculados em tempo real.

    Args:
        atributos: Dicionário com os 4 atributos principais.
    """
    st.header("4 · Saúde Calculada")
    derivados = calcular_derivados(atributos)
    cols = st.columns(3)
    cols[0].metric("Vitalidade", derivados["Vitalidade"])
    cols[1].metric("Resistência", derivados["Resistência"])
    cols[2].metric("Iniciativa", derivados["Iniciativa"])


def _secao_narrativa() -> dict:
    """Renderiza inputs dos campos narrativos da ficha.

    Returns:
        Dicionário com cada campo narrativo preenchido.
    """
    st.header("5 · Informações Narrativas")
    col1, col2 = st.columns(2)
    with col1:
        conceito = st.text_input("Conceito do Personagem", max_chars=120)
        profissao = st.text_input("Profissão", max_chars=80)
        medo = st.text_input("Medo Pessoal", max_chars=120)
        contato = st.text_input("Contato Importante", max_chars=120)
    with col2:
        trauma = st.text_area("Trauma ou Segredo", height=88)
        ligacao = st.text_area("Ligação com o Caso", height=88)
        objetivo = st.text_input("Objetivo Pessoal", max_chars=120)

    equipamento = st.text_area("Equipamento Inicial", height=100)
    anotacoes = st.text_area("Anotações", height=100)

    return {
        "conceito": conceito,
        "profissao": profissao,
        "trauma": trauma,
        "ligacao": ligacao,
        "medo": medo,
        "objetivo": objetivo,
        "contato": contato,
        "equipamento": equipamento,
        "anotacoes": anotacoes,
    }


# ---------------------------------------------------------------------------
# Geração do PDF
# ---------------------------------------------------------------------------

def _secao_pdf(
    dados_basicos: dict,
    atributos: dict,
    pericias: dict,
    narrativa: dict,
) -> None:
    """Mostra resumo de validação e o botão de geração do PDF.

    Args:
        dados_basicos: Dicionário de identificação.
        atributos: Dicionário de atributos.
        pericias: Dicionário de perícias.
        narrativa: Dicionário com campos narrativos.
    """
    st.header("6 · Gerar PDF")

    erros = validar_ficha_completa(
        dados_basicos["nome_personagem"],
        dados_basicos["nome_jogador"],
        atributos,
        pericias,
    )

    if erros:
        st.error("A ficha ainda não está válida. Corrija os pontos abaixo:")
        for erro in erros:
            st.markdown(f"- {erro}")
        st.button("Gerar PDF", disabled=True)
        return

    st.success("Ficha válida. Você pode gerar o PDF abaixo.")

    if st.button("Gerar PDF", type="primary"):
        try:
            buffer = gerar_pdf_ficha(dados_basicos, atributos, pericias, narrativa)
        except Exception as exc:  # noqa: BLE001 — feedback amigável ao usuário
            st.error(f"Falha ao gerar o PDF: {exc}")
            return

        slug = normalizar_nome_arquivo(dados_basicos["nome_personagem"])
        st.download_button(
            label="📥 Baixar ficha em PDF",
            data=buffer,
            file_name=f"ficha_{slug}.pdf",
            mime="application/pdf",
        )


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def main() -> None:
    """Ponto de entrada da aplicação Streamlit."""
    _aplicar_estilo()
    _renderizar_cabecalho()
    st.divider()

    dados_basicos = _secao_dados_basicos()
    st.divider()
    atributos = _secao_atributos()

    # Validação imediata (em tempo real) também via lista de erros — útil
    # quando o usuário extrapola via colagem ou recarregamento.
    erros_atr = validar_atributos(atributos)
    if erros_atr:
        for erro in erros_atr:
            st.caption(f"⚠ {erro}")

    st.divider()
    pericias = _secao_pericias()
    erros_per = validar_pericias(pericias)
    if erros_per:
        for erro in erros_per:
            st.caption(f"⚠ {erro}")

    st.divider()
    _secao_saude(atributos)

    st.divider()
    narrativa = _secao_narrativa()

    st.divider()
    _secao_pdf(dados_basicos, atributos, pericias, narrativa)


if __name__ == "__main__":
    main()
