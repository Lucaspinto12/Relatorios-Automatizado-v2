import config
import xml.etree.ElementTree as ET

def tag(t): 
    return f"{{{config.NS_URL}}}{t}"

def sub(parent, tagname, text=None, attrib=None):
    el = ET.SubElement(parent, tag(tagname), attrib or {})
    if text is not None:
        el.text = str(text) # O finalizer.py vai tratar as aspas com segurança
    return el

def criar_metadados_tecnicos(qi, info_banco, is_id=False, is_fato=False, force_attribute=False):
    # info_banco: (NAME, TYPE, PREC, SCALE, LEN, NULL, COMMENT)
    name, o_type, prec, scale, length, null, _ = info_banco
    o_type = o_type.upper()
    
    sub(qi, 'lastChanged', config.DATA_HOJE)
    sub(qi, 'lastChangedBy', config.USUARIO)
    
    # Usage — force_attribute=True usado na Original Database (padrão dos eventos UNI)
    if force_attribute:
        usage = 'attribute'
    else:
        usage = 'attribute'
        if is_id or name.startswith('ID_') or name.startswith('DT_') or name.startswith('HR_'):
            usage = 'identifier'
        if is_fato or name == 'QTD_EVENT' or name.startswith('VL_'):
            usage = 'fact'
    sub(qi, 'usage', usage)

    # Tipos Internos do Cognos
    if "NUMBER" in o_type: 
        sub(qi, 'datatype', 'float64')
        sub(qi, 'precision', '0')
        sub(qi, 'scale', '0')
        sub(qi, 'size', '8')
        if name == 'QTD_EVENT':
            agg = 'countDistinct'
        elif name == 'VL_EVENT' or (is_fato and name.startswith('VL_')):
            agg = 'sum'
        else:
            agg = 'count'
        sub(qi, 'regularAggregate', agg)
    elif "DATE" in o_type or "TIMESTAMP" in o_type: 
        sub(qi, 'datatype', 'dateTime')
        sub(qi, 'precision', '0')
        sub(qi, 'scale', '0' if 'DATE' in o_type else '6')
        sub(qi, 'size', '12')
        sub(qi, 'regularAggregate', 'unsupported')
    else:
        sub(qi, 'datatype', 'characterLength16')
        str_prec = int(length) if length else 255
        sub(qi, 'precision', str(str_prec))
        sub(qi, 'scale', '0')
        sub(qi, 'size', str((str_prec * 2) + 2))
        sub(qi, 'regularAggregate', 'unsupported')

    sub(qi, 'nullable', "true" if null == "Y" else "false")
    sub(qi, 'semiAggregate', 'unsupported')
    sub(qi, 'collationSequenceName', 'pt-br')
    sub(qi, 'collationSequenceLevel', '1')