import xml.etree.ElementTree as ET
import config
import oracle_utils
import xml_helpers as h
import finalizer  

def get_nome_negocio(nome_tecnico, colunas_banco):
    """Busca o comentário do banco ou usa o dicionário padrão"""
    if nome_tecnico in config.DICIONARIO_NEGOCIO:
        return config.DICIONARIO_NEGOCIO[nome_tecnico]
    info = next((c for c in colunas_banco if c[0].upper() == nome_tecnico), None)
    if info and info[6]:
        return info[6].strip()
    return nome_tecnico

def get_info_banco(nome_tecnico, colunas_banco):
    return next((c for c in colunas_banco if c[0].upper() == nome_tecnico), (nome_tecnico, 'VARCHAR2', 0, 0, 255, 'Y', ''))

def montar_camada_fisica(root, colunas_banco):
    print("[1/5] A montar Original Database...")
    folder = next(f for f in root.iter(h.tag('folder')) if f.find(h.tag('name')).text == "Original Database for Alias")
    
    qs = h.sub(folder, 'querySubject', attrib={'status': 'valid'})
    h.sub(qs, 'name', config.NOME_COGNOS, {'locale': 'pt-br'})
    h.sub(qs, 'lastChanged', config.DATA_HOJE); h.sub(qs, 'lastChangedBy', config.USUARIO)

    v = config.NOME_VIEW.upper()

    mapa_sql = {
        "ID_EVENT": f"{v}.ID_EVENT", "ID_EVENT_TYPE": f"{v}.ID_EVENT_TYPE",
        "DT_HR_EVENT": f"{v}.DT_EVENT DT_HR_EVENT", "DT_EVENT": f"TRUNC({v}.DT_EVENT) DT_EVENT",
        "HR_EVENT": f"TO_CHAR({v}.DT_EVENT, 'HH24:MI:SS') HR_EVENT",
        "DT_HR_PROCESSING": f"{v}.DT_PROCESSING DT_HR_PROCESSING", "DT_PROCESSING": f"TRUNC({v}.DT_PROCESSING) DT_PROCESSING",
        "HR_PROCESSING": f"TO_CHAR({v}.DT_PROCESSING, 'HH24:MI:SS') HR_PROCESSING",
        "NR_EVENT": f"{v}.ID_EVENT NR_EVENT", "QTD_EVENT": f"{v}.ID_EVENT || '-' || {v}.ID_EVENT_TYPE QTD_EVENT"
    }

    # Adicionar VL_EVENT como alias do campo configurado em VL_EVENT_CAMPO, se definido
    campo_vl = getattr(config, 'VL_EVENT_CAMPO', None)
    if campo_vl:
        mapa_sql["VL_EVENT"] = f"{v}.{campo_vl} VL_EVENT"
        print(f"  [*] VL_EVENT -> {campo_vl}")

    nomes_tecnicos = list(mapa_sql.keys())
    sql_parts = [f"{form}" for form in mapa_sql.values()]
    for col in colunas_banco:
        c_name = col[0].upper()
        if c_name not in ["DT_EVENT", "DT_PROCESSING"] and c_name not in nomes_tecnicos:
            nomes_tecnicos.append(c_name)
            sql_parts.append(f"{v}.{c_name}")

    for nome in nomes_tecnicos:
        qi = h.sub(qs, 'queryItem')
        h.sub(qi, 'name', nome, {'locale': 'pt-br'})
        h.sub(qi, 'externalName', nome)
        h.criar_metadados_tecnicos(qi, get_info_banco(nome, colunas_banco), force_attribute=True)

    sql_final = "select\n  " + "\n  , ".join(sql_parts) + f"\nfrom {v}"
    definition = h.sub(qs, 'definition')
    dbq = h.sub(definition, 'dbQuery')
    h.sub(h.sub(dbq, 'sources'), 'dataSourceRef', f"[].[dataSources].[{config.DATA_SOURCE}]")
    h.sub(dbq, 'sql', sql_final, {'type': 'cognos'})
    return nomes_tecnicos

def montar_camada_star(root):
    print("[2/5] A montar Star Schema (Atalhos)...")
    ns = next(n for n in root.iter(h.tag('namespace')) if n.find(h.tag('name')).text == "Star Schema View (Database)")
    
    # Atalho para a tabela física base (alias da Original Database)
    # NOTA: No model - Certo.xml este atalho NÃO existe na Star Schema View
    # Não criar o atalho base EVENT_UNI_CASH_IN aqui

    N = config.NOME_COGNOS  # ex: EVENT_UNI_CASH_IN

    # Atalhos FT_ e DIM_ — apontam para a tabela física na Star Schema View
    # Padrão confirmado no model - Certo.xml: ambos existem com refobj=[SS].[EVENT_UNI_CASH_IN]
    for prefix in [f"FT_{N}", f"DIM_{N}"]:
        sh = h.sub(ns, 'shortcut')
        h.sub(sh, 'name', prefix, {'locale': 'pt-br'})
        h.sub(sh, 'lastChanged', config.DATA_HOJE); h.sub(sh, 'lastChangedBy', config.USUARIO)
        h.sub(sh, 'refobj', f"{config.BASE_SS}.[{N}]")
        h.sub(sh, 'targetType', 'querySubject'); h.sub(sh, 'treatAs', 'alias')

    # Atalhos das 4 pontes — apontam para a tabela física da ponte (ex: ALARMED_RULE)
    # Padrão confirmado no model.xml: refobj = [Star Schema View (Database)].[ALARMED_RULE]
    pontes_fisicas = [
        (f"FT_PT_{N}_x_ALARMED_RULE",          "ALARMED_RULE"),
        (f"FT_PT_{N}_x_ACTION_RECOMMENDATION",  "ACTION_RECOMMENDATION"),
        (f"FT_PT_{N}_x_EVENT_POC_STATE_LAST",   "EVENT_POC_STATE_LAST"),
        (f"FT_PT_{N}_x_EVENT_STATE_LAST",       "EVENT_STATE_LAST"),
    ]
    for nome_atalho, tabela_fisica in pontes_fisicas:
        sh = h.sub(ns, 'shortcut')
        h.sub(sh, 'name', nome_atalho, {'locale': 'pt-br'})
        h.sub(sh, 'lastChanged', config.DATA_HOJE); h.sub(sh, 'lastChangedBy', config.USUARIO)
        h.sub(sh, 'refobj', f"{config.BASE_SS}.[{tabela_fisica}]")
        h.sub(sh, 'targetType', 'querySubject'); h.sub(sh, 'treatAs', 'alias')

