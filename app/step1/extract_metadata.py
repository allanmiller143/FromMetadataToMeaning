import os
import time
import json
import urllib.parse
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# =========================================================
# Configurações e conexão
# =========================================================
load_dotenv()

PG_USER = os.getenv("PG_USER")
PG_PASS = os.getenv("PG_PASS")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_DB = os.getenv("PG_DB")

if not PG_USER or PG_PASS is None or not PG_DB:
    raise ValueError("Defina PG_USER, PG_PASS e PG_DB no arquivo .env")

PG_PASS_ENC = urllib.parse.quote_plus(PG_PASS)
conn_string = f"postgresql://{PG_USER}:{PG_PASS_ENC}@{PG_HOST}:{PG_PORT}/{PG_DB}"

# =========================================================
# Flags de controle
# =========================================================
GET_COLUMN_STATS = True
TOP_N_FREQUENT_VALUES = 5
SAMPLE_ROWS = 3
RETRY_FAILED_TABLES = True

# =========================================================
# Diretórios e arquivos
# =========================================================
try:
    ROOT_DIR = Path(__file__).resolve().parents[2]
except Exception:
    ROOT_DIR = Path.cwd()
    

DATA_DIR = ROOT_DIR / "data" / 'teixeira'
OUTPUT_DIR = DATA_DIR / "step1_output"
PER_TABLE_DIR = OUTPUT_DIR / "per_table"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PER_TABLE_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_PATH = OUTPUT_DIR / "metadata_checkpoint.json"
METADATA_PATH = OUTPUT_DIR / "metadata.json"
SUMMARY_PATH = OUTPUT_DIR / "tables_summary_advanced.csv"
RUN_STATS_PATH = OUTPUT_DIR / "execution_stats.json"

# =========================================================
# Helpers
# =========================================================
def table_key(schema, table):
    return f"{schema}.{table}"


def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in name)


def atomic_write_json(path, data):
    tmp_path = Path(str(path) + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    tmp_path.replace(path)


def atomic_write_csv(path, df):
    tmp_path = Path(str(path) + ".tmp")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def default_state():
    return {
        "first_started_at": datetime.now().isoformat(),
        "last_update": None,
        "completed_tables": [],
        "failed_tables": [],
        "table_timings": {},
        "table_attempts": {},
        "results_by_table": {}
    }


def load_checkpoint():
    if CHECKPOINT_PATH.exists():
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)

            state.setdefault("first_started_at", datetime.now().isoformat())
            state.setdefault("last_update", None)
            state.setdefault("completed_tables", [])
            state.setdefault("failed_tables", [])
            state.setdefault("table_timings", {})
            state.setdefault("table_attempts", {})
            state.setdefault("results_by_table", {})
            return state

        except Exception as e:
            print(f"Aviso: checkpoint inválido/corrompido: {e}")
            print("Iniciando um novo checkpoint.")

    return default_state()


def write_per_table_file(key, table_result):
    file_name = sanitize_filename(key) + ".json"
    file_path = PER_TABLE_DIR / file_name
    atomic_write_json(file_path, table_result)


def build_results_list(results_by_table):
    return [results_by_table[k] for k in sorted(results_by_table.keys())]


def build_summary_df(results_by_table, table_timings, table_attempts):
    rows = []

    for key in sorted(results_by_table.keys()):
        m = results_by_table[key]
        execution = m.get("execution", {})

        rows.append({
            "schema": m.get("schema"),
            "table": m.get("table_name"),
            "row_count": m.get("row_count"),
            "column_count": len(m.get("columns", [])),
            "pk": "|".join(m.get("primary_key", [])) if isinstance(m.get("primary_key"), list) else "",
            "status": execution.get("status", "unknown"),
            "execution_seconds": execution.get("seconds"),
            "attempts": table_attempts.get(key, 0),
            "processed_at": execution.get("processed_at"),
            "error": m.get("error")
        })

    return pd.DataFrame(rows)


def save_progress(state, total_tables, current_run_started_at, current_run_wall_seconds):
    state["last_update"] = datetime.now().isoformat()

    results_list = build_results_list(state["results_by_table"])
    summary_df = build_summary_df(
        state["results_by_table"],
        state["table_timings"],
        state["table_attempts"]
    )

    atomic_write_json(CHECKPOINT_PATH, state)
    atomic_write_json(METADATA_PATH, results_list)
    atomic_write_csv(SUMMARY_PATH, summary_df)

    successful_tables = len(state["completed_tables"])
    failed_tables = len(state["failed_tables"])
    processed_tables = len(state["results_by_table"])
    accumulated_table_seconds = round(sum(state["table_timings"].values()), 2)
    remaining_tables = max(total_tables - successful_tables, 0)

    run_stats = {
        "checkpoint_started_at": state["first_started_at"],
        "current_run_started_at": current_run_started_at,
        "last_update": state["last_update"],
        "total_tables_detected": total_tables,
        "successful_tables": successful_tables,
        "failed_tables": failed_tables,
        "processed_tables_with_result": processed_tables,
        "remaining_tables": remaining_tables,
        "current_run_wall_seconds": round(current_run_wall_seconds, 2),
        "current_run_wall_minutes": round(current_run_wall_seconds / 60, 2),
        "accumulated_table_seconds": accumulated_table_seconds,
        "accumulated_table_minutes": round(accumulated_table_seconds / 60, 2),
        "average_seconds_per_processed_table": round(
            accumulated_table_seconds / processed_tables, 2
        ) if processed_tables > 0 else 0
    }

    atomic_write_json(RUN_STATS_PATH, run_stats)


