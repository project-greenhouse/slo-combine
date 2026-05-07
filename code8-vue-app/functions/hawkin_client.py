"""
Direct HTTP client for the Hawkin Dynamics Force Platform API (v1.13).
Replaces the hdforce SDK package.

Spec: hawkin-api-v1.13.json (in repo root)
Base URL: https://cloud.hawkindynamics.com (Americas; eu/apac variants exist)

Auth flow:
  1. User provides a Refresh Token (from HD dashboard → Settings → Integrations).
  2. We exchange it via GET /api/token for a 1-hour Access Token.
  3. All other endpoints take Bearer {AccessToken}.
"""
import os
import re
import time
import requests

DEFAULT_BASE = "https://cloud.hawkindynamics.com"


def _unwrap_data(payload):
    """HD endpoints sometimes return {data: [...]}, sometimes a raw [...].
    Normalize both to a list."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("data", [])
    return []


def normalize_metric_key(metric_name: str) -> str:
    """Match the snake_case key style the hdforce SDK used.
    e.g. 'Jump Height(m)' -> 'jump_height_m', 'mRSI' -> 'mrsi',
         'Peak Relative Propulsive Power(W/kg)' -> 'peak_relative_propulsive_power_w_kg'
    """
    s = metric_name.lower()
    s = s.replace("(", "_").replace(")", "")
    s = s.replace(" ", "_").replace("/", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


class HawkinClient:
    """Stateless-ish HTTP client. One instance per request lifetime is fine."""

    def __init__(self, refresh_token: str = None, base_url: str = None):
        self.refresh_token = refresh_token or os.environ.get("HD_TOKEN", "").strip().strip("\"'")
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self._access_token = None
        self._access_expires_at = 0  # unix ts
        self._test_type_cache = None

    # ─── Auth ───────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """Exchange refresh token for a short-lived access token. Cached for ~55 min."""
        if self._access_token and time.time() < self._access_expires_at - 60:
            return self._access_token
        if not self.refresh_token:
            raise RuntimeError("HD_TOKEN (refresh token) not configured.")

        resp = requests.get(
            f"{self.base_url}/api/token",
            headers={"Authorization": f"Bearer {self.refresh_token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HD token exchange failed ({resp.status_code}): {resp.text[:200]}")
        body = resp.json()
        self._access_token = body["access_token"]
        self._access_expires_at = int(body.get("expires_at", time.time() + 3600))
        return self._access_token

    def _headers(self):
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    # ─── Athletes ───────────────────────────────────────────────

    def get_athletes(self, include_inactive: bool = True) -> list[dict]:
        """GET /api/v1/athletes — returns list of {id, name, active, teams, groups, external}."""
        params = {}
        if include_inactive:
            params["includeInactive"] = "true"
        resp = requests.get(
            f"{self.base_url}/api/v1/athletes",
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return _unwrap_data(resp.json())

    def create_athlete(self, name: str, active: bool = True, teams: list[str] = None,
                       groups: list[str] = None, external: dict = None) -> dict:
        """POST /api/v1/athletes — returns the created athlete."""
        payload = {"name": name, "active": active}
        if teams is not None:
            payload["teams"] = teams
        if groups is not None:
            payload["groups"] = groups
        if external is not None:
            payload["external"] = external
        resp = requests.post(
            f"{self.base_url}/api/v1/athletes",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def create_athletes_bulk(self, athletes: list[dict]) -> dict:
        """POST /api/v1/athletes/bulk — up to 500 athletes."""
        resp = requests.post(
            f"{self.base_url}/api/v1/athletes/bulk",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=athletes,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def update_athlete(self, athlete_id: str, name: str = None, active: bool = None,
                       teams: list[str] = None, groups: list[str] = None,
                       external: dict = None) -> dict:
        """PUT /api/v1/athletes/{athleteId} — partial update."""
        payload = {"id": athlete_id}
        if name is not None:
            payload["name"] = name
        if active is not None:
            payload["active"] = active
        if teams is not None:
            payload["teams"] = teams
        if groups is not None:
            payload["groups"] = groups
        if external is not None:
            payload["external"] = external
        resp = requests.put(
            f"{self.base_url}/api/v1/athletes/{athlete_id}",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def update_athletes_bulk(self, athletes: list[dict]) -> dict:
        """PUT /api/v1/athletes/bulk — up to 500."""
        resp = requests.put(
            f"{self.base_url}/api/v1/athletes/bulk",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=athletes,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    # ─── Test Types ─────────────────────────────────────────────

    def get_test_types(self) -> list[dict]:
        """GET /api/v1/test_types — cached for the lifetime of this client."""
        if self._test_type_cache is not None:
            return self._test_type_cache
        resp = requests.get(
            f"{self.base_url}/api/v1/test_types",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        self._test_type_cache = _unwrap_data(resp.json())
        return self._test_type_cache

    def find_test_type_id(self, hint: str) -> str | None:
        """Look up an org-specific test type ID. Tries multiple strategies:
        - exact-match against canonicalId (most stable; CMJ canonicalId is well-known)
        - substring match against name (case + whitespace insensitive)
        - shortcut alias: 'CMJ', 'MR', 'SJ', 'DJ'
        Returns None if not found.
        """
        ALIASES = {
            "CMJ": ["countermovement jump", "counter movement jump", "cmj"],
            "MR": ["multi rebound", "multi-rebound", "multirebound", "mr"],
            "SJ": ["squat jump", "sj"],
            "DJ": ["drop jump", "dj"],
        }
        # Known canonical IDs (stable across orgs)
        CANONICAL = {
            "CMJ": "7nNduHeM5zETPjHxvm7s",
        }

        candidates = ALIASES.get(hint.upper(), [hint.lower()])

        def normalize(s: str) -> str:
            return (s or "").lower().replace(" ", "").replace("-", "").replace("_", "")

        types = self.get_test_types()

        # 1. Try canonical ID match
        canonical = CANONICAL.get(hint.upper())
        if canonical:
            for t in types:
                if t.get("canonicalId") == canonical:
                    return t["id"]

        # 2. Try normalized name match
        normalized_candidates = [normalize(c) for c in candidates]
        for t in types:
            n = normalize(t.get("name"))
            if n in normalized_candidates or any(c in n for c in normalized_candidates):
                return t["id"]

        return None

    # ─── Tests ──────────────────────────────────────────────────

    def get_tests(self, test_type_id: str = None, from_ts: int = None, to_ts: int = None,
                  athlete_id: str = None, include_inactive: bool = True) -> list[dict]:
        """GET /api/v1 — fetch tests. Returns a list of test dicts with metric values
        flattened into snake_case keys (matches old hdforce SDK column naming).

        Each returned dict has at least: athlete_id, athlete_name, timestamp, segment,
        plus all metric keys (e.g. jump_height_m, mrsi, peak_relative_propulsive_power_w_kg).
        """
        params = {}
        if test_type_id:
            params["testTypeId"] = test_type_id
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if athlete_id:
            params["athleteId"] = athlete_id
        if include_inactive:
            params["includeInactive"] = "true"

        resp = requests.get(
            f"{self.base_url}/api/v1",
            headers=self._headers(),
            params=params,
            timeout=60,
        )
        resp.raise_for_status()
        tests = _unwrap_data(resp.json())
        return [self._flatten_test(t) for t in tests]

    @staticmethod
    def _flatten_test(test: dict) -> dict:
        """Flatten the API's nested test object into a single-level dict with
        snake_case metric keys, so existing pandas code can use .iloc[0]['jump_height_m']."""
        out = {}
        athlete = test.get("athlete") or {}
        out["athlete_id"] = athlete.get("id")
        out["athlete_name"] = athlete.get("name")
        out["test_id"] = test.get("id")
        out["timestamp"] = test.get("timestamp")
        out["segment"] = test.get("segment")
        test_type = test.get("testType") or {}
        out["test_type_id"] = test_type.get("id")
        out["test_type_name"] = test_type.get("name")

        # All other top-level fields are metric values. Skip the structured keys.
        skip = {"id", "athlete", "testType", "timestamp", "segment"}
        for k, v in test.items():
            if k in skip:
                continue
            out[normalize_metric_key(k)] = v
        return out
