import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import requests
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / 'magento2'
METADATA_PATH = DATA_DIR / "step2_output" / "metadata.json"
OUTPUT_DIR = DATA_DIR / "step3_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DO MODELO LOCAL (Ollama)
# ---------------------------------------------------------------------------
# Instale o Ollama (https://ollama.com) e baixe o modelo antes de rodar:
#   ollama pull qwen2.5:7b-instruct
#
# Rodando num Nitro V15 (RTX 4050 6GB VRAM + 24GB RAM), o qwen2.5:7b-instruct
# é o melhor equilíbrio entre qualidade e velocidade (cabe quase todo na GPU).
#
# Para trocar de modelo, baixe outro com `ollama pull <nome>` e mude a
# variável abaixo. Alguns candidatos, do mais leve ao mais pesado:
#   - llama3.2:3b-instruct      (muito rápido, qualidade menor)
#   - qwen2.5:7b-instruct       (recomendado para essa GPU)
#   - llama3.1:8b-instruct
#   - qwen2.5:14b-instruct      (mais lento nessa GPU, faz offload p/ CPU)
# ---------------------------------------------------------------------------
MODEL_NAME = os.getenv("LOCAL_MODEL", "qwen2.5:7b-instruct")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

RUN = int(sys.argv[1]) if len(sys.argv) > 1 else 1
# nome de arquivo "seguro" (troca ':' por '-')
MODEL_TAG = MODEL_NAME.replace(":", "-").replace("/", "-")
DESCRIPTIONS_PATH = OUTPUT_DIR / f"table_descriptions_{MODEL_TAG}_{RUN}.json"
TOPICS_PATH = OUTPUT_DIR / f"table_topics_{MODEL_TAG}_{RUN}.json"