# =========================================================
# Conexão e listagem de tabelas
# =========================================================
def connect(engine_str):
    try:
        engine = create_engine(engine_str, pool_pre_ping=True)
        return engine
    except SQLAlchemyError as e:
        print("Erro ao criar engine:", e)
        raise


def list_tables(inspector):
    tables = []
    for schema in inspector.get_schema_names():
        if schema in ("pg_catalog", "information_schema"):
            continue
        for tbl in inspector.get_table_names(schema=schema):
            tables.append((schema, tbl))
    return sorted(tables, key=lambda x: (x[0], x[1]))


# =========================================================
# Estatísticas avançadas de coluna
# =========================================================
def get_column_advanced_stats(conn, schema, table, column_info, row_count):
    col_name = column_info["name"]
    col_type_str = str(column_info["type"]).upper()
    stats = {}

    if row_count == 0:
        return {"error": "Tabela vazia"}

    try:
        q_stats = text(f"""
            SELECT
                COUNT(*) FILTER (WHERE "{col_name}" IS NULL) AS null_count,
                COUNT(DISTINCT "{col_name}") AS distinct_count
            FROM "{schema}"."{table}"
        """)
        result = conn.execute(q_stats).first()

        stats["null_count"] = int(result.null_count)
        stats["distinct_count"] = int(result.distinct_count)
        stats["null_percentage"] = round((stats["null_count"] / row_count) * 100, 2) if row_count > 0 else 0

        if any(t in col_type_str for t in ["INT", "BIGINT", "NUMERIC", "DECIMAL", "REAL", "DOUBLE", "FLOAT"]):
            q_numeric = text(f"""
                SELECT
                    AVG("{col_name}") AS avg_val,
                    MIN("{col_name}") AS min_val,
                    MAX("{col_name}") AS max_val,
                    STDDEV("{col_name}") AS stddev_val
                FROM "{schema}"."{table}"
            """)
            num_result = conn.execute(q_numeric).first()

            stats["numeric_stats"] = {
                "avg": float(num_result.avg_val) if num_result.avg_val is not None else None,
                "min": float(num_result.min_val) if num_result.min_val is not None else None,
                "max": float(num_result.max_val) if num_result.max_val is not None else None,
                "stddev": float(num_result.stddev_val) if num_result.stddev_val is not None else None,
            }

        if TOP_N_FREQUENT_VALUES > 0 and stats.get("distinct_count", 0) < (row_count * 0.5):
            q_freq = text(f"""
                SELECT "{col_name}", COUNT(*) AS frequency
                FROM "{schema}"."{table}"
                WHERE "{col_name}" IS NOT NULL
                GROUP BY "{col_name}"
                ORDER BY frequency DESC
                LIMIT {TOP_N_FREQUENT_VALUES}
            """)
            freq_result = conn.execute(q_freq).fetchall()

            stats["frequent_values"] = [
                {"value": str(row[0]), "count": int(row[1])}
                for row in freq_result
            ]

        q_sample = text(f"""
            SELECT DISTINCT "{col_name}"
            FROM "{schema}"."{table}"
            WHERE "{col_name}" IS NOT NULL
            LIMIT 15
        """)
        sample_result = conn.execute(q_sample).fetchall()
        stats["sample_values"] = [str(row[0]) for row in sample_result]

    except Exception as e:
        error_message = str(e).split("\n")[0]
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        stats["error"] = f"Falha ao analisar coluna: {error_message}"

    return stats


# =========================================================
# Extração de metadados por tabela
# =========================================================
def extract_table_metadata(inspector, conn, schema, table):
    meta = {
        "schema": schema,
        "table_name": table
    }

    fullname = f"{schema}.{table}"

    row_count = 0
    try:
        q_count = text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
        row_count = conn.execute(q_count).scalar()
    except Exception as e:
        print(f"Erro COUNT(*) em {fullname}: {e}")
        row_count = -1

    meta["row_count"] = row_count

    cols_info = inspector.get_columns(table, schema=schema)
    meta["primary_key"] = inspector.get_pk_constraint(table, schema=schema).get("constrained_columns", [])
    meta["foreign_keys"] = inspector.get_foreign_keys(table, schema=schema)

    print(f" -> {fullname}: {row_count} linhas - {len(cols_info)} colunas encontradas")

    processed_columns = []
    for i, col_info in enumerate(cols_info):
        col_data = {
            "name": col_info["name"],
            "type": str(col_info["type"]),
            "nullable": col_info.get("nullable", True)
        }

        print(f" - Processando coluna {i+1}/{len(cols_info)}: {col_data['name']} ({col_data['type']})")

        if GET_COLUMN_STATS and row_count > 0:
            advanced_stats = get_column_advanced_stats(conn, schema, table, col_info, row_count)
            col_data["stats"] = advanced_stats

        processed_columns.append(col_data)

    meta["columns"] = processed_columns

    if SAMPLE_ROWS > 0 and row_count > 0:
        try:
            qs = text(f'SELECT * FROM "{schema}"."{table}" LIMIT :lim')
            sample_df = pd.read_sql(qs, conn, params={"lim": SAMPLE_ROWS})
            meta["sample_rows"] = sample_df.to_dict(orient="records")
        except Exception as e:
            meta["sample_rows"] = [{"error": f"Erro ao obter amostra: {str(e)}"}]
    else:
        meta["sample_rows"] = []

    return meta


