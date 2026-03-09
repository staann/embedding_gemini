🚀 Recomendador de Disciplinas Acadêmicas
Este projeto utiliza agentes de IA para recomendar disciplinas com base nos interesses do usuário, integrando Supabase como banco de dados e diversos provedores de LLM.

🛠️ Configuração do Ambiente
Antes de iniciar, você precisa configurar as variáveis de ambiente. Crie um arquivo .env na raiz do projeto e preencha com suas credenciais:

Snippet de código

# Configurações do Banco de Dados (Supabase)
SUPABASE_URL="sua_url_aqui"
SUPABASE_SERVICE_ROLE_KEY="sua_chave_service_role_aqui"

# Chaves de API de IA
GOOGLE_API_KEY="sua_chave_google_gemini_aqui"
MARITACA_API_KEY="sua_chave_maritalk_aqui"
💻 Como Executar
Siga os passos abaixo para rodar a aplicação localmente:

1. Instale as dependências
Certifique-se de ter o Python instalado e execute:

Bash

pip install -r requirements.txt
2. Inicie o servidor da API
Execute o arquivo principal de produção:

Bash

python api_producao_gemini.py
Aguarde até visualizar a mensagem: INFO: Application startup complete.

3. Realize uma requisição
Com o servidor rodando, abra um novo terminal e utilize o curl para testar o recomendador:

Bash

curl -X POST "http://127.0.0.1:8000/recomendar" \
     -H "Content-Type: application/json" \
     -d '{"interesse": "IA e Aprendizado de Máquina"}'
📂 Arquivos Principais
api_producao_gemini.py: Ponto de entrada da API FastAPI que gerencia a lógica de recomendação.

requirements.txt: Lista de todas as bibliotecas necessárias para o funcionamento do projeto.