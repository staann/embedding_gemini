import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Pega a chave do seu .env
chave = os.environ.get("GOOGLE_API_KEY")
print(f"🔑 Chave carregada termina em: ...{chave[-4:]}")

genai.configure(api_key=chave)

print("⏳ Enviando requisição para o Google...")
try:
    resposta = genai.embed_content(
        model="models/gemini-embedding-001",
        content="Teste de conexão UnB",
        task_type="retrieval_document"
    )
    print("✅ SUCESSO! A API respondeu e gerou um vetor de tamanho:", len(resposta['embedding']))
except Exception as e:
    print("❌ FALHA na comunicação com a API:", e)