"""
Mesure des temps de réponse des routes principales ClearBot.

Usage :
    python evaluation/benchmark_latency.py --base-url http://localhost:8000 --runs 5 --save evaluation/rapports/latency_report.json

Le backend doit être lancé sans CLEARBOT_TEST_MODE afin de mesurer les vrais
agents et les appels LLM/RAG.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_CASES = [
    {
        "name": "GET /chat-session",
        "method": "GET",
        "path": "/chat-session",
        "payload": None,
        "auth": False,
    },
    {
        "name": "POST /chat public - identité",
        "method": "POST",
        "path": "/chat",
        "payload": {"message": "Qui es-tu ?", "context": "public"},
        "auth": False,
    },
    {
        "name": "POST /chat private - classification",
        "method": "POST",
        "path": "/chat",
        "payload": {"message": "Je n'arrive pas à accéder à TCS BaNCS depuis ce matin.", "context": "private"},
        "auth": True,
    },
    {
        "name": "POST /chat-informationnel",
        "method": "POST",
        "path": "/chat-informationnel",
        "payload": {"message": "Quel est le rôle de Maroclear ?", "context": "public"},
        "auth": False,
    },
    {
        "name": "POST /chat-reglementaire",
        "method": "POST",
        "path": "/chat-reglementaire",
        "payload": {"message": "Que prévoit la loi 35-96 sur le dépositaire central ?", "context": "private"},
        "auth": False,
    },
    {
        "name": "POST /feedback",
        "method": "POST",
        "path": "/feedback",
        "payload": {"rating": 5, "comment": "Benchmark latence", "ticket_id": "BENCH-LATENCY"},
        "auth": False,
    },
]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def request_once(session: requests.Session, base_url: str, case: dict[str, Any], timeout: int) -> tuple[float, int, str]:
    url = base_url.rstrip("/") + case["path"]
    start = time.perf_counter()
    try:
        if case["method"] == "GET":
            response = session.get(url, timeout=timeout)
        else:
            response = session.post(url, json=case["payload"], timeout=timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, response.status_code, ""
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, 0, f"{type(exc).__name__}: {exc}"


def login(session: requests.Session, base_url: str, timeout: int) -> None:
    response = session.post(
        base_url.rstrip("/") + "/auth/login",
        json={"username": "asmae.hidra", "password": "maroclear123"},
        timeout=timeout,
    )
    response.raise_for_status()


def run_benchmark(base_url: str, runs: int, warmup: int, timeout: int) -> dict[str, Any]:
    session = requests.Session()
    login(session, base_url, timeout)

    results = []
    for case in DEFAULT_CASES:
        if case["auth"]:
            login(session, base_url, timeout)

        for _ in range(warmup):
            request_once(session, base_url, case, timeout)

        latencies = []
        statuses = []
        errors = []
        for _ in range(runs):
            elapsed_ms, status, error = request_once(session, base_url, case, timeout)
            latencies.append(elapsed_ms)
            statuses.append(status)
            if error:
                errors.append(error)

        results.append({
            "route": case["name"],
            "runs": runs,
            "status_codes": sorted(set(statuses)),
            "success_rate": round(sum(1 for s in statuses if 200 <= s < 300) / runs, 4),
            "mean_ms": round(statistics.mean(latencies), 2),
            "median_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(percentile(latencies, 95), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "errors": errors[:3],
        })

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": base_url,
        "runs_per_route": runs,
        "warmup_per_route": warmup,
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de latence ClearBot")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--save", default="evaluation/rapports/latency_report.json")
    args = parser.parse_args()

    try:
        report = run_benchmark(args.base_url, args.runs, args.warmup, args.timeout)
    except requests.RequestException as exc:
        print("\nImpossible de joindre le backend ClearBot.")
        print(f"URL testée : {args.base_url}")
        print("Vérifiez que le backend est lancé, par exemple :")
        print("  python -m uvicorn api.api:app --reload --host 0.0.0.0 --port 8000")
        print(f"Détail : {type(exc).__name__}: {exc}")
        raise SystemExit(1)

    print("\n=== Benchmark latence ClearBot ===")
    print(f"Backend : {report['base_url']}")
    print(f"Répétitions par route : {report['runs_per_route']}")
    print("")
    for row in report["results"]:
        print(
            f"{row['route']:<38} "
            f"moy={row['mean_ms']:>8.2f} ms | "
            f"p95={row['p95_ms']:>8.2f} ms | "
            f"statuts={row['status_codes']} | "
            f"succès={row['success_rate']:.0%}"
        )
        if row["errors"]:
            print(f"  erreurs: {row['errors']}")

    save_path = Path(args.save)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapport sauvegardé : {save_path}")


if __name__ == "__main__":
    main()
