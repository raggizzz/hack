# app.py - Agente Validador do Sandbox CAIXA
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import math, os, uuid, datetime
from enum import Enum

app = FastAPI(
    title="Agente Validador do Sandbox CAIXA",
    description="API para validação de experimentos com scoring automático, criação de tickets e busca na base de conhecimento. Reduz decisão de ideias de 90 dias para 1 dia (p95).",
    version="1.0.0",
    contact={
        "name": "Sandbox CAIXA",
        "email": "sandbox@caixa.gov.br"
    }
)

# ---------- MODELOS ----------
class ClassificacaoEnum(str, Enum):
    RECLAMACAO = "Reclamacao"
    SUGESTAO = "Sugestao"
    EXPERIMENTO = "Experimento"

class ODSItem(BaseModel):
    id: int = Field(..., description="ID do ODS (1-17)")
    titulo: str = Field(..., description="Título do Objetivo de Desenvolvimento Sustentável")
    justificativa: str = Field(..., description="Justificativa de 1 linha para aplicação do ODS")

class Experimento(BaseModel):
    problema: str = Field(..., description="Descrição clara do problema a ser resolvido")
    hipotese: str = Field(..., description="Hipótese no formato 'Se... então... medido por...'")
    kpi: str = Field(..., description="Indicador-chave de performance a ser medido")
    baseline: str = Field(..., description="Valor atual/baseline do KPI")
    alvo: str = Field(..., description="Meta/objetivo a ser alcançado")
    plano_teste: str = Field(..., description="Plano detalhado: quem/como/onde/tempo; amostra; A/B")
    riscos_lgpd: str = Field(..., description="Análise LGPD: consentimento, escopo, opt-out, retenção, minimização")
    dependencias: Optional[str] = Field("", description="Dependências técnicas ou de negócio")
    unidade_gestora: str = Field(..., description="Unidade gestora responsável")
    patrocinador: str = Field(..., description="Patrocinador/sponsor do experimento")
    referencias: Optional[str] = Field("", description="Referências, benchmarks ou evidências de apoio")

class ScoreReq(BaseModel):
    experimento: Experimento = Field(..., description="Dados do experimento para scoring")

class Breakdown(BaseModel):
    criterio: str = Field(..., description="Nome do critério avaliado")
    peso: int = Field(..., description="Peso do critério (1-5)")
    nota: float = Field(..., description="Nota obtida (0-10)")
    comentario: str = Field(..., description="Comentário explicativo da avaliação")

