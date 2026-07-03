import sys
import time
import queue
import subprocess
from pathlib import Path
from threading import Thread

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="EsqueMapa", layout="wide")


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
APP_DIR = ROOT_DIR / "app"


load_dotenv(ROOT_DIR / ".env")



# =========================================================
# SAFE UI HELPERS
# =========================================================
def safe_ui_call(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        return True
    except Exception:
        return False


def enqueue_output(stream, out_queue):
    try:
        for line in iter(stream.readline, ""):
            out_queue.put(line)
    except Exception:
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass


# =========================================================
# SUBPROCESS RUNNER
# =========================================================
def run_script(
    script_path,
    args=None,
    live_output=True,
    progress_bar=None,  # None => não mostra barra
    status_container=None,  # pode ser None
):
    """
    Executa um script externo com barra de progresso opcional.
    A barra só é usada se `progress_bar` e `status_container` forem passados.
    """
    if not Path(script_path).exists():
        st.error(f"Script não encontrado: {script_path}")
        return False

    python_exe = sys.executable or "python"
    cmd = [python_exe, "-u", str(script_path)]

    if args:
        cmd.extend([str(a) for a in args])

    # Saída em blocos de código
    output_container = st.empty()
    error_container = st.empty()

    stdout_queue = queue.Queue()
    stderr_queue = queue.Queue()
    full_stdout = []
    full_stderr = []

    total_items = 0
    current_item = 0

    ui_alive = True
    process = None

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT_DIR),
            bufsize=1,
        )

        stdout_thread = Thread(
            target=enqueue_output,
            args=(process.stdout, stdout_queue),
            daemon=True,
        )
        stderr_thread = Thread(
            target=enqueue_output,
            args=(process.stderr, stderr_queue),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        pending_lines = []
        pending_chars = 0
        last_flush = time.time()

        FLUSH_LINE_COUNT = 20
        FLUSH_CHAR_COUNT = 3000
        FLUSH_SECONDS = 0.4
        MAX_RENDER_LINES = 800

        while True:
            got_data = False

            # Consumir stdout
            while True:
                try:
                    line = stdout_queue.get_nowait()
                    got_data = True
                except queue.Empty:
                    break

                if line.startswith("PROGRESS_TOTAL:"):
                    try:
                        total_items = int(line.split(":", 1)[1].strip())
                    except Exception:
                        pass
                    continue

                if line.startswith("PROGRESS_CURRENT:"):
                    try:
                        current_item = int(line.split(":", 1)[1].strip())
                    except Exception:
                        current_item = 0

                    # Só atualiza barra se foram passados
                    if (
                        ui_alive
                        and total_items > 0
                        and progress_bar is not None
                        and status_container is not None
                    ):
                        ok1 = safe_ui_call(
                            progress_bar.progress,
                            min(current_item / total_items, 1.0),
                        )
                        ok2 = safe_ui_call(
                            status_container.text,
                            f"Processando item {current_item} de {total_items}..."
                        )
                        ui_alive = ok1 and ok2

                    continue

                full_stdout.append(line)
                if live_output:
                    pending_lines.append(line)
                    pending_chars += len(line)

            # Consumir stderr
            while True:
                try:
                    err_line = stderr_queue.get_nowait()
                    full_stderr.append(err_line)
                    got_data = True
                except queue.Empty:
                    break

            # Atualizar em lotes
            should_flush = (
                len(pending_lines) >= FLUSH_LINE_COUNT
                or pending_chars >= FLUSH_CHAR_COUNT
                or (pending_lines and (time.time() - last_flush) >= FLUSH_SECONDS)
            )
            if live_output and ui_alive and should_flush:
                text_to_render = "".join(full_stdout[-MAX_RENDER_LINES:])
                ui_alive = safe_ui_call(output_container.code, text_to_render)
                pending_lines = []
                pending_chars = 0
                last_flush = time.time()

            # Processo terminou?
            if process.poll() is not None:
                break

            if not got_data:
                time.sleep(0.05)

            # Se a UI morreu, encerra o processo
            if not ui_alive:
                try:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                except Exception:
                    pass
                return False

        # Drenar filas restantes
        while True:
            try:
                line = stdout_queue.get_nowait()
                full_stdout.append(line)
            except queue.Empty:
                break

        while True:
            try:
                line = stderr_queue.get_nowait()
                full_stderr.append(line)
            except queue.Empty:
                break

        return_code = process.wait()

        if live_output and ui_alive and full_stdout:
            safe_ui_call(output_container.code, "".join(full_stdout[-MAX_RENDER_LINES:]))

        if (
            ui_alive
            and total_items > 0
            and progress_bar is not None
            and status_container is not None
        ):
            safe_ui_call(progress_bar.progress, 1.0)
            safe_ui_call(status_container.text, "Processamento concluído.")

        stderr_text = "".join(full_stderr).strip()

        if return_code != 0:
            msg = stderr_text or f"Script finalizou com código {return_code}."
            safe_ui_call(error_container.error, f"Erro na execução:\n{msg}")
            return False

        if stderr_text:
            safe_ui_call(
                error_container.warning,
                f"O script gerou mensagens em stderr:\n{stderr_text}"
            )

        return True

    except Exception as e:
        try:
            if process and process.poll() is None:
                process.terminate()
        except Exception:
            pass
        safe_ui_call(error_container.error, f"Erro inesperado: {e}")
        return False


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("EsqueMapa")

step5_output_dir = DATA_DIR / "step5_output"

som_files_exist = any([
    (step5_output_dir / "mapa_interativo_refinado.html").exists(),
    (step5_output_dir / "fig_top_macrothemes.png").exists(),
    (step5_output_dir / "fig_umatrix_hex_colmeia.png").exists(),
])

if som_files_exist:
    steps = [
        "SOM",
        "1. Extração",
        "2. Filtragem",
        "3. LLMs",
        "4. Consistência",
        "Informações Gerais",
    ]
else:
    steps = [
        "1. Extração",
        "2. Filtragem",
        "3. LLMs",
        "4. Consistência",
        "5. SOM",
        "Informações Gerais",
    ]

step = st.sidebar.radio("Selecione o Step:", steps)

# =========================================================
# Informações Gerais
# =========================================================
if step == "Informações Gerais":
    st.title("EsqueMapa")

    st.markdown(
"""
Esta aplicação demonstra um pipeline para **mostrar o que existe em um banco de dados**
com apoio de **Modelos de Linguagem de Grande Escala (LLMs)** e **Mapas Auto-Organizáveis (SOM)**.

A ideia do fluxo é analisar os **metadados das tabelas**, identificar **sobre o que cada tabela trata**
e, depois, agrupar esses temas em uma visão mais ampla da base, facilitando a exploração do conteúdo do banco.
"""
    )

    st.info(
        "A demo foi pensada para funcionar como um pipeline geral. "
        "A lógica pode ser aplicada a diferentes bases de dados, desde que haja acesso aos metadados necessários."
    )

    st.divider()

    st.subheader("O que o pipeline faz")
    st.markdown(
        """
Em vez de depender de documentação manual ou conhecimento prévio do domínio, o pipeline utiliza
**schema**, **estatísticas descritivas**, **características das colunas** e **amostras de dados**
para inferir sobre o conteúdo de cada tabela.

Depois disso, ele compara múltiplas execuções de LLMs para medir consistência e usa **SOM**
para agrupar os temas encontrados em uma estrutura visual e explorável.
"""
    )

    st.divider()

    st.subheader("Etapas")
    st.markdown(
        """
### 1. Extração
Coleta os metadados das tabelas diretamente do banco de dados.
Dependendo da configuração, essa etapa inclui nome do schema, nome da tabela, número de linhas,
chaves, tipos de colunas, nulabilidade, estatísticas descritivas e pequenas amostras de registros.

### 2. Filtragem
Remove tabelas que não agregam valor para a análise, como tabelas vazias ou artefatos que inviabilizam
a interpretação semântica posterior.

### 3. Classificação com LLMs
Envia os metadados de cada tabela para um ou mais modelos de linguagem,
pedindo que eles gerem temas curtos e interpretáveis que representem o conteúdo da tabela.

Essa etapa pode ser executada múltiplas vezes por modelo, o que permite observar
se as respostas permanecem estáveis ou variam entre execuções.

### 4. Consistência
Compara as classificações geradas pelas LLMs usando duas perspectivas:
**lexical**, baseada em palavras exatas, e **semântica**, baseada em embeddings e similaridade conceitual.

Aqui o objetivo é verificar tanto a estabilidade de um mesmo modelo em execuções repetidas
quanto a convergência entre modelos diferentes.

### 5. SOM
Agrupa os temas identificados em uma estrutura topológica bidimensional usando
**Self-Organizing Maps**, facilitando a visualização de macrotemas, regiões densas e relações de proximidade entre conceitos.
"""
    )

    st.divider()

    st.subheader("O que você encontra em cada step")
    st.markdown(
        """
- **Step 1 — Extração:** geração dos arquivos de metadados que representam cada tabela.
- **Step 2 — Filtragem:** limpeza do conjunto de entrada para evitar ruído desnecessário.
- **Step 3 — LLMs:** produção dos temas por tabela para cada modelo e execução.
- **Step 4 — Consistência:** cálculo das métricas de estabilidade e concordância.
- **Step 5 — SOM:** agrupamento temático e visualização da macroestrutura semântica da base.
"""
    )

    st.divider()

    st.subheader("Como usar a demo")
    st.markdown(
        """
Use o menu lateral para navegar entre as etapas do pipeline.
A ideia é acompanhar o fluxo desde a **extração dos metadados** até a **organização temática final**.

Cada etapa produz artefatos intermediários que alimentam a próxima, permitindo observar
não apenas o resultado final, mas também como a informação é transformada ao longo do processo.
"""
    )

# =========================================================
# STEP 1
# =========================================================
elif step == "1. Extração":
    st.header("Step 1: Extração de Metadados")
    st.info("Este step conecta ao banco de dados PostgreSQL configurado no arquivo .env.")

    output_file = DATA_DIR / "step1_output" / "tables_summary_advanced.csv"

    if st.button("Executar Extração"):
        script = APP_DIR / "step1" / "extract_metadata.py"

        # Criar containers e barra APENAS no Step 1
        progress_container = st.empty()
        status_container = st.empty()
        progress_bar = progress_container.progress(0.0)

        with st.spinner("Executando extração..."):
            ok = run_script(
                script,
                live_output=True,
                progress_bar=progress_bar,
                status_container=status_container,
            )

        if ok:
            st.success("Extração concluída!")

    if output_file.exists():
        st.subheader("Resumo das Tabelas Extraídas")
        try:
            df = pd.read_csv(output_file)
            st.write(f"Total de Tabelas: {len(df)}")
            st.dataframe(df, use_container_width=True, height=800)
        except Exception as e:
            st.warning(f"Falha ao abrir o CSV de saída: {e}")


# =========================================================
# STEP 2
# =========================================================
elif step == "2. Filtragem":
    st.header("Step 2: Filtragem de Metadados")
    st.write("Remove tabelas com row_count = 0.")

    if st.button("Executar Filtragem"):
        script = APP_DIR / "step2" / "filter_metadata.py"

        with st.spinner("Executando filtragem..."):
            ok = run_script(script, live_output=True)

        if ok:
            st.success("Filtragem concluída!")

    report_file = DATA_DIR / "step2_output" / "relatorio_filtragem.md"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        except Exception as e:
            st.warning(f"Falha ao abrir relatório: {e}")
# =========================================================
# STEP 3
# =========================================================
elif step == "3. LLMs":
    import json

    st.header("🤖 Step 3: Geração de Temas com LLMs")
    st.markdown(
        """
Execute cada modelo **3 vezes** para avaliar consistência e variabilidade dos resultados.  
Os outputs serão utilizados no Step 4.
"""
    )

    if "running_step3" not in st.session_state:
        st.session_state.running_step3 = False

    def run_all_models():
        models = [
            ("OpenAI (GPT)", "gpt.py"),
            ("DeepSeek", "deepseek.py"),
            ("Mistral", "mistral.py"),
        ]

        total_runs = len(models) * 3
        current_run = 0

        global_progress = st.progress(0)
        status_text = st.empty()
        model_status = {name: st.empty() for name, _ in models}

        for model_name, script_name in models:
            script = APP_DIR / "step3" / script_name
            model_status[model_name].info(f"{model_name} • aguardando execução...")

            for run in range(1, 4):
                status_text.markdown(
                    f"### 🔄 Executando: **{model_name}** • Run {run}/3"
                )
                model_status[model_name].warning(
                    f"{model_name} • executando run {run}/3..."
                )

                with st.spinner(f"{model_name} • Run {run}..."):
                    run_script(script, args=[str(run)], live_output=True)

                model_status[model_name].info(
                    f"{model_name} • concluído {run}/3 runs"
                )

                current_run += 1
                global_progress.progress(current_run / total_runs)

            model_status[model_name].success(
                f"{model_name} finalizado ✅ (3/3 runs)"
            )

        status_text.success("🎉 Todos os modelos foram executados com sucesso!")
        st.session_state.running_step3 = False

    if st.button("▶ Rodar TODOS os modelos", disabled=st.session_state.running_step3):
        st.session_state.running_step3 = True
        run_all_models()

    st.divider()
    st.subheader("📁 Arquivos Gerados")

    st.markdown(
        """
        <style>
        .json-card-container {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e6e9ef;
            border-radius: 5px;
            padding: 18px 18px 14px 18px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
            margin-bottom: 16px;
        }
        .json-card-container::-webkit-scrollbar {
            width: 8px;
        }
        .json-card-container::-webkit-scrollbar-thumb {
            background-color: #d1d5db;
            border-radius: 5px;
        }
        .json-card-container::-webkit-scrollbar-track {
            background-color: #f3f4f6;
        }
        .json-card-title {
            font-size: 1.0rem;
            font-weight: 700;
            word-break: break-word;
            margin-bottom: 12px;
        }
        .json-table-block {
            padding: 5px 12px;
            margin-bottom: 8px;
            border-radius: 12px;
        }
        .json-table-name {
            font-size: 0.88rem;
            font-weight: 600;
            word-break: break-word;
        }
        .json-topics {
            margin: 4px 0 0 0;
            padding-left: 16px;
            font-size: 0.75rem;
            list-style-type: circle;
        }
        .json-topics li {
            margin-bottom: 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    step3_dir = DATA_DIR / "step3_output"
    if step3_dir.exists():
        files = sorted([f for f in step3_dir.glob("*.json") if "temp" not in str(f)])

        if files:
            cols = st.columns(3)

            for i, f in enumerate(files):
                with cols[i % 3]:
                    try:
                        with open(f, "r", encoding="utf-8") as json_file:
                            data = json.load(json_file)

                        # Container com scroll
                        html = "<div class='json-card-container'>"
                        html += f"<div class='json-card-title'>✅ {f.name}</div>"

                        for table_name, topics in data.items():
                            html += "<div class='json-table-block'>"
                            html += f"<div class='json-table-name'>{table_name}</div>"

                            if isinstance(topics, list) and topics:
                                html += "<ul class='json-topics'>"
                                for topic in topics:
                                    html += f"<li>{topic}</li>"
                                html += "</ul>"
                            else:
                                html += "<div class='json-topics'>Sem temas.</div>"

                            html += "</div>"

                        html += "</div>"

                        st.markdown(html, unsafe_allow_html=True)

                    except Exception as e:
                        st.warning(f"Falha ao abrir {f.name}: {e}")
        else:
            st.info("Nenhum arquivo gerado ainda.")
    else:
        st.warning("Diretório de saída ainda não foi criado.")

# =========================================================
# STEP 4
# =========================================================
elif step == "4. Consistência":
    st.header("Step 4: Análise de Consistência")
    st.write("Calcula a similaridade léxica (Hard Dice) e semântica (Soft Dice) entre as execuções.")

    def interpret_dice(value: float) -> str:
        if value >= 0.80:
            return "Muito consistente"
        elif value >= 0.60:
            return "Consistente"
        elif value >= 0.40:
            return "Moderadamente consistente"
        elif value >= 0.20:
            return "Pouco consistente"
        return "Muito pouco consistente"

    def interpret_pair(row) -> str:
        tipo = row["Tipo"]
        alvo = row["Alvo"]
        hard = float(row["HardDice_Lex_mean"])
        soft = float(row["SoftDice_Sem_mean"])
        n = int(row["N_Tabelas"])

        if tipo == "INTRA":
            return (
                f"O modelo {alvo} foi avaliado em {n} tabelas. "
                f"No nível léxico, apresentou Hard Dice médio de {hard:.3f}, "
                f"o que indica {interpret_dice(hard).lower()}. "
                f"No nível semântico, apresentou Soft Dice médio de {soft:.3f}, "
                f"indicando {interpret_dice(soft).lower()}."
            )

        return (
            f"O par {alvo.replace('__VS__', ' vs ')} foi avaliado em {n} tabelas. "
            f"O Hard Dice médio foi {hard:.3f}, sugerindo {interpret_dice(hard).lower()} em termos de palavras exatas. "
            f"O Soft Dice médio foi {soft:.3f}, sugerindo {interpret_dice(soft).lower()} em termos de significado."
        )

    if st.button("Calcular Consistência"):
        script = APP_DIR / "step4" / "step4.py"

        with st.spinner("Calculando consistência..."):
            ok = run_script(script, live_output=True)

        if ok:
            st.success("Análise concluída!")

    output_dir = DATA_DIR / "step4_output"
    if output_dir.exists():
        cols = st.columns(2)

        with cols[0]:
            intra_img = output_dir / "dice_bar_intra.png"
            if intra_img.exists():
                st.image(str(intra_img), caption="Consistência Intra-Modelo")

        with cols[1]:
            inter_img = output_dir / "dice_bar_inter.png"
            if inter_img.exists():
                st.image(str(inter_img), caption="Consistência Inter-Modelo")

        hist_cols = st.columns(2)


        summary_file = output_dir / "summary_consistency.csv"
        if summary_file.exists():
            st.subheader("Resumo de Consistência")
            try:
                df = pd.read_csv(summary_file)
                st.dataframe(df, use_container_width=True)

                st.divider()

                intra_df = df[df["Tipo"] == "INTRA"].copy()
                inter_df = df[df["Tipo"] == "INTER"].copy()

                st.subheader("Como interpretar")

                st.markdown(
                    """
- **Hard Dice** mede a consistência **léxica**, isto é, quantos temas aparecem com palavras iguais entre execuções ou entre modelos.
- **Soft Dice** mede a consistência **semântica**, isto é, o quanto os temas permanecem parecidos em significado mesmo quando mudam as palavras .
- Valores próximos de **1.0** indicam alta similaridade; valores próximos de **0.0** indicam baixa similaridade.
"""
                )

                guide_df = pd.DataFrame(
                    [
                        ["0.80 – 1.00", "Muito consistente / alta similaridade"],
                        ["0.60 – 0.79", "Consistente / boa similaridade"],
                        ["0.40 – 0.59", "Moderadamente consistente"],
                        ["0.20 – 0.39", "Pouco consistente"],
                        ["0.00 – 0.19", "Muito pouco consistente"],
                    ],
                    columns=["Faixa", "Interpretação"],
                )
                st.dataframe(guide_df, use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("Leitura dos resultados")

                intra_df = df[df["Tipo"] == "INTRA"].sort_values("SoftDice_Sem_mean", ascending=False)
                inter_df = df[df["Tipo"] == "INTER"].sort_values("SoftDice_Sem_mean", ascending=False)

                if not intra_df.empty:
                    st.markdown("### Intra-modelo")
                    for _, row in intra_df.iterrows():
                        st.markdown(f"- {interpret_pair(row)}")

                if not inter_df.empty:
                    st.markdown("### Inter-modelos")
                    for _, row in inter_df.iterrows():
                        st.markdown(f"- {interpret_pair(row)}")

                st.divider()
                st.subheader("Leitura rápida")

                if not intra_df.empty:
                    best_semantic_model = intra_df.iloc[0]
                    best_lexical_model = intra_df.sort_values("HardDice_Lex_mean", ascending=False).iloc[0]

                    st.info(
                        f"O modelo mais estável semanticamente foi {best_semantic_model['Alvo']}, "
                        f"com Soft Dice médio de {best_semantic_model['SoftDice_Sem_mean']:.3f}. "
                        f"O mais estável lexicalmente foi {best_lexical_model['Alvo']}, "
                        f"com Hard Dice médio de {best_lexical_model['HardDice_Lex_mean']:.3f}."
                    )

                if not inter_df.empty:
                    best_inter_pair = inter_df.iloc[0]
                    worst_inter_pair = inter_df.iloc[-1]

                    st.info(
                        f"O par de modelos mais próximo semanticamente foi "
                        f"{best_inter_pair['Alvo'].replace('__VS__', ' vs ')}, "
                        f"com Soft Dice médio de {best_inter_pair['SoftDice_Sem_mean']:.3f}. "
                        f"O par mais distante foi "
                        f"{worst_inter_pair['Alvo'].replace('__VS__', ' vs ')}, "
                        f"com Soft Dice médio de {worst_inter_pair['SoftDice_Sem_mean']:.3f}."
                    )

            except Exception as e:
                st.warning(f"Falha ao abrir summary_consistency.csv: {e}")


# =========================================================
# STEP 5
# =========================================================

elif step in ["SOM", "5. SOM"]:
    st.header("Step 5: Mapa Auto-Organizável (SOM)")
    st.write("Geração de clusters temáticos e visualização espacial.")

    output_dir = DATA_DIR / "step5_output"

    if "som_ready" not in st.session_state:
        st.session_state.som_ready = False

    if st.button("Gerar Mapa SOM"):
        script = APP_DIR / "step5" / "SOM.py"

        with st.spinner("Gerando mapa SOM..."):
            ok = run_script(script, live_output=True)

        if ok:
            st.session_state.som_ready = True
            st.success("Mapa gerado com sucesso!")
        else:
            st.error("Erro ao gerar o mapa.")

    if st.session_state.som_ready or output_dir.exists():
        st.subheader("Visualizações")

        tab1, tab2, tab3 = st.tabs(
            ["Mapa Interativo", "Macrotemas", "U-Matrix"]
        )

        with tab1:
            html_file = output_dir / "mapa_interativo_refinado.html"
            if html_file.exists():
                try:
                    with open(html_file, "r", encoding="utf-8") as f:
                        st.components.v1.html(
                            f.read(),
                            height=800,
                            scrolling=True
                        )
                except Exception as e:
                    st.warning(f"Falha ao abrir HTML do mapa: {e}")
            else:
                st.info("Mapa interativo ainda não disponível.")

        with tab2:
            img2 = output_dir / "fig_top_macrothemes.png"
            if img2.exists():
                st.image(str(img2))
            else:
                st.info("Macrotemas ainda não gerados.")

        with tab3:
            img1 = output_dir / "fig_umatrix_hex_colmeia.png"
            if img1.exists():
                st.image(str(img1))
            else:
                st.info("U-Matrix ainda não gerada.")
                              