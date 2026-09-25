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
    page_title="Lector de etiquetas",
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
        "No fue posible conectarse a la base "
        f"de datos: {erro}"
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

coluna_esquerda, coluna_logo, coluna_direita = st.columns(
    [1, 1, 1]
)

with coluna_logo:
    st.image(
        "vesuvius.png",
        use_container_width=True,
    )

st.markdown(
    '<h2 style="text-align: center; margin-top: 0.25rem; '
    'margin-bottom: 0.25rem;">Lector de etiquetas</h2>',
    unsafe_allow_html=True,
)

st.markdown(
    '<p style="text-align: center; color: #6b7280; '
    'font-size: 0.95rem; margin-top: 0; margin-bottom: 1.5rem;">'
    'Extracción y registro de datos mediante reconocimiento óptico'
    '</p>',
    unsafe_allow_html=True,
)

st.write(
    "Cargue una fotografía de la etiqueta para "
    "extraer Item Number, Box Number y Quantity."
)

st.info(
    f"Código de cliente utilizado: {CODIGO_CLIENTE}"
)


arquivo = st.file_uploader(
    "Seleccione la imagen",
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
        caption="Imagen seleccionada",
        use_container_width=True,
    )

    if st.button(
        "Procesar etiqueta",
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
                "Procesando la etiqueta..."
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
                "Procesamiento finalizado."
            )

        except Exception as erro:
            st.error(
                "No fue posible procesar "
                f"la imagen: {erro}"
            )

        finally:
            if os.path.exists(
                caminho_temporario
            ):
                os.remove(
                    caminho_temporario
                )