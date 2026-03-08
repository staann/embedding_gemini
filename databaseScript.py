import os
import time
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

NOME_MODELO = "models/gemini-embedding-001" 

# ... (resto do código igual)

def atualizar_embeddings_batch():
    # Buscamos um pedaço por vez para não sobrecarregar a memória do Python
    for _ in range(10):
        print("Loop numero :", _+1)
        print("🔍 Verificando matérias sem embeddings...")
        resposta = supabase.table("materias_vetorizadas").select("id_materia, codigo_materia, nome_materia, ementa").is_("embedding", "null").limit(2000).execute()
        materias = resposta.data

        if not materias:
            print("✅ Tudo pronto ou lote concluído!")
            return

        tamanho_lote = 200 # Aumentado para 100
        
        for i in tqdm(range(0, len(materias), tamanho_lote)):
            lote = materias[i:i + tamanho_lote]
            textos_lote = [f"{m['nome_materia']} {m.get('ementa') or ''}".strip() for m in lote]
            
            try:
                result = genai.embed_content(
                    model=NOME_MODELO,
                    content=textos_lote,
                    task_type="retrieval_document",
                    output_dimensionality=256
                )
                
                embeddings = result.get('embeddings') or result.get('embedding')

                dados_para_upsert = []
                # Update no Supabase
                '''
                for j, materia in enumerate(lote):
                    supabase.table("materias_vetorizadas").update({
                        "embedding": embeddings[j]
                    }).eq("codigo_materia", materia["codigo_materia"]).execute()
                '''
                for j, materia in enumerate(lote):
                    dados_para_upsert.append({
                        "id_materia": materia["id_materia"], # <--- A verdadeira Chave Primária!
                        "codigo_materia": materia["codigo_materia"], 
                        "embedding": embeddings[j]
                    })
                supabase.table("materias_vetorizadas").upsert(dados_para_upsert).execute()
                # ESPERA OBRIGATÓRIA: 5 segundos para garantir que o RPM fique baixo
                time.sleep(5) 

            except Exception as e:
                if "429" in str(e):
                    print(f"\n⏳ Limite atingido. Descansando 70 segundos...")
                    time.sleep(70)
                else:
                    print(f"\n⚠️ Erro: {e}")
                    time.sleep(10)

    time.sleep(60)
    
if __name__ == "__main__":
    atualizar_embeddings_batch()