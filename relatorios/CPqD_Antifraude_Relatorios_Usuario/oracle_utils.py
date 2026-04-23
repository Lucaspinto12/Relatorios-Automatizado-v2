import oracledb
import config

def buscar_metadados():
    print(f"[*] Extraindo metadados e COMENTÁRIOS do Oracle para {config.NOME_VIEW}...")
    try:
        conn = oracledb.connect(user=config.USER, password=config.PASS, dsn=config.DSN)
        cursor = conn.cursor()
        # Join com ALL_COL_COMMENTS para pegar as descrições
        query = f"""
            SELECT c.COLUMN_NAME, c.DATA_TYPE, c.DATA_PRECISION, c.DATA_SCALE, c.CHAR_LENGTH, c.NULLABLE, m.COMMENTS
            FROM ALL_TAB_COLUMNS c
            LEFT JOIN ALL_COL_COMMENTS m ON c.TABLE_NAME = m.TABLE_NAME AND c.COLUMN_NAME = m.COLUMN_NAME
            WHERE c.TABLE_NAME = '{config.NOME_VIEW.upper()}' 
            ORDER BY c.COLUMN_ID
        """
        cursor.execute(query)
        dados = cursor.fetchall()
        conn.close()
        return dados
    except Exception as e:
        print(f"Erro Oracle: {e}")
        return None

def buscar_nomes_negocio():
    """
    Busca os nomes de negócio e a ORDEM das colunas na tabela column_configuration,
    usando o nome da tabela configurado em NOME_COGNOS.
    Retorna:
      - dict {COLUMN_NAME: DS_COLUMN}  (nomes de negócio)
      - list [COLUMN_NAME, ...]        (ordem por ID_COLUMN_CONFIGURATION)
    """
    print(f"[*] Buscando nomes de negócio em column_configuration para {config.NOME_COGNOS}...")
    try:
        conn = oracledb.connect(user=config.USER, password=config.PASS, dsn=config.DSN)
        cursor = conn.cursor()
        query = """
            SELECT cc.NM_COLUMN, cc.DS_COLUMN
            FROM column_configuration cc
            WHERE cc.id_table_configuration IN (
                SELECT tc.id_table_configuration
                FROM table_configuration tc
                WHERE tc.NM_TABLE_CONFIGURATION = :nome_tabela
            )
            ORDER BY cc.ID_COLUMN_CONFIGURATION
        """
        cursor.execute(query, nome_tabela=config.NOME_COGNOS.upper())
        rows = cursor.fetchall()
        conn.close()
        nomes   = {row[0].upper(): row[1] for row in rows if row[1]}
        ordem   = [row[0].upper() for row in rows]
        return nomes, ordem
    except Exception as e:
        print(f"  [AVISO] Não foi possível buscar column_configuration: {e}")
        return {}, []