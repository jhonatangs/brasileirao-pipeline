import os
import sys
import atexit
from dotenv import load_dotenv
from agent.agent import ask_agent
from agent.memory import _get_memory

load_dotenv()

USER_ID = os.getenv("USER_ID", "default")


def cleanup():
    try:
        memory = _get_memory()
        if memory and hasattr(memory, 'vector_store'):
            client = getattr(memory.vector_store, 'client', None)
            if client:
                client.close()
        if 'agent' in sys.modules:
             pass 
    except:
        pass
    finally:
        os._exit(0)


def main():
    print("=" * 60)
    print("⚽  Agente de IA — Brasileirão 2026")
    print("=" * 60)
    print("Faça perguntas sobre a classificação e partidas do campeonato.")
    print("Digite 'sair' ou 'exit' para encerrar.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nAté logo! 👋")
            cleanup()

        if not user_input:
            continue

        if user_input.lower() in {"sair", "exit", "quit"}:
            print("\nAté logo! 👋")
            cleanup()
        print("\nAgente: pensando...", end="\r")

        try:
            answer = ask_agent(user_input, conversation_history, user_id=USER_ID)
            print(f"Agente: {answer}\n")
        except Exception as e:
            print(f"Agente: ⚠️  Ocorreu um erro: {e}\n")


if __name__ == "__main__":
    atexit.register(cleanup)
    main()
