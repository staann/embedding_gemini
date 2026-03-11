from fastapi import FastAPI, HTTPException
import os
import json
import re
from pydantic import BaseModel
from openai import OpenAI
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv

# 1. INICIALIZAÇÃO GLOBAL (Roda apenas quando o servidor liga)
load_dotenv()

# Clientes globais mantêm conexões persistentes ("quentes")
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
client_maritaca = OpenAI(api_key=os.environ.get("MARITACA_API_KEY"), base_url="https://chat.maritaca.ai/api")

# Configuração do FastAPI
app = FastAPI(title="Darcy AI - API da UnB", version="1.0")

# Modelo de entrada de dados esperado do frontend/usuário
class Consulta(BaseModel):
    interesse: str

# Prompt do Sistema (mantido do seu código original)
SYSTEM_PROMPT = (
    "Você é o Darcy, assistente da UnB. Sua tarefa é listar as disciplinas encontradas no banco de dados.\n\n"
    "REGRAS CRÍTICAS:\n"
    "1. Se a ferramenta 'buscar_materias_unb' retornar dados, você DEVE listar as disciplinas.\n"
    "2. Use EXATAMENTE este formato: **CÓDIGO - NOME DA DISCIPLINA | Nota: X/10 | Motivo:** justificativa curta.\n"
    "3. NÃO diga que não encontrou resultados se a ferramenta retornou uma lista.\n"
    "4. NÃO adicione introduções ou conclusões. Apenas a lista."
    "ESCOPO PROIBIDO:\n"
        "- Conversar sobre temas gerais, cultura, entretenimento, programação ou assuntos pessoais.\n"
        "- Responder perguntas que não sejam sobre recomendação de disciplinas.\n"
        "- Explicar conceitos, ensinar conteúdo ou manter conversa livre.\n\n"    
    "REGRAS:\n"
        "- Liste SEMPRE entre 5-8 disciplinas (use todas as retornadas pela ferramenta se relevantes)\n"
        "- Ignore disciplinas de extensão ou 'projeto integrador'\n"
        "- Priorize sobreposição técnica direta com o interesse do aluno\n"
        "- Nota de 1-10 baseada na relevância para o tema pesquisado\n"
        "- Justificativa deve ter no máximo 15 palavras\n"
        "- Se o conteúdo digitado não tiver nenhuma relação com o meio acadêmico, responda de forma educada e neutra\n"
        "- SEMPRE use o formato exato: **CÓDIGO - NOME | Nota: X/10 | Motivo:** texto"
    "REGRAS PARA DISCIPLINAS GENÉRICAS:\n"
        "- Disciplinas genéricas ou administrativas NÃO devem ser recomendadas.\n"
        "- Exemplos: Projeto Integrador, Práticas de Extensão, Atividades Complementares, "
        "Estágio Supervisionado, Tópicos Especiais, Seminários.\n"
    "- EXCEÇÃO: Se o usuário digitar EXATAMENTE o nome da disciplina, ela pode ser recomendada.\n"
        "- 'Exatamente' significa que o texto do usuário corresponde diretamente ao nome da disciplina.\n"
        "Exemplos:\n"
        "Usuário: 'projeto integrador' → pode recomendar 'Projeto Integrador'\n"
        "Usuário: 'ferramentas integradoras' → NÃO recomendar 'Projeto Integrador'\n"
        "Usuário: 'seminários' → pode recomendar 'Seminários'\n"
        "Usuário: 'seminários integrados' → NÃO recomendar 'Seminários'\n"

        "- Nunca use similaridade de palavras para recomendar disciplinas genéricas.\n"
        "- Se o nome não for exatamente o mesmo da pesquisa do usuário, ignore completamente.\n"

        "- Se uma disciplina for genérica ou administrativa e não corresponder "
        "exatamente ao nome pesquisado pelo usuário, ignore completamente.\n"

        "REGRA ABSOLUTA:\n"
        "- Retorne APENAS a lista de disciplinas.\n"
        "- NÃO explique decisões.\n"
        "- NÃO mencione disciplinas que foram ignoradas.\n"
        "- NÃO escreva frases após a lista.\n"
        "- A resposta deve conter SOMENTE linhas no formato exigido.\n"
            
)

TOOLS = [{
    "type": "function",
    "function": {
        "name": "buscar_materias_unb",
        "description": "Busca matérias na base de dados da UnB usando o termo exato.",
        "parameters": {
            "type": "object",
            "properties": {
                "interesse": {
                    "type": "string",
                    "description": "Extraia APENAS a palavra-chave principal ou frase curta do usuário. NÃO adicione explicações ou termos extras. Exemplo: 'inteligência artificial'"
                }
            },
            "required": ["interesse"]
        }
    }
}]

