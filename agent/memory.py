"""
memory.py — Camada de memória persistente do agente usando mem0 (modo OSS/local).

Responsabilidades:
- Inicializar o cliente mem0 em modo local (sem API key própria do mem0).
  O mem0 local usa OPENAI_API_KEY para embeddings, portanto load_dotenv()
  deve ser chamado antes da primeira utilização destas funções.
- Persistir cada interação usuário/agente via `add_interaction()`.
- Recuperar memórias relevantes via `get_memories_context()` para enriquecer o system prompt.
"""

from __future__ import annotations
from mem0 import Memory

# Inicialização lazy: o cliente só é criado na primeira chamada,
# após load_dotenv() ter sido executado em agent.py/main.py.
_memory: Memory | None = None

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "path": "data/qdrant_memory",
            "host": None,
            "port": None,
        }
    }
}


def _get_memory() -> Memory:
    """Returns the singleton Memory instance, initializing it if needed."""
    global _memory
    if _memory is None:
        _memory = Memory().from_config(config)
    return _memory


def add_interaction(user_id: str, user_message: str, agent_message: str) -> None:
    """
    Persiste um par de mensagens (usuário + agente) no mem0.

    Args:
        user_id: Identificador único do usuário (lido de USER_ID no .env).
        user_message: A pergunta ou mensagem do usuário.
        agent_message: A resposta gerada pelo agente.
    """
    messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": agent_message},
    ]
    _get_memory().add(messages, user_id=user_id)


def get_memories_context(user_id: str, query: str) -> str:
    """
    Busca memórias relevantes para a query do usuário e retorna uma string
    formatada para injeção no system prompt.

    Args:
        user_id: Identificador único do usuário.
        query: A pergunta atual do usuário (usada como vetor de busca).

    Returns:
        String formatada com as memórias relevantes, ou mensagem padrão se não houver.
    """
    try:
        results = _get_memory().search(query=query, user_id=user_id, limit=5)
        memories = results.get("results", []) if isinstance(results, dict) else results

        if not memories:
            return "Nenhuma memória prévia relevante encontrada."

        lines = ["Informações lembradas de interações anteriores com este usuário:"]
        for mem in memories:
            text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
            if text:
                lines.append(f"- {text}")

        return "\n".join(lines)
    except Exception as e:
        # Não deixa falha na memória quebrar o agente
        print(f"⚠️  mem0: erro ao recuperar memórias: {e}")
        return ""