def montar_relacionamentos(root):
    NS_URL = "http://www.developer.cognos.com/schemas/bmt/60/12"
    tag = lambda t: f"{{{NS_URL}}}{t}"

    ns = next(
        n for n in root.iter(tag('namespace'))
        if n.find(tag('name')).text == "Star Schema View (Database)"
    )

    # Mapeamento de pontes com seus pares de chave específicos
    # EVENT_POC_STATE_LAST usa colunas diferentes — atenção
    pontes_config = {
        "ALARMED_RULE":          [("ID_EVENT", "ID_EVENT"),
                                  ("ID_EVENT_TYPE", "ID_EVENT_TYPE")],
        "ACTION_RECOMMENDATION": [("ID_EVENT", "ID_EVENT"),
                                  ("ID_EVENT_TYPE", "ID_EVENT_TYPE")],
        "EVENT_POC_STATE_LAST":  [("ID_EVENT", "ID_EVENT_POC"),
                                  ("ID_EVENT_TYPE", "ID_EVENT_POC_TYPE")],
        "EVENT_STATE_LAST":      [("ID_EVENT", "ID_EVENT"),
                                  ("ID_EVENT_TYPE", "ID_EVENT_TYPE")],
    }

    BASE = "[Star Schema View (Database)]"
    FT   = f"FT_{config.NOME_COGNOS}"

    for ponte, pares in pontes_config.items():
        FT_PONTE = f"FT_PT_{config.NOME_COGNOS}_x_{ponte}"

        rel = ET.SubElement(ns, tag('relationship'), {'status': 'valid'})

        # <name> — sem locale, igual ao padrão do model.xml
        name_el = ET.SubElement(rel, tag('name'))
        name_el.text = f"{FT} <--> {FT_PONTE}"

        # <expression> com .tail para os operadores
        # CORRETO: "\n                    =\n                    " entre os refobj
        exp = ET.SubElement(rel, tag('expression'))

        sep_eq  = "\n                    =\n                    "
        sep_and = "\n                    AND\n                    "

        for i, (col_esq, col_dir) in enumerate(pares):
            ref_esq = ET.SubElement(exp, tag('refobj'))
            ref_esq.text = f"{BASE}.[{FT}].[{col_esq}]"
            ref_esq.tail = sep_eq

            ref_dir = ET.SubElement(exp, tag('refobj'))
            ref_dir.text = f"{BASE}.[{FT_PONTE}].[{col_dir}]"
            # Se não é o último par, adiciona " and " para o próximo par
            ref_dir.tail = sep_and if i < len(pares) - 1 else "\n\t\t\t\t"

        # <left> e <right> — MINÚSCULO, sem "End"
        # Valores: "one"/"many"/"zero" — NÃO "1"/"n"/"0"
        left = ET.SubElement(rel, tag('left'))
        left_ref = ET.SubElement(left, tag('refobj'))
        left_ref.text = f"{BASE}.[{FT}]"
        ET.SubElement(left, tag('mincard')).text = "one"
        ET.SubElement(left, tag('maxcard')).text = "many"

        right = ET.SubElement(rel, tag('right'))
        right_ref = ET.SubElement(right, tag('refobj'))
        right_ref.text = f"{BASE}.[{FT_PONTE}]"
        ET.SubElement(right, tag('mincard')).text = "zero"
        ET.SubElement(right, tag('maxcard')).text = "one"
        
