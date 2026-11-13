"""팀 이름(영어)을 입력하면 데이터 수집 -> 선정 -> 점수 계산 -> JSON 저장.
사용: python analyze.py "Real Madrid" "FC Barcelona" "Atletico Madrid"
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

import config
import scoring
from api_client import ApiFootball

RESULTS = Path("results")
PHOTOS = Path("photos")


def download_photo(pid: int, url: str | None):
    if not url:
        return None
    PHOTOS.mkdir(exist_ok=True)
    path = PHOTOS / f"{pid}.png"
    if not path.exists():
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            path.write_bytes(r.content)
        except requests.RequestException:
            return None  # 사진이 없어도 분석은 계속
    return str(path)


def run_analysis(team_name: str, client: ApiFootball) -> dict:
    team_id, team = client.find_team(team_name)
    fixtures = client.recent_official_fixtures(team_id)
    if not fixtures:
        raise RuntimeError("최근 공식 경기를 찾지 못했습니다. (요금제의 시즌 제한일 수 있습니다)")

    per_fixture, matches = [], []
    w = d = l = gf = ga = 0
    for fx in fixtures:
        per_fixture.append(client.team_players_in_fixture(fx["fixture"]["id"], team_id))
        home = fx["teams"]["home"]["id"] == team_id
        mine = fx["goals"]["home" if home else "away"] or 0
        theirs = fx["goals"]["away" if home else "home"] or 0
        gf, ga = gf + mine, ga + theirs
        w, d, l = w + (mine > theirs), d + (mine == theirs), l + (mine < theirs)
        opp = fx["teams"]["away" if home else "home"]["name"]
        matches.append({"date": fx["fixture"]["date"][:10], "league": fx["league"]["name"],
                        "opponent": opp, "home": home, "score": f"{mine}-{theirs}"})

    chosen = scoring.select_players(scoring.aggregate(per_fixture))
    scored = []
    for p in chosen:
        p["photo"] = download_photo(p["id"], p.get("photo_url"))
        scored.append(scoring.score_player(p))

    result = {"team": team, "team_ko": config.TEAM_KO.get(team, team), "team_id": team_id,
              "generated": datetime.now().isoformat(timespec="seconds"),
              "n_matches": len(fixtures), "record": {"W": w, "D": d, "L": l, "GF": gf, "GA": ga},
              "matches": matches, "players": scored, "summary": scoring.team_summary(scored)}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{team.lower().replace(' ', '_')}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    names = sys.argv[1:] or ["Real Madrid", "FC Barcelona", "Atletico Madrid"]
    api = ApiFootball()
    for n in names:
        res = run_analysis(n, api)
        print(f"{res['team']}: 전체 평균 {res['summary']['overall']} / 경기 {res['n_matches']}")
