# 🚀 Recomendador de Disciplinas Acadêmicas UnB

Sistema inteligente de recomendação de disciplinas acadêmicas utilizando agentes de IA para sugerir cursos com base nos interesses do usuário. O projeto integra múltiplos provedores de LLM (Large Language Models) e utiliza Supabase como banco de dados.


## ✨ Características

- 🤖 **Agentes de IA Inteligentes**: Utiliza agentes especializados para análise e recomendação de disciplinas
- 🔍 **Busca Semântica**: Análise de similaridade entre interesses do usuário e conteúdo das disciplinas
- 🌐 **API REST**: Interface FastAPI para fácil integração
- 📊 **Base de Dados Completa**: Integração com Supabase para persistência de dados
- 🔄 **Múltiplos Provedores LLM**: Suporte para Google Gemini e Maritaca AI
- 🎯 **Recomendações Personalizadas**: Sistema que aprende com os interesses específicos de cada usuário

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Descrição |
|------------|-----------|
| **Python 3.x** | Linguagem de programação principal |
| **FastAPI** | Framework web para construção da API |
| **Supabase** | Banco de dados PostgreSQL hospedado |
| **Google Gemini** | Modelo de linguagem da Google |
| **Maritaca AI** | Modelo de linguagem brasileiro |
| **Uvicorn** | Servidor ASGI para Python |
| **MCP** | Model Context Protocol para agentes |

---

## 📦 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.8+**
- **pip** (gerenciador de pacotes Python)
- **Git** (para clonar o repositório)
- Conta no [Supabase](https://supabase.com/)
- API Keys para os provedores de IA (Google Gemini e/ou Maritaca)

---

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd recomendador_unb
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Configurações do Banco de Dados (Supabase)
SUPABASE_URL="https://seu-projeto.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="sua_chave_service_role_aqui"

# Chaves de API de IA
GOOGLE_API_KEY="sua_chave_google_gemini_aqui"
MARITACA_API_KEY="sua_chave_maritalk_aqui"
```

## 💻 Como Usar



#### Comando direto

```bash
uvicorn api_producao:app --reload
```

O servidor iniciará em `http://127.0.0.1:8000`

Aguarde a mensagem: 
```
INFO: Application startup complete.
```

## 📖 Exemplos de Uso

### Exemplo 1: Usando cURL

```bash
curl -X POST "http://127.0.0.1:8000/recomendar" \
     -H "Content-Type: application/json" \
     -d '{"interesse": "Aprendizado de Máquina"}'
```

### Estrutura de Dados

O sistema trabalha com dados de disciplinas da UnB, incluindo:
- Códigos de disciplina
- Nomes e descrições

---

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---