def montar_relacionamentos_ft(root):
    """
    Cria os relacionamentos do FT_EVENT_UNI_CASH_IN com as DIMs compartilhadas
    e com as 4 pontes. Nomenclatura e cardinalidades espelhadas do model - Certo.xml.
    
    Padrão do modelo certo:
      - Nome do rel usa "FT_PT_EVENT_UNI_CASH_IN" mas refobj interno = FT_EVENT_UNI_CASH_IN
      - DIMs de data/hora: left=DIM(zero:one), right=FT(one:many)  [direção invertida vs. outros eventos]
      - Pontes: left=PONTE(one:many), right=FT(zero:one)
    """
    ns = next(
        n for n in root.iter(h.tag('namespace'))
        if n.find(h.tag('name')).text == "Star Schema View (Database)"
    )

    BASE = "[Star Schema View (Database)]"
    N    = config.NOME_COGNOS        # EVENT_UNI_CASH_IN
    FT   = f"FT_{N}"                 # FT_EVENT_UNI_CASH_IN  (refobj interno)
    FT_NOME = f"FT_PT_{N}"           # FT_PT_EVENT_UNI_CASH_IN (nome do relacionamento)

    SEP_EQ  = "\n                    =\n                    "
    SEP_AND = "\n                    AND\n                    "
    SEP_FIM = "\n\t\t\t\t"

    def add_rel(name, exp_fn, left_ref, left_cards, right_ref, right_cards):
        rel = ET.SubElement(ns, h.tag('relationship'), {'status': 'valid'})
        ET.SubElement(rel, h.tag('name')).text = name
        exp = ET.SubElement(rel, h.tag('expression'))
        exp_fn(exp)
        left = ET.SubElement(rel, h.tag('left'))
        ET.SubElement(left, h.tag('refobj')).text = left_ref
        ET.SubElement(left, h.tag('mincard')).text = left_cards[0]
        ET.SubElement(left, h.tag('maxcard')).text = left_cards[1]
        right = ET.SubElement(rel, h.tag('right'))
        ET.SubElement(right, h.tag('refobj')).text = right_ref
        ET.SubElement(right, h.tag('mincard')).text = right_cards[0]
        ET.SubElement(right, h.tag('maxcard')).text = right_cards[1]

    def rvs(parent, atalho, tabela_fisica, coluna, tail=None):
        """Cria um refobjViaShortcut com tail opcional."""
        el = ET.SubElement(parent, h.tag('refobjViaShortcut'))
        ET.SubElement(el, h.tag('refobj')).text = f"{BASE}.[{atalho}]"
        ET.SubElement(el, h.tag('refobj')).text = f"{BASE}.[{tabela_fisica}].[{coluna}]"
        if tail is not None:
            el.tail = tail
        return el

    # --- 1. FT <--> Pontes (nome usa FT_PT_, refobj interno usa FT_) ---
    # Padrão do certo: left=FT(one:many), right=PONTE(zero:one)
    # Cada ponte tem colunas específicas de join no lado da ponte

    # FT_PT_EVENT_UNI_CASH_IN <--> FT_PT_..._x_EVENT_POC_STATE_LAST
    # POC usa ID_EVENT_POC e ID_EVENT_POC_TYPE no lado da ponte
    def exp_poc(exp):
        rvs(exp, FT, N, "ID_EVENT",      tail=SEP_EQ)
        rvs(exp, f"FT_PT_{N}_x_EVENT_POC_STATE_LAST", "EVENT_POC_STATE_LAST", "ID_EVENT_POC",      tail=SEP_AND)
        rvs(exp, FT, N, "ID_EVENT_TYPE", tail=SEP_EQ)
        rvs(exp, f"FT_PT_{N}_x_EVENT_POC_STATE_LAST", "EVENT_POC_STATE_LAST", "ID_EVENT_POC_TYPE", tail=SEP_FIM)
    add_rel(f"{FT_NOME} <--> FT_PT_{N}_x_EVENT_POC_STATE_LAST",
            exp_poc,
            f"{BASE}.[{FT}]",                              ("one", "many"),
            f"{BASE}.[FT_PT_{N}_x_EVENT_POC_STATE_LAST]",  ("zero", "one"))

    # FT_PT_..._x_ALARMED_RULE <--> FT_PT_EVENT_UNI_CASH_IN
    def exp_alarmed(exp):
        rvs(exp, f"FT_PT_{N}_x_ALARMED_RULE", "ALARMED_RULE", "ID_EVENT",      tail=SEP_EQ)
        rvs(exp, FT, N, "ID_EVENT",      tail=SEP_AND)
        rvs(exp, f"FT_PT_{N}_x_ALARMED_RULE", "ALARMED_RULE", "ID_EVENT_TYPE", tail=SEP_EQ)
        rvs(exp, FT, N, "ID_EVENT_TYPE", tail=SEP_FIM)
    add_rel(f"FT_PT_{N}_x_ALARMED_RULE <--> {FT_NOME}",
            exp_alarmed,
            f"{BASE}.[FT_PT_{N}_x_ALARMED_RULE]", ("one", "many"),
            f"{BASE}.[{FT}]",                      ("zero", "one"))

    # FT_PT_..._x_ACTION_RECOMMENDATION <--> FT_PT_EVENT_UNI_CASH_IN
    def exp_action(exp):
        rvs(exp, f"FT_PT_{N}_x_ACTION_RECOMMENDATION", "ACTION_RECOMMENDATION", "ID_EVENT",      tail=SEP_EQ)
        rvs(exp, FT, N, "ID_EVENT",      tail=SEP_AND)
        rvs(exp, f"FT_PT_{N}_x_ACTION_RECOMMENDATION", "ACTION_RECOMMENDATION", "ID_EVENT_TYPE", tail=SEP_EQ)
        rvs(exp, FT, N, "ID_EVENT_TYPE", tail=SEP_FIM)
    add_rel(f"FT_PT_{N}_x_ACTION_RECOMMENDATION <--> {FT_NOME}",
            exp_action,
            f"{BASE}.[FT_PT_{N}_x_ACTION_RECOMMENDATION]", ("one", "many"),
            f"{BASE}.[{FT}]",                               ("zero", "one"))

    # FT_PT_EVENT_UNI_CASH_IN <--> FT_PT_..._x_EVENT_STATE_LAST
    def exp_state(exp):
        rvs(exp, FT, N, "ID_EVENT",      tail=SEP_EQ)
        rvs(exp, f"FT_PT_{N}_x_EVENT_STATE_LAST", "EVENT_STATE_LAST", "ID_EVENT",      tail=SEP_AND)
        rvs(exp, FT, N, "ID_EVENT_TYPE", tail=SEP_EQ)
        rvs(exp, f"FT_PT_{N}_x_EVENT_STATE_LAST", "EVENT_STATE_LAST", "ID_EVENT_TYPE", tail=SEP_FIM)
    add_rel(f"{FT_NOME} <--> FT_PT_{N}_x_EVENT_STATE_LAST",
            exp_state,
            f"{BASE}.[{FT}]",                             ("one", "many"),
            f"{BASE}.[FT_PT_{N}_x_EVENT_STATE_LAST]",     ("zero", "one"))

    # --- 2. FT <--> DIMs de data/hora/tipo ---
    # Padrão do certo: cardinalidades INVERTIDAS — DIM(zero:one) left, FT(one:many) right
    # Exceto DIM_HOUR(PROCESSING_EVENT) e DIM_DATE(EVENT) que têm FT left
    dims_ft = [
        # (nome_rel, left_ref, left_cards, right_ref, right_cards, exp_fn_args)
        # DIM_EVENT_TYPE <--> FT  (left=DIM zero:one, right=FT one:many)
        ("DIM_EVENT_TYPE",
         f"{BASE}.[DIM_EVENT_TYPE]",       ("zero", "one"),
         f"{BASE}.[{FT}]",                 ("one",  "many"),
         lambda exp: (
             setattr(ET.SubElement(exp, h.tag('refobj')), 'text',
                     f"{BASE}.[DIM_EVENT_TYPE].[ID_EVENT_TYPE]") or
             setattr(ET.SubElement(exp, h.tag('refobj')), 'tail', SEP_EQ) or
             rvs(exp, FT, N, "ID_EVENT_TYPE", tail=SEP_FIM)
         )),
    ]

    # DIM_EVENT_TYPE — expression simples: refobj direto = refobjViaShortcut
    def exp_dim_event_type(exp):
        r1 = ET.SubElement(exp, h.tag('refobj'))
        r1.text = f"{BASE}.[DIM_EVENT_TYPE].[ID_EVENT_TYPE]"
        r1.tail = SEP_EQ
        rvs(exp, FT, N, "ID_EVENT_TYPE", tail=SEP_FIM)

    add_rel(f"DIM_EVENT_TYPE <--> {FT_NOME}",
            exp_dim_event_type,
            f"{BASE}.[DIM_EVENT_TYPE]", ("zero", "one"),
            f"{BASE}.[{FT}]",           ("one",  "many"))

    # FT_PT <--> DIM_DATE (EVENT)  — left=FT(zero:one), right=DIM(one:many)
    def exp_date_event(exp):
        rvs(exp, FT, N, "DT_EVENT", tail=SEP_EQ)
        rvs(exp, "DIM_DATE (EVENT)", "DIM_DATE", "DAY_ID", tail=SEP_FIM)

    add_rel(f"{FT_NOME} <--> DIM_DATE (EVENT)",
            exp_date_event,
            f"{BASE}.[{FT}]",              ("zero", "one"),
            f"{BASE}.[DIM_DATE (EVENT)]",  ("one",  "many"))

    # DIM_DATE (PROCESSING_EVENT) <--> FT_PT — left=DIM(zero:one), right=FT(one:many)
    def exp_date_proc(exp):
        rvs(exp, "DIM_DATE (PROCESSING_EVENT)", "DIM_DATE", "DAY_ID", tail=SEP_EQ)
        rvs(exp, FT, N, "DT_PROCESSING", tail=SEP_FIM)

    add_rel(f"DIM_DATE (PROCESSING_EVENT) <--> {FT_NOME}",
            exp_date_proc,
            f"{BASE}.[DIM_DATE (PROCESSING_EVENT)]", ("zero", "one"),
            f"{BASE}.[{FT}]",                        ("one",  "many"))

    # DIM_HOUR (EVENT) <--> FT_PT — left=DIM(zero:one), right=FT(one:many)
    def exp_hour_event(exp):
        rvs(exp, "DIM_HOUR (EVENT)", "DIM_HOUR", "ID_HOUR", tail=SEP_EQ)
        rvs(exp, FT, N, "HR_EVENT", tail=SEP_FIM)

    add_rel(f"DIM_HOUR (EVENT) <--> {FT_NOME}",
            exp_hour_event,
            f"{BASE}.[DIM_HOUR (EVENT)]", ("zero", "one"),
            f"{BASE}.[{FT}]",             ("one",  "many"))

    # FT_PT <--> DIM_HOUR (PROCESSING_EVENT) — left=FT(one:many), right=DIM(zero:one)
    def exp_hour_proc(exp):
        rvs(exp, FT, N, "HR_PROCESSING", tail=SEP_EQ)
        rvs(exp, "DIM_HOUR (PROCESSING_EVENT)", "DIM_HOUR", "ID_HOUR", tail=SEP_FIM)

    add_rel(f"{FT_NOME} <--> DIM_HOUR (PROCESSING_EVENT)",
            exp_hour_proc,
            f"{BASE}.[{FT}]",                        ("one",  "many"),
            f"{BASE}.[DIM_HOUR (PROCESSING_EVENT)]", ("zero", "one"))

    # --- 3. FD_UNI_COOPERADO <--> FT_PT (chave NR_CONTA + CD_COOPERATIVA) ---
    def exp_cooperado(exp):
        r1 = ET.SubElement(exp, h.tag('refobj'))
        r1.text = f"{BASE}.[FD_UNI_COOPERADO].[NR_CONTA]"
        r1.tail = SEP_EQ
        rvs(exp, FT, N, "NR_CONTA", tail=SEP_AND)
        r2 = ET.SubElement(exp, h.tag('refobj'))
        r2.text = f"{BASE}.[FD_UNI_COOPERADO].[CD_COOPERATIVA]"
        r2.tail = SEP_EQ
        rvs(exp, FT, N, "CD_COOPERATIVA", tail=SEP_FIM)

    add_rel(f"FD_UNI_COOPERADO <--> {FT_NOME}",
            exp_cooperado,
            f"{BASE}.[FD_UNI_COOPERADO]", ("zero", "one"),
            f"{BASE}.[{FT}]",             ("one",  "many"))


