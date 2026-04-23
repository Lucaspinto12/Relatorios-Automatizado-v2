import oracledb
import xml.etree.ElementTree as ET
import datetime

# =================================================================
# CONFIGURAÇÕES
# =================================================================
USER          = "SAFPOC542_SCH"
PASS          = "SAFPOC542_SCH"
DSN           = "ocipgd01.aquarius.cpqd.com.br:1521/bd119i1"
NOME_VIEW     = "VW_EVENT_UNI_CASH_IN"
NOME_COGNOS   = "EVENT_UNI_CASH_IN"
NOME_NEGOCIO  = "Cash-In"
DATA_SOURCE   = "SAFO_UNICRED"
CD_EVENT_TYPE = "CASHIN"
CAMPO_ORIGEM_VL_EVENT = "VL_OPERACAO"   # None se não tiver valor
CAMPOS_IDENTIFICADORES = ['ID_EVENT', 'ID_EVENT_TYPE', 'NR_EVENT', 'NM_SERVER_DECISION']

NS_URL = "http://www.developer.cognos.com/schemas/bmt/60/12"

def tag(t):
    return f"{{{NS_URL}}}{t}"

def sub(parent, tagname, text=None, attrib=None):
    """SubElement com texto e atributos opcionais."""
    el = ET.SubElement(parent, tag(tagname), attrib or {})
    if text is not None:
        el.text = text
    return el

def now():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def find_ns(root, name):
    for n in root.iter(tag('namespace')):
        el = n.find(tag('name'))
        if el is not None and el.text == name:
            return n
    raise ValueError(f"Namespace '{name}' não encontrado")

def find_folder(root, name):
    for f in root.iter(tag('folder')):
        el = f.find(tag('name'))
        if el is not None and el.text == name:
            return f
    raise ValueError(f"Folder '{name}' não encontrado")

def criar_shortcut_star(parent, nome, refobj_path):
    sh = ET.SubElement(parent, tag('shortcut'))
    sub(sh, 'name', nome, {'locale': 'pt-br'})
    sub(sh, 'lastChanged', now())
    sub(sh, 'refobj', refobj_path)
    sub(sh, 'targetType', 'querySubject')
    sub(sh, 'treatAs', 'alias')
    return sh

def criar_relacionamento(star_schema, nome_rel, sh_esq, sh_dir, pares):
    rel = ET.SubElement(star_schema, tag('relationship'), {'status': 'valid'})
    sub(rel, 'name', nome_rel)

    exp = ET.SubElement(rel, tag('expression'))
    base = "[Star Schema View (Database)]"

    for i, (col_esq, col_dir) in enumerate(pares):
        ref_esq = sub(exp, 'refobj', f"{base}.[{sh_esq}].[{col_esq}]")
        ref_esq.tail = "\n                    =\n                    "

        ref_dir = sub(exp, 'refobj', f"{base}.[{sh_dir}].[{col_dir}]")
        if i < len(pares) - 1:
            ref_dir.tail = "\n                    AND\n                    "

    left = ET.SubElement(rel, tag('left'))
    sub(left, 'refobj', f"{base}.[{sh_esq}]")
    sub(left, 'mincard', 'one')
    sub(left, 'maxcard', 'many')

    right = ET.SubElement(rel, tag('right'))
    sub(right, 'refobj', f"{base}.[{sh_dir}]")
    sub(right, 'mincard', 'zero')
    sub(right, 'maxcard', 'one')

def criar_queryitem_consolidation(parent, nome_exib, sh_via, orig_col, col,
                                   usage, regular_agg, semi_agg='unsupported'):
    qi = ET.SubElement(parent, tag('queryItem'))
    sub(qi, 'name', nome_exib, {'locale': 'pt-br'})
    sub(qi, 'lastChanged', now())

    exp = ET.SubElement(qi, tag('expression'))
    rvs = ET.SubElement(exp, tag('refobjViaShortcut'))
    sub(rvs, 'refobj', f"[Star Schema View (Database)].[{sh_via}]")
    sub(rvs, 'refobj', f"[Star Schema View (Database)].[{orig_col}].[{col}]")

    sub(qi, 'usage', usage)

    sub(qi, 'datatype', 'characterLength16')
    sub(qi, 'precision', '16')
    sub(qi, 'scale', '0')
    sub(qi, 'size', '32')
    sub(qi, 'nullable', 'true')
    sub(qi, 'regularAggregate', regular_agg)
    sub(qi, 'semiAggregate', semi_agg)
    sub(qi, 'collationSequenceName', 'pt-br')
    sub(qi, 'collationSequenceLevel', '1')

    return qi

