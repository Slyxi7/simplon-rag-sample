# Runbook — HighErrorRate5xx

## Alerte

**Nom :** `HighErrorRate5xx`
**Sévérité :** critical
**Condition :** Plus de **5 %** des requêtes HTTP retournent un code **5xx** pendant
**2 minutes** consécutives.

## Impact

Le chatbot est partiellement ou totalement indisponible. Les utilisateurs reçoivent des
erreurs serveur. L'ingestion de documents et les conversations sont potentiellement
impactées.

## Diagnostic

1. **Dashboard Grafana** → Row « RED Metrics » → panel **Taux d'erreur 5xx (%)**
   - Identifier l'endpoint concerné : `/messages`, `/documents/ingest-*`, `/eval/run` ?
   - Si tous les endpoints sont impactés → problème d'infrastructure (DB, réseau)

2. **Logs Loki** → Row « Logs »
   - Filtrer par `status_code >= 500` ou chercher `"level": "ERROR"`
   - Examiner les stack traces pour identifier la root cause
   - Chercher des patterns récurrents (même type d'erreur ?)

3. **Santé des dépendances**
   - PostgreSQL/pgvector : `docker compose ps postgres` — le conteneur est-il healthy ?
   - Provider LLM : vérifier la connectivité Mistral API ou `ollama ps`
   - Mémoire/CPU : `docker stats` pour identifier un conteneur en OOM

4. **Corrélation temporelle**
   - L'erreur a-t-elle commencé après un déploiement ? Un changement de configuration ?
   - Y a-t-il eu un pic d'ingestion (beaucoup de PDF) juste avant ?

## Mitigation

| Cause identifiée | Action |
|-----------------|--------|
| PostgreSQL down | `docker compose restart postgres` ; vérifier les logs postgres |
| LLM timeout/erreur | Vérifier Mistral API status ; basculer sur Ollama si disponible |
| OOM conteneur | Augmenter les limites mémoire dans `docker-compose.yml` ; redémarrer |
| Erreur applicative | Identifier le bug dans les logs, hotfix si possible |
| Surcharge ingestion | Limiter le nombre de PDF ingérés simultanément |

## Escalade

**Sévérité critical** — Si le problème persiste > 10 min, contacter immédiatement
l'équipe infra et le CTO.
