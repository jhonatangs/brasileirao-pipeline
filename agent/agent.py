import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from agent.tools import run_query
from agent.system_prompt import SYSTEM_PROMPT
from agent.memory import add_interaction, get_memories_context

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USER_ID = os.getenv("USER_ID", "default")

client = OpenAI(api_key=OPENAI_API_KEY)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_query",
            "description": "Executa uma query SQL no banco de dados DuckDB do Brasileirão e retorna os resultados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "A query SQL a ser executada no DuckDB.",
                    }
                },
                "required": ["sql_query"],
            },
        },
    }
]


def process_tool_call(tool_name: str, tool_args: dict) -> str:
    if tool_name == "run_query":
        return run_query(tool_args["sql_query"])
    return f"Ferramenta desconhecida: {tool_name}"


def ask_agent(question: str, conversation_history: list, user_id: str = USER_ID) -> str:
    """
    Sends a question to the agent and returns its natural language response.

    Enriches the system prompt with relevant memories from mem0 before calling
    the LLM, and persists the interaction to mem0 after receiving the final answer.

    Args:
        question: The user's question.
        conversation_history: The ongoing conversation history (list of messages).
        user_id: The user identifier used for mem0 memory storage/retrieval.

    Returns:
        The agent's natural language response as a string.
    """
    # Retrieve relevant memories and inject them into the system prompt
    memory_context = get_memories_context(user_id=user_id, query=question)
    enriched_prompt = SYSTEM_PROMPT.format(memory_context=memory_context)

    conversation_history.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": enriched_prompt}] + conversation_history,
        tools=TOOLS,
        tool_choice="auto",
    )

    message = response.choices[0].message

    # Handle tool calls in a loop (agent may call tools multiple times)
    while message.tool_calls:
        conversation_history.append(message)

        tool_results = []
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"\n🔍 Executando query SQL:\n{tool_args.get('sql_query', '')}\n")

            result = process_tool_call(tool_name, tool_args)

            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

        conversation_history.extend(tool_results)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": enriched_prompt}] + conversation_history,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message

    final_answer = message.content
    conversation_history.append({"role": "assistant", "content": final_answer})

    # Persist the interaction to mem0 for future context
    try:
        add_interaction(user_id=user_id, user_message=question, agent_message=final_answer)
        print(f"🧠 Memória salva para o usuário '{user_id}'.")
    except Exception as e:
        print(f"⚠️  mem0: erro ao salvar memória: {e}")

    return final_answer
