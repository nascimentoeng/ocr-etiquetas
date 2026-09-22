import re

import cv2
import pytesseract


PREFIXOS_ITEM = (
    "KC",
    "BD",
    "PK",
    "BP",
    "BF",
)

PREFIXOS_BOX = (
    "WG",
    "RJ",
    "SZ",
)


def carregar_imagem(caminho_imagem):
    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        raise FileNotFoundError(
            f"Nao foi possivel abrir a imagem: {caminho_imagem}"
        )

    return imagem


def redimensionar_imagem(imagem, limite=2400):
    altura, largura = imagem.shape[:2]
    maior_dimensao = max(altura, largura)

    if maior_dimensao <= limite:
        return imagem

    escala = limite / maior_dimensao

    return cv2.resize(
        imagem,
        None,
        fx=escala,
        fy=escala,
        interpolation=cv2.INTER_AREA,
    )


def criar_regioes(imagem):
    altura, largura = imagem.shape[:2]

    return {
        "imagem_completa": imagem,
        "parte_superior": imagem[
            0:int(altura * 0.70),
            0:largura,
        ],
        "parte_superior_central": imagem[
            int(altura * 0.05):int(altura * 0.65),
            int(largura * 0.03):int(largura * 0.97),
        ],
    }


def criar_variacoes(imagem):
    cinza = cv2.cvtColor(
        imagem,
        cv2.COLOR_BGR2GRAY,
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    contraste = clahe.apply(cinza)

    ampliada = cv2.resize(
        contraste,
        None,
        fx=1.5,
        fy=1.5,
        interpolation=cv2.INTER_CUBIC,
    )

    suavizada = cv2.GaussianBlur(
        ampliada,
        (3, 3),
        0,
    )

    binaria = cv2.adaptiveThreshold(
        suavizada,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )

    return {
        "cinza": cinza,
        "contraste": contraste,
        "ampliada": ampliada,
        "binaria": binaria,
    }


def executar_ocr(imagem):
    textos = []

    for psm in (6, 11, 12):
        texto = pytesseract.image_to_string(
            imagem,
            config=f"--oem 3 --psm {psm}",
        )

        if texto.strip():
            textos.append(texto)

    return "\n".join(textos)


def coletar_texto_ocr(imagem):
    textos = []
    regioes = criar_regioes(imagem)

    for nome_regiao, regiao in regioes.items():
        variacoes = criar_variacoes(regiao)

        for nome_variacao, variacao in variacoes.items():
            texto = executar_ocr(variacao)

            if texto.strip():
                textos.append(
                    f"\n### {nome_regiao} - "
                    f"{nome_variacao}\n{texto}"
                )

    return "\n".join(textos)


def limpar_texto(texto):
    texto = texto.upper()

    substituicoes = {
        "|": "I",
        "§": "S",
        "$": "S",
        "’": "",
        "'": "",
        '"': "",
    }

    for caractere, substituto in substituicoes.items():
        texto = texto.replace(
            caractere,
            substituto,
        )

    return texto


def localizar_item_number(texto):
    prefixos = "|".join(PREFIXOS_ITEM)

    padrao = (
        rf"(?<![A-Z0-9])"
        rf"({prefixos})[O0-9]{{5,10}}"
        rf"(?![A-Z0-9])"
    )

    encontrados = re.findall(
        padrao,
        texto,
        re.IGNORECASE,
    )

    correspondencias = re.finditer(
        padrao,
        texto,
        re.IGNORECASE,
    )

    for correspondencia in correspondencias:
        valor = correspondencia.group(0).upper()

        prefixo = valor[:2]
        numeros = valor[2:].replace("O", "0")
        valor_normalizado = prefixo + numeros

        if numeros.isdigit():
            return valor_normalizado, "alta"

    if encontrados:
        return encontrados[0].upper(), "media"

    return None, "baixa"


def localizar_box_number(texto):
    prefixos = "|".join(PREFIXOS_BOX)

    padrao_direto = (
        rf"(?<![A-Z0-9])"
        rf"({prefixos})[O0-9]{{6,10}}"
        rf"(?![A-Z0-9])"
    )

    correspondencias = re.finditer(
        padrao_direto,
        texto,
        re.IGNORECASE,
    )

    for correspondencia in correspondencias:
        valor = correspondencia.group(0).upper()

        prefixo = valor[:2]
        numeros = valor[2:].replace("O", "0")
        valor_normalizado = prefixo + numeros

        if numeros.isdigit():
            return valor_normalizado, "alta"

    padrao_contexto = re.compile(
        r"BOX\s*NUMBER\s*[:\-]?\s*"
        r"[^A-Z0-9]{0,8}"
        r"([A-Z0-9$§}]{7,14})",
        re.IGNORECASE,
    )

    contexto = padrao_contexto.search(texto)

    if contexto:
        valor = contexto.group(1).upper()
        valor = valor.replace("$", "S")
        valor = valor.replace("§", "S")
        valor = valor.replace("}", "")

        for prefixo in PREFIXOS_BOX:
            posicao = valor.find(prefixo)

            if posicao >= 0:
                candidato = valor[posicao:]
                candidato = re.sub(
                    r"[^A-Z0-9]",
                    "",
                    candidato,
                )

                return candidato, "media"

    return None, "baixa"

def localizar_quantidade(texto):
    from collections import Counter

    candidatos = []

    padroes = [
        r"QUANTITY[\s:.,\-]*([0-9AO]{1,4})",
        r"\b([0-9AO]{1,4})[\s.]*P[CE]\b",
    ]

    for padrao in padroes:
        correspondencias = re.finditer(
            padrao,
            texto,
            re.IGNORECASE,
        )

        for correspondencia in correspondencias:
            valor = correspondencia.group(1).upper()

            valor = valor.replace("A", "4")
            valor = valor.replace("O", "0")

            if valor.isdigit():
                quantidade = int(valor)

                if 0 < quantidade <= 10000:
                    candidatos.append(quantidade)

    if candidatos:
        contagem = Counter(candidatos)
        quantidade, repeticoes = contagem.most_common(1)[0]

        if repeticoes >= 2:
            return quantidade, "alta"

        return quantidade, "media"

    return None, "baixa"

def extrair_dados(caminho_imagem):
    imagem = carregar_imagem(caminho_imagem)
    imagem = redimensionar_imagem(imagem)

    texto_ocr = coletar_texto_ocr(imagem)
    texto_limpo = limpar_texto(texto_ocr)

    item_number, confianca_item = localizar_item_number(
        texto_limpo
    )

    box_number, confianca_box = localizar_box_number(
        texto_limpo
    )

    quantity, confianca_quantidade = localizar_quantidade(
        texto_limpo
    )

    return {
        "item_number": item_number,
        "box_number": box_number,
        "quantity": quantity,
        "confianca": {
            "item_number": confianca_item,
            "box_number": confianca_box,
            "quantity": confianca_quantidade,
        },
        "texto_ocr": texto_ocr,
    }


if __name__ == "__main__":
    caminho = "IMG-20260811-WA0040.jpg"
    resultado = extrair_dados(caminho)

    print("\n--- DADOS EXTRAIDOS ---")
    print("Item Number:", resultado["item_number"])
    print("Box Number:", resultado["box_number"])
    print("Quantity:", resultado["quantity"])

    print("\n--- CONFIANCA ---")
    print(
        "Item Number:",
        resultado["confianca"]["item_number"],
    )
    print(
        "Box Number:",
        resultado["confianca"]["box_number"],
    )
    print(
        "Quantity:",
        resultado["confianca"]["quantity"],
    )

    print("\n--- TEXTO OCR ---")
    print(resultado["texto_ocr"])