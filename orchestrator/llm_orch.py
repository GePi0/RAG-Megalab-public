"""
llm_orch.py
Orchestrator LLM interface using the RunnableSequence API (LangChain 0.3+).
"""

from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM


def build_ollama_chain():
    """
    Crea una secuencia LangChain (PromptTemplate | LLM)
    usando el modelo Llama 3.1 8B local.
    """

    llm = OllamaLLM(model="llama3.1:8b", base_url="http://ollama-service:11434")
    prompt = PromptTemplate.from_template("{prompt}")

    # Nuevo estilo: composición funcional del pipeline
    chain = prompt | llm
    return chain
