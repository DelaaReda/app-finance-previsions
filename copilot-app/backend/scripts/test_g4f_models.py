#!/usr/bin/env python3
"""
Test runner for a curated list of G4F models (DeepInfra + CohereForAI + Flux).
Runs a tiny prompt against each model and reports success / error / latency.

Usage:
  PYTHONPATH=src python scripts/test_g4f_models.py
"""
import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple
import tempfile

import requests
import shutil

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from g4f.client import Client

WORKING_RESULTS_URL = (
    "https://raw.githubusercontent.com/Free-AI-Things/g4f-working/main/working/working_results.txt"
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "tested_g4f_models.json"
)

PROMPT = "Salut, réponds strictement après ce message par: OK"


def main():
    # Exécuter les appels g4f dans un répertoire temporaire pour éviter les fichiers
    # générés dans le repo (ex: generated_media).
    tmpdir = tempfile.mkdtemp(prefix="g4f_tests_")
    prev_cwd = os.getcwd()
    os.chdir(tmpdir)

    # Charge les variables d'environnement depuis .env si disponible
    if load_dotenv:
        # backend/.env en priorité, sinon racine
        env_paths = [
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        ]
        for p in env_paths:
            if os.path.exists(p):
                load_dotenv(p)
                break

    model_list = fetch_remote_models(WORKING_RESULTS_URL)
    if not model_list:
        print("⚠️  Impossible de récupérer working_results.txt, aucun test exécuté.")
        return 1

    results = asyncio.run(_run_async(model_list))

    # Résumé des OK (latence) et shortlist filtrée
    ok_results = [r for r in results if r["ok"]]
    ok_sorted = sorted(ok_results, key=lambda r: r["ms"]) if ok_results else []
    if ok_sorted:
        print("\n=== OK MODELS (sorted by latency) ===")
        for r in ok_sorted:
            print(f"{r['ms']:6.1f} ms  {r['provider']} | {r['model']} | {r['task']} -> {r['answer']}")

    # Shortlist: ok + answer non-vide + pas d'erreur audio/quota
    def _is_clean(r: Dict[str, Any]) -> bool:
        if not r.get("ok"):
            return False
        ans = (r.get("answer") or "").strip()
        if not ans:
            return False
        err = (r.get("error") or "").lower()
        if "audioresponse" in err:
            return False
        if "gpu quota" in err or "model busy" in err:
            return False
        # filtrer les réponses qui contiennent des erreurs masquées
        ans_low = ans.lower()
        bad_patterns = [
            "nonetype",
            "does not exist",
            "not exist",
            "not in our api",
            "<span",  # html error wraps
            "api key is required",
            "no .har file found",
        ]
        if any(p in ans_low for p in bad_patterns):
            return False
        return True

    shortlist = [r for r in ok_sorted if _is_clean(r)]

    # JSON dump at the end for scripts
    print("\n=== JSON RESULTS ===")
    print(json.dumps(results, indent=2))

    # Sauvegarde dans src/tested_g4f_models.json pour consultation ultérieure
    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved results -> {OUTPUT_PATH}")
    except Exception as e:
        print(f"⚠️  Impossible de sauver le fichier {OUTPUT_PATH}: {e}")

    # Sauvegarde shortlist filtrée avec catégorie (par capacités)
    shortlist_path = OUTPUT_PATH.replace(".json", "_ok.json")
    try:
        # Catégoriser la shortlist
        cats = categorize_models(shortlist)
        tagged: List[Dict[str, Any]] = []
        for cat, items in cats.items():
            for it in items:
                it_cat = dict(it)
                it_cat["category"] = cat
                tagged.append(it_cat)
        with open(shortlist_path, "w", encoding="utf-8") as f:
            json.dump(tagged, f, indent=2, ensure_ascii=False)
        print(f"Saved shortlist -> {shortlist_path} (count={len(shortlist)})")
    except Exception as e:
        print(f"⚠️  Impossible de sauver la shortlist {shortlist_path}: {e}")

    # Catégorisation simple par capacités perçues (forecast vs parsing vs basique) sur tous les OK
    categorized = categorize_models(ok_sorted)
    cat_path = OUTPUT_PATH.replace(".json", "_categorized.json")
    try:
        with open(cat_path, "w", encoding="utf-8") as f:
            json.dump(categorized, f, indent=2, ensure_ascii=False)
        print(f"Saved categorized -> {cat_path}")
    except Exception as e:
        print(f"⚠️  Impossible de sauver la catégorisation {cat_path}: {e}")

    # Revenir au répertoire initial et nettoyer le tmp
    os.chdir(prev_cwd)
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