class ScoreResp(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score final (0-100)")
    fase: int = Field(..., ge=1, le=3, description="Fase recomendada: 1=Inicial, 2=Piloto, 3=Produção")
    trl: int = Field(..., ge=1, le=9, description="Technology Readiness Level (1-9)")
    ods_sugeridos: List[ODSItem] = Field(..., description="Objetivos de Desenvolvimento Sustentável aplicáveis")
    breakdown: List[Breakdown] = Field(..., description="Detalhamento da avaliação por critério")
    parecer_resumido: str = Field(..., description="Parecer resumido da análise")

class TicketReq(BaseModel):
    classificacao: ClassificacaoEnum = Field(..., description="Tipo de entrada: Reclamacao, Sugestao ou Experimento")
    resumo_executivo: str = Field(..., description="Resumo executivo (5-8 linhas)")
    score: int = Field(..., ge=0, le=100, description="Score obtido na avaliação")
    fase: int = Field(..., ge=1, le=3, description="Fase recomendada")
    trl: int = Field(..., ge=1, le=9, description="Technology Readiness Level")
    ods: List[ODSItem] = Field(..., description="Objetivos de Desenvolvimento Sustentável")
    parecer: str = Field(..., description="Parecer detalhado da análise")
    proximos_passos: List[str] = Field(..., description="Lista de próximos passos recomendados")
    experimento: dict = Field(..., description="Dados completos do experimento")
    anexos: Optional[List[dict]] = Field([], description="Lista de anexos (nome, url)")

class TicketResp(BaseModel):
    ticket_id: str = Field(..., description="ID único do ticket criado")
    status_url: str = Field(..., description="URL para acompanhamento do status")

class KBHit(BaseModel):
    titulo: str = Field(..., description="Título do documento")
    trecho: str = Field(..., description="Trecho relevante encontrado")
    fonte: str = Field(..., description="Fonte do documento (ex: FAQ — Objetivos)")
    url: str = Field(..., description="URL do documento completo")

class KBSearchResp(BaseModel):
    hits: List[KBHit] = Field(..., description="Resultados da busca na base de conhecimento")

# ---------- HELPERS ----------
def has_keywords(text, ks):
    t = text.lower()
    return any(k in t for k in ks)

def nota_cap(max10, cond, bonus=0):
    return min(10.0, max(0.0, (max10 + bonus) if cond else max10))

def sugere_trl(exp: Experimento):
    t = (exp.plano_teste + " " + exp.referencias).lower()
    if "produção" in t or "producao" in t or "integrado" in t or "integração" in t:
        return 8
    if "piloto" in t or "a/b" in t or "coorte" in t:
        return 6
    if "poc" in t or "prova de conceito" in t or "homolog" in t:
        return 5
    return 4

def sugere_ods(exp: Experimento):
    """Sugere ODSs baseado no conteúdo do experimento, priorizando 8, 9 e 4 conforme especificação."""
    txt = (exp.problema + " " + exp.hipotese + " " + exp.plano_teste).lower()
    hits = []
    
    # ODS 8 - Trabalho decente (prioridade alta)
    if has_keywords(txt, ["emprego","retenc","trabalho","renda","perman","colaborador","funcionario"]):
        hits.append(ODSItem(id=8, titulo="Trabalho decente e crescimento econômico",
                            justificativa="Impacta retenção, produtividade e qualidade do trabalho."))
    
    # ODS 9 - Inovação (prioridade alta)
    if has_keywords(txt, ["inovação","process","autom","efici","digital","open finance","modelo","tecnolog","ia","api"]):
        hits.append(ODSItem(id=9, titulo="Indústria, inovação e infraestrutura",
                            justificativa="Inovação de processo/tecnologia na operação bancária."))
    
    # ODS 4 - Educação (prioridade alta)
    if has_keywords(txt, ["trein","capacita","educa","aprend","conhecimento","skill"]):
        hits.append(ODSItem(id=4, titulo="Educação de qualidade",
                            justificativa="Ações de capacitação e desenvolvimento envolvidas."))
    
    # Outros ODSs com justificativa específica
    if has_keywords(txt, ["sustent","ambient","verde","carbon","clima"]):
        hits.append(ODSItem(id=13, titulo="Ação contra a mudança global do clima",
                            justificativa="Contribui para sustentabilidade e responsabilidade ambiental."))
    
    if has_keywords(txt, ["inclusão","acessib","diversid","equidad","social"]):
        hits.append(ODSItem(id=10, titulo="Redução das desigualdades",
                            justificativa="Promove inclusão e redução de desigualdades sociais."))
    
    # Fallback padrão se nenhum ODS específico for identificado
    return hits[:3] or [ODSItem(id=9, titulo="Indústria, inovação e infraestrutura",
                                justificativa="Transformação de processo por experimentação controlada.")]

def avalia(exp: Experimento):
    """Avalia experimento conforme rubrica: Valor×5, KPIs×4, LGPD×3, Plano×3, Recursos×2, Benchmark×1"""
    pesos = {
        "Valor/Viabilidade": 5,
        "Mensuração/KPIs": 4,
        "Aderência & LGPD": 3,
        "Maturidade/Plano": 3,
        "Recursos/UG": 2,
        "Benchmark": 1
    }
    breakdown = []

    # Valor/Viabilidade (peso 5) - Clareza do problema e impacto esperado
    problema_claro = len(exp.problema.strip()) > 20
    hipotese_estruturada = "se" in exp.hipotese.lower() and "então" in exp.hipotese.lower()
    n_valor = 9.0 if (problema_claro and hipotese_estruturada) else (7.0 if problema_claro else 4.0)
    breakdown.append(Breakdown(criterio="Valor/Viabilidade", peso=pesos["Valor/Viabilidade"],
                               nota=n_valor, comentario="Problema claro e hipótese bem estruturada." if n_valor >= 7 else "Detalhar problema e estruturar hipótese."))

    # Mensuração/KPIs (peso 4) - Baseline, meta e KPI definidos
    tem_baseline = exp.baseline and len(exp.baseline.strip()) > 2
    tem_alvo = exp.alvo and len(exp.alvo.strip()) > 2
    tem_kpi = exp.kpi and len(exp.kpi.strip()) > 5
    n_kpi = 9.5 if (tem_baseline and tem_alvo and tem_kpi) else (6.0 if tem_kpi else 3.0)
    breakdown.append(Breakdown(criterio="Mensuração/KPIs", peso=pesos["Mensuração/KPIs"],
                               nota=n_kpi, comentario="KPI, baseline e alvo bem definidos." if n_kpi >= 8 else "Completar KPI/baseline/alvo."))

    # Aderência & LGPD (peso 3) - Conformidade LGPD obrigatória
    lgpd_txt = exp.riscos_lgpd.lower()
    tem_consentimento = any(k in lgpd_txt for k in ["consent", "consentimento", "autoriza"])
    tem_optout = "opt-out" in lgpd_txt or "opt out" in lgpd_txt or "cancelar" in lgpd_txt
    tem_retencao = any(k in lgpd_txt for k in ["reten", "prazo", "tempo", "período"])
    tem_minimizacao = any(k in lgpd_txt for k in ["minim", "anonimiz", "pseudonim", "mascarar"])
    lgpd_completo = tem_consentimento and tem_optout and tem_retencao
    n_lgpd = 9.0 if lgpd_completo and tem_minimizacao else (7.0 if lgpd_completo else 4.0)
    c_lgpd = "LGPD completo: consentimento, opt-out, retenção e minimização." if n_lgpd >= 8 else "Completar análise LGPD (consentimento/opt-out/retenção)."
    breakdown.append(Breakdown(criterio="Aderência & LGPD", peso=pesos["Aderência & LGPD"],
                               nota=n_lgpd, comentario=c_lgpd))

    # Maturidade/Plano (peso 3) - Metodologia e execução
    plano = exp.plano_teste.lower()
    has_ab = any(k in plano for k in ["a/b", "ab ", "ab-", "teste a/b"])
    has_coorte = any(k in plano for k in ["coorte", "cohort", "grupo controle"])
    has_amostra = any(k in plano for k in ["amostra", "sample", "participantes", "usuários"])
    has_tempo = any(k in plano for k in ["semana", "mês", "dia", "prazo", "duração"])
    metodologia_robusta = (has_ab or has_coorte) and has_amostra and has_tempo
    n_plano = 9.0 if metodologia_robusta else (7.0 if (has_ab or has_coorte) else 5.0)
    breakdown.append(Breakdown(criterio="Maturidade/Plano", peso=pesos["Maturidade/Plano"],
                               nota=n_plano, comentario="Metodologia robusta com A/B, amostra e cronograma." if n_plano >= 8 else "Detalhar metodologia (A/B/coorte, amostra, tempo)."))

    # Recursos/UG (peso 2) - Governança e patrocínio
    tem_ug = exp.unidade_gestora and len(exp.unidade_gestora.strip()) > 3
    tem_patrocinador = exp.patrocinador and len(exp.patrocinador.strip()) > 3
    n_rec = 8.5 if (tem_ug and tem_patrocinador) else (6.0 if tem_ug else 3.0)
    breakdown.append(Breakdown(criterio="Recursos/UG", peso=pesos["Recursos/UG"],
                               nota=n_rec, comentario="UG e patrocinador claramente definidos." if n_rec >= 7 else "Definir UG responsável e patrocinador."))

    # Benchmark (peso 1) - Evidências e referências
    tem_referencias = exp.referencias and len(exp.referencias.strip()) > 10
    tem_dependencias = exp.dependencias and len(exp.dependencias.strip()) > 5
    n_bench = 8.0 if tem_referencias else (6.0 if tem_dependencias else 5.0)
    breakdown.append(Breakdown(criterio="Benchmark", peso=pesos["Benchmark"],
                               nota=n_bench, comentario="Referências e evidências de apoio identificadas." if n_bench >= 7 else "Incluir referências ou benchmarks."))

    # Cálculo final
    soma = sum(b.nota * b.peso for b in breakdown)
    maximo = sum(10 * b.peso for b in breakdown)
    score = int(round((soma / maximo) * 100))
    
    # Determinação de fase: F3≥75, F2=50-74, F1<50
    if score >= 75:
        fase = 3
    elif score >= 50:
        fase = 2
    else:
        fase = 1
    
    trl = sugere_trl(exp)
    ods = sugere_ods(exp)
    
    # Parecer baseado no score e critérios críticos
    if score >= 75:
        parecer = "Experimento maduro, pronto para fase avançada. LGPD conforme, metodologia robusta."
    elif score >= 65:
        parecer = "Bom potencial, requer ajustes menores em LGPD ou metodologia antes do piloto."
    elif score >= 50:
        parecer = "Potencial identificado, necessário amadurecer métricas e plano de execução."
    else:
        parecer = "Experimento inicial, requer desenvolvimento significativo antes de prosseguir."

    return ScoreResp(score=score, fase=fase, trl=trl,
                     ods_sugeridos=ods, breakdown=breakdown, parecer_resumido=parecer)

# ---------- ENDPOINTS ----------
@app.post(
    "/score-api/score",
    response_model=ScoreResp,
    summary="Avaliação de Experimento",
    description="Calcula score (0-100), fase (1/2/3), TRL (1-9) e análise detalhada por critério. SLA: ≤1min.",
    tags=["Scoring"]
)
def score_endpoint(req: ScoreReq):
    """Endpoint principal para scoring de experimentos conforme rubrica CAIXA."""
    try:
        resultado = avalia(req.experimento)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no scoring: {str(e)}")

@app.post(
    "/ticket-api/tickets",
    response_model=TicketResp,
    summary="Criação de Ticket",
    description="Cria ticket no sistema de acompanhamento com JSON interno anexado. SLA: ≤1min.",
    tags=["Tickets"]
)
def ticket_endpoint(req: TicketReq):
    """Cria ticket de acompanhamento com dados completos da decisão."""
    try:
        # Gera ID único baseado em timestamp e hash
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
        hash_content = abs(hash(req.resumo_executivo + str(req.score))) % 10000
        tid = f"SBX-{timestamp}-{hash_content:04d}"
        
        base_url = os.getenv("TICKET_BASE_URL", "https://tickets.sandbox.caixa.gov.br")
        status_url = f"{base_url}/ticket/{tid}"
        
        # Em produção, aqui seria feita a integração real com sistema de tickets
        # incluindo anexo do JSON completo da decisão
        
        return TicketResp(ticket_id=tid, status_url=status_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na criação do ticket: {str(e)}")

@app.get(
    "/kb/kb/search",
    response_model=KBSearchResp,
    summary="Busca na Base de Conhecimento",
    description="Busca semântica na KB do Sandbox retornando top-k trechos citáveis. SLA: ≤30s.",
    tags=["Knowledge Base"]
)
def kb_search(
    q: str = Query(..., description="Termo de busca", min_length=2),
    top_k: int = Query(3, description="Número máximo de resultados", ge=1, le=10)
):
    """Busca na base de conhecimento do Sandbox CAIXA."""
    try:
        if len(q.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query deve ter pelo menos 2 caracteres")
        
        # Base de conhecimento simulada - em produção seria integração real
        kb_data = [
            KBHit(
                titulo="FAQ — Objetivos do Sandbox",
                trecho="O Sandbox CAIXA é um ambiente controlado para experimentação com governança, visando reduzir o tempo de decisão de 90 dias para 1 dia (p95).",
                fonte="FAQ — Objetivos",
                url="https://kb.sandbox.caixa.gov.br/faq#objetivos"
            ),
            KBHit(
                titulo="Critérios de Avaliação — Pesos",
                trecho="Rubrica de scoring: Valor/Viabilidade×5; Mensuração/KPIs×4; Aderência & LGPD×3; Maturidade/Plano×3; Recursos/UG×2; Benchmark×1.",
                fonte="Critérios — Pesos",
                url="https://kb.sandbox.caixa.gov.br/criterios#pesos"
            ),
            KBHit(
                titulo="LGPD — Requisitos Obrigatórios",
                trecho="Todo experimento deve especificar: consentimento, escopo de dados, mecanismo de opt-out, período de retenção e estratégias de minimização/anonimização.",
                fonte="LGPD — Compliance",
                url="https://kb.sandbox.caixa.gov.br/lgpd#requisitos"
            ),
            KBHit(
                titulo="Metodologia A/B — Boas Práticas",
                trecho="Testes A/B devem definir: hipótese clara, amostra representativa (≥1000), duração adequada, métricas primárias/secundárias e critérios de parada.",
                fonte="Metodologia — A/B Testing",
                url="https://kb.sandbox.caixa.gov.br/metodologia#ab-testing"
            ),
            KBHit(
                titulo="ODS Prioritários — Diretrizes",
                trecho="Priorizar ODS 8 (Trabalho decente), ODS 9 (Inovação) e ODS 4 (Educação). Outros ODSs requerem justificativa específica de 1 linha.",
                fonte="ODS — Diretrizes",
                url="https://kb.sandbox.caixa.gov.br/ods#diretrizes"
            )
        ]
        
        # Busca simples por palavras-chave (em produção seria busca semântica)
        query_lower = q.lower()
        resultados = []
        for item in kb_data:
            if any(palavra in item.trecho.lower() or palavra in item.titulo.lower() 
                   for palavra in query_lower.split()):
                resultados.append(item)
        
        # Retorna top_k resultados
        hits = resultados[:top_k] if resultados else kb_data[:top_k]
        
        return KBSearchResp(hits=hits)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca KB: {str(e)}")

# ---------- HEALTH CHECK ----------
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint para monitoramento."""
    return {
        "status": "healthy",
        "service": "Agente Validador Sandbox CAIXA",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/", tags=["System"])
def root():
    """Endpoint raiz com informações básicas."""
    return {
        "service": "Agente Validador do Sandbox CAIXA",
        "description": "API para validação de experimentos - 90 dias → 1 dia (p95)",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "scoring": "/score-api/score",
            "tickets": "/ticket-api/tickets",
            "knowledge_base": "/kb/kb/search"
        }
    }
