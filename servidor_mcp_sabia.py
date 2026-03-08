from mcp.server.fastmcp import FastMCP
import json
import sys
import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

# Carrega variáveis
script_dir = Path(__file__).parent
load_dotenv(script_dir / ".env")

# Inicializa Google Gemini
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

mcp = FastMCP("Darcy_AI_Gemini")

# Inicializa Supabase uma única vez
supabase_client = create_client(
    os.environ.get("SUPABASE_URL"), 
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

@mcp.tool()
def buscar_materias_unb(interesse: str) -> str:
    """Busca matérias na UnB usando embeddings do Gemini."""
    try:
        # 1. Gera o vetor via API (Modelo: text-embedding-004 ou gemini-embedding-001)
        # Certifique-se de que seu banco Supabase suporte a dimensão (ex: 768)
        embedding_res = genai.embed_content(
            model="models/gemini-embedding-001",
            content=interesse,
            task_type="retrieval_query"
        )
        vetor_pergunta = embedding_res['embedding']

        # 2. Busca no Supabase
        resposta = supabase_client.rpc(
            "match_materias", 
            {
                "query_embedding": vetor_pergunta,
                "match_threshold": 0.3,
                "match_count": 10
            }
        ).execute()
        
        dados = resposta.data or []
        lista_final = []
        for item in dados:
            lista_final.append({
                "Codigo": item.get("codigo_materia"),
                "Materia": item.get("nome_materia"),
                "Ementa_Resumida": str(item.get("ementa", ""))[:250] + "...",
                "Score_DB": round(item.get("similaridade", 0), 2)
            })
        
        return json.dumps(lista_final, ensure_ascii=False)
    except Exception as e:
        print(f"[MCP] ERRO: {e}", file=sys.stderr)
        return json.dumps([])

if __name__ == "__main__":
    mcp.run(transport='stdio')