def fetch_remote_models(url: str) -> List[Tuple[str, str, str]]:
    """
    Parse working_results.txt (provider|model|type) and keep only text models.
    Returns list of tuples (provider, model, task).
    """
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        lines = resp.text.splitlines()
    except Exception as e:
        print(f"⚠️  fetch_remote_models failed: {e}")
        return []

    out: List[Tuple[str, str, str]] = []
    seen: Dict[Tuple[str, str], bool] = {}
    for line in lines:
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        provider, model, mtype = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if mtype != "text":
            continue
        # Filtrer les modèles trop basiques (nano/mini/très petits)
        low_keywords = [
            "nano",
            "mini",
            "tiny",
            "audio",
            "tts",
            "image",
            "0.6b",
            "1.7b",
            "-2b",
            "-3b",
            "-4b",
            "-5b",
            "-6b",
            "-7b",
        ]
        mlow = model.lower()
        if any(k in mlow for k in low_keywords):
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen[key] = True
        out.append((provider, model, mtype))
    return out


async def _run_async(model_list: List[Tuple[str, str, str]]):
    client = Client()
    results: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(10)  # limiter la concurrence

    async def _run_one(provider: str, model: str, task: str):
        start = time.perf_counter()
        ok = False
        error = None
        answer_preview = ""
        try:
            # g4f client n'est pas async => on déporte dans to_thread
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=model,
                provider=provider,
                messages=[{"role": "user", "content": PROMPT}],
                max_tokens=64,
                temperature=0.1,
                timeout=1,
            )
            msg = resp.choices[0].message.content if resp and resp.choices else ""
            ok = bool(msg)
            answer_preview = (msg or "")[:120].replace("\n", " ")
        except Exception as e:
            error = str(e)
        duration = (time.perf_counter() - start) * 1000
        results.append(
            {
                "provider": provider,
                "model": model,
                "task": task,
                "ok": ok,
                "ms": round(duration, 1),
                "answer": answer_preview,
                "error": error,
            }
        )
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {provider}|{model} ({task}) in {duration:0.1f} ms -> {answer_preview or error}")

    async def _bounded_run(item):
        async with sem:
            await _run_one(*item)

    await asyncio.gather(*[_bounded_run(it) for it in model_list])
    return results


def categorize_models(models: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Classe les modèles OK en trois niveaux:
    - forecast: périmètre resserré (gpt5/gpt-5, o3/o3pro, pplx, claude, turbo, auto, gpt-5 de AnyProvider)
    - helper_json: command-* (y compris r/a/plus/24/25/7b), qwen>=14b, phi-4, mistral
    - basic: tout le reste
    """
    cat = {"forecast": [], "helper_json": [], "basic": []}
    for m in models:
        name = f"{m.get('provider','')}|{m.get('model','')}".lower()
        ans = (m.get("answer") or "").lower()
        target = "basic"
        if any(k in name for k in ["gpt5", "gpt-5", "o3pro", "o3|", "pplx", "claude", "turbo", "auto"]):
            target = "forecast"
        elif any(k in name for k in ["command-", "qwen-3-14", "qwen-3-30", "qwen-3-32", "phi-4", "mistral", "llama-3.3-70b"]):
            target = "helper_json"
        # Si la réponse est vide/erreur format, reléguer basic
        if not ans.strip() or "noneType" in ans:
            target = "basic"
        cat[target].append(m)
    # Trier chaque catégorie par latence
    for k in cat:
        cat[k] = sorted(cat[k], key=lambda r: r.get("ms", 1e9))
    return cat


if __name__ == "__main__":
    sys.exit(main())
