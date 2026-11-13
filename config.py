"""설정 파일: 팀 목록, 평가 기준(벤치마크), 가중치.
벤치마크와 가중치는 이 프로젝트에서 정한 '가정값'이므로 필요하면 여기서 조정하세요."""
import os
import unicodedata

API_BASE = "https://v3.football.api-sports.io"
API_KEY = os.environ.get("API_FOOTBALL_KEY", "")

N_MATCHES = 10          # 분석할 최근 공식 경기 수
FETCH_LAST = 20         # 친선경기를 거르기 위해 여유 있게 가져올 경기 수
FINISHED = {"FT", "AET", "PEN"}

# 팀 이름(영어, 소문자) -> (API-Football 팀 ID, 표시 이름). 목록에 없으면 API로 검색합니다.
TEAMS = {
    "real madrid": (541, "Real Madrid"),
    "fc barcelona": (529, "FC Barcelona"),
    "barcelona": (529, "FC Barcelona"),
    "atletico madrid": (530, "Atletico Madrid"),
    "atletico de madrid": (530, "Atletico Madrid"),
}
TEAM_KO = {"Real Madrid": "레알 마드리드", "FC Barcelona": "FC 바르셀로나", "Atletico Madrid": "아틀레티코 마드리드"}

# 포지션 코드(API) -> 선정 인원
POSITIONS = {"F": 3, "D": 3, "G": 1}
POS_KO = {"F": "공격수", "D": "수비수", "G": "골키퍼"}

# 100점(만점) 기준값: 이 값 이상이면 해당 지표는 만점. (90분당 기준, 골키퍼는 별도 표기)
# 지표: (key, 한글 이름, 만점 기준값, 가중치)
METRICS = {
    "F": [
        ("goals_p90", "골 (90분당)", 0.8, 0.50),
        ("assists_p90", "어시스트 (90분당)", 0.4, 0.30),
        ("passes_p90", "성공한 패스 (90분당)", 40.0, 0.20),
    ],
    "D": [
        ("tackles_p90", "태클 (90분당)", 3.0, 0.35),
        ("interceptions_p90", "가로채기 (90분당)", 2.0, 0.35),
        ("duels_won_p90", "경합 승리 (90분당)*", 7.0, 0.30),
    ],
    "G": [
        ("save_pct", "선방률", 0.80, 0.40),
        ("conceded_p90", "실점 억제 (90분당 실점이 적을수록 높음)", 2.0, 0.30),
        ("clean_sheet_rate", "클린시트 비율", 0.60, 0.30),
    ],
}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())
