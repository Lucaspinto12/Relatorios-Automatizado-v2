import re
import os

def finalizar_xml(root):
    import xml.etree.ElementTree as ET
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    xml_str = xml_str.replace('ns0:', '').replace(':ns0', '')
    
    # Substituição de aspas protegendo os atributos XML
    xml_str = xml_str.replace('"', '___QUOT___')
    xml_str = re.sub(r'=(\s*)___QUOT___(.*?)\___QUOT___', r'="\2"', xml_str)
    xml_str = xml_str.replace('___QUOT___', '&quot;')
    xml_str = xml_str.replace("'", "&apos;")
    xml_str = xml_str.replace('&amp;', '&')
    xml_str = xml_str.replace("> = <", ">=<").replace("> AND <", ">AND<")

    # Salvar em /app/output se rodando no container, senão na pasta local
    output_dir = "/app/output" if os.path.isdir("/app/output") else "."
    output_path = os.path.join(output_dir, "model_final.xml")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        f.write(xml_str)
    print(f"\n[SUCESSO FINAL] {output_path} gerado sem erros de aspas.")