"""Streamlit 화면: streamlit run app.py"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import config
from analyze import RESULTS, run_analysis
from api_client import ApiError, ApiFootball

st.set_page_config(page_title="라리가 선수 성과 분석", layout="wide")
st.title("라리가 선수 성과 분석")
st.caption("최근 공식 경기 기준 · 공격수 3 / 수비수 3 / 골키퍼 1 · 100점 만점")

with st.sidebar:
    key = st.text_input("API-Football 키", value=config.API_KEY, type="password")
    team = st.text_input("팀 이름 (영어)", placeholder="Real Madrid")
    run = st.button("분석 실행", type="primary", disabled=not team)
    st.markdown("**예시**: Real Madrid, FC Barcelona, Atletico Madrid")

if run:
    try:
        with st.spinner("API에서 경기 기록을 불러오는 중입니다 (처음 한 번은 1~2분 걸릴 수 있습니다)"):
            run_analysis(team, ApiFootball(key or None))
        st.success("분석이 끝났습니다.")
    except (ApiError, RuntimeError, Exception) as e:  # 화면에 원인을 그대로 보여줍니다
        st.error(str(e))

files = sorted(RESULTS.glob("*.json")) if RESULTS.exists() else []
results = [json.loads(f.read_text(encoding="utf-8")) for f in files]
if not results:
    st.info("왼쪽에서 팀 이름을 입력하고 '분석 실행'을 눌러 주세요.")
    st.stop()

tab_players, tab_compare = st.tabs(["선수 점수", "팀 비교"])

with tab_players:
    names = [r["team"] for r in results]
    sel = st.selectbox("팀 선택", names)
    res = results[names.index(sel)]
    rec = res["record"]
    st.write(f"**{res['team_ko']}** · 최근 공식 {res['n_matches']}경기: "
             f"{rec['W']}승 {rec['D']}무 {rec['L']}패, {rec['GF']}득점 {rec['GA']}실점")
    c = st.columns(4)
    c[0].metric("전체 평균", res["summary"]["overall"])
    for i, pos in enumerate(config.POSITIONS):
        c[i + 1].metric(f"{config.POS_KO[pos]} 평균", res["summary"]["by_position"][pos])
    for pos in config.POSITIONS:
        st.subheader(config.POS_KO[pos])
        group = [p for p in res["players"] if p["position"] == pos]
        cols = st.columns(max(len(group), 1))
        for col, p in zip(cols, group):
            with col:
                if p.get("photo") and Path(p["photo"]).exists():
                    st.image(p["photo"], width=110)
                st.markdown(f"**{p['name']}**")
                st.metric("점수", f"{p['score']} / 100")
                st.progress(min(p["score"] / 100, 1.0))
                st.caption(f"출전 {int(p['apps'])}경기 · {int(p['minutes'])}분")
                with st.expander("세부 평가"):
                    st.dataframe(pd.DataFrame(p["details"]), hide_index=True)
    st.caption("* 경합 승리는 API가 공중볼만 따로 제공하지 않아 전체 경합 승리 수로 대신했습니다.")

with tab_compare:
    if len(results) < 2:
        st.info("두 팀 이상 분석하면 비교표가 나타납니다.")
    else:
        rows = [{"팀": r["team_ko"], **{config.POS_KO[p]: r["summary"]["by_position"][p] for p in config.POSITIONS},
                 "전체 평균": r["summary"]["overall"]} for r in results]
        df = pd.DataFrame(rows).set_index("팀")
        st.dataframe(df)
        st.bar_chart(df[[config.POS_KO[p] for p in config.POSITIONS]])
