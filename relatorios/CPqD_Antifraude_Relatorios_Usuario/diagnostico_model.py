import xml.etree.ElementTree as ET

def diagnosticar_modelos(path_original, path_gerado):
    def get_root(path):
        tree = ET.parse(path)
        return tree.getroot()

    print("--- INICIANDO DIAGNÓSTICO ---")
    
    try:
        orig = get_root(path_original)
        novo = get_root(path_gerado)
        
        # 1. Verificar Namespace (Causa comum de erro fatal)
        ns_orig = orig.tag.split('}')[0].strip('{')
        ns_novo = novo.tag.split('}')[0].strip('{')
        
        print(f"[1] Namespace Original: {ns_orig}")
        print(f"[1] Namespace Gerado:   {ns_novo}")
        
        if ns_orig != ns_novo:
            print("!!! ALERTA: Os Namespaces são diferentes! O Cognos vai travar.")

        # 2. Comparar um Query Subject (Amostra)
        def pegar_primeiro_qs(root):
            for qs in root.iter():
                if 'querySubject' in qs.tag:
                    return qs
            return None

        qs_o = pegar_primeiro_qs(orig)
        qs_n = pegar_primeiro_qs(novo)

        if qs_o is not None and qs_n is not None:
            print("\n[2] Comparando atributos do QuerySubject:")
            print(f"Original: {qs_o.attrib}")
            print(f"Gerado:   {qs_n.attrib}")
            
            if 'id' not in qs_n.attrib:
                print("!!! ERRO: O objeto gerado está SEM ID.")

            # 3. Verificar Ordem das Tags Internas
            print("\n[3] Ordem das Tags Internas:")
            ordem_o = [child.tag.split('}')[1] for child in qs_o]
            ordem_n = [child.tag.split('}')[1] for child in qs_n]
            print(f"Original: {ordem_o[:5]}...")
            print(f"Gerado:   {ordem_n[:5]}...")
            
            if ordem_o[0] != ordem_n[0]:
                 print(f"!!! ALERTA: A primeira tag deveria ser '{ordem_o[0]}', mas o Python criou '{ordem_n[0]}'.")

    except Exception as e:
        print(f"Erro ao ler arquivos: {e}")

diagnosticar_modelos('model.xml', 'model_final.xml')