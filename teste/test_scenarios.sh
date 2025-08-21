#!/bin/bash
# Scripts de teste para os 4 cenários do Agente Validador Sandbox CAIXA
# Execute: bash test_scenarios.sh

BASE_URL="http://localhost:8080"

echo "=== TESTES DO AGENTE VALIDADOR SANDBOX CAIXA ==="
echo "Base URL: $BASE_URL"
echo ""

# Função para fazer requisições POST
post_request() {
    local endpoint=$1
    local data=$2
    local description=$3
    
    echo "--- $description ---"
    echo "Endpoint: $endpoint"
    echo "Enviando requisição..."
    
    curl -X POST "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data" \
        -w "\nStatus: %{http_code}\nTempo: %{time_total}s\n" \
        -s | jq .
    
    echo ""
}

# Função para fazer requisições GET
get_request() {
    local endpoint=$1
    local description=$2
    
    echo "--- $description ---"
    echo "Endpoint: $endpoint"
    echo "Enviando requisição..."
    
    curl -X GET "$BASE_URL$endpoint" \
        -H "Content-Type: application/json" \
        -w "\nStatus: %{http_code}\nTempo: %{time_total}s\n" \
        -s | jq .
    
    echo ""
}

# CENÁRIO 1: Habitação — push 3 dias
# Baseline 82%, meta 86%, 2m usuários, A/B 50/50, 20k amostra, opt-out
# Esperado: Score~70, F2, TRL6, ODS9/8
CENARIO_1='{
  "experimento": {
    "problema": "Baixa adesão ao push de notificações de habitação (82%), impactando engajamento e conversão em financiamentos.",
    "hipotese": "Se implementarmos push personalizado com timing otimizado, então aumentaremos a taxa de abertura de 82% para 86%, medido por taxa de clique em 30 dias.",
    "kpi": "Taxa de abertura de push de habitação",
    "baseline": "82%",
    "alvo": "86%",
    "plano_teste": "Teste A/B com 2 milhões de usuários, 50/50 split, amostra de 20.000 por grupo, duração 30 dias, segmentação por perfil de renda e região.",
    "riscos_lgpd": "Consentimento via opt-in no onboarding, opt-out disponível nas configurações, retenção de dados por 2 anos, minimização via anonimização de dados sensíveis.",
    "unidade_gestora": "GIHAB - Gerência de Habitação",
    "patrocinador": "Diretoria de Habitação",
    "dependencias": "Integração com plataforma de push, segmentação de base de clientes",
    "referencias": "Benchmark Banco do Brasil: aumento de 15% em push personalizados (2023)"
  }
}'

post_request "/score-api/score" "$CENARIO_1" "CENÁRIO 1: Habitação - Push 3 dias"

# CENÁRIO 2: Cartões — Open Finance
# Aprovação +25% sem ↑NPL; 4 semanas; 20k; consentimento
# Esperado: Score~78, F2-avançada, TRL7, ODS8/9
CENARIO_2='{
  "experimento": {
    "problema": "Taxa de aprovação de cartões limitada por análise de crédito tradicional, perdendo clientes qualificados para concorrência.",
    "hipotese": "Se utilizarmos dados do Open Finance na análise de crédito, então aumentaremos aprovação em 25% mantendo mesmo nível de NPL, medido por taxa de aprovação e inadimplência em 90 dias.",
    "kpi": "Taxa de aprovação de cartões sem aumento de NPL",
    "baseline": "65% aprovação, NPL 3.2%",
    "alvo": "81% aprovação, NPL ≤3.2%",
    "plano_teste": "Teste A/B com 20.000 solicitações, grupo controle (análise tradicional) vs grupo teste (Open Finance), duração 4 semanas, acompanhamento de NPL por 90 dias.",
    "riscos_lgpd": "Consentimento explícito para uso de dados Open Finance, opt-out a qualquer momento, retenção conforme regulamentação BACEN, pseudonimização de dados pessoais.",
    "unidade_gestora": "GECRE - Gerência de Crédito",
    "patrocinador": "Diretoria de Negócios",
    "dependencias": "API Open Finance, modelo de ML atualizado, compliance BACEN",
    "referencias": "Estudo FEBRABAN 2023: Open Finance reduz NPL em 18% com aumento de 22% em aprovações"
  }
}'

