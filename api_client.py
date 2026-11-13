"""API-Football(v3) 호출 모듈. 응답은 디스크에 캐시해 하루 100회 한도를 아낍니다."""
import hashlib
import json
import time
from pathlib import Path

import requests

import config

CACHE_DIR = Path(".cache")


class ApiError(RuntimeError):
    pass


class ApiFootball:
    def __init__(self, api_key: str | None = None, use_cache: bool = True):
        self.key = api_key or config.API_KEY
        if not self.key:
            raise ApiError("API 키가 없습니다. 환경변수 API_FOOTBALL_KEY를 설정하거나 앱 사이드바에 입력하세요.")
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": self.key})
        CACHE_DIR.mkdir(exist_ok=True)

    def get(self, path: str, **params):
        cache_file = CACHE_DIR / (hashlib.md5(f"{path}{sorted(params.items())}".encode()).hexdigest() + ".json")
        if self.use_cache and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        r = self.session.get(config.API_BASE + path, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        errors = data.get("errors")
        if errors:  # 빈 리스트/딕셔너리가 아니면 오류 (요금제의 시즌 제한 메시지도 여기로 옵니다)
            raise ApiError(f"API 오류: {errors}")

        daily_left = r.headers.get("x-ratelimit-requests-remaining")
        minute_left = r.headers.get("X-RateLimit-Remaining")
        if self.use_cache:
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        if daily_left is not None and int(daily_left) <= 0:
            raise ApiError("오늘의 호출 한도를 모두 사용했습니다. 내일(UTC 자정 이후) 다시 시도하세요.")
        if minute_left is not None and int(minute_left) <= 1:
            time.sleep(61)  # 분당 한도 보호
        return data

    # ---- 편의 함수 ----
    def find_team(self, name: str):
        key = config.norm_name(name)
        if key in config.TEAMS:
            return config.TEAMS[key]
        data = self.get("/teams", search=name)
        for item in data.get("response", []):
            t = item["team"]
            if item["team"].get("country") == "Spain" and not t.get("national"):
                return t["id"], t["name"]
        raise ApiError(f"'{name}' 팀을 찾지 못했습니다. 영어 팀 이름을 확인하세요.")

    def recent_official_fixtures(self, team_id: int, n: int = config.N_MATCHES):
        data = self.get("/fixtures", team=team_id, last=config.FETCH_LAST)
        out = []
        for fx in data.get("response", []):
            if fx["fixture"]["status"]["short"] not in config.FINISHED:
                continue
            if "friendl" in fx["league"]["name"].lower():  # 친선경기 제외 = 공식 경기만
                continue
            out.append(fx)
        out.sort(key=lambda f: f["fixture"]["timestamp"], reverse=True)
        return out[:n]

    def team_players_in_fixture(self, fixture_id: int, team_id: int):
        data = self.get("/fixtures/players", fixture=fixture_id)
        for block in data.get("response", []):
            if block["team"]["id"] == team_id:
                return block["players"]
        return []
