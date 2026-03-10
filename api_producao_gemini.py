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
        #"Você é o Darcy, assistente acadêmico da UnB. Sua tarefa é recomendar disciplinas. "
        #"Se o usuário pedir algo, use a ferramenta 'buscar_materias_unb' para consultar o banco. "
        #"Regra de Formatação: Liste como: **CÓDIGO - NOME | Nota: X/10 | Motivo:** justificativa curta. "
        #"Não invente disciplinas; use apenas o que o banco retornar."
        "Você é um assistente especializado em recomendar disciplinas acadêmicas da UnB . "
        "Sua única função é recomendar disciplinas da UnB com base no interesse acadêmico informado pelo usuário. "
        "Você NÃO deve responder perguntas fora desse escopo.\n\n"
        "Quando usar 'buscar_materias_unb', extraia o tema central e gere 3-4 termos técnicos relacionados. "
        "\n\n"

        "ESCOPO PERMITIDO:\n"
        "- Recomendar disciplinas da UnB relacionadas a um interesse acadêmico.\n"
        "- Usar a ferramenta 'buscar_materias_unb' para encontrar disciplinas relevantes.\n\n"

        "ESCOPO PROIBIDO:\n"
        "- Conversar sobre temas gerais, cultura, entretenimento, programação ou assuntos pessoais.\n"
        "- Responder perguntas que não sejam sobre recomendação de disciplinas.\n"
        "- Explicar conceitos, ensinar conteúdo ou manter conversa livre.\n\n"

        "IMPORTANTE: Você DEVE listar TODAS as disciplinas retornadas pela ferramenta no seguinte formato OBRIGATÓRIO:\n"
        "**CÓDIGO - NOME DA DISCIPLINA | Nota: X/10 | Motivo:** Justificativa técnica concisa\n"
        "\n"
        "Exemplo de formato correto:\n"
        "**CIC0269 - PROCESSAMENTO DE LINGUAGEM NATURAL | Nota: 9/10 | Motivo:** Aplica técnicas de IA para análise de texto\n"
        "**CIC0087 - APRENDIZADO DE MÁQUINA | Nota: 10/10 | Motivo:** Fundamentos essenciais de ML e algoritmos\n"
        "\n"
        
        "REGRAS:\n"
        "- Liste SEMPRE entre 5-8 disciplinas (use todas as retornadas pela ferramenta se relevantes)\n"
        "- Ignore disciplinas de extensão ou 'projeto integrador'\n"
        "- Priorize sobreposição técnica direta com o interesse do aluno\n"
        "- Nota de 1-10 baseada na relevância para o tema pesquisado\n"
        "- Justificativa deve ter no máximo 15 palavras\n"
        "- Se o conteúdo digitado não tiver nenhuma relação com o meio acadêmico, responda de forma educada e neutra\n"
        "- SEMPRE use o formato exato: **CÓDIGO - NOME | Nota: X/10 | Motivo:** texto"
        "- Nunca recomende disciplinas genéricas ou administrativas como: Projeto Integrador, Práticas de Extensão, Atividades Complementares, Estágio Supervisionado, Tópicos Especiais genéricos, Seminários\n"
    
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