import os
import tempfile

import streamlit as st

from extrair_etiqueta import extrair_dados


st.set_page_config(
    page_title="Leitor de etiquetas",
    page_icon="📦",
    layout="centered",
)

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

    if st.button("Processar etiqueta", type="primary"):
        extensao = os.path.splitext(arquivo.name)[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extensao,
        ) as arquivo_temporario:
            arquivo_temporario.write(arquivo.getbuffer())
            caminho_temporario = arquivo_temporario.name

        try:
            with st.spinner("Processando a etiqueta..."):
                resultado = extrair_dados(caminho_temporario)

            st.success("Processamento concluído.")

            st.subheader("Dados extraídos")

            item_number = st.text_input(
                "Item Number",
                value=resultado["item_number"] or "",
            )

            box_number = st.text_input(
                "Box Number",
                value=resultado["box_number"] or "",
            )

            quantity = st.number_input(
                "Quantity",
                min_value=0,
                step=1,
                value=resultado["quantity"] or 0,
            )

            with st.expander("Ver texto bruto do OCR"):
                st.text(resultado["texto_ocr"])

        except Exception as erro:
            st.error(
                f"Não foi possível processar a imagem: {erro}"
            )

        finally:
            if os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)