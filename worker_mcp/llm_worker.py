"""
llm_worker.py
Worker MCP interface for CodeLlama 7B using RunnableSequence.
"""

import os
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM


def init_llm_chain():
    """
    Construye la secuencia Prompt → LLM (RunnableSequence).
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama-service:11434")
    llm = OllamaLLM(model="codellama:7b", base_url=base_url)

    template = (
        "You are a code assistant.\n"
        "Task:\n{task}\n\n"
        "Please analyze or generate code clearly and concisely."
    )

    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    return chain


def generate_code_response(task: str) -> str:
    """
    Ejecuta la secuencia Prompt|LLM y garantiza retorno textual.
    """
    chain = init_llm_chain()

    try:
        result = chain.invoke({"task": task})

        if isinstance(result, dict):
            text = result.get("text") or result.get("output_text") or "(no output)"
        elif hasattr(result, "content"):
            text = result.content
        else:
            text = str(result) if result else "(no output)"

    except Exception as e:
        text = f"(worker error: {e})"

    return text
