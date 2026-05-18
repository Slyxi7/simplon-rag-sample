1. api/pyproject.toml
  - Remettre langchain-mistralai>=0.2 et mistralai>=1.0                                                                                                                                                  
 ```
 "langchain-mistralai>=0.2",
 "mistralai>=1.0",
 ```                                           
   
2. api/src/rag/config/settings.py                                                                                                                                                                        
                                                                                                                                                                                                         
  Ajouter :                                                                                                                 

  ```                                                          
  # Mistral AI

  mistral_api_key: str
  ```                                                                          

3. api/src/rag/rag/embeddings/

  - Recréer mistral_embeddings.py (version main) — utilise MistralAIEmbeddings(model="mistral-embed", api_key=settings.mistral_api_key) avec aembed_documents / aembed_query.

```
from functools import lru_cache

from langchain_mistralai import MistralAIEmbeddings

from rag.config.settings import get_settings


@lru_cache
def get_embeddings() -> MistralAIEmbeddings:
    settings = get_settings()
    return MistralAIEmbeddings(
        model="mistral-embed",
        api_key=settings.mistral_api_key,
    )


async def embed_documents(texts: list[str]) -> list[list[float]]:
    return await get_embeddings().aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    return await get_embeddings().aembed_query(text)
```

4. api/src/rag/rag/agent/nodes.py

  - _get_llm :
```
  def _get_llm(settings=None, model: str = "mistral-large-latest") -> ChatMistralAI:
    s = settings or get_settings()
    return ChatMistralAI(model=model, api_key=s.mistral_api_key)
```
  - Dans guard_route : model="mistral-small-latest"
  - Dans evaluate : _get_llm(model="mistral-small-latest") (plus besoin de récupérer settings)
  
5. api/src/rag/rag/ingestion/pipeline.py et api/src/rag/rag/retriever/pgvector_retriever.py

  - Remplacer from rag.rag.embeddings import ollama_embeddings par mistral_embeddings                                                                                                                      
  - Et les appels ollama_embeddings.embed_* → mistral_embeddings.embed_*
                                                                                                                                                                                                           
6. api/src/rag/evaluation/ragas_pipeline.py                                                                                                                                                            
                                                                                                                                                                                                           
  Supprimer toute la section ajoutée (imports langchain_ollama, LangchainLLMWrapper, LangchainEmbeddingsWrapper, instanciation judge_llm/judge_embed) et revenir à :                                       
  result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall])
  Restaurer le commentaire d'origine : # Lazy imports to avoid ragas/mistralai version conflict at app startup.

```
# Lazy imports to avoid ragas/mistralai version conflict at app startup
from datasets import Dataset  # noqa: PLC0415
from ragas import evaluate  # noqa: PLC0415
from ragas.metrics import answer_relevancy, context_recall, faithfulness  # noqa: PLC0415

dataset = Dataset.from_dict(
    {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    }
)

result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_recall])

```

7. api/.env.example et .env.example (racine)

  Remettre MISTRAL_API_KEY= dans api/.env.example (la racine n'avait rien à l'origine côté Mistral).


