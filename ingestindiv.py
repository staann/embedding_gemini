import google.generativeai as genai
from supabase import create_client
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Configurações
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

def repovoar_embeddings():

    for _ in range(3):  # Tenta até 3 vezes para lidar com possíveis falhas temporárias
        # 1. Busca matérias que estão sem vetor
        print("Loop numero :", _+1)
        print("🔍 Verificando matérias sem embeddings...")
        res = supabase.table("materias_vetorizadas").select("codigo_materia, nome_materia").is_("embedding", "null").execute()
        
        materias_faltantes = res.data
        total = len(materias_faltantes)
        
        if total == 0:
            print("✅ Todas as matérias já possuem embeddings!")
            return

        print(f"⚠️ Encontradas {total} matérias para processar.")

        for i, materia in enumerate(materias_faltantes):
            codigo = materia['codigo_materia']
            nome = materia['nome_materia']
            
            try:
                # 2. Gera o embedding (usando 256 dimensões como combinado)
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=nome,
                    task_type="retrieval_document",
                    output_dimensionality=256
                )
                vetor = result['embedding']

                # 3. Atualiza apenas aquela linha no Supabase
                supabase.table("materias_vetorizadas").update({"embedding": vetor}).eq("codigo_materia", codigo).execute()
                
                print(f"[{i+1}/{total}] ✅ Sucesso: {codigo} - {nome}")
                
                # Pequena pausa para evitar o Rate Limit da conta gratuita
                time.sleep(2) 

            except Exception as e:
                print(f"[{i+1}/{total}] ❌ Erro em {codigo}: {e}")
                time.sleep(2) # Pausa maior em caso de erro

        print(60*"=")
if __name__ == "__main__":
    repovoar_embeddings()
