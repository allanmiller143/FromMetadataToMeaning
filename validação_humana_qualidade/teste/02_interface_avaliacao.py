"""Interface do avaliador.  Rodar:  streamlit run 02_interface_avaliacao.py

- Cada avaliador grava só no próprio arquivo: data/avaliacoes/avaliacao_{id}.jsonl
- O progresso é salvo a cada resposta (tabela atual + etapa atual + respostas parciais).
- Ao reabrir com o mesmo identificador, volta exatamente para a tabela e a etapa em que parou.
- Nada aqui revela modelo, run de origem ou contagem de ocorrências dos temas.
"""
import hashlib
import html
import json
import random
import re
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from common import VAL

st.set_page_config(page_title="Avaliação de temas de tabelas", layout="wide")
st.markdown(
    """<style>
    .block-container{max-width:1200px}
    h1,h2,h3{font-weight:600}
    .tema{font-size:1.9rem;font-weight:700;line-height:1.3;padding:10px 4px 6px 4px;color:#1d4ed8}
    .pergunta{font-size:1.45rem;font-weight:700;line-height:1.35;margin:18px 0 6px 0}
    div[role="radiogroup"] label p{font-size:1.1rem}
    .runlinha{margin:6px 0;padding:8px 10px;border-radius:8px;background:rgba(128,128,128,0.08);line-height:2.2}
    .runrot{display:inline-block;min-width:64px;font-weight:700;margin-right:8px}
    .chip{display:inline-block;padding:3px 12px;margin:2px 6px 2px 0;border-radius:999px;background:#dbeafe;color:#1e3a8a;font-size:1.05rem}
    .passo{padding:6px 12px;border-radius:8px;margin-right:6px;display:inline-block;font-size:0.9rem}
    .passo-ok{background:#d1fae5;color:#065f46}
    .passo-atual{background:#2563eb;color:#fff;font-weight:600}
    .passo-fut{background:#e5e7eb;color:#6b7280}
    </style>""",
    unsafe_allow_html=True,
)

# ---------- escalas ----------
ESCALA = {
    "perfeito": "🌟 Perfeito: Define o núcleo da tabela",
    "adequado": "✅ Adequado: Correto, mas poderia ser mais preciso",
    "impreciso": "⚠️ Impreciso: Toca no assunto, mas erra o foco",
    "errado": "❌ Errado: Não tem relação com os metadados",
}
COMPLETUDE = [
    "Exaustivo: Descreve a tabela perfeitamente, sem omissões",
    "Suficiente: Cobre a função principal, mas omite detalhes secundários",
    "Insuficiente: Falha em capturar a essência ou ignora partes vitais",
    "Nulo: Não descreve a tabela de forma útil",
]
MOTIVOS = ["Paráfrases do mesmo conceito", "Granularidade diferente", "Facetas diferentes, todas válidas",
           "Algum sistema está errado", "Priorizaram colunas diferentes"]
OPCOES_CONSISTENCIA = {
    1: "1: Nada idênticas (muita variação)",
    2: "2: Pouca concordância",
    3: "3: Concordância moderada",
    4: "4: Alta concordância",
    5: "5: Idênticas",
}
OPCOES_CONFIANCA = {
    1: "1: Nada confiante",
    2: "2: Pouca confiança",
    3: "3: Confiança moderada",
    4: "4: Confiante",
    5: "5: Totalmente confiante",
}
OPCOES_COESAO = ["1: um propósito único", "2: um propósito principal e alguns secundários",
                 "3: vários propósitos distintos"]
ETAPAS = ["Contexto e resposta livre", "Julgar cada tema", "Comparar as listas", "Coesão da tabela"]
INSTRUCOES = {
    0: "Leia o contexto da tabela (colunas, chaves, exemplos). **Antes de ver qualquer tema sugerido**, "
       "escreva de 1 a 3 temas (1 a 3 palavras cada) que descrevem a tabela.",
    1: "Cada tema abaixo foi sugerido por algum modelo. Julgue **cada um isoladamente**, "
       "com base apenas nos metadados da tabela. A ordem é aleatória.",
    2: "Agora veja as listas completas de cada sistema (3 execuções por sistema) e responda sobre "
       "consistência e completude.",
    3: "Última etapa: avalie a coesão da tabela e sua confiança geral nas respostas.",
}


# ---------- dados ----------
@st.cache_data
def carregar_itens():
    man = pd.read_csv(VAL / "amostra" / "manifesto_amostra.csv")
    return list(man.sort_values("piloto", ascending=False, kind="stable").item_id), dict(zip(man.item_id, man.piloto))


