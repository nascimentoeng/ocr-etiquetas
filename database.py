import libsql


class RegistroDuplicadoError(Exception):
    pass


def conectar_banco(database_url, auth_token):
    conexao = libsql.connect(
        database_url,
        auth_token=auth_token,
    )

    return conexao


def criar_tabela(database_url, auth_token):
    conexao = conectar_banco(
        database_url,
        auth_token,
    )

    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS registros_etiquetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            data_registro TEXT NOT NULL,
            codigo_cliente TEXT NOT NULL,
            item_number TEXT NOT NULL,
            box_number TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conexao.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_registro_unico_diario
        ON registros_etiquetas (
            codigo_cliente,
            box_number,
            data_registro
        )
        """
    )

    conexao.commit()
    conexao.close()


def verificar_registro_existente(
    database_url,
    auth_token,
    codigo_cliente,
    box_number,
    data_registro,
):
    conexao = conectar_banco(
        database_url,
        auth_token,
    )

    cursor = conexao.execute(
        """
        SELECT id
        FROM registros_etiquetas
        WHERE codigo_cliente = ?
          AND box_number = ?
          AND data_registro = ?
        LIMIT 1
        """,
        (
            codigo_cliente,
            box_number,
            data_registro,
        ),
    )

    registro = cursor.fetchone()
    conexao.close()

    return registro is not None


def salvar_registro(
    database_url,
    auth_token,
    data_hora,
    data_registro,
    codigo_cliente,
    item_number,
    box_number,
    quantity,
):
    codigo_cliente = codigo_cliente.strip().upper()
    item_number = item_number.strip().upper()
    box_number = box_number.strip().upper()

    registro_existente = verificar_registro_existente(
        database_url=database_url,
        auth_token=auth_token,
        codigo_cliente=codigo_cliente,
        box_number=box_number,
        data_registro=data_registro,
    )

    if registro_existente:
        raise RegistroDuplicadoError(
            "Este Box Number já foi registrado hoje "
            f"para o Código Cliente {codigo_cliente}."
        )

    conexao = conectar_banco(
        database_url,
        auth_token,
    )

    try:
        cursor = conexao.execute(
            """
            INSERT INTO registros_etiquetas (
                data_hora,
                data_registro,
                codigo_cliente,
                item_number,
                box_number,
                quantity
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data_hora,
                data_registro,
                codigo_cliente,
                item_number,
                box_number,
                quantity,
            ),
        )

        conexao.commit()
        registro_id = cursor.lastrowid

    except Exception as erro:
        conexao.close()

        if "UNIQUE constraint failed" in str(erro):
            raise RegistroDuplicadoError(
                "Este Box Number já foi registrado hoje "
                f"para o Código Cliente {codigo_cliente}."
            ) from erro

        raise

    conexao.close()

    return registro_id


def listar_registros(
    database_url,
    auth_token,
):
    conexao = conectar_banco(
        database_url,
        auth_token,
    )

    cursor = conexao.execute(
        """
        SELECT
            id,
            data_hora,
            codigo_cliente,
            item_number,
            box_number,
            quantity,
            criado_em
        FROM registros_etiquetas
        ORDER BY id DESC
        """
    )

    colunas = [
        "id",
        "data_hora",
        "codigo_cliente",
        "item_number",
        "box_number",
        "quantity",
        "criado_em",
    ]

    registros = [
        dict(zip(colunas, linha))
        for linha in cursor.fetchall()
    ]

    conexao.close()

    return registros