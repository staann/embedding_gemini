import pandas as pd
import numpy as np
import google.generativeai as genai
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

def analisar_csv_similaridade(caminho_csv, pesquisa_usuario):
    # 1. Carrega o CSV enviado
    df = pd.read_csv(caminho_csv)
    
    # Remove as matérias que estão sem embedding (NULL) no seu arquivo
    df = df.dropna(subset=['vetor_embedding'])
    
    print(f"🔎 Pesquisando por: '{pesquisa_usuario}'")
    
    # 2. Gera o vetor para a sua nova pesquisa
    res = genai.embed_content(
        model="models/gemini-embedding-001",
        content=pesquisa_usuario,
        task_type="retrieval_document",
        output_dimensionality=256
    )
    v_query = np.array(res['embedding']).reshape(1, -1)

    # 3. Função para converter a string do CSV em um array numérico
    def str_para_vetor(string_vetor):
        # Converte a string "[0.1, 0.2...]" em uma lista real de floats
        lista = json.loads(string_vetor)
        return np.array(lista).reshape(1, -1)

    # 4. Calcula a similaridade para cada linha
    resultados = []
    for _, row in df.iterrows():
        v_banco = str_para_vetor(row['vetor_embedding'])
        sim = cosine_similarity(v_query, v_banco)[0][0]
        
        resultados.append({
            'codigo': row['codigo_materia'],
            'nome': row['nome_materia'],
            'similaridade': sim
        })

    # 5. Ordena pelos mais parecidos
    df_final = pd.DataFrame(resultados).sort_values(by='similaridade', ascending=False)
    
    print("\nTop  Matérias Encontradas no seu Arquivo:")
    print(df_final.to_string(index=False))

if __name__ == "__main__":
    # Use o nome exato do arquivo que você me enviou
    arquivo = "Supabase Snippet Materias com termos de IA_ML.csv"
    analisar_csv_similaridade(arquivo, "inteligência artificial aplicada")