def parse_resposta_sabia(texto: str) -> list:
    """Extrai as disciplinas do texto da IA."""
    disciplinas = []
    linhas = texto.split('\n')
    for linha in linhas:
        linha = linha.strip().lstrip('*').lstrip('-').lstrip('•').strip()
        codigo_match = re.match(r'([A-Z]{3}\d{4})', linha)
        if not codigo_match: continue
            
        try:
            codigo = codigo_match.group(1)
            resto = linha[len(codigo):].strip().lstrip('-').strip()
            
            nome = resto.split('|')[0].strip() if '|' in resto else resto.split('Nota:')[0].strip() if 'Nota:' in resto else resto.strip()
            nome = nome.strip('*').strip()
            
            nota = 7
            if 'Nota:' in linha:
                nota_texto = re.sub(r'[^\d]', '', linha.split('Nota:')[1].split('/')[0])
                if nota_texto: nota = int(nota_texto)
            
            justificativa = ""
            if 'Motivo:' in linha:
                justificativa = linha.split('Motivo:')[1].strip().strip('*').strip()
            
            disciplinas.append({"codigo": codigo, "nome": nome, "nota": nota, "justificativa": justificativa})
        except Exception:
            continue
    return disciplinas

def ferramenta_buscar_materias_unb(interesse: str) -> str:
    try:
        termo_puro = interesse.replace(".", "").replace('"', "").strip()
        print(f"\n[DEBUG] Buscando por: '{termo_puro}'")

        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=termo_puro,
            task_type="retrieval_query", 
            output_dimensionality=256
        )
        
        vetor = result.get('embeddings') or result.get('embedding')
        if isinstance(vetor, list) and len(vetor) > 0 and isinstance(vetor[0], list):
            vetor = vetor[0]

        # Aumentamos para 50 para garantir que as de Computação entrem na lista
        resposta = supabase.rpc("match_materias", {
            "query_embedding": vetor,
            "match_threshold": 0.50, 
            "match_count": 10         
        }).execute()
        
        dados = resposta.data or []
        
        # FILTRO DE ELITE: Prioriza departamentos de tecnologia (CIC, FGA, ENE)
        # e remove ruídos óbvios (Educação Física, Pedagogia) se houver opção melhor
        #tecnologia = [i for i in dados if any(prefix in i.get('codigo_materia', '') for prefix in ['CIC', 'FGA', 'ENE', 'MAT'])]
        #outros = [i for i in dados if i not in tecnologia]
        
        # Junta dando prioridade total para tecnologia
        #dados_filtrados = (tecnologia + outros)[:20]

        print("\n" + "="*50)
        print("🔍 DEBUG: MATÉRIAS DIRETAS DO BANCO (PRÉ-IA)")
        for i, item in enumerate(dados):#dados_filtrados[:10]): # Mostra as top 10
             print(f"{i+1}. {item.get('codigo_materia')} - {item.get('nome_materia')} (Sim: {item.get('similaridade')})")
        print("="*50 + "\n")

        lista_final = []
        for item in dados:#dados_filtrados:
            lista_final.append({
                "codigo": item.get("codigo_materia"),
                "nome": item.get("nome_materia"),
                "similaridade": round(item.get("similaridade", 0), 2)
            })

        print(f"[DEBUG] Filtradas {len(lista_final)} matérias.")
        return json.dumps(lista_final, ensure_ascii=False)
    
    except Exception as e:
        print(f"Erro na ferramenta: {e}")
        return json.dumps([])

# 3. O ENDPOINT PRINCIPAL DA API
@app.post("/recomendar")
async def recomendar_materias(consulta: Consulta):
    if not consulta.interesse.strip():
        raise HTTPException(status_code=400, detail="O campo 'interesse' não pode estar vazio.")

    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": consulta.interesse}]

    try:
        # Passa a bola para o Sabiá analisar o interesse
        response = client_maritaca.chat.completions.create(
            model="sabiazinho-4", 
            messages=mensagens,
            tools=TOOLS,
            tool_choice="auto"
        )

        msg_ia = response.choices[0].message
        
        # Se o Sabiá decidir buscar no banco
        if msg_ia.tool_calls:
            mensagens.append(msg_ia)
            tool_call = msg_ia.tool_calls[0] # Usa apenas a primeira para economia extrema
            args = json.loads(tool_call.function.arguments)
            
            print(f"\n[DEBUG] Termo puro enviado para o banco: {args['interesse']}\n")
            # Chama a função Python diretamente (Milissegundos!)
            dados_banco = ferramenta_buscar_materias_unb(args["interesse"])
            
            mensagens.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": "buscar_materias_unb",
                "content": dados_banco
            })

            # Resposta final do Sabiá
            final_response = client_maritaca.chat.completions.create(model="sabia-4", messages=mensagens)
            resposta_texto = final_response.choices[0].message.content
            print(f"\n[DEBUG] Texto bruto da IA:\n{resposta_texto}\n")
        else:
            resposta_texto = msg_ia.content

        # Retorna o JSON estruturado pronto para o frontend
        return {
            "success": True,
            "disciplinas": parse_resposta_sabia(resposta_texto),
            "resposta_completa": resposta_texto
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))