def montar_relacionamentos_pontes_dim(root):
    """
    Cria os 4 relacionamentos das pontes com as DIMs de estado/recomendação:
      - FT_PT_{NOME}_x_EVENT_STATE_LAST      → DIM_EVENT_STATE
          via CD_LABEL_EVENT_STATE = CD_LABEL AND ID_EVENT_TYPE = ID_OWNER_TYPE
      - FT_PT_{NOME}_x_EVENT_POC_STATE_LAST  → DIM_EVENT_POC_STATE
          via CD_LABEL_EVENT_POC_STATE = CD_LABEL AND ID_EVENT_POC_TYPE = ID_OWNER_TYPE
      - FT_PT_{NOME}_x_ACTION_RECOMMENDATION → DIM_APPROVAL_RECOMMENDATION
          via ID_ACTION_TYPE = ID_ACTION_TYPE
      - FT_PT_{NOME}_x_ALARMED_RULE          → DIM_RULE
          via ID_RULE = ID_RULE
    Cardinalidade: ponte (one:many) → DIM (zero:one).
    """
    ns = next(
        n for n in root.iter(h.tag('namespace'))
        if n.find(h.tag('name')).text == "Star Schema View (Database)"
    )

    BASE = "[Star Schema View (Database)]"
    N    = config.NOME_COGNOS  # ex: EVENT_UNI_CASH_IN

    SEP_EQ  = "\n                    =\n                    "
    SEP_AND = "\n                    AND\n                    "

    # Cada entrada: (nome_ponte, tabela_fisica_ponte, dim_direita, pares_col)
    # pares_col: lista de (col_ponte_fisica, col_dim_direta_refobj)
    # Se col_dim_direta_refobj é None → usa refobj direto na DIM
    configs = [
        (
            f"FT_PT_{N}_x_EVENT_STATE_LAST",
            "EVENT_STATE_LAST",
            "DIM_EVENT_STATE",
            [
                ("CD_LABEL_EVENT_STATE", "CD_LABEL"),
                ("ID_EVENT_TYPE",        "ID_OWNER_TYPE"),
            ]
        ),
        (
            f"FT_PT_{N}_x_EVENT_POC_STATE_LAST",
            "EVENT_POC_STATE_LAST",
            "DIM_EVENT_POC_STATE",
            [
                ("CD_LABEL_EVENT_POC_STATE", "CD_LABEL"),
                ("ID_EVENT_POC_TYPE",        "ID_OWNER_TYPE"),
            ]
        ),
        (
            f"FT_PT_{N}_x_ACTION_RECOMMENDATION",
            "ACTION_RECOMMENDATION",
            "DIM_APPROVAL_RECOMMENDATION",
            [
                ("ID_ACTION_TYPE", "ID_ACTION_TYPE"),
            ]
        ),
        (
            f"FT_PT_{N}_x_ALARMED_RULE",
            "ALARMED_RULE",
            "DIM_RULE",
            [
                ("ID_RULE", "ID_RULE"),
            ]
        ),
    ]

    for nome_ponte, tab_fisica_ponte, dim_dir, pares in configs:
        rel = ET.SubElement(ns, h.tag('relationship'), {'status': 'valid'})
        ET.SubElement(rel, h.tag('name')).text = f"{nome_ponte} <--> {dim_dir}"

        exp = ET.SubElement(rel, h.tag('expression'))

        for i, (col_ponte, col_dim) in enumerate(pares):
            # Lado esquerdo: refobjViaShortcut (ponte → tabela física da ponte)
            rvs_esq = ET.SubElement(exp, h.tag('refobjViaShortcut'))
            ET.SubElement(rvs_esq, h.tag('refobj')).text = f"{BASE}.[{nome_ponte}]"
            ET.SubElement(rvs_esq, h.tag('refobj')).text = f"{BASE}.[{tab_fisica_ponte}].[{col_ponte}]"
            rvs_esq.tail = SEP_EQ

            # Lado direito: refobj direto na DIM
            ref_dir = ET.SubElement(exp, h.tag('refobj'))
            ref_dir.text = f"{BASE}.[{dim_dir}].[{col_dim}]"
            ref_dir.tail = SEP_AND if i < len(pares) - 1 else "\n\t\t\t\t"

        # <left> — ponte: one-to-many
        left = ET.SubElement(rel, h.tag('left'))
        ET.SubElement(left, h.tag('refobj')).text = f"{BASE}.[{nome_ponte}]"
        ET.SubElement(left, h.tag('mincard')).text = "one"
        ET.SubElement(left, h.tag('maxcard')).text = "many"

        # <right> — DIM: zero-to-one
        right = ET.SubElement(rel, h.tag('right'))
        ET.SubElement(right, h.tag('refobj')).text = f"{BASE}.[{dim_dir}]"
        ET.SubElement(right, h.tag('mincard')).text = "zero"
        ET.SubElement(right, h.tag('maxcard')).text = "one"


