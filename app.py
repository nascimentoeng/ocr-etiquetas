import os
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from extrair_etiqueta import extrair_dados


st.set_page_config(
    page_title="Leitor de etiquetas",
    page_icon="📦",
    layout="centered",
)


# Inicializa o armazenamento temporário da sessão
if "resultado_ocr" not in st.session_state:
    st.session_state.resultado_ocr = None

if "registros_salvos" not in st.session_state:
    st.session_state.registros_salvos = []


st.title("Leitor de etiquetas")

st.write(
    "Envie uma fotografia da etiqueta para extrair "
    "Item Number, Box Number e Quantity."
)

arquivo = st.file_uploader(
    "Selecione a imagem",
    type=["jpg", "jpeg", "jfif", "png"],
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
        extensao = os.path.splitext(arquivo.name)[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extensao,
        ) as arquivo_temporario:
            arquivo_temporario.write(
                arquivo.getbuffer()
            )
            caminho_temporario = arquivo_temporario.name

        try:
            with st.spinner(
                "Processando a etiqueta..."
            ):
                resultado = extrair_dados(
                    caminho_temporario
                )

            st.session_state.resultado_ocr = resultado
            st.session_state.nome_arquivo = arquivo.name

            st.success("Processamento concluído.")

        except Exception as erro:
            st.error(
                "Não foi possível processar a imagem: "
                f"{erro}"
            )

        finally:
            if os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)


if st.session_state.resultado_ocr is not None:
    resultado = st.session_state.resultado_ocr

    st.subheader("Dados extraídos")

    st.write(
        "Confira os dados abaixo. Você pode corrigir "
        "qualquer valor antes de salvar."
    )

    item_number = st.text_input(
        "Item Number",
        value=resultado["item_number"] or "",
        key="campo_item_number",
    )

    box_number = st.text_input(
        "Box Number",
        value=resultado["box_number"] or "",
        key="campo_box_number",
    )

    quantity = st.number_input(
        "Quantity",
        min_value=0,
        step=1,
        value=resultado["quantity"] or 0,
        key="campo_quantity",
    )

    with st.expander("Ver texto bruto do OCR"):
        st.text(resultado["texto_ocr"])

    if st.button(
        "Confirmar e salvar",
        type="primary",
    ):
        erros = []

        if not item_number.strip():
            erros.append(
                "O Item Number deve ser preenchido."
            )

        if not box_number.strip():
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

            registro = {
                "data_hora": data_hora.strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
                "item_number": item_number
                .strip()
                .upper(),
                "box_number": box_number
                .strip()
                .upper(),
                "quantity": int(quantity),
                "nome_arquivo": st.session_state.get(
                    "nome_arquivo",
                    "",
                ),
            }

            st.session_state.registros_salvos.append(
                registro
            )

            st.success(
                "Registro salvo temporariamente."
            )

            st.info(
                "Nesta etapa, os dados permanecem "
                "salvos somente durante esta sessão. "
                "Posteriormente, conectaremos ao banco."
            )


if st.session_state.registros_salvos:
    st.divider()
    st.subheader("Registros salvos nesta sessão")

    st.dataframe(
        st.session_state.registros_salvos,
        use_container_width=True,
        hide_index=True,
    )