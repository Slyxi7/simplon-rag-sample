# Runbook — LLMDailyBudgetExceeded

## Alerte

**Nom :** `LLMDailyBudgetExceeded`
**Sévérité :** warning
**Condition :** Le coût LLM quotidien dépasse **15€** pendant **5 minutes**.

## Impact

Le budget Mistral API risque d'être dépassé. La facture mensuelle pourrait exploser si
le trafic reste élevé ou si des inefficiences (loops, requêtes trop longues) ne sont
pas corrigées.

## Diagnostic

1. **Dashboard Grafana** → Row « Agent RAG » → panels **Taux d'escalade** et **Décisions d'évaluation**
   - Un pic d'escalades → l'agent fait des loops de rewrite qui consomment des tokens
   - Vérifier le ratio `rewrite` vs `answer` dans les décisions

2. **Langfuse** (traces LLM)
   - Identifier les conversations les plus coûteuses
   - Chercher des spans avec beaucoup de tokens (input/output)
   - Vérifier si le modèle `mistral-large-latest` est utilisé alors que `small` suffirait

3. **Métriques ingestion**
   - Un pic d'ingestion de documents peut générer beaucoup d'embeddings
   - Vérifier `/documents/ingest-*` dans les métriques HTTP

4. **Corrélation temporelle**
   - Le dépassement coïncide-t-il avec une montée en charge utilisateurs ?
   - Y a-t-il eu un changement de modèle ou de prompt ?

## Mitigation

| Cause identifiée | Action |
|-----------------|--------|
| Loops d'évaluation (rewrite) | Vérifier la logique `evaluate` — ajuster le seuil de retry |
| Mauvais modèle utilisé | Forcer `mistral-small-latest` dans la config |
| Requêtes trop longues | Limiter la taille du contexte récupéré |
| Pic d'ingestion | Étaler l'ingestion sur plusieurs heures |
| Attaque/abus | Mettre en place rate limiting |

## Escalade

Si le coût continue de monter malgré la mitigation → contacter le CTO pour décision
d'arrêt temporaire du service ou changement de clé API.

## Prévention

- Configurer une alerte à 10€ (early warning)
- Réviser les prompts pour réduire la taille du contexte
- Implémenter un circuit breaker sur les loops de rewrite

