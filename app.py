# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import math, os

app = FastAPI(title="Sandbox Tools")

# ---------- MODELOS ----------
class ODSItem(BaseModel):
    id: int
    titulo: str
    justificativa: str

class Experimento(BaseModel):
    problema: str
    hipotese: str
    kpi: str
    baseline: str
    alvo: str
    plano_teste: str
    riscos_lgpd: str
    dependencias: Optional[str] = ""
    unidade_gestora: str
    patrocinador: str
    referencias: Optional[str] = ""

class ScoreReq(BaseModel):
    experimento: Experimento

class Breakdown(BaseModel):
    criterio: str
    peso: int
    nota: float
    comentario: str

class ScoreResp(BaseModel):
    score: int
    fase: int
    trl: int
    ods_sugeridos: List[ODSItem]
    breakdown: List[Breakdown]
    parecer_resumido: str

class TicketReq(BaseModel):
    classificacao: str
    resumo_executivo: str
    score: int
    fase: int
    trl: int
    ods: List[ODSItem]
    parecer: str
    proximos_passos: List[str]
    experimento: dict
    anexos: Optional[List[dict]] = []

class TicketResp(BaseModel):
    ticket_id: str
    status_url: str

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
    txt = (exp.problema + " " + exp.hipotese + " " + exp.plano_teste).lower()
    hits = []
    if has_keywords(txt, ["emprego","retenc","trabalho","renda","perman"]):
        hits.append(ODSItem(id=8, titulo="Trabalho decente e crescimento econômico",
                            justificativa="Impacta retenção/produtividade/emprego."))
    if has_keywords(txt, ["inovação","process","autom","efici","digital","open finance","modelo"]):
        hits.append(ODSItem(id=9, titulo="Indústria, inovação e infraestrutura",
                            justificativa="Inovação de processo/tecnologia na operação."))
    if has_keywords(txt, ["trein","capacita","educa","aprend"]):
        hits.append(ODSItem(id=4, titulo="Educação de qualidade",
                            justificativa="Ações de capacitação/educação envolvidas."))
    return hits[:3] or [ODSItem(id=9, titulo="Indústria, inovação e infraestrutura",
                                justificativa="Transformação de processo por experimentação.")]

def avalia(exp: Experimento):
    pesos = {
        "Valor/Viabilidade": 5,
        "Mensuração/KPIs": 4,
        "Aderência & LGPD": 3,
        "Maturidade/Plano": 3,
        "Recursos/UG": 2,
        "Benchmark": 1
    }
    breakdown = []

    # Valor/Viabilidade
    n_valor = 8.0 if len(exp.problema) > 5 else 4.0
    breakdown.append(Breakdown(criterio="Valor/Viabilidade", peso=pesos["Valor/Viabilidade"],
                               nota=n_valor, comentario="Clareza do problema e valor esperado."))

    # Mensuração/KPIs
    n_kpi = 9.0 if exp.kpi and exp.baseline and exp.alvo else 5.0
    breakdown.append(Breakdown(criterio="Mensuração/KPIs", peso=pesos["Mensuração/KPIs"],
                               nota=n_kpi, comentario="KPI/baseline/alvo definidos."))

    # Aderência & LGPD
    lgpd_txt = exp.riscos_lgpd.lower()
    lgpd_ok = all(k in lgpd_txt for k in ["consent", "opt-out", "reten"])
    n_lgpd = 9.0 if lgpd_ok else 5.0
    c_lgpd = "LGPD completo (consentimento/opt-out/retencao)" if lgpd_ok else "Detalhar consentimento/opt-out/retencao"
    breakdown.append(Breakdown(criterio="Aderência & LGPD", peso=pesos["Aderência & LGPD"],
                               nota=n_lgpd, comentario=c_lgpd))

    # Maturidade/Plano
    plano = exp.plano_teste.lower()
    has_ab = "a/b" in plano or "ab " in plano or "ab-" in plano
    has_coorte = "coorte" in plano or "cohort" in plano
    n_plano = 8.5 if (has_ab or has_coorte) else 6.0
    breakdown.append(Breakdown(criterio="Maturidade/Plano", peso=pesos["Maturidade/Plano"],
                               nota=n_plano, comentario="Plano com A/B ou análise por coorte."))

    # Recursos/UG
    n_rec = 8.0 if exp.unidade_gestora and exp.patrocinador else 5.0
    breakdown.append(Breakdown(criterio="Recursos/UG", peso=pesos["Recursos/UG"],
                               nota=n_rec, comentario="UG e patrocinador definidos."))

    # Benchmark
    n_bench = 7.0 if exp.referencias else 5.0
    breakdown.append(Breakdown(criterio="Benchmark", peso=pesos["Benchmark"],
                               nota=n_bench, comentario="Evidências ou referências de apoio."))

    soma = sum(b.nota * b.peso for b in breakdown)
    maximo = sum(10 * (b.peso) for b in breakdown)
    score = int(round((soma / maximo) * 100))
    fase = 3 if score >= 75 else (2 if score >= 50 else 1)
    trl = sugere_trl(exp)
    ods = sugere_ods(exp)
    parecer = "Bom potencial com mensuração adequada; assegurar LGPD e execução pela UG." if score >= 65 else \
              "Necessário amadurecer métricas/Plano/LGPD antes de avançar."

    return ScoreResp(score=score, fase=fase, trl=trl,
                     ods_sugeridos=ods, breakdown=breakdown, parecer_resumido=parecer)

# ---------- ENDPOINTS ----------
@app.post("/score-api/score", response_model=ScoreResp)
def score_endpoint(req: ScoreReq):
    return avalia(req.experimento)

@app.post("/ticket-api/tickets", response_model=TicketResp)
def ticket_endpoint(req: TicketReq):
    # mock simples
    tid = f"TIX-{abs(hash(req.resumo_executivo)) % 10_000_000}"
    base = os.getenv("TICKET_BASE_URL", "https://tickets.sandbox.local")
    return TicketResp(ticket_id=tid, status_url=f"{base}/{tid}")

@app.get("/kb/kb/search")
def kb_search(q: str, top_k: int = 3):
    # mock simples – substitua por busca real no seu índice
    demo = [
        {"titulo":"FAQ — Objetivos","trecho":"O Sandbox é um ambiente seguro para experimentos com governança.","fonte":"FAQ — Objetivos","url":"https://kb/faq#objetivos"},
        {"titulo":"Critérios — Pesos","trecho":"Valor×5; KPIs×4; LGPD×3; Plano×3; Recursos×2; Benchmark×1.","fonte":"Critérios — Pesos","url":"https://kb/criterios#pesos"}
    ]
    return {"hits": demo[:top_k]}