post_request "/score-api/score" "$CENARIO_2" "CENÁRIO 2: Cartões - Open Finance"

# CENÁRIO 3: Bem-estar — clubes de mangá
# Alvo ~14% redução de saída; A/B 6m; ≥1.000; enquetes anônimas
# Esperado: Score~72, F2, TRL6, ODS8/9
CENARIO_3='{
  "experimento": {
    "problema": "Alta rotatividade de funcionários (18% ao ano) impacta produtividade e custos de recontratação, especialmente em áreas técnicas.",
    "hipotese": "Se criarmos clubes de interesse (mangá, livros, games) para funcionários, então reduziremos turnover de 18% para 14%, medido por taxa de desligamento voluntário em 12 meses.",
    "kpi": "Taxa de turnover voluntário anual",
    "baseline": "18% ao ano",
    "alvo": "14% ao ano",
    "plano_teste": "Teste A/B com funcionários de TI e operações, grupo controle vs grupo com acesso a clubes, amostra mínima 1.000 funcionários por grupo, duração 6 meses, enquetes de satisfação anônimas mensais.",
    "riscos_lgpd": "Participação voluntária com consentimento, enquetes anônimas, opt-out sem penalização, retenção de dados por período do experimento, anonimização completa dos resultados.",
    "unidade_gestora": "GERHU - Gerência de Recursos Humanos",
    "patrocinador": "Diretoria de Pessoas e Gestão",
    "dependencias": "Plataforma interna de comunidades, orçamento para atividades",
    "referencias": "Google: programas de bem-estar reduzem turnover em 27% (Harvard Business Review, 2022)"
  }
}'

post_request "/score-api/score" "$CENARIO_3" "CENÁRIO 3: Bem-estar - Clubes de Mangá"

# CENÁRIO 4: LGPD faltando — deve bloquear
# Esperado: Score baixo, bloqueio por LGPD incompleto
CENARIO_4='{
  "experimento": {
    "problema": "Baixa conversão em produtos de investimento para clientes PF, perdendo receita de spread.",
    "hipotese": "Se oferecermos recomendações personalizadas baseadas em histórico, então aumentaremos conversão em 30%.",
    "kpi": "Taxa de conversão em produtos de investimento",
    "baseline": "8%",
    "alvo": "10.4%",
    "plano_teste": "Teste com 50.000 clientes, recomendações via app e email, duração 2 meses.",
    "riscos_lgpd": "Vamos usar os dados dos clientes para personalização.",
    "unidade_gestora": "GEINV - Gerência de Investimentos",
    "patrocinador": "Diretoria Comercial",
    "dependencias": "Sistema de recomendação, base de dados de clientes",
    "referencias": ""
  }
}'

post_request "/score-api/score" "$CENARIO_4" "CENÁRIO 4: LGPD Incompleto (deve bloquear)"

# TESTE DE BUSCA NA KB
echo "--- TESTE: Busca na Base de Conhecimento ---"
get_request "/kb/kb/search?q=LGPD&top_k=3" "Busca por LGPD"
get_request "/kb/kb/search?q=scoring&top_k=2" "Busca por scoring"
get_request "/kb/kb/search?q=metodologia&top_k=3" "Busca por metodologia"

# TESTE DE HEALTH CHECK
get_request "/health" "Health Check"
get_request "/" "Endpoint Raiz"

echo "=== TESTES CONCLUÍDOS ==="
echo "Verifique os resultados acima para validar:"
echo "1. Cenário 1 (Habitação): Score ~70, Fase 2, TRL 6"
echo "2. Cenário 2 (Open Finance): Score ~78, Fase 2+, TRL 7"
echo "3. Cenário 3 (Bem-estar): Score ~72, Fase 2, TRL 6"
echo "4. Cenário 4 (LGPD): Score baixo, bloqueio por LGPD"
echo "5. KB Search: Resultados relevantes"
echo "6. Health: Status healthy"