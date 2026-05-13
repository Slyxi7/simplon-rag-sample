# Runbook — HighLatencyMessages

## Alerte

**Nom :** `HighLatencyMessages`
**Sévérité :** warning
**Condition :** La latence p95 sur l'endpoint `/messages` dépasse **5 secondes** pendant **2 minutes** consécutives.

## Impact

Les utilisateurs du chatbot RAG subissent des temps de réponse dégradés. L'expérience
utilisateur est directement affectée — les apprenants et l'équipe pédagogique perçoivent
le chatbot comme « lent ».

## Diagnostic

1. **Dashboard Grafana** → Row « RED Metrics » → panels **Latence p95** et **Latence p99**
   - Vérifier si la latence est élevée sur `/messages` uniquement ou sur tous les endpoints
   - Comparer p50 vs p95 vs p99 : si p50 est normal mais p95/p99 explosent → problème
     intermittent (certaines requêtes seulement)

2. **Latence par nœud du graphe** → Row « Ingestion & Nœuds » → panel « Latence p95 par
   nœud »
   - Identifier quel nœud est lent : `retrieve`, `generate`, `evaluate`, `guard_route` ?
   - Si `generate` est lent → problème côté LLM (Mistral API / Ollama)
   - Si `retrieve` est lent → problème côté pgvector (index, connexion DB)
   - Si `evaluate` est lent → possiblement la rewrite-loop qui boucle

3. **Logs Loki** → Row « Logs » → filtrer par `request_id` des requêtes lentes
   - Chercher des patterns de retry ou d'erreur dans les logs
   - Vérifier la présence de `event: "request_complete"` avec `latency_ms` élevé

4. **Métriques agent** → Row « Agent RAG »
   - Taux d'escalade en hausse → l'évaluateur rejette les réponses → boucle de rewrite
   - Décisions d'évaluation : ratio `rewrite` anormalement élevé ?

## Mitigation

| Cause identifiée | Action |
|-----------------|--------|
| `retrieve` lent | Vérifier la connexion pgvector, la taille des index, le nombre de chunks |
| `generate` lent | Vérifier le statut du provider LLM (Mistral API status page / `ollama ps`) |
| Rewrite-loop | Vérifier le nombre de retries dans les logs ; considérer un circuit breaker |
| Charge globale | Vérifier la charge CPU/mémoire des conteneurs Docker |

## Escalade

Si le problème persiste > 15 min après mitigation, contacter l'équipe backend.