# =========================================================
# Main
# =========================================================
def main():
    current_run_started_at = datetime.now().isoformat()
    run_start = time.perf_counter()

    engine = None

    try:
        engine = connect(conn_string)
        inspector = inspect(engine)
        tables = list_tables(inspector)
        total_tables = len(tables)

        state = load_checkpoint()
        completed_tables = set(state["completed_tables"])
        failed_tables = set(state["failed_tables"])

        print(f"PROGRESS_TOTAL:{total_tables}")
        print(f"Tabelas já concluídas: {len(completed_tables)}")
        print(f"Tabelas com falha registradas: {len(failed_tables)}")
        print(f"Retentar falhas: {RETRY_FAILED_TABLES}")

        save_progress(
            state=state,
            total_tables=total_tables,
            current_run_started_at=current_run_started_at,
            current_run_wall_seconds=(time.perf_counter() - run_start)
        )

        for i, (schema, table) in enumerate(tables):
            current_idx = i + 1
            key = table_key(schema, table)

            print(f"PROGRESS_CURRENT:{current_idx}")

            if key in completed_tables:
                print(f" -> Pulando {key}: já processada com sucesso.")
                continue

            if key in failed_tables and not RETRY_FAILED_TABLES:
                print(f" -> Pulando {key}: falha anterior registrada e RETRY_FAILED_TABLES=False.")
                continue

            print(f"\n[{current_idx}/{total_tables}] Processando {key}...")
            table_start = time.perf_counter()
            attempts = state["table_attempts"].get(key, 0) + 1
            state["table_attempts"][key] = attempts

            try:
                with engine.connect() as conn:
                    table_result = extract_table_metadata(inspector, conn, schema, table)

                elapsed = round(time.perf_counter() - table_start, 2)

                table_result["execution"] = {
                    "status": "success",
                    "seconds": elapsed,
                    "processed_at": datetime.now().isoformat(),
                    "attempt": attempts
                }

                state["results_by_table"][key] = table_result
                state["table_timings"][key] = elapsed

                completed_tables.add(key)
                failed_tables.discard(key)

                state["completed_tables"] = sorted(completed_tables)
                state["failed_tables"] = sorted(failed_tables)

                write_per_table_file(key, table_result)

                save_progress(
                    state=state,
                    total_tables=total_tables,
                    current_run_started_at=current_run_started_at,
                    current_run_wall_seconds=(time.perf_counter() - run_start)
                )

                print(f" -> {key} salvo com sucesso em {elapsed:.2f}s")

            except Exception as e:
                elapsed = round(time.perf_counter() - table_start, 2)
                error_message = str(e)

                error_result = {
                    "schema": schema,
                    "table_name": table,
                    "error": error_message,
                    "columns": [],
                    "sample_rows": [],
                    "execution": {
                        "status": "error",
                        "seconds": elapsed,
                        "processed_at": datetime.now().isoformat(),
                        "attempt": attempts
                    }
                }

                state["results_by_table"][key] = error_result
                state["table_timings"][key] = elapsed

                failed_tables.add(key)
                state["completed_tables"] = sorted(completed_tables)
                state["failed_tables"] = sorted(failed_tables)

                write_per_table_file(key, error_result)

                save_progress(
                    state=state,
                    total_tables=total_tables,
                    current_run_started_at=current_run_started_at,
                    current_run_wall_seconds=(time.perf_counter() - run_start)
                )

                print(f" -> ERRO em {key} após {elapsed:.2f}s")
                print(f" -> Mensagem: {error_message}")

        total_wall_seconds = round(time.perf_counter() - run_start, 2)

        save_progress(
            state=state,
            total_tables=total_tables,
            current_run_started_at=current_run_started_at,
            current_run_wall_seconds=total_wall_seconds
        )

        print("\nProcessamento concluído.")
        print(f"Tempo total desta execução: {total_wall_seconds:.2f}s")
        print(f"Tempo acumulado das tabelas: {sum(state['table_timings'].values()):.2f}s")
        print(f"Checkpoint: {CHECKPOINT_PATH}")
        print(f"Metadata consolidado: {METADATA_PATH}")
        print(f"Resumo CSV: {SUMMARY_PATH}")
        print(f"Estatísticas de execução: {RUN_STATS_PATH}")
        print(f"Arquivos por tabela: {PER_TABLE_DIR}")

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()