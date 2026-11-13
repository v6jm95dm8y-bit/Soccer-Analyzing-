"""results/*.json 을 읽어 PPT를 만듭니다. 사용: python make_ppt.py [출력파일]"""
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

import config

FONT = "Malgun Gothic"
DARK, GREEN, LIGHT, GOLD, GRAY = (RGBColor(*c) for c in [(11, 61, 46), (31, 122, 77), (234, 243, 238), (242, 183, 5), (108, 117, 125)])
WHITE, BLACK = RGBColor(255, 255, 255), RGBColor(27, 27, 27)


def text(slide, s, x, y, w, h, size=16, bold=False, color=BLACK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(str(s).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.name = Pt(size), bold, FONT
        r.font.color.rgb = color
    return tb


def box(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    return sh


def new_slide(prs, title):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, title, 0.6, 0.4, 12, 0.8, size=32, bold=True, color=DARK, anchor=MSO_ANCHOR.MIDDLE)
    return s


def build(results, out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 표지
    s = prs.slides.add_slide(prs.slide_layouts[6])
    box(s, 0, 0, 13.333, 7.5, DARK, MSO_SHAPE.RECTANGLE)
    text(s, "라리가 3개 팀 선수 성과 분석", 0.9, 2.3, 11, 1.2, size=44, bold=True, color=WHITE, anchor=MSO_ANCHOR.BOTTOM)
    text(s, "최근 공식 경기 기록 기반 · 포지션별 100점 평가", 0.9, 3.7, 11, 0.6, size=20, color=LIGHT)
    text(s, "  ·  ".join(r["team_ko"] for r in results), 0.9, 6.2, 11, 0.5, size=16, bold=True, color=GOLD)

    # 평가 방법
    s = new_slide(prs, "평가 방법")
    y = 1.6
    for pos, n in config.POSITIONS.items():
        box(s, 0.6, y, 12.1, 1.5, LIGHT)
        text(s, f"{config.POS_KO[pos]} ({n}명)", 0.9, y + 0.15, 3, 0.5, size=20, bold=True, color=DARK)
        parts = [f"{label} {int(w * 100)}%" for _, label, _, w in config.METRICS[pos]]
        text(s, "  /  ".join(parts), 0.9, y + 0.75, 11.5, 0.6, size=16)
        y += 1.75
    text(s, "선정: 포지션별 출전 시간 상위 선수 · 지표는 만점 기준값 대비 비율로 환산 후 가중 합산 (기준값은 config.py에서 조정)",
         0.6, 6.9, 12.1, 0.4, size=12, color=GRAY)

    # 팀별 선수 카드
    for r in results:
        rec = r["record"]
        s = new_slide(prs, f"{r['team_ko']} 선수 점수")
        text(s, f"최근 공식 {r['n_matches']}경기  {rec['W']}승 {rec['D']}무 {rec['L']}패 · {rec['GF']}득점 {rec['GA']}실점 · 전체 평균 {r['summary']['overall']}점",
             0.6, 1.2, 12.1, 0.4, size=16, color=GRAY)
        players = sorted(r["players"], key=lambda p: list(config.POSITIONS).index(p["position"]))
        cw, gap, x0 = 1.65, 0.12, 0.6
        for i, p in enumerate(players):
            x = x0 + i * (cw + gap)
            box(s, x, 1.9, cw, 4.6, LIGHT)
            if p.get("photo") and Path(p["photo"]).exists():
                s.shapes.add_picture(p["photo"], Inches(x + 0.25), Inches(2.05), Inches(1.15), Inches(1.15))
            else:
                box(s, x + 0.25, 2.05, 1.15, 1.15, RGBColor(138, 177, 125), MSO_SHAPE.OVAL)
            text(s, p["pos_ko"], x, 3.35, cw, 0.3, size=12, color=GRAY, align=PP_ALIGN.CENTER)
            text(s, p["name"], x + 0.05, 3.65, cw - 0.1, 0.8, size=14, bold=True, color=DARK, align=PP_ALIGN.CENTER)
            text(s, f"{p['score']:.1f}", x, 4.55, cw, 0.7, size=32, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
            text(s, "/ 100", x, 5.25, cw, 0.3, size=12, color=GRAY, align=PP_ALIGN.CENTER)
            text(s, f"{int(p['apps'])}경기 {int(p['minutes'])}분", x, 5.75, cw, 0.3, size=12, color=GRAY, align=PP_ALIGN.CENTER)

    # 포지션별 비교 그래프
    s = new_slide(prs, "포지션별 평균 점수 비교")
    cd = CategoryChartData()
    cd.categories = [config.POS_KO[p] for p in config.POSITIONS]
    for r in results:
        cd.add_series(r["team_ko"], [r["summary"]["by_position"][p] or 0 for p in config.POSITIONS])
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.4), Inches(12.1), Inches(5.6), cd)
    ch = gf.chart
    ch.has_legend, ch.legend.position, ch.legend.include_in_layout = True, XL_LEGEND_POSITION.BOTTOM, False
    ch.legend.font.size = Pt(14)
    ch.value_axis.maximum_scale, ch.value_axis.minimum_scale = 100, 0
    ch.value_axis.tick_labels.font.size = ch.category_axis.tick_labels.font.size = Pt(14)
    ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(227, 231, 229)
    pl = ch.plots[0]
    pl.has_data_labels = True
    pl.data_labels.font.size = Pt(14)
    pl.data_labels.number_format, pl.data_labels.number_format_is_linked = "0.0", False
    for ser, col in zip(pl.series, [GREEN, GOLD, RGBColor(46, 134, 171)]):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = col

    # 팀 평균표 + 비교
    s = new_slide(prs, "팀 간 비교")
    heads = ["팀", "공격수", "수비수", "골키퍼", "전체 평균"]
    tbl = s.shapes.add_table(len(results) + 1, 5, Inches(0.6), Inches(1.5), Inches(12.1), Inches(0.6 * (len(results) + 1))).table
    for j, h in enumerate(heads):
        c = tbl.cell(0, j)
        c.text = h
        c.fill.solid()
        c.fill.fore_color.rgb = DARK
    for i, r in enumerate(results, start=1):
        vals = [r["team_ko"]] + [r["summary"]["by_position"][p] for p in config.POSITIONS] + [r["summary"]["overall"]]
        for j, v in enumerate(vals):
            c = tbl.cell(i, j)
            c.text = str(v)
            c.fill.solid()
            c.fill.fore_color.rgb = LIGHT
    for i in range(len(results) + 1):
        for j in range(5):
            c = tbl.cell(i, j)
            for p in c.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
                for run in p.runs:
                    run.font.size, run.font.name = Pt(16), FONT
                    run.font.bold = (i == 0 or j == 0)
                    run.font.color.rgb = WHITE if i == 0 else BLACK
            c.vertical_anchor = MSO_ANCHOR.MIDDLE

    # 수치에서 바로 계산되는 사실 요약
    lines = []
    for pos in config.POSITIONS:
        best = max(results, key=lambda r: r["summary"]["by_position"][pos] or 0)
        lines.append(f"{config.POS_KO[pos]} 평균 1위: {best['team_ko']} ({best['summary']['by_position'][pos]}점)")
    ranked = sorted(results, key=lambda r: r["summary"]["overall"] or 0, reverse=True)
    lines.append("전체 평균 순위: " + " > ".join(f"{r['team_ko']} {r['summary']['overall']}" for r in ranked))
    text(s, "\n".join(lines), 0.6, 4.0, 12.1, 2.2, size=18, color=BLACK)
    text(s, "※ 점수는 최근 공식 경기 표본과 config.py의 기준값에 따른 상대적 지표이며, 경기력의 절대 평가가 아닙니다.",
         0.6, 6.8, 12.1, 0.4, size=12, color=GRAY)
    prs.save(out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "laliga_analysis.pptx"
    files = sorted(Path("results").glob("*.json"))
    order = ["real_madrid", "fc_barcelona", "atletico_madrid"]
    files.sort(key=lambda f: order.index(f.stem) if f.stem in order else 99)
    if not files:
        sys.exit("results/ 폴더에 분석 결과가 없습니다. 먼저 python analyze.py 를 실행하세요.")
    build([json.loads(f.read_text(encoding="utf-8")) for f in files], out)
    print("저장:", out)
