from fastapi import FastAPI, HTTPException
import os
import json
import re
from pydantic import BaseModel
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv

# 1. CONFIGURAÇÃO E CLIENTES
load_dotenv()

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

# Inicializamos o modelo do Gemini com a ferramenta
# O Gemini 1.5 Flash é ideal para latência baixa
model_gemini = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=(
        "Você é o Darcy, assistente acadêmico da UnB. Sua tarefa é recomendar disciplinas de tecnologia. "
        "Se o usuário pedir algo, use a ferramenta 'buscar_materias_unb' para consultar o banco. "
        "Regra de Formatação: Liste como: **CÓDIGO - NOME | Nota: X/10 | Motivo:** justificativa curta. "
        "Não invente disciplinas; use apenas o que o banco retornar."
    )
)

app = FastAPI(title="Darcy AI - Gemini Edition")

class Consulta(BaseModel):
    interesse: str

# 2. A FERRAMENTA (Lógica de busca mantida com o debug)
def ferramenta_buscar_materias_unb(interesse: str):
    """Busca matérias no banco de dados da UnB."""
    try:
        termo_puro = interesse.replace(".", "").replace('"', "").strip()
        print(f"\n[DEBUG] Buscando por: '{termo_puro}'")

        # Embedding de 256 dimensões
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=termo_puro,
            task_type="retrieval_document",
            output_dimensionality=256
        )
        vetor = result['embedding']

        # Busca no Supabase
        resposta = supabase.rpc("match_materias", {
            "query_embedding": vetor,
            "match_threshold": 0.30,
            "match_count": 40
        }).execute()
        
        dados = resposta.data or []
        
        # Priorização de Tecnologia (CIC, FGA, ENE)
        tecnologia = [i for i in dados if any(p in i.get('codigo_materia', '') for p in ['CIC', 'FGA', 'ENE', 'MAT'])]
        outros = [i for i in dados if i not in tecnologia]
        dados_filtrados = (tecnologia + outros)[:15]

        # --- DEBUG VISUAL NO TERMINAL ---
        print("\n" + "="*50)
        print("🔍 TOP 5 RESULTADOS DO BANCO:")
        for i, item in enumerate(dados_filtrados[:5]):
             print(f"{i+1}. {item.get('codigo_materia')} - {item.get('nome_materia')} (Sim: {item.get('similaridade')})")
        print("="*50 + "\n")

        return dados_filtrados
    except Exception as e:
        print(f"Erro na ferramenta: {e}")
        return []

# 3. PARSER DE RESPOSTA
def parse_resposta(texto: str) -> list:
    disciplinas = []
    # Regex para capturar: CÓDIGO - NOME | Nota: X | Motivo: TEXTO
    padrao = r"\*\*([A-Z]{3}\d{4})\s*-\s*([^|]+)\|\s*Nota:\s*(\d+(?:[,.]\d+)?)/10\s*\|\s*Motivo:\s*([^*]+)"
    matches = re.findall(padrao, texto)
    
    for m in matches:
        disciplinas.append({
            "codigo": m[0],
            "nome": m[1].strip(),
            "nota": float(m[2].replace(',', '.')),
            "justificativa": m[3].strip()
        })
    return disciplinas

# 4. ENDPOINT PRINCIPAL
@app.post("/recomendar")
async def recomendar(consulta: Consulta):
    try:
        # Iniciamos o chat com o histórico
        chat = model_gemini.start_chat()
        
        # O Gemini gerencia a chamada de ferramenta automaticamente se usarmos a função como callable
        # Mas para controle total, vamos simular o fluxo manual para você ver o que acontece:
        
        prompt = f"O usuário tem interesse em: {consulta.interesse}. Busque matérias relevantes e recomende."
        
        # 1. Envia ao Gemini
        response = chat.send_message(prompt)
        
        # Se o Gemini quiser chamar a ferramenta (Function Calling)
        # Nota: Para habilitar isso de forma automática, passar tools=[ferramenta_...] no GenerativeModel
        # Aqui fazemos o fluxo controlado para depuração:
        
        # Se o Gemini respondeu com texto direto (sem chamar ferramenta) ou precisamos forçar
        # Vamos usar um fluxo simplificado para os seus testes de debug:
        
        conteudo_banco = ferramenta_buscar_materias_unb(consulta.interesse)
        
        contexto_final = f"Baseado nestes dados do banco: {json.dumps(conteudo_banco)}, responda ao usuário seguindo o formato de lista de disciplinas."
        
        final_res = chat.send_message(contexto_final)
        texto_ia = final_res.text
        
        print(f"\n[DEBUG] RESPOSTA FINAL DO GEMINI:\n{texto_ia}\n")

        return {
            "success": True,
            "disciplinas": parse_resposta(texto_ia),
            "resposta_completa": texto_ia
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))