def montar_relacionamentos_dim(root):
    """
    Cria os relacionamentos da DIM_EVENT_UNI_CASH_IN com as tabelas
    de histórico/gerenciamento de caso na Star Schema View (Database).
    
    Padrão do model - Certo.xml:
      - DIM_EVENT_UNI_CASH_IN <--> FT_ALARMED_RULE:
          left=DIM(zero:one), right=FT(one:many)  [invertido vs. outros eventos]
      - FT_PT_CASE_MANAGEMENT_x_EVENT <--> DIM_EVENT_UNI_CASH_IN:
          left=FT_PT(one:many), right=DIM(zero:one)
      - DIM_EVENT_UNI_CASH_IN <--> FT_ACTION_HISTORY: NÃO existe no certo — removido
    """
    ns = next(
        n for n in root.iter(h.tag('namespace'))
        if n.find(h.tag('name')).text == "Star Schema View (Database)"
    )

    BASE = "[Star Schema View (Database)]"
    N   = config.NOME_COGNOS          # EVENT_UNI_CASH_IN
    DIM = f"DIM_{N}"                  # DIM_EVENT_UNI_CASH_IN

    SEP_EQ  = "\n                    =\n                    "
    SEP_AND = "\n                    AND\n                    "
    SEP_FIM = "\n\t\t\t\t"

    def rvs(parent, atalho, tabela_fisica, coluna, tail=None):
        el = ET.SubElement(parent, h.tag('refobjViaShortcut'))
        ET.SubElement(el, h.tag('refobj')).text = f"{BASE}.[{atalho}]"
        ET.SubElement(el, h.tag('refobj')).text = f"{BASE}.[{tabela_fisica}].[{coluna}]"
        if tail is not None:
            el.tail = tail
        return el

    # 1. DIM_EVENT_UNI_CASH_IN <--> FT_ALARMED_RULE
    #    left=DIM(zero:one), right=FT_ALARMED_RULE(one:many)
    rel1 = ET.SubElement(ns, h.tag('relationship'), {'status': 'valid'})
    ET.SubElement(rel1, h.tag('name')).text = f"{DIM} <--> FT_ALARMED_RULE"
    exp1 = ET.SubElement(rel1, h.tag('expression'))
    rvs(exp1, DIM, N, "ID_EVENT",      tail=SEP_EQ)
    rvs(exp1, "FT_ALARMED_RULE", "ALARMED_RULE", "ID_EVENT", tail=SEP_AND)
    rvs(exp1, DIM, N, "ID_EVENT_TYPE", tail=SEP_EQ)
    rvs(exp1, "FT_ALARMED_RULE", "ALARMED_RULE", "ID_EVENT_TYPE", tail=SEP_FIM)
    left1 = ET.SubElement(rel1, h.tag('left'))
    ET.SubElement(left1, h.tag('refobj')).text = f"{BASE}.[{DIM}]"
    ET.SubElement(left1, h.tag('mincard')).text = "zero"
    ET.SubElement(left1, h.tag('maxcard')).text = "one"
    right1 = ET.SubElement(rel1, h.tag('right'))
    ET.SubElement(right1, h.tag('refobj')).text = f"{BASE}.[FT_ALARMED_RULE]"
    ET.SubElement(right1, h.tag('mincard')).text = "one"
    ET.SubElement(right1, h.tag('maxcard')).text = "many"

    # 2. FT_PT_CASE_MANAGEMENT_x_EVENT <--> DIM_EVENT_UNI_CASH_IN
    #    left=FT_PT(one:many), right=DIM(zero:one)
    rel2 = ET.SubElement(ns, h.tag('relationship'), {'status': 'valid'})
    ET.SubElement(rel2, h.tag('name')).text = f"FT_PT_CASE_MANAGEMENT_x_EVENT <--> {DIM}"
    exp2 = ET.SubElement(rel2, h.tag('expression'))
    r1 = ET.SubElement(exp2, h.tag('refobj'))
    r1.text = f"{BASE}.[FT_PT_CASE_MANAGEMENT_x_EVENT].[ID_EVENT]"
    r1.tail = SEP_EQ
    rvs(exp2, DIM, N, "ID_EVENT",      tail=SEP_AND)
    r2 = ET.SubElement(exp2, h.tag('refobj'))
    r2.text = f"{BASE}.[FT_PT_CASE_MANAGEMENT_x_EVENT].[ID_EVENT_TYPE]"
    r2.tail = SEP_EQ
    rvs(exp2, DIM, N, "ID_EVENT_TYPE", tail=SEP_FIM)
    left2 = ET.SubElement(rel2, h.tag('left'))
    ET.SubElement(left2, h.tag('refobj')).text = f"{BASE}.[FT_PT_CASE_MANAGEMENT_x_EVENT]"
    ET.SubElement(left2, h.tag('mincard')).text = "one"
    ET.SubElement(left2, h.tag('maxcard')).text = "many"
    right2 = ET.SubElement(rel2, h.tag('right'))
    ET.SubElement(right2, h.tag('refobj')).text = f"{BASE}.[{DIM}]"
    ET.SubElement(right2, h.tag('mincard')).text = "zero"
    ET.SubElement(right2, h.tag('maxcard')).text = "one"


