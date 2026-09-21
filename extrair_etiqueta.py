import re

import cv2
import pytesseract


ARQUIVO_IMAGEM = "foto_original.jfif"


def extrair_dados(caminho_imagem):
    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        raise FileNotFoundError(
            f"Nao foi possivel abrir a imagem: {caminho_imagem}"
        )

    # Recorte aproximado da etiqueta na foto de teste
    etiqueta = imagem[280:1320, 80:1160]

    # Usa a parte superior, onde estão os campos necessários
    altura, largura = etiqueta.shape[:2]
    area_interesse = etiqueta[0:int(altura * 0.40), 0:largura]

    # Prepara a imagem para o OCR
    cinza = cv2.cvtColor(
        area_interesse,
        cv2.COLOR_BGR2GRAY,
    )

    ampliada = cv2.resize(
        cinza,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC,
    )

    # Executa o OCR
    texto_ocr = pytesseract.image_to_string(
        ampliada,
        config="--psm 11",
    )

    # Procura o Item Number
    item = re.search(
        r"\b[A-Z]{2}\d{6,}\b",
        texto_ocr,
    )

    # Procura o Box Number, mesmo que o OCR
    # acrescente caracteres antes de WG
    caixa = re.search(
        r"WG\d{5,}",
        texto_ocr,
        re.IGNORECASE,
    )

    # Procura a quantidade e corrige erros comuns de OCR:
    # A no lugar de 4, O no lugar de 0 e "pe" no lugar de "pc"
    quantidade_bruta = re.search(
        r"\b([0-9AO]{1,4})\s*p[ce]\b",
        texto_ocr,
        re.IGNORECASE,
    )

    quantidade = None

    if quantidade_bruta:
        valor_quantidade = quantidade_bruta.group(1).upper()
        valor_quantidade = valor_quantidade.replace("A", "4")
        valor_quantidade = valor_quantidade.replace("O", "0")

        if valor_quantidade.isdigit():
            quantidade = int(valor_quantidade)

    return {
        "item_number": item.group(0).upper() if item else None,
        "box_number": caixa.group(0).upper() if caixa else None,
        "quantity": quantidade,
        "texto_ocr": texto_ocr,
    }


resultado = extrair_dados(ARQUIVO_IMAGEM)

print("\n--- TEXTO IDENTIFICADO PELO OCR ---")
print(resultado["texto_ocr"])

print("--- DADOS EXTRAIDOS ---")
print("Item Number:", resultado["item_number"])
print("Box Number:", resultado["box_number"])
print("Quantity:", resultado["quantity"])