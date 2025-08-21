# Sandbox Tools API

API FastAPI para avaliação de experimentos, criação de tickets e busca em base de conhecimento.

## 🚀 Funcionalidades

- **Score API**: Avaliação automática de experimentos com scoring baseado em critérios
- **Ticket API**: Criação de tickets para experimentos aprovados
- **Knowledge Base**: Busca em base de conhecimento para suporte

## 📋 Pré-requisitos

- Docker
- Docker Compose (opcional, para desenvolvimento)

## 🐳 Deploy com Docker

### Build da Imagem

```bash
docker build -t sandbox-tools .
```

### Execução Local

```bash
docker run -p 8080:8080 sandbox-tools
```

### Com Docker Compose

```bash
docker-compose up -d
```

## ☁️ Deploy no IBM Code Engine

### 1. Build e Push da Imagem

```bash
# Tag para registry
docker tag sandbox-tools:latest <your-registry>/sandbox-tools:latest

# Push para registry
docker push <your-registry>/sandbox-tools:latest
```

### 2. Deploy via CLI

```bash
# Instalar IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Login
ibmcloud login

# Selecionar resource group
ibmcloud target -g <resource-group>

# Criar aplicação
ibmcloud ce application create \
  --name sandbox-tools \
  --image <your-registry>/sandbox-tools:latest \
  --port 8080 \
  --min-scale 0 \
  --max-scale 10 \
  --cpu 0.25 \
  --memory 0.5G \
  --env TICKET_BASE_URL=https://tickets.sandbox.local
```

### 3. Deploy via Console

1. Acesse o IBM Cloud Console
2. Navegue para Code Engine
3. Crie um novo projeto ou selecione existente
4. Clique em "Create Application"
5. Configure:
   - **Name**: sandbox-tools
   - **Container image**: `<your-registry>/sandbox-tools:latest`
   - **Listening port**: 8080
   - **Resources**: CPU 0.25, Memory 0.5G
   - **Scaling**: Min 0, Max 10
   - **Environment variables**:
     - `TICKET_BASE_URL=https://tickets.sandbox.local`

## 📚 Endpoints da API

### Score API
- `POST /score-api/score` - Avalia experimento e retorna score

### Ticket API
- `POST /ticket-api/tickets` - Cria ticket para experimento

### Knowledge Base
- `GET /kb/kb/search?q={query}&top_k={limit}` - Busca na base de conhecimento

### Documentação
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

## 🔧 Configuração

### Variáveis de Ambiente

- `TICKET_BASE_URL`: URL base para sistema de tickets (padrão: https://tickets.sandbox.local)

## 🏗️ Estrutura do Projeto

```
.
├── app.py              # Aplicação FastAPI principal
├── requirements.txt    # Dependências Python
├── Dockerfile         # Configuração Docker
├── docker-compose.yml # Orquestração local
├── .dockerignore     # Arquivos ignorados no build
└── README.md         # Esta documentação
```

## 🧪 Testando a API

### Exemplo de Request - Score

```bash
curl -X POST "http://localhost:8080/score-api/score" \
  -H "Content-Type: application/json" \
  -d '{
    "experimento": {
      "problema": "Baixa retenção de clientes",
      "hipotese": "Melhorar onboarding aumenta retenção",
      "kpi": "Taxa de retenção 30 dias",
      "baseline": "65%",
      "alvo": "75%",
      "plano_teste": "Teste A/B com novo fluxo de onboarding",
      "riscos_lgpd": "Dados anonimizados, consent explícito, opt-out disponível, retenção 2 anos",
      "unidade_gestora": "UG Digital",
      "patrocinador": "Diretor de Produto",
      "referencias": "Estudo McKinsey sobre onboarding"
    }
  }'
```

## 📊 Monitoramento

A aplicação inclui:
- Health check endpoint automático
- Logs estruturados via uvicorn
- Métricas de performance integradas

## 🔒 Segurança

- Container roda com usuário não-root
- Imagem baseada em Python slim para menor superfície de ataque
- Variáveis de ambiente para configuração sensível

## 📝 Licença

Este projeto é proprietário e confidencial.