def _add_model_query(parent):
    """Cria a definition com modelQuery e sql corretos — padrão do Cognos para querySubjects mesclados."""
    definition = h.sub(parent, 'definition')
    mq = h.sub(definition, 'modelQuery')
    sql = h.sub(mq, 'sql', attrib={'type': 'cognos'})
    col = ET.SubElement(sql, h.tag('column'))
    col.text = '*'
    col.tail = '\n                            from\n                            '
    ET.SubElement(sql, h.tag('table'))
    sql.text = 'Select\n                            '


def montar_camada_consolidation(root, nomes_tecnicos, colunas_banco):
    print("[4/5] A montar Consolidation View (DIM e FATO)...")
    ns = next(n for n in root.iter(h.tag('namespace')) if n.find(h.tag('name')).text == "Consolidation View")

    # Verificar quais querySubjects já existem para não duplicar
    nomes_existentes = set()
    for qs in ns.iter(h.tag('querySubject')):
        nome_el = qs.find(h.tag('name'))
        if nome_el is not None:
            nomes_existentes.add(nome_el.text)

    # ------ 1. DIMENSÃO ------
    nome_dim = f"Evento {config.NOME_NEGOCIO}"
    if nome_dim not in nomes_existentes:
        qs_dim = h.sub(ns, 'querySubject', attrib={'status': 'valid'})
        h.sub(qs_dim, 'name', nome_dim, {'locale': 'pt-br'})
        h.sub(qs_dim, 'lastChanged', config.DATA_HOJE)
        h.sub(qs_dim, 'lastChangedBy', config.USUARIO)
        _add_model_query(qs_dim)

        folder_id = h.sub(qs_dim, 'queryItemFolder')
        h.sub(folder_id, 'name', 'Identificadores', {'locale': 'pt-br'})

        for nome_tec in nomes_tecnicos:
            nome_negocio = get_nome_negocio(nome_tec, colunas_banco)
            is_identificador = ("ID_" in nome_tec or "DT_INPUT_" in nome_tec or "DT_OUTPUT_" in nome_tec or "DT_EXTRA_FIELD_" in nome_tec or nome_tec == "NM_SERVER_DECISION")
            qi = h.sub(folder_id if is_identificador else qs_dim, 'queryItem')
            h.sub(qi, 'name', nome_negocio, {'locale': 'pt-br'})
            rvs = h.sub(h.sub(qi, 'expression'), 'refobjViaShortcut')
            h.sub(rvs, 'refobj', f"{config.BASE_SS}.[DIM_{config.NOME_COGNOS}]")
            h.sub(rvs, 'refobj', f"{config.BASE_SS}.[{config.NOME_COGNOS}].[{nome_tec}]")
            # DIM: todos os campos são attribute, a pasta é só organização visual
            h.criar_metadados_tecnicos(qi, get_info_banco(nome_tec, colunas_banco), is_id=False, is_fato=False, force_attribute=True)
    else:
        print(f"  [SKIP] '{nome_dim}' já existe — não duplicando.")

    # ------ 2. FATO (Merge das 5 FTs) ------
    nome_fato = f"Fato Evento {config.NOME_NEGOCIO}"
    if nome_fato not in nomes_existentes:
        qs_fato = h.sub(ns, 'querySubject', attrib={'status': 'valid'})
        h.sub(qs_fato, 'name', nome_fato, {'locale': 'pt-br'})
        h.sub(qs_fato, 'lastChanged', config.DATA_HOJE)
        h.sub(qs_fato, 'lastChangedBy', config.USUARIO)
        _add_model_query(qs_fato)

        # Usar a ordem da column_configuration (banco), filtrada pelas colunas disponíveis.
        # Colunas calculadas no SQL (NR_EVENT, QTD_EVENT, DT_HR_*, HR_*) são
        # inseridas no início/fim conforme padrão dos outros eventos.
        ordem_db = getattr(config, 'ORDEM_COLUNAS_DB', [])
        colunas_disponiveis = set(nomes_tecnicos)

        # Colunas calculadas que ficam no início
        colunas_inicio = [c for c in ["NR_EVENT", "QTD_EVENT"] if c in colunas_disponiveis]
        # Colunas calculadas que ficam no fim (datas/horas derivadas + IDs)
        colunas_fim = [c for c in ["DT_EVENT", "DT_PROCESSING", "DT_HR_EVENT",
                                   "DT_HR_PROCESSING", "HR_EVENT", "HR_PROCESSING",
                                   "ID_EVENT", "ID_EVENT_TYPE", "NM_SERVER_DECISION"]
                       if c in colunas_disponiveis]
        excluir = set(colunas_inicio + colunas_fim)

        # Colunas do banco na ordem do column_configuration, excluindo as calculadas
        colunas_banco_ordenadas = [c for c in ordem_db
                                   if c in colunas_disponiveis and c not in excluir]

        # Colunas disponíveis que não estão no banco (extras do Oracle não mapeadas)
        # são ignoradas para manter paridade com o modelo certo
        ordem_fato = colunas_inicio + colunas_banco_ordenadas + colunas_fim

        # Conjuntos de colunas conforme o manual do Cognos
        # Vão para a pasta Identificadores
        COLS_PASTA_ID = {
            "ID_EVENT", "ID_EVENT_TYPE",
            "DT_HR_EVENT", "DT_EVENT", "HR_EVENT",
            "DT_HR_PROCESSING", "DT_PROCESSING", "HR_PROCESSING",
            "NM_SERVER_DECISION",
            "ID_RULE", "CD_LABEL_EVENT_POC_STATE", "CD_LABEL_EVENT_STATE", "ID_ACTION_TYPE",
        }
        # Padrões de prefixo que também vão para Identificadores
        PREFIXOS_ID = ("DT_EXTRA_FIELD_", "DT_INPUT_", "DT_OUTPUT_")

        # Campos que ficam como identifier dentro da pasta Identificadores
        # Apenas IDs e labels — datas, horas e NM_SERVER_DECISION ficam como attribute
        COLS_IDENTIFIER = {
            "ID_EVENT", "ID_EVENT_TYPE",
            "ID_RULE", "ID_ACTION_TYPE",
            "CD_LABEL_EVENT_STATE", "CD_LABEL_EVENT_POC_STATE",
        }

        # Colunas com usage=fact
        COLS_FACT = {"QTD_EVENT", "VL_EVENT"}

        def get_usage_fato(nome):
            if nome in COLS_IDENTIFIER:
                return 'identifier'
            if nome in COLS_FACT:
                return 'fact'
            return 'attribute'

        def is_identificador(nome):
            return nome in COLS_PASTA_ID or any(nome.startswith(p) for p in PREFIXOS_ID)

        folder_id_fato = h.sub(qs_fato, 'queryItemFolder')
        h.sub(folder_id_fato, 'name', 'Identificadores', {'locale': 'pt-br'})

        for nome_tec in ordem_fato:
            nome_negocio = get_nome_negocio(nome_tec, colunas_banco)
            destino = folder_id_fato if is_identificador(nome_tec) else qs_fato
            qi = h.sub(destino, 'queryItem')
            h.sub(qi, 'name', nome_negocio, {'locale': 'pt-br'})
            rvs = h.sub(h.sub(qi, 'expression'), 'refobjViaShortcut')
            h.sub(rvs, 'refobj', f"{config.BASE_SS}.[FT_{config.NOME_COGNOS}]")
            h.sub(rvs, 'refobj', f"{config.BASE_SS}.[{config.NOME_COGNOS}].[{nome_tec}]")
            # Metadados com usage correto
            info = get_info_banco(nome_tec, colunas_banco)
            usage = get_usage_fato(nome_tec)
            h.criar_metadados_tecnicos(qi, info, is_id=(usage == 'identifier'), is_fato=(usage == 'fact'))

        # B) Colunas das 4 pontes (o Merge inclui essas tabelas)
        pontes = [
            ("ACTION_RECOMMENDATION", "ID_ACTION_TYPE",           "Identificador da Recomendação de Aprovação"),
            ("ALARMED_RULE",          "ID_RULE",                  "Identificador da Regra"),
            ("EVENT_STATE_LAST",      "CD_LABEL_EVENT_STATE",     "Identificador do Status do Evento"),
            ("EVENT_POC_STATE_LAST",  "CD_LABEL_EVENT_POC_STATE", "Identificador do Status do Evento de POC"),
        ]
        for tab_ponte, col_ponte, nome_pt in pontes:
            qi = h.sub(qs_fato, 'queryItem')
            h.sub(qi, 'name', nome_pt, {'locale': 'pt-br'})
            rvs = h.sub(h.sub(qi, 'expression'), 'refobjViaShortcut')
            h.sub(rvs, 'refobj', f"{config.BASE_SS}.[FT_PT_{config.NOME_COGNOS}_x_{tab_ponte}]")
            h.sub(rvs, 'refobj', f"{config.BASE_SS}.[{tab_ponte}].[{col_ponte}]")
            h.criar_metadados_tecnicos(qi, (col_ponte, 'NUMBER' if 'ID' in col_ponte else 'VARCHAR2', 0, 0, 255, 'Y', ''))
    else:
        print(f"  [SKIP] '{nome_fato}' já existe — não duplicando.")