# Delay entre chamadas. Rodando local não existe rate limit de API, mas um
# pequeno respiro evita saturar a GPU/CPU em lotes muito longos.
SLEEP_BETWEEN_CALLS = float(os.getenv("SLEEP_BETWEEN_CALLS", "0.2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "300"))  # modelos locais podem demorar mais



def check_ollama_running():
    """Confere se o Ollama está de pé e se o modelo está baixado."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(
            "Não consegui falar com o Ollama em http://localhost:11434. "
            "Ele está rodando? (tente `ollama serve` ou abra o app Ollama). "
            f"Erro original: {e}"
        )

    models = [m.get("name") for m in r.json().get("models", [])]
    # o Ollama às vezes lista com ':latest' implícito
    if MODEL_NAME not in models and f"{MODEL_NAME}:latest" not in models:
        print(f"  [AVISO] Modelo '{MODEL_NAME}' não encontrado localmente. "
              f"Rode: ollama pull {MODEL_NAME}")
        print(f"  Modelos disponíveis: {models}")



def load_metadata() -> List[Dict[str, Any]]:
    with METADATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)



def summarize_table(table_meta: Dict[str, Any]) -> str:
    schema = table_meta.get("schema")
    table_name = table_meta.get("table_name")
    row_count = table_meta.get("row_count")

    cols = table_meta.get("columns", [])
    col_samples = []
    for c in cols:
        col_samples.append({
            "name": c.get("name"),
            "type": c.get("type"),
            "nullable": c.get("nullable"),
            "stats": c.get("stats", {})
        })

    fk_info = []
    for fk in table_meta.get("foreign_keys", []):
        fk_info.append({
            "constrained_columns": fk.get("constrained_columns"),
            "referred_table": f"{fk.get('referred_schema')}.{fk.get('referred_table')}",
            "referred_columns": fk.get("referred_columns")
        })

    summary = {
        "schema": schema,
        "table_name": table_name,
        "row_count": row_count,
        "primary_key": table_meta.get("primary_key"),
        "foreign_keys": fk_info,
        "columns": col_samples,
        "sample_rows": table_meta.get("sample_rows", [])[:3]
    }

    return json.dumps(summary, ensure_ascii=False)



def truncate_value(value, max_len=120):
    if value is None:
        return None
    value_str = str(value)
    if len(value_str) > max_len:
        return value_str[:max_len] + "..."
    return value_str



def summarize_table_compact(table_meta: Dict[str, Any]) -> str:
    schema = table_meta.get("schema")
    table_name = table_meta.get("table_name")
    row_count = table_meta.get("row_count")

    cols = table_meta.get("columns", [])
    col_samples = []
    for c in cols[:15]:
        stats = c.get("stats", {})
        compact_stats = {}

        if isinstance(stats, dict):
            for key in ["null_count", "distinct_count", "null_percentage", "min", "max", "mean", "avg"]:
                if key in stats:
                    compact_stats[key] = stats[key]

            sample_values = stats.get("sample_values", [])
            if isinstance(sample_values, list):
                compact_stats["sample_values"] = [
                    truncate_value(v, 60) for v in sample_values[:3]
                ]

            frequent_values = stats.get("frequent_values", [])
            if isinstance(frequent_values, list):
                compact_stats["frequent_values"] = frequent_values[:3]

        col_samples.append({
            "name": c.get("name"),
            "type": c.get("type"),
            "nullable": c.get("nullable"),
            "stats": compact_stats
        })

    fk_info = []
    for fk in table_meta.get("foreign_keys", [])[:10]:
        fk_info.append({
            "constrained_columns": fk.get("constrained_columns"),
            "referred_table": f"{fk.get('referred_schema')}.{fk.get('referred_table')}",
            "referred_columns": fk.get("referred_columns")
        })

    compact_sample_rows = []
    for row in table_meta.get("sample_rows", [])[:1]:
        if isinstance(row, dict):
            compact_row = {}
            for k, v in row.items():
                compact_row[k] = truncate_value(v, 80)
            compact_sample_rows.append(compact_row)
        else:
            compact_sample_rows.append(truncate_value(row, 80))

    summary = {
        "schema": schema,
        "table_name": table_name,
        "row_count": row_count,
        "primary_key": table_meta.get("primary_key"),
        "foreign_keys": fk_info,
        "columns": col_samples,
        "sample_rows": compact_sample_rows
    }

    return json.dumps(summary, ensure_ascii=False)



def is_context_limit_error(e: Exception) -> bool:
    error_msg = str(e).lower()
    terms = [
        "token", "tokens", "context", "context length", "too many tokens",
        "too large", "prompt is too long", "input is too long",
        "context_length_exceeded", "400", "request body too large",
        "payload too large",
    ]
    return any(term in error_msg for term in terms)



def call_local_model(prompt: str, system_prompt: str, temperature: float = TEMPERATURE,
                      max_tokens: int = 180) -> str:
    text, _, _ = call_local_model_with_meta(prompt, system_prompt, temperature, max_tokens)
    return text



def call_local_model_with_meta(prompt: str, system_prompt: str, temperature: float = TEMPERATURE,
                                max_tokens: int = 180) -> tuple:
    """Chama o Ollama local (API /api/chat) com retry simples para erros
    transitórios (o modelo pode ainda estar carregando na GPU, por exemplo)."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }

    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            text = data.get("message", {}).get("content", "").strip()
            tokens_in = data.get("prompt_eval_count", 0) or 0
            tokens_out = data.get("eval_count", 0) or 0
            return text, tokens_in, tokens_out

        except requests.exceptions.RequestException as e:
            last_exception = e
            wait = 2 ** attempt
            print(f"    [ERRO] {e}. Aguardando {wait:.1f}s (tentativa {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(wait)

    raise Exception(f"Falha após {MAX_RETRIES} tentativas. Último erro: {last_exception}")



PROMPT_TEMPLATE = """
Com base na descrição e metadados da tabela abaixo, liste até 3 temas principais de pesquisa ou análise que essa tabela pode ajudar a estudar.

OBJETIVO:
- Descrever o propósito funcional da tabela.
- Responder à pergunta: "O que essa tabela É no sistema?"
- Encontrar o conceito mais específico possível.
- Usar apenas evidências contidas na própria tabela.
- Não usar conhecimento externo nem contexto de domínio fornecido fora da entrada.
- Usar linguagem direta e objetiva, como faria um arquiteto de dados.


CRITÉRIOS:
1. Examine nomes de colunas, sample_values, frequent_values, sample_rows, foreign_keys e nome da tabela.
2. Prefira temas específicos sustentados por pelo menos 2 evidências independentes.
3. Evite temas muito genéricos isoladamente como:
"dados", "registros", "informações", "cadastro", "atendimento", "sistema".
4. Caso use um tema genérico, ele deve ser acompanhado por um tema específico relacionado. Exemplo: "atendimento de (subjetivo)" + "cadastro de (específico)".
5. Cada tema deve ter 1 a 4 palavras.
6. Use termos que apareçam explicitamente ou sejam fortemente inferíveis a partir dos valores.
7. Se a tabela parecer estrutural ou administrativa, retorne temas estruturais honestos.
8. Se não houver evidência confiável, retorne menos temas; não invente.
9. Use LINGUAGEM SIMPLES e CLARA

Responda APENAS com um array JSON válido.

REGRAS IMPORTANTES:
- NÃO use ```json ou ```
- NÃO adicione explicações
- NÃO quebre linhas
- Retorne tudo em UMA LINHA
- O resultado deve começar com [ e terminar com ]

Exemplo válido:
["Tema 1", "Tema 2", "Tema 3"]

O formato do JSON de entrada segue esta estrutura:
    - schema: nome do schema
    - table_name: nome da tabela
    - row_count: número de linhas
    - primary_key: lista de colunas da chave primária
    - columns: lista de colunas com name, type, nullable, sample_values, quando possivel dentro de stats, frequent_values, min, max, mean, etc.
    - foreign_keys: lista de chaves estrangeiras
    - sample_rows: exemplos de linhas

OBS. Se houver menos de 3 temas relevantes, liste apenas os que fizerem sentido. Não invente temas irrelevantes. você pode listar apenas 1 ou 2 temas, se apropriado.


Metadados da tabela:
```json
{table_summary}
```"""


def llm_suggest_topics_with_meta(table_summary: str) -> tuple:
    system_prompt = "Você rotula tabelas de dados com temas de pesquisa. Responda sempre em português."
    prompt = PROMPT_TEMPLATE.format(table_summary=table_summary)

    content, tokens_in, tokens_out = call_local_model_with_meta(
        prompt, system_prompt, temperature=TEMPERATURE, max_tokens=120
    )

    try:
        topics = json.loads(content)
        if isinstance(topics, list):
            return [str(t).strip() for t in topics][:3], tokens_in, tokens_out
    except json.JSONDecodeError:
        pass

    # fallback: tenta extrair um array JSON de dentro de um texto maior
    # (alguns modelos locais insistem em adicionar comentário antes/depois)
    start = content.find("[")
    end = content.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            topics = json.loads(content[start:end + 1])
            if isinstance(topics, list):
                return [str(t).strip() for t in topics][:3], tokens_in, tokens_out
        except json.JSONDecodeError:
            pass

    topics = [line.strip("- ").strip() for line in content.splitlines() if line.strip()][:3]
    return topics, tokens_in, tokens_out


def llm_suggest_topics(table_summary: str) -> List[str]:
    topics, _, _ = llm_suggest_topics_with_meta(table_summary)
    return topics


def save_progress(table_topics: Dict[str, Any]):
    with TOPICS_PATH.open("w", encoding="utf-8") as f:
        json.dump(table_topics, f, ensure_ascii=False, indent=2)



def main():
    print(f"Usando modelo local: {MODEL_NAME} (via {OLLAMA_URL})")
    check_ollama_running()

    metadata = load_metadata()

    table_topics: Dict[str, Any] = {}
    if TOPICS_PATH.exists():
        try:
            with TOPICS_PATH.open("r", encoding="utf-8") as f:
                table_topics = json.load(f)
            print(f"Progresso anterior encontrado: {len(table_topics)} tabelas já processadas.")
        except Exception:
            table_topics = {}

    for idx, table_meta in enumerate(metadata, 1):
        full_name = f"{table_meta.get('schema')}.{table_meta.get('table_name')}"

        if full_name in table_topics and table_topics[full_name]:
            print(f"[{idx}/{len(metadata)}] {full_name} já processado, pulando...")
            continue

        print(f"[{idx}/{len(metadata)}] Processando {full_name}...")

        try:
            try:
                summary = summarize_table(table_meta)
                topics = llm_suggest_topics(summary)
            except Exception as e:
                if is_context_limit_error(e):
                    print(f"  Limite de contexto detectado em {full_name}. Tentando versão compacta...")
                    summary = summarize_table_compact(table_meta)
                    topics = llm_suggest_topics(summary)
                else:
                    raise e

            table_topics[full_name] = topics
            print(f"  OK Temas: {topics}")

        except Exception as e:
            print(f"  ERRO ao processar {full_name}: {e}")
            table_topics[full_name] = []

        save_progress(table_topics)
        time.sleep(SLEEP_BETWEEN_CALLS)

    save_progress(table_topics)
    print(f"Temas salvos com sucesso em {TOPICS_PATH}")



if __name__ == "__main__":
    main()