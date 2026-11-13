"""선수 기록 집계, 선정, 100점 만점 점수 계산."""
from collections import Counter, defaultdict

import config


def _n(x):
    """None/문자열을 숫자로."""
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def aggregate(fixture_players: list[list[dict]]):
    """경기별 선수 목록(여러 경기)을 선수별 누적 기록으로 합칩니다."""
    agg = defaultdict(lambda: Counter())
    meta = {}
    positions = defaultdict(Counter)
    for players in fixture_players:
        for entry in players:
            st = (entry.get("statistics") or [{}])[0]
            minutes = _n(st.get("games", {}).get("minutes"))
            if minutes <= 0:
                continue
            pid = entry["player"]["id"]
            meta[pid] = {"id": pid, "name": entry["player"]["name"], "photo_url": entry["player"].get("photo")}
            positions[pid][st["games"].get("position")] += 1
            a = agg[pid]
            a["minutes"] += minutes
            a["apps"] += 1
            a["goals"] += _n(st.get("goals", {}).get("total"))
            a["assists"] += _n(st.get("goals", {}).get("assists"))
            a["saves"] += _n(st.get("goals", {}).get("saves"))
            conceded = _n(st.get("goals", {}).get("conceded"))
            a["conceded"] += conceded
            total = _n(st.get("passes", {}).get("total"))
            # fixtures/players의 passes.accuracy는 '정확한 패스 수'로 내려옵니다(퍼센트가 아님).
            acc = min(_n(st.get("passes", {}).get("accuracy")), total) if total else 0.0
            a["passes_ok"] += acc
            a["tackles"] += _n(st.get("tackles", {}).get("total"))
            a["interceptions"] += _n(st.get("tackles", {}).get("interceptions"))
            a["duels_won"] += _n(st.get("duels", {}).get("won"))
            if conceded == 0 and minutes >= 60:
                a["clean_sheets"] += 1
    out = []
    for pid, a in agg.items():
        pos = positions[pid].most_common(1)[0][0]
        out.append({**meta[pid], "position": pos, **dict(a)})
    return out


def select_players(players: list[dict]):
    """포지션별로 출전 시간이 가장 긴 선수를 선정(주전급)."""
    chosen = []
    for pos, n in config.POSITIONS.items():
        pool = sorted((p for p in players if p["position"] == pos), key=lambda p: (-p["minutes"], -p["apps"]))
        chosen.extend(pool[:n])
    return chosen


def score_player(p: dict) -> dict:
    pos = p["position"]
    m90 = p["minutes"] / 90.0
    raw = {
        "goals_p90": p.get("goals", 0) / m90,
        "assists_p90": p.get("assists", 0) / m90,
        "passes_p90": p.get("passes_ok", 0) / m90,
        "tackles_p90": p.get("tackles", 0) / m90,
        "interceptions_p90": p.get("interceptions", 0) / m90,
        "duels_won_p90": p.get("duels_won", 0) / m90,
        "conceded_p90": p.get("conceded", 0) / m90,
        "clean_sheet_rate": p.get("clean_sheets", 0) / p["apps"],
    }
    faced = p.get("saves", 0) + p.get("conceded", 0)
    raw["save_pct"] = (p.get("saves", 0) / faced) if faced else 1.0

    details, total = [], 0.0
    for key, label, bench, weight in config.METRICS[pos]:
        v = raw[key]
        ratio = max(0.0, 1 - v / bench) if key == "conceded_p90" else min(v / bench, 1.0)
        sub = ratio * 100
        total += sub * weight
        details.append({"지표": label, "기록": round(v, 2), "만점 기준": bench, "지표 점수": round(sub, 1),
                        "가중치": weight, "반영 점수": round(sub * weight, 1)})
    return {**p, "pos_ko": config.POS_KO[pos], "score": round(total, 1), "details": details}


def team_summary(scored: list[dict]):
    by_pos = {}
    for pos in config.POSITIONS:
        vals = [p["score"] for p in scored if p["position"] == pos]
        by_pos[pos] = round(sum(vals) / len(vals), 1) if vals else None
    allv = [p["score"] for p in scored]
    return {"by_position": by_pos, "overall": round(sum(allv) / len(allv), 1) if allv else None}