def montar_camada_presentation(root):
    print("[5/5] A montar Presentation View (Atalhos + Namespace do Evento)...")
    pres_view = next(n for n in root.iter(h.tag('namespace')) if n.find(h.tag('name')).text == "Presentation View")

    # Verificar se a namespace do evento já existe
    nome_ns_evento = f"Evento {config.NOME_NEGOCIO}"  # ex: "Evento Cash-In"
    ns_existente = next(
        (n for n in pres_view.iter(h.tag('namespace'))
         if n.find(h.tag('name')) is not None and n.find(h.tag('name')).text == nome_ns_evento),
        None
    )

    if ns_existente is None:
        # Criar a namespace do evento na Presentation View
        ns_evento = h.sub(pres_view, 'namespace')
        h.sub(ns_evento, 'name', nome_ns_evento, {'locale': 'pt-br'})
        h.sub(ns_evento, 'lastChanged', config.DATA_HOJE)
        h.sub(ns_evento, 'lastChangedBy', config.USUARIO)

        # Atalhos padrão de todos os eventos
        atalhos_padrao = [
            (f"Fato Evento {config.NOME_NEGOCIO}", f"[Consolidation View].[Fato Evento {config.NOME_NEGOCIO}]"),
            ("Data do Evento",                     "[Consolidation View].[Data do Evento]"),
            ("Data do Processamento do Evento",    "[Consolidation View].[Data do Processamento do Evento]"),
            ("Hora do Evento",                     "[Consolidation View].[Hora do Evento]"),
            ("Hora do Processamento do Evento",    "[Consolidation View].[Hora do Processamento do Evento]"),
            ("Recomendação de Aprovação",           "[Consolidation View].[Recomendação de Aprovação]"),
            ("Regra",                              "[Consolidation View].[Regra]"),
            ("Status do Evento",                   "[Consolidation View].[Status do Evento]"),
            ("Status do Evento de POC",            "[Consolidation View].[Status do Evento de POC]"),
            ("Tipo de Evento",                     "[Consolidation View].[Tipo de Evento]"),
            (f"Evento {config.NOME_NEGOCIO}",      f"[Consolidation View].[Evento {config.NOME_NEGOCIO}]"),
        ]

        for nome_sh, refobj_sh in atalhos_padrao:
            sh = h.sub(ns_evento, 'shortcut')
            h.sub(sh, 'name', nome_sh, {'locale': 'pt-br'})
            h.sub(sh, 'lastChanged', config.DATA_HOJE)
            h.sub(sh, 'lastChangedBy', config.USUARIO)
            h.sub(sh, 'refobj', refobj_sh)
            h.sub(sh, 'targetType', 'querySubject')

        print(f"  [OK] Namespace '{nome_ns_evento}' criada na Presentation View.")
    else:
        print(f"  [SKIP] Namespace '{nome_ns_evento}' já existe na Presentation View.")

    # Adicionar atalho do Fato nas pastas Ação, Gerenciamento do Caso e Regra Alarmada
    pastas_alvo = ["Ação", "Gerenciamento do Caso", "Regra Alarmada"]
    for folder in pres_view.iter(h.tag('namespace')):
        folder_name = folder.find(h.tag('name')).text
        if folder_name in pastas_alvo:
            # Verificar se o atalho já existe
            ja_existe = any(
                sh.find(h.tag('name')) is not None and
                sh.find(h.tag('name')).text == f"Fato Evento {config.NOME_NEGOCIO}"
                for sh in folder.iter(h.tag('shortcut'))
            )
            if not ja_existe:
                sh = h.sub(folder, 'shortcut')
                h.sub(sh, 'name', f"Fato Evento {config.NOME_NEGOCIO}", {'locale': 'pt-br'})
                h.sub(sh, 'lastChanged', config.DATA_HOJE)
                h.sub(sh, 'lastChangedBy', config.USUARIO)
                h.sub(sh, 'refobj', f"[Consolidation View].[Fato Evento {config.NOME_NEGOCIO}]")
                h.sub(sh, 'targetType', 'querySubject')
                h.sub(sh, 'treatAs', 'alias')