def tarefa(item_id):
    return json.loads((VAL / "tarefas" / f"tarefa_{item_id}.json").read_text(encoding="utf-8"))


def limpar_id(av):
    return re.sub(r"[^A-Za-z0-9_-]", "_", av.strip().lower())


def arquivo(av):
    return VAL / "avaliacoes" / f"avaliacao_{av}.jsonl"


def registros(av):
    """Último registro de cada item (o arquivo é append-only)."""
    p, out = arquivo(av), {}
    if p.exists():
        for linha in p.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                try:
                    r = json.loads(linha)
                except json.JSONDecodeError:
                    continue                      # linha truncada por queda no meio da escrita
                out[r["item_id"]] = r
    return out


def salvar(rec):
    rec["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (VAL / "avaliacoes").mkdir(parents=True, exist_ok=True)
    with open(arquivo(rec["avaliador"]), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def ordem(av, ids, piloto):
    """Piloto primeiro; o restante em ordem embaralhada e fixa por avaliador."""
    pil = [i for i in ids if piloto[i]]
    resto = [i for i in ids if not piloto[i]]
    random.Random(hashlib.md5(av.encode()).hexdigest()).shuffle(resto)
    return pil + resto


def cronometrar():
    agora = time.time()
    dt = agora - st.session_state.get("t0", agora)
    st.session_state.t0 = agora
    return round(dt, 1)


def pergunta(txt):
    st.markdown(f"<div class='pergunta'>{html.escape(txt)}</div>", unsafe_allow_html=True)


def chips(temas):
    return "".join(f"<span class='chip'>{html.escape(str(t))}</span>" for t in temas)


def ir_para(n):
    """Muda de etapa e grava a posição, para poder retomar exatamente daqui."""
    rec["etapa_atual"] = n
    salvar({**rec, "completo": False})
    st.session_state.etapa = n
    st.session_state.rolar_topo = True
    st.rerun()


# ---------- login ----------
ids, piloto = carregar_itens()
if "av_input" not in st.session_state:
    st.session_state.av_input = st.query_params.get("av", "")
st.sidebar.header("Avaliador")
av = limpar_id(st.sidebar.text_input("Seu identificador (ex.: a1)", key="av_input"))
if not av:
    st.title("Avaliação de temas de tabelas")
    st.write("Informe seu identificador na barra lateral para começar (ou retomar de onde parou).")
    st.stop()
st.query_params["av"] = av          # mantém o login se a página for recarregada

feitos = registros(av)
fila = ordem(av, ids, piloto)
pendentes = [i for i in fila if not feitos.get(i, {}).get("completo")]
n_feitas = len(fila) - len(pendentes)
st.sidebar.progress(n_feitas / len(fila), text=f"Tabela {n_feitas + 1} de {len(fila)} · {n_feitas} concluídas")
if not pendentes:
    st.success("Você concluiu todas as tabelas. Obrigado!")
    st.stop()

item = pendentes[0]
T = tarefa(item)

# (re)inicia o estado quando muda o item ou o avaliador; retoma a etapa salva
if st.session_state.get("item") != item or st.session_state.get("av_ativo") != av:
    salvo = feitos.get(item)
    rec_ini = salvo or {"item_id": item, "avaliador": av, "piloto": bool(T["piloto"]), "tempos": {}}
    rec_ini.setdefault("tempos", {})
    st.session_state.update(item=item, av_ativo=av, rec=rec_ini,
                            etapa=int(rec_ini.get("etapa_atual", 0)), t0=time.time())
    if salvo and salvo.get("etapa_atual", 0) > 0:
        st.toast(f"Retomando a tabela {n_feitas + 1} na etapa {salvo['etapa_atual'] + 1}.", icon="↩️")
rec, etapa = st.session_state.rec, st.session_state.etapa

# ---------- sidebar informativa ----------
with st.sidebar:
    st.markdown(f"**Você:** `{av}`")
    n_pil = sum(1 for i in fila if piloto[i])
    if T["piloto"]:
        st.info(f"Tabela de piloto ({n_feitas + 1}/{n_pil}).")
    st.markdown(f"**Etapa:** {etapa + 1} de {len(ETAPAS)} — {ETAPAS[etapa]}")
    tempos = [v for v in (r.get("tempos", {}).get("e3") for r in feitos.values()) if v]
    st.caption("Suas respostas são salvas automaticamente. Se fechar a janela, digite o mesmo "
               "identificador para voltar exatamente a este ponto.")

# ---------- rolar para o topo ao mudar de etapa/tabela ----------
if st.session_state.pop("rolar_topo", False):
    components.html(
        f"""<script>/* {time.time()} */
        const d = window.parent.document;
        const alvos = [d.querySelector('[data-testid="stMain"]'), d.querySelector('section.main'),
                       d.querySelector('[data-testid="stAppViewContainer"]'), d.scrollingElement, d.documentElement];
        alvos.forEach(a => {{ if (a) {{ a.scrollTop = 0; try {{ a.scrollTo({{top: 0, behavior: 'instant'}}); }} catch (e) {{}} }} }});
        window.parent.scrollTo(0, 0);
        </script>""", height=0)

# ---------- cabeçalho ----------
st.title(T["table_key"] + ("  (piloto)" if T["piloto"] else ""))
st.caption(f"Base: {T.get('base', '—')} · Tabela {n_feitas + 1} de {len(fila)}")
st.markdown(
    "".join(
        f"<span class='passo {'passo-ok' if i < etapa else 'passo-atual' if i == etapa else 'passo-fut'}'>"
        f"{i + 1}. {nome}</span>" for i, nome in enumerate(ETAPAS)),
    unsafe_allow_html=True,
)
st.progress((etapa) / len(ETAPAS))
st.info(INSTRUCOES[etapa])

if etapa > 0 and st.button("⬅️ Voltar etapa"):
    ir_para(etapa - 1)


# ---------- contexto da tabela ----------
def contexto():
    c = T["contexto"]
    cols_df = pd.DataFrame(c["colunas"])
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Tabela", c["tabela"])
    k2.metric("Linhas", f"{c['linhas']:,}".replace(",", ".") if isinstance(c["linhas"], int) else c["linhas"])
    k3.metric("Colunas", len(c["colunas"]))
    k4.metric("Chaves estrangeiras", len(c["fks"]))
    st.write("**Chave primária:** " + (", ".join(c["pk"]) or "não declarada"))
    if c["fks"]:
        st.write("**Chaves estrangeiras:** " + "; ".join(c["fks"]))
    with st.expander(f"Colunas ({len(c['colunas'])}) — tipo, nulos, valores distintos, mais frequentes e amostra",
                     expanded=(etapa == 0)):
        st.dataframe(cols_df.astype(str), use_container_width=True,
                     height=min(60 + 35 * len(c["colunas"]), 560))
    if c["amostra_linhas"]:
        with st.expander("Linhas de exemplo", expanded=(etapa == 0)):
            st.dataframe(pd.DataFrame(c["amostra_linhas"]).astype(str), use_container_width=True)


contexto()
st.divider()

# ---------- etapa 0: resposta livre ----------
if etapa == 0:
    livre = st.text_area("Seus temas, um por linha (1 a 3 temas)",
                         value="\n".join(rec.get("resposta_cega", [])), height=240)
    if st.button("Continuar ➡️"):
        temas = [x.strip() for x in livre.splitlines() if x.strip()]
        if not temas:
            st.error("Escreva pelo menos um tema antes de continuar.")
        else:
            rec["resposta_cega"] = temas[:3]
            rec["tempos"]["e0"] = cronometrar()
            ir_para(1)

# ---------- etapa 1: pool de temas ----------
elif etapa == 1:
    pool = T["pool"][:]
    random.Random(f"{av}-{item}").shuffle(pool)            # ordem fixa por avaliador e tabela
    julgados_antes = rec.get("julgamento_temas", {})

    with st.expander("Legenda da escala", expanded=False):
        for v in ESCALA.values():
            st.write(v)

    resp = {}
    for p in pool:
        nota_ant = julgados_antes.get(p["tema_id"], {}).get("nota")
        idx = list(ESCALA).index(nota_ant) if nota_ant in ESCALA else None
        with st.container(border=True):
            st.caption("Tema sugerido:")
            st.markdown(f"<div class='tema'>{html.escape(p['texto'])}</div>", unsafe_allow_html=True)
            resp[p["tema_id"]] = st.radio(
                p["texto"], list(ESCALA), format_func=lambda x: ESCALA[x],
                index=idx, key=f"n_{av}_{item}_{p['tema_id']}", label_visibility="collapsed")

    n_ok = sum(v is not None for v in resp.values())
    st.sidebar.markdown(f"**Temas julgados:** {n_ok} de {len(resp)}")
    st.sidebar.progress(n_ok / max(len(resp), 1))

    atual = {k: {"nota": v} for k, v in resp.items() if v is not None}
    if atual != julgados_antes:                              # autosave parcial
        rec["julgamento_temas"] = atual
        rec["etapa_atual"] = 1
        salvar({**rec, "completo": False})

    if st.button("Confirmar e continuar ➡️"):
        if n_ok < len(resp):
            st.error(f"Faltam {len(resp) - n_ok} tema(s) para julgar.")
        else:
            rec["julgamento_temas"] = atual
            rec["tempos"]["e1"] = cronometrar()
            ir_para(2)

# ---------- etapa 2: listas ----------
elif etapa == 2:
    salvas = rec.get("listas", {})
    out = {}
    for s, runs in T["listas"].items():
        st.subheader(s)
        st.markdown("".join(f"<div class='runlinha'><span class='runrot'>Run {r}</span>{chips(runs[r])}</div>"
                            for r in sorted(runs)), unsafe_allow_html=True)

        v_intra = salvas.get(s, {}).get("intra")
        v_comp = salvas.get(s, {}).get("completude")
        c1, c2 = st.columns(2)
        with c1:
            pergunta(f"As 3 runs do {s} dizem essencialmente a mesma coisa?")
            intra = st.radio(f"intra {s}", list(OPCOES_CONSISTENCIA), format_func=lambda x: OPCOES_CONSISTENCIA[x],
                             index=list(OPCOES_CONSISTENCIA).index(v_intra) if v_intra in OPCOES_CONSISTENCIA else None,
                             key=f"i_{av}_{item}_{s}", label_visibility="collapsed")
        with c2:
            pergunta(f"O conjunto de temas do {s} cobre o que a tabela é?")
            comp = st.radio(f"completude {s}", COMPLETUDE,
                            index=COMPLETUDE.index(v_comp) if v_comp in COMPLETUDE else None,
                            key=f"c_{av}_{item}_{s}", label_visibility="collapsed")
        out[s] = {"intra": intra, "completude": comp}
        st.divider()

    v_inter = rec.get("inter")
    pergunta("Os três sistemas dizem essencialmente a mesma coisa?")
    inter = st.radio("inter", list(OPCOES_CONSISTENCIA),
                     format_func=lambda x: OPCOES_CONSISTENCIA[x],
                     index=list(OPCOES_CONSISTENCIA).index(v_inter) if v_inter in OPCOES_CONSISTENCIA else None,
                     key=f"inter_{av}_{item}", label_visibility="collapsed")
    pergunta("Se há diferenças, por quê?")
    motivos = st.multiselect("motivos", MOTIVOS, default=rec.get("motivos", []),
                             key=f"mot_{av}_{item}", label_visibility="collapsed")

    # autosave parcial
    parcial = {s: {k: v for k, v in d.items() if v is not None} for s, d in out.items()}
    if parcial != salvas or inter != v_inter or motivos != rec.get("motivos", []):
        rec.update(listas=parcial, motivos=motivos, etapa_atual=2)
        if inter is not None:
            rec["inter"] = inter
        salvar({**rec, "completo": False})

    if st.button("Confirmar e continuar ➡️"):
        faltam = any(d["intra"] is None or d["completude"] is None for d in out.values()) or inter is None
        if faltam:
            st.error("Responda consistência e completude de cada sistema, e a pergunta entre sistemas.")
        else:
            rec.update(listas=out, inter=inter, motivos=motivos)
            rec["tempos"]["e2"] = cronometrar()
            ir_para(3)

# ---------- etapa 3: coesão ----------
else:
    v_coe = rec.get("coesao")
    pergunta("Esta tabela tem…")
    coesao = st.radio("coesão", OPCOES_COESAO, index=v_coe - 1 if v_coe in (1, 2, 3) else None,
                      key=f"coe_{av}_{item}", label_visibility="collapsed")
    v_conf = rec.get("confianca")
    pergunta("Sua confiança geral nesta tabela")
    conf = st.radio("confiança", list(OPCOES_CONFIANCA),
                    format_func=lambda x: OPCOES_CONFIANCA[x],
                    index=list(OPCOES_CONFIANCA).index(v_conf) if v_conf in OPCOES_CONFIANCA else None,
                    key=f"conf_{av}_{item}", label_visibility="collapsed")
    pergunta("Comentário (opcional)")
    com = st.text_area("comentário", value=rec.get("comentario", ""), key=f"com_{av}_{item}",
                       height=140, label_visibility="collapsed")

    if st.button("✅ Concluir tabela"):
        if coesao is None or conf is None:
            st.error("Selecione a coesão e a sua confiança.")
        else:
            rec.update(coesao=int(coesao[0]), confianca=conf, comentario=com, completo=True, etapa_atual=3)
            rec["tempos"]["e3"] = cronometrar()
            salvar(rec)
            st.session_state.item = None      # força carregar a próxima tabela pendente
            st.session_state.rolar_topo = True
            st.rerun()