import xml.etree.ElementTree as ET
import os

# --- CONFIGURAÇÃO ---
arquivo_input = 'model.xml'
arquivo_output = 'model_atualizado.xml'
novo_evento = 'uni_cash_in'  # Altere aqui (Ex: pix_internacional)
valor_evento = 'vl_operacao'       # Altere para o nome da coluna de valor ou '0'

# Trechos de SQL para injetar
sql_fatos = f"union all select id_event , id_event_type , {valor_evento} vl_event , dt_event from vw_event_{novo_evento} "
sql_dashboard = f"where dt_event >= trunc(sysdate) and dt_event < trunc(sysdate+1) union all select id_event , id_event_type , dt_event , 1 qtd_event from vw_event_{novo_evento} "

# Lógica específica para DIM_SCORE (pág 15 do manual)
sql_score_part1 = f"union all select id_score_type , id_event_type , id_event , vl_score from vw_score_{novo_evento} "
sql_score_part2 = f"union all select id_event_type , id_event , max(vl_score) as max_vl_score from vw_score_{novo_evento} group by id_event_type , id_event "

def atualizar_modelo():
    if not os.path.exists(arquivo_input):
        print(f"Erro: Arquivo {arquivo_input} não encontrado na pasta!")
        return

    ET.register_namespace('', "http://www.developer.cognos.com/schemas/bmt/60/12")
    tree = ET.parse(arquivo_input)
    root = tree.getroot()
    ns = {'bmt': 'http://www.developer.cognos.com/schemas/bmt/60/12'}

    for query_subject in root.findall('.//bmt:querySubject', ns):
        name = query_subject.find('./bmt:name', ns).text
        sql_elem = query_subject.find('.//bmt:sql[@type="native"]', ns)
        
        if sql_elem is not None and sql_elem.text:
            sql = sql_elem.text
            
            # Tabelas de Fato Simples (pág 13 e 14)
            if name in ["FT_NOT_ALARMED_RULE", "FT_CASE_MANAGEMENT"]:
                sql_elem.text = sql.replace(") event", f"{sql_fatos}) event")
                print(f"[OK] {name} atualizada.")

            # Tabelas de Dashboard (pág 16)
            elif name in ["FT_EVENT_TODAY", "FT_EVENT_LAST_24HRS", "FT_EVENT_LAST_7DAYS"]:
                # Note: O manual pede filtros de data específicos para cada uma, 
                # o script injeta antes do fechamento do bloco 'union all'
                sql_elem.text = sql.replace("union all select id_event , id_event_type , dt_event , 1 qtd_event from", 
                                            f"union all select id_event , id_event_type , dt_event , 1 qtd_event from vw_event_{novo_evento} union all select id_event , id_event_type , dt_event , 1 qtd_event from")
                print(f"[OK] {name} (Dashboard) atualizada.")

            # DIM_SCORE (pág 15) - Possui dois blocos de Union
            elif name == "DIM_SCORE":
                # Injeta na parte 1 (Select simples)
                sql = sql.replace(") score ,", f"{sql_score_part1}) score ,")
                # Injeta na parte 2 (Group by)
                sql = sql.replace(") score_max ,", f"{sql_score_part2}) score_max ,")
                sql_elem.text = sql
                print(f"[OK] DIM_SCORE atualizada.")

    tree.write(arquivo_output, encoding='utf-8', xml_declaration=True)
    print(f"\nPRONTO! O arquivo '{arquivo_output}' foi gerado com as alterações.")

if __name__ == "__main__":
    atualizar_modelo()