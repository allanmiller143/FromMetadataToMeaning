import os
import json
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI
import sys


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / 'teixeira'
METADATA_PATH = DATA_DIR / "step2_output" / "metadata.json"
OUTPUT_DIR = DATA_DIR / "step3_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
MODEL_NAME = "OPENAI"
RUN = int(sys.argv[1]) if len(sys.argv) > 1 else 1
DESCRIPTIONS_PATH = OUTPUT_DIR / f"table_descriptions_{MODEL_NAME}_{RUN}.json"
TOPICS_PATH = OUTPUT_DIR / f"table_topics_{MODEL_NAME}_{RUN}.json"



def load_env():
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY não encontrado no .env")
    return OpenAI(api_key=api_key)



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



def is_token_limit_error(e: Exception) -> bool:
    error_msg = str(e).lower()

    token_error_terms = [
        "token",
        "tokens",
        "context",
        "maximum context length",
        "context length",
        "too many tokens",
        "too large",
        "prompt is too long",
        "input is too long",
        "context_length_exceeded",
        "bad request",
        "400 client error",
        "400",
        "request body too large",
        "payload too large",
        "max_tokens must be at least 1"
    ]

    return any(term in error_msg for term in token_error_terms)



def call_openai(client: OpenAI, prompt: str, system_prompt: str, temperature: float = TEMPERATURE, max_tokens: int = 180) -> str:
    text, _, _ = call_openai_with_meta(client, prompt, system_prompt, temperature, max_tokens)
    return text


def call_openai_with_meta(client: OpenAI, prompt: str, system_prompt: str, temperature: float = TEMPERATURE, max_tokens: int = 180) -> tuple:
    """Igual a call_openai, mas retorna (texto, tokens_entrada, tokens_saida)."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    text = response.choices[0].message.content.strip()
    usage = response.usage
    tokens_in  = getattr(usage, "prompt_tokens",     0) or 0
    tokens_out = getattr(usage, "completion_tokens", 0) or 0
    return text, tokens_in, tokens_out



# def llm_describe_table(client: OpenAI, table_summary: str) -> str:
#     system_prompt = "Você é um assistente especializado em bancos de dados."
#     prompt = f"""Você receberá metadados de uma tabela de banco de dados.


# Use todas as informaçôes disponíveis em cada tabela, para escrever UMA descrição curta, em até 2 frases,


# O formato do JSON de entrada segue esta estrutura:
# - schema: nome do schema
# - table_name: nome da tabela
# - row_count: número de linhas
# - primary_key: lista de colunas da chave primária
# - columns: lista de colunas com name, type, nullable, sample_values, quando possivel dentro de stats, frequent_values, min, max, mean, etc.
# - foreign_keys: lista de chaves estrangeiras
# - sample_rows: exemplos de linhas


# Essa descrição deve estar em formato simples e claro, para que qualquer usuário, seja ele técnico ou não possa entender facilmente o propósito da tabela.


# Use os metadados abaixo para gerar a descrição.


# Metadados da tabela:
# ```json
# {table_summary}
# ```


# O formato de saída deve ser apenas texto simples, sem marcações ou formatações especiais.


# exemplo de saída:


# Descrição: ''


# """


#     return call_openai(client, prompt, system_prompt, temperature=TEMPERATURE, max_tokens=180)



def llm_suggest_topics(client: OpenAI, table_summary: str) -> List[str]:
    system_prompt = "Você rotula tabelas de dados com temas de pesquisa."
    prompt = f"""
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

    Exemplo de saída JSON:

    Temas: ["Tema 1", "tema 2", "tema 3"]    
    
    OBS. Se houver menos de 3 temas relevantes, liste apenas os que fizerem sentido. Não invente temas irrelevantes. você pode listar apenas 1 ou 2 temas, se apropriado.

Metadados da tabela:
```json
{table_summary}
```"""


    content = call_openai(client, prompt, system_prompt, temperature=TEMPERATURE, max_tokens=120)


    try:
        topics = json.loads(content)
        if isinstance(topics, list):
            return [str(t).strip() for t in topics][:3]
    except json.JSONDecodeError:
        pass


    return [line.strip("- ").strip() for line in content.splitlines() if line.strip()][:3]


def llm_suggest_topics_with_meta(client: OpenAI, table_summary: str) -> tuple:
    """Igual a llm_suggest_topics, mas retorna (topics, tokens_entrada, tokens_saida)."""
    system_prompt = "Você rotula tabelas de dados com temas de pesquisa."
    prompt = f"""
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

    Exemplo de saída JSON:

    Temas: ["Tema 1", "tema 2", "tema 3"]    
    
    OBS. Se houver menos de 3 temas relevantes, liste apenas os que fizerem sentido. Não invente temas irrelevantes. você pode listar apenas 1 ou 2 temas, se apropriado.

Metadados da tabela:
```json
{table_summary}
```"""

    content, tokens_in, tokens_out = call_openai_with_meta(
        client, prompt, system_prompt, temperature=TEMPERATURE, max_tokens=120
    )

    try:
        topics = json.loads(content)
        if isinstance(topics, list):
            return [str(t).strip() for t in topics][:3], tokens_in, tokens_out
    except json.JSONDecodeError:
        pass

    topics = [line.strip("- ").strip() for line in content.splitlines() if line.strip()][:3]
    return topics, tokens_in, tokens_out


def main():
    client = load_env()
    metadata = load_metadata()


    table_descriptions = {}
    table_topics = {}


    # for idx, table_meta in enumerate(metadata[:5], 1):
    # for idx, table_meta in enumerate(metadata[305:306], 1):
    for idx, table_meta in enumerate(metadata, 1):  
        full_name = f"{table_meta.get('schema')}.{table_meta.get('table_name')}"
        print(f"[{idx}/{len(metadata)}] Processando {full_name}...")


        try:
            try:
                summary = summarize_table(table_meta)
                # desc = llm_describe_table(client, summary)
                topics = llm_suggest_topics(client, summary)
            except Exception as e:
                if is_token_limit_error(e):
                    print(f"  Limite de tokens/contexto detectado em {full_name}. Tentando versão compacta...")
                    summary = summarize_table_compact(table_meta)
                    # desc = llm_describe_table(client, summary)
                    topics = llm_suggest_topics(client, summary)
                else:
                    raise e


            # table_descriptions[full_name] = desc
            table_topics[full_name] = topics


            # print(f"  OK Descricao: {desc[:80]}...")
            # print(f"  OK Temas: {topics}")
        except Exception as e:
            print(f"  ERRO ao processar {full_name}: {e}")
            # table_descriptions[full_name] = f"Erro ao gerar descricao: {str(e)}"
            table_topics[full_name] = []


    # with DESCRIPTIONS_PATH.open("w", encoding="utf-8") as f:
    #     json.dump(table_descriptions, f, ensure_ascii=False, indent=2)


    with TOPICS_PATH.open("w", encoding="utf-8") as f:
        json.dump(table_topics, f, ensure_ascii=False, indent=2)


    # print(f"\nDescricoes salvas em {DESCRIPTIONS_PATH}")
    print(f"Temas salvos com sucesso ")

if __name__ == "__main__":
    main()