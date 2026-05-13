#!/usr/bin/env python3
"""
Exporte le coût quotidien Langfuse vers Prometheus.

Ce script est conçu pour être exécuté périodiquement (cronjob) ou comme
un exporter Prometheus exposant la métrique llm_daily_cost_euros.

Usage:
    # Mode one-shot (cron)
    python export_langfuse_cost.py --push-gateway http://pushgateway:9091
    
    # Mode exporter (HTTP server)
    python export_langfuse_cost.py --exporter --port 8001
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import requests
from prometheus_client import Gauge, start_http_server, push_to_gateway

# Métrique Prometheus pour le coût LLM quotidien
LLM_DAILY_COST = Gauge(
    "llm_daily_cost_euros",
    "Coût LLM quotidien en euros (source: Langfuse)",
    ["date"]
)

LLM_TOTAL_TOKENS = Gauge(
    "llm_daily_tokens_total",
    "Nombre total de tokens consommés aujourd'hui",
    ["date", "token_type"]  # input, output
)


def get_langfuse_cost(
    langfuse_host: str,
    langfuse_public_key: str,
    langfuse_secret_key: str,
    date: Optional[str] = None
) -> dict:
    """
    Récupère le coût et les stats depuis l'API Langfuse.
    
    Args:
        langfuse_host: URL de l'instance Langfuse (ex: http://langfuse:3000)
        langfuse_public_key: Clé publique Langfuse
        langfuse_secret_key: Clé secrète Langfuse
        date: Date au format YYYY-MM-DD (defaut: aujourd'hui)
    
    Returns:
        dict avec 'cost_eur', 'input_tokens', 'output_tokens'
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Calculer le timestamp de début/fin de journée
    start_of_day = datetime.strptime(date, "%Y-%m-%d")
    end_of_day = start_of_day + timedelta(days=1)
    
    # Headers d'authentification Basic
    auth = (langfuse_public_key, langfuse_secret_key)
    
    try:
        # Appel API Langfuse pour récupérer les traces du jour
        response = requests.get(
            f"{langfuse_host}/api/public/traces",
            auth=auth,
            params={
                "from": start_of_day.isoformat() + "Z",
                "to": end_of_day.isoformat() + "Z",
                "limit": 1000,
            },
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        traces = data.get("data", [])
        
        # Calculer le coût estimé (prix Mistral: ~3€/M tokens input, 9€/M output)
        total_input_tokens = 0
        total_output_tokens = 0
        
        for trace in traces:
            # Extraire les observations/spans avec token usage
            for observation in trace.get("observations", []):
                usage = observation.get("usage", {})
                total_input_tokens += usage.get("input", 0) or usage.get("promptTokens", 0) or 0
                total_output_tokens += usage.get("output", 0) or usage.get("completionTokens", 0) or 0
        
        # Prix approximatifs Mistral (à ajuster selon le modèle exact)
        # mistral-small: 1€/M input, 3€/M output
        # mistral-large: 3€/M input, 9€/M output
        # On fait une estimation conservative
        cost_eur = (total_input_tokens * 2.0 / 1_000_000) + (total_output_tokens * 6.0 / 1_000_000)
        
        return {
            "date": date,
            "cost_eur": round(cost_eur, 2),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "trace_count": len(traces),
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur API Langfuse: {e}", file=sys.stderr)
        return {
            "date": date,
            "cost_eur": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "trace_count": 0,
            "error": str(e)
        }


def update_metrics(stats: dict) -> None:
    """Met à jour les métriques Prometheus avec les stats récupérées."""
    date = stats["date"]
    
    LLM_DAILY_COST.labels(date=date).set(stats["cost_eur"])
    LLM_TOTAL_TOKENS.labels(date=date, token_type="input").set(stats["input_tokens"])
    LLM_TOTAL_TOKENS.labels(date=date, token_type="output").set(stats["output_tokens"])
    
    print(f"[export_langfuse_cost] Date: {date}, Coût: {stats['cost_eur']}€, "
          f"Tokens: {stats['input_tokens']}/{stats['output_tokens']}, "
          f"Traces: {stats.get('trace_count', 0)}")


def main():
    parser = argparse.ArgumentParser(description="Exporte le coût Langfuse vers Prometheus")
    parser.add_argument("--exporter", action="store_true", help="Mode exporter HTTP")
    parser.add_argument("--port", type=int, default=8001, help="Port pour le mode exporter")
    parser.add_argument("--push-gateway", help="URL du Pushgateway (ex: http://pushgateway:9091)")
    parser.add_argument("--job-name", default="langfuse-cost-exporter", help="Nom du job pour Pushgateway")
    parser.add_argument("--date", help="Date spécifique (YYYY-MM-DD), défaut: aujourd'hui")
    
    args = parser.parse_args()
    
    # Récupérer les credentials Langfuse depuis l'environnement
    langfuse_host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
    langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    
    if not langfuse_public_key or not langfuse_secret_key:
        print("Erreur: LANGFUSE_PUBLIC_KEY et LANGFUSE_SECRET_KEY requis", file=sys.stderr)
        sys.exit(1)
    
    if args.exporter:
        # Mode exporter: lance un serveur HTTP qui expose les métriques
        print(f"Starting exporter on port {args.port}")
        start_http_server(args.port)
        
        # Rafraîchit les métriques périodiquement
        import time
        while True:
            stats = get_langfuse_cost(
                langfuse_host, langfuse_public_key, langfuse_secret_key, args.date
            )
            update_metrics(stats)
            time.sleep(300)  # Rafraîchit toutes les 5 minutes
            
    elif args.push_gateway:
        # Mode one-shot: pousse les métriques vers un Pushgateway
        stats = get_langfuse_cost(
            langfuse_host, langfuse_public_key, langfuse_secret_key, args.date
        )
        update_metrics(stats)
        
        try:
            push_to_gateway(args.push_gateway, job=args.job_name, registry=None)
            print(f"Métriques poussées vers {args.push_gateway}")
        except Exception as e:
            print(f"Erreur Pushgateway: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Mode dry-run: affiche juste les stats
        stats = get_langfuse_cost(
            langfuse_host, langfuse_public_key, langfuse_secret_key, args.date
        )
        print(f"Stats: {stats}")
        print("Utilisez --exporter ou --push-gateway pour exporter vers Prometheus")


if __name__ == "__main__":
    main()