if __name__ == "__main__":
    ET.register_namespace('', config.NS_URL)
    cols_oracle = oracle_utils.buscar_metadados()
    if cols_oracle:
        # Enriquecer o dicionário de negócio com dados da column_configuration
        # e obter a ordem oficial das colunas
        nomes_negocio_db, ordem_colunas_db = oracle_utils.buscar_nomes_negocio()
        if nomes_negocio_db:
            print(f"  [*] {len(nomes_negocio_db)} nomes de negócio carregados da column_configuration.")
            config.DICIONARIO_NEGOCIO.update(nomes_negocio_db)
        # Guardar a ordem para uso na consolidation
        config.ORDEM_COLUNAS_DB = ordem_colunas_db

        tree = ET.parse('model.xml')
        root_xml = tree.getroot()
        
        lista = montar_camada_fisica(root_xml, cols_oracle)
        montar_camada_star(root_xml)
        
        # Relacionamentos FT <--> Pontes + DIMs + FD_UNI_COOPERADO (padrão model certo)
        montar_relacionamentos_ft(root_xml)
        # Relacionamentos Pontes <--> DIMs de estado/recomendação/regra
        montar_relacionamentos_pontes_dim(root_xml)
        # Relacionamentos DIM <--> FTs de histórico/caso (chave composta)
        montar_relacionamentos_dim(root_xml)
        
        montar_camada_consolidation(root_xml, lista, cols_oracle)
        montar_camada_presentation(root_xml)
        
        finalizer.finalizar_xml(root_xml)