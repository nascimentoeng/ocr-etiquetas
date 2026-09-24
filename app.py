import os
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from database import (
    RegistroDuplicadoError,
    criar_tabela,
    listar_registros,
    salvar_registro,
)
from extrair_etiqueta import extrair_dados


st.set_page_config(
    page_title="Leitor de etiquetas",
    page_icon="📦",
    layout="centered",
)


DATABASE_URL = st.secrets["TURSO_DATABASE_URL"]
AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]
CODIGO_CLIENTE = "101015"


@st.cache_resource
def inicializar_banco():
    criar_tabela(
        DATABASE_URL,
        AUTH_TOKEN,
    )

    return True


try:
    inicializar_banco()

except Exception as erro:
    st.error(
        "Não foi possível conectar ao banco de dados: "
        f"{erro}"
    )
    st.stop()


if "resultado_ocr" not in st.session_state:
    st.session_state.resultado_ocr = None

if "campo_item_number" not in st.session_state:
    st.session_state.campo_item_number = ""

if "campo_box_number" not in st.session_state:
    st.session_state.campo_box_number = ""

if "campo_quantity" not in st.session_state:
    st.session_state.campo_quantity = 0


st.title("Leitor de etiquetas")

st.write(
    "Envie uma fotografia da etiqueta para extrair "
    "Item Number, Box Number e Quantity."
)

st.info(
    f"Código Cliente utilizado: {CODIGO_CLIENTE}"
)


arquivo = st.file_uploader(
    "Selecione a imagem",
    type=[
        "jpg",
        "jpeg",
        "jfif",
        "png",
    ],
)


if arquivo is not None:
    st.image(
        arquivo,
        caption="Imagem selecionada",
        use_container_width=True,
    )

    if st.button(
        "Processar etiqueta",
        type="primary",
    ):
        extensao = os.path.splitext(
            arquivo.name
        )[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extensao,
        ) as arquivo_temporario:
            arquivo_temporario.write(
                arquivo.getbuffer()
            )

            caminho_temporario = (
                arquivo_temporario.name
            )

        try:
            with st.spinner(
                "Processando a etiqueta..."
            ):
                resultado = extrair_dados(
                    caminho_temporario
                )

            st.session_state.resultado_ocr = resultado

            st.session_state.campo_item_number = (
                resultado["item_number"] or ""
            )

            st.session_state.campo_box_number = (
                resultado["box_number"] or ""
            )

            st.session_state.campo_quantity = (
                resultado["quantity"] or 0
            )

            st.success(
                "Processamento concluído."
            )

        except Exception as erro:
            st.error(
                "Não foi possível processar "
                f"a imagem: {erro}"
            )

        finally:
            if os.path.exists(
                caminho_temporario
            ):
                os.remove(
                    caminho_temporario
                )


if st.session_state.resultado_ocr is not None:
    resultado = st.session_state.resultado_ocr

    st.subheader("Dados extraídos")

    st.write(
        "Confira os dados abaixo. Você pode corrigir "
        "qualquer valor antes de salvar."
    )

    item_number = st.text_input(
        "Item Number",
        key="campo_item_number",
    )

    box_number = st.text_input(
        "Box Number",
        key="campo_box_number",
    )

    quantity = st.number_input(
        "Quantity",
        min_value=0,
        step=1,
        key="campo_quantity",
    )

    with st.expander(
        "Ver texto bruto do OCR"
    ):
        st.text(
            resultado["texto_ocr"]
        )

    if st.button(
        "Confirmar e salvar",
        type="primary",
    ):
        erros = []

        item_number_normalizado = (
            item_number.strip().upper()
        )

        box_number_normalizado = (
            box_number.strip().upper()
        )

        if not item_number_normalizado:
                      erros.append(
                "O Item Number deve ser preenchido."
            )

        if not box_number_normalizado:
            erros.append(
                "O Box Number deve ser preenchido."
            )

        if quantity <= 0:
            erros.append(
                "A Quantity deve ser maior que zero."
            )

        if erros:
            for erro in erros:
                st.error(erro)

        else:
            data_hora = datetime.now(
                ZoneInfo("America/Sao_Paulo")
            )

            data_registro = data_hora.strftime(
                "%Y-%m-%d"
            )

            try:
                registro_id = salvar_registro(
                    database_url=DATABASE_URL,
                    auth_token=AUTH_TOKEN,
                    data_hora=data_hora.strftime(
                        "%d/%m/%Y %H:%M:%S"
                    ),
                    data_registro=data_registro,
                    codigo_cliente=CODIGO_CLIENTE,
                    item_number=item_number_normalizado,
                    box_number=box_number_normalizado,
                    quantity=int(quantity),
                )

                st.success(
                    "Registro salvo permanentemente "
                    "no banco."
                )

                st.info(
                    f"Registro ID: {registro_id} | "
                    f"Código Cliente: {CODIGO_CLIENTE}"
                )

            except RegistroDuplicadoError as erro:
                st.warning(str(erro))

                st.info(
                    "Nenhum novo registro foi criado. "
                    "O mesmo Box Number poderá ser "
                    "registrado novamente em outro dia."
                )

            except Exception as erro:
                st.error(
                    "Não foi possível salvar o registro "
                    f"no banco de dados: {erro}"
                )


st.divider()
st.subheader("Registros salvos no banco")


try:
    registros = listar_registros(
        DATABASE_URL,
        AUTH_TOKEN,
    )

    if registros:
        st.dataframe(
            registros,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Nenhum registro foi salvo até o momento."
        )

except Exception as erro:
    st.warning(
        "Não foi possível carregar os registros: "
        f"{erro}"
    )