def executar_automacao():
    print(f"[*] Conectando ao Oracle — {CD_EVENT_TYPE}...")
    try:
        conn   = oracledb.connect(user=USER, password=PASS, dsn=DSN)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS "
            "WHERE TABLE_NAME = :1 ORDER BY COLUMN_ID",
            [NOME_VIEW.upper()]
        )
        colunas_banco = [row[0].upper() for row in cursor.fetchall()]

        cursor.execute(
            "SELECT NM_COLUMN, DS_COLUMN FROM column_configuration "
            "WHERE id_table_configuration = ("
            "  SELECT id_table_configuration FROM event_type "
            "  WHERE cd_event_type = :1)",
            [CD_EVENT_TYPE]
        )
        TRADUCOES = {
            row[0].upper().strip(): row[1].strip()
            for row in cursor.fetchall() if row[0] and row[1]
        }
        conn.close()
    except Exception as e:
        print(f"[!] Erro Oracle: {e}")
        return

    ET.register_namespace('', NS_URL)
    tree = ET.parse('model.xml')
    root = tree.getroot()

    original_db = find_folder(root, "Original Database for Alias")
    star_schema = find_ns(root, "Star Schema View (Database)")
    consolidation = find_ns(root, "Consolidation View")
    presentation  = find_ns(root, "Presentation View")

    v = NOME_VIEW.upper()

    # PASSO 1: Físico
    campos_padrao = [
        ("ID_EVENT", f"{v}.ID_EVENT"),
        ("ID_EVENT_TYPE", f"{v}.ID_EVENT_TYPE"),
        ("DT_HR_EVENT", f"{v}.DT_EVENT DT_HR_EVENT"),
        ("DT_EVENT", f"TRUNC({v}.DT_EVENT) DT_EVENT"),
        ("HR_EVENT", f"TO_CHAR({v}.DT_EVENT, 'HH24:MI:SS') HR_EVENT"),
        ("DT_HR_PROCESSING", f"{v}.DT_PROCESSING DT_HR_PROCESSING"),
        ("DT_PROCESSING", f"TRUNC({v}.DT_PROCESSING) DT_PROCESSING"),
        ("HR_PROCESSING", f"TO_CHAR({v}.DT_PROCESSING, 'HH24:MI:SS') HR_PROCESSING"),
        ("NR_EVENT", f"{v}.ID_EVENT NR_EVENT"),
        ("QTD_EVENT", f"{v}.ID_EVENT || '-' || {v}.ID_EVENT_TYPE QTD_EVENT"),
    ]
    if CAMPO_ORIGEM_VL_EVENT:
        campos_padrao.append(("VL_EVENT", f"{v}.{CAMPO_ORIGEM_VL_EVENT} VL_EVENT"))

    nomes_finais = [p[0] for p in campos_padrao]
    sql_linhas   = [p[1] for p in campos_padrao]

    for col in colunas_banco:
        if col not in nomes_finais and col not in ['DT_EVENT', 'DT_PROCESSING']:
            nomes_finais.append(col)
            sql_linhas.append(f"{v}.{col}")

    sql_text = "\nselect\n  " + "\n  , ".join(sql_linhas) + f"\nfrom\n  {v}\n"

    qs_orig = ET.SubElement(original_db, tag('querySubject'), {'status': 'valid'})
    sub(qs_orig, 'name', NOME_COGNOS, {'locale': 'pt-br'})
    sub(qs_orig, 'lastChanged', now())

    for nc in nomes_finais:
        qi = ET.SubElement(qs_orig, tag('queryItem'))
        sub(qi, 'name', nc, {'locale': 'pt-br'})
        sub(qi, 'externalName', nc)
        sub(qi, 'usage', 'attribute')

    defn = ET.SubElement(qs_orig, tag('definition'))
    dbq  = ET.SubElement(defn, tag('dbQuery'))
    srcs = ET.SubElement(dbq, tag('sources'))
    sub(srcs, 'dataSourceRef', f"[].[dataSources].[{DATA_SOURCE}]")
    sql_el = ET.SubElement(dbq, tag('sql'), {'type': 'cognos'})
    sql_el.text = sql_text
    sub(dbq, 'tableType', 'table')

    # PASSO 2: Shortcuts
    base_ss = "[Star Schema View (Database)]"
    criar_shortcut_star(star_schema, NOME_COGNOS, f"{base_ss}.[Original Database for Alias].[{NOME_COGNOS}]")
    criar_shortcut_star(star_schema, f"DIM_{NOME_COGNOS}", f"{base_ss}.[{NOME_COGNOS}]")
    criar_shortcut_star(star_schema, f"FT_{NOME_COGNOS}",  f"{base_ss}.[{NOME_COGNOS}]")

    fts_ponte = ["ALARMED_RULE", "ACTION_RECOMMENDATION", "EVENT_POC_STATE_LAST", "EVENT_STATE_LAST"]
    for ft in fts_ponte:
        criar_shortcut_star(star_schema, f"FT_PT_{NOME_COGNOS}_x_{ft}", f"{base_ss}.[{ft}]")

    # PASSO 3: Relacionamentos (As 13 relações corretas)
    add = lambda nome, esq, dir_, pares: criar_relacionamento(star_schema, nome, esq, dir_, pares)
    FT = f"FT_{NOME_COGNOS}"
    NC = NOME_COGNOS

    add(f"{FT} <--> FT_PT_{NC}_x_ALARMED_RULE", FT, f"FT_PT_{NC}_x_ALARMED_RULE", [("ID_EVENT", "ID_EVENT"), ("ID_EVENT_TYPE", "ID_EVENT_TYPE")])
    add(f"{FT} <--> FT_PT_{NC}_x_ACTION_RECOMMENDATION", FT, f"FT_PT_{NC}_x_ACTION_RECOMMENDATION", [("ID_EVENT", "ID_EVENT"), ("ID_EVENT_TYPE", "ID_EVENT_TYPE")])
    add(f"{FT} <--> FT_PT_{NC}_x_EVENT_POC_STATE_LAST", FT, f"FT_PT_{NC}_x_EVENT_POC_STATE_LAST", [("ID_EVENT", "ID_EVENT_POC"), ("ID_EVENT_TYPE", "ID_EVENT_POC_TYPE")])
    add(f"{FT} <--> FT_PT_{NC}_x_EVENT_STATE_LAST", FT, f"FT_PT_{NC}_x_EVENT_STATE_LAST", [("ID_EVENT", "ID_EVENT"), ("ID_EVENT_TYPE", "ID_EVENT_TYPE")])
    add(f"{FT} <--> DIM_HOUR (PROCESSING_EVENT)", FT, "DIM_HOUR (PROCESSING_EVENT)", [("HR_PROCESSING", "ID_HOUR")])
    add(f"{FT} <--> DIM_HOUR (EVENT)", FT, "DIM_HOUR (EVENT)", [("HR_EVENT", "ID_HOUR")])
    add(f"{FT} <--> DIM_DATE (PROCESSING_EVENT)", FT, "DIM_DATE (PROCESSING_EVENT)", [("DT_PROCESSING", "DAY_ID")])
    add(f"{FT} <--> DIM_DATE (EVENT)", FT, "DIM_DATE (EVENT)", [("DT_EVENT", "DAY_ID")])
    add(f"{FT} <--> DIM_EVENT_TYPE", FT, "DIM_EVENT_TYPE", [("ID_EVENT_TYPE", "ID_EVENT_TYPE")])
    add(f"FT_PT_{NC}_x_ALARMED_RULE <--> DIM_RULE", f"FT_PT_{NC}_x_ALARMED_RULE", "DIM_RULE", [("ID_RULE", "ID_RULE")])
    add(f"FT_PT_{NC}_x_ACTION_RECOMMENDATION <--> DIM_APPROVAL_RECOMMENDATION", f"FT_PT_{NC}_x_ACTION_RECOMMENDATION", "DIM_APPROVAL_RECOMMENDATION", [("ID_ACTION_TYPE", "ID_ACTION_TYPE")])
    add(f"FT_PT_{NC}_x_EVENT_POC_STATE_LAST <--> DIM_EVENT_POC_STATE", f"FT_PT_{NC}_x_EVENT_POC_STATE_LAST", "DIM_EVENT_POC_STATE", [("CD_LABEL_EVENT_POC_STATE", "CD_LABEL"), ("ID_EVENT_POC_TYPE", "ID_OWNER_TYPE")])
    add(f"FT_PT_{NC}_x_EVENT_STATE_LAST <--> DIM_EVENT_STATE", f"FT_PT_{NC}_x_EVENT_STATE_LAST", "DIM_EVENT_STATE", [("CD_LABEL_EVENT_STATE", "CD_LABEL"), ("ID_EVENT_TYPE", "ID_OWNER_TYPE")])

    # PASSO 4: Consolidation
    MAP_PONTES = {
        "ID_RULE": (f"FT_PT_{NC}_x_ALARMED_RULE", "ALARMED_RULE"),
        "CD_LABEL_EVENT_STATE": (f"FT_PT_{NC}_x_EVENT_STATE_LAST", "EVENT_STATE_LAST"),
        "CD_LABEL_EVENT_POC_STATE": (f"FT_PT_{NC}_x_EVENT_POC_STATE_LAST", "EVENT_POC_STATE_LAST"),
        "ID_ACTION_TYPE": (f"FT_PT_{NC}_x_ACTION_RECOMMENDATION", "ACTION_RECOMMENDATION"),
    }

    def criar_qs_consolidation(nome_prefixo, atalho_star):
        nome_completo = f"{nome_prefixo} Evento {NOME_NEGOCIO}"
        qs = ET.SubElement(consolidation, tag('querySubject'), {'status': 'valid'})
        sub(qs, 'name', nome_completo, {'locale': 'pt-br'})
        sub(qs, 'lastChanged', now())
        defn = ET.SubElement(qs, tag('definition'))
        mq   = ET.SubElement(defn, tag('modelQuery'))
        sql_node = ET.SubElement(mq, tag('sql'), {'type': 'cognos'})
        sql_node.text = "\nSelect\n"
        sub(sql_node, 'column', "*").tail = "\nfrom\n"
        sub(sql_node, 'table')
        pasta_id = ET.SubElement(qs, tag('queryItemFolder'))
        sub(pasta_id, 'name', 'Identificadores', {'locale': 'pt-br'})
        for col in nomes_finais:
            is_id = (col in CAMPOS_IDENTIFICADORES or col.startswith('DT_EXTRA_') or col.startswith('DT_INPUT_') or col.startswith('DT_OUTPUT_'))
            container = pasta_id if is_id else qs
            nome_exib = "Valor do Evento" if col == "VL_EVENT" else "Quantidade de Eventos" if col == "QTD_EVENT" else TRADUCOES.get(col, col)
            sh_via, orig_col = MAP_PONTES[col] if col in MAP_PONTES else (atalho_star, NOME_COGNOS)
            is_fact = col == "QTD_EVENT" or col.startswith("VL_")
            reg_agg = ("countDistinct" if col == "QTD_EVENT" else "sum") if is_fact else ("count" if (col.startswith('ID_') or col.startswith('NR_')) else "unsupported")
            criar_queryitem_consolidation(container, nome_exib, sh_via, orig_col, col, "fact" if is_fact else "attribute", reg_agg)
        return nome_completo

    nome_dim  = criar_qs_consolidation("Dimensão", f"DIM_{NOME_COGNOS}")
    nome_fato = criar_qs_consolidation("Fato",     f"FT_{NOME_COGNOS}")

    # PASSO 5: Presentation
    ns_pres = ET.SubElement(presentation, tag('namespace'))
    sub(ns_pres, 'name', f"Evento {NOME_NEGOCIO}", {'locale': 'pt-br'})
    sub(ns_pres, 'lastChanged', now())
    def criar_sh_pres(n, r):
        sh = ET.SubElement(ns_pres, tag('shortcut'))
        sub(sh, 'name', n, {'locale': 'pt-br'})
        sub(sh, 'lastChanged', now())
        sub(sh, 'refobj', f"[Consolidation View].[{r}]")
        sub(sh, 'targetType', 'querySubject')

    criar_sh_pres(nome_fato, nome_fato)
    criar_sh_pres(nome_dim,  nome_dim)
    for dim in ["Data do Evento", "Data do Processamento do Evento", "Hora do Evento", "Hora do Processamento do Evento", "Recomendação de Aprovação", "Regra", "Status do Evento", "Status do Evento de POC", "Tipo de Evento"]:
        criar_sh_pres(dim, dim)

    # ================================================================
    # SALVAR COM LÓGICA DE &APOS; (Substituindo apenas na string final)
    # ================================================================
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    # Substitui aspas simples por entidade para evitar erros em expressões NVL/Strings
    xml_final = xml_str.replace("'", "&apos;")
    
    output = f"model_final.xml"
    with open(output, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        f.write(xml_final)
    
    print(f"\n[SUCESSO] {output} gerado com as 13 relações e aspas tratadas.")

if __name__ == "__main__":
    executar_automacao()