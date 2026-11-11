"""JEV (TypeSafe System One) decision adapter.

JEV is a fast, structured decision model. It is NOT an LLM: it does not
generate text. It returns typed answers (choice/score/yes-no) with calibrated
probabilities. We use it for categorization, which is a bounded choice problem.

Configuration (env):
  JEV_API_KEY   - TypeSafe API key
  JEV_API_URL   - endpoint (default: https://api.typesafe.ai/v1/decide)
  JEV_MODEL     - model id (default: jev-1)

The request shape follows JEV's "state + typed questions" contract:
  { "state": <text>, "questions": { "<name>": {"type":"choice","options":[...]} } }
Response:
  { "answers": { "<name>": {"choice": "...", "probability": 0.0-1.0} } }

If the endpoint is unreachable or unconfigured, this adapter raises, and the
decision service falls back to the LLM adapter.
"""
from __future__ import annotations

import json
import os
from typing import Any



class JEVDecisionModel:
    def __init__(self):
        self.api_key = os.environ.get("JEV_API_KEY")
        self.base_url = os.environ.get("JEV_API_URL", "https://api.typesafe.ai/v1/decide")
        self.model = os.environ.get("JEV_MODEL", "jev-1")

    def _configured(self) -> bool:
        return bool(self.api_key)

    def categorize(self, transactions, categories):
        if not self._configured():
            raise RuntimeError("JEV not configured (JEV_API_KEY missing).")
        results = []
        for t in transactions:
            state = (
                f"Transaction: {t.get('description')} | amount: {t.get('amount_cents')} cents | "
                f"date: {t.get('date')}"
            )
            payload = {
                "model": self.model,
                "state": state,
                "questions": {
                    "category": {"type": "choice", "options": categories},
                },
            }
            import urllib.request
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            answer = data.get("answers", {}).get("category", {})
            choice = answer.get("choice") or (categories[0] if categories else "Outros")
            prob = float(answer.get("probability", 0.0))
            results.append({"id": t.get("id"), "category": choice, "confidence": prob})
        return results
