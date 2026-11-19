# 응급환자 KTAS 분류 후 이송 병원 매칭 (학습용 모델)
# 실행: streamlit run app.py
import xml.etree.ElementTree as ET
from datetime import datetime
from math import radians, sin, cos, asin, sqrt
from zoneinfo import ZoneInfo

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="응급환자 KTAS 분류 후 이송 병원 매칭", page_icon="🚑",
                   layout="wide", initial_sidebar_state="collapsed")

KST = ZoneInfo("Asia/Seoul")
BASE = "http://apis.data.go.kr/B552657/ErmctInfoInqireService/"
SIDO_LIST = ["울산광역시", "전북특별자치도", "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
             "대전광역시", "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도",
             "전라남도", "경상북도", "경상남도", "제주특별자치도"]
SIDO_CENTER = {"울산광역시": (35.5384, 129.3114), "전북특별자치도": (35.8242, 127.1480),
               "서울특별시": (37.5665, 126.9780), "부산광역시": (35.1796, 129.0756),
               "대구광역시": (35.8714, 128.6014), "인천광역시": (37.4563, 126.7052),
               "광주광역시": (35.1595, 126.8526), "대전광역시": (36.3504, 127.3845),
               "세종특별자치시": (36.4800, 127.2890), "경기도": (37.2636, 127.0286),
               "강원특별자치도": (37.8813, 127.7298), "충청북도": (36.6424, 127.4890),
               "충청남도": (36.6588, 126.6728), "전라남도": (34.8161, 126.4629),
               "경상북도": (36.5760, 128.5056), "경상남도": (35.2280, 128.6811),
               "제주특별자치도": (33.4996, 126.5312)}
FRESH_MIN = 60
LEVEL_NAME = {1: "소생", 2: "긴급", 3: "응급", 4: "준응급", 5: "비응급"}
LEVEL_COLOR = {1: "#D32F2F", 2: "#F57C00", 3: "#F9A825", 4: "#2E7D32", 5: "#1565C0"}
DEMO_CENTER = (35.82, 127.14)       # 가상 병원 모드의 환자 위치 (보고서 Ⅵ-6과 같음)
SPEED_KMH = 30                       # 최민서 방식: 예상 이동시간 계산용 평균 속도 (가정)
M_CONFIRM, D_MIN = 2, 3              # 최민서 방식: 호전 확인 횟수 m, 목적지 변경 기준 d분 (가정)

def html(s):
    """마크다운이 들여쓴 줄을 코드로 보지 않도록 각 줄의 앞 공백을 없앤다."""
    st.markdown("\n".join(line.strip() for line in s.strip().splitlines()), unsafe_allow_html=True)


# ───────────────────────── 화면 스타일 ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, label { font-family: 'Noto Sans KR', sans-serif !important; }
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 0 !important; max-width: 1180px; }
.nav { display:flex; align-items:center; justify-content:space-between; padding:14px 4px; border-bottom:1px solid #E6E9F0; margin-bottom:22px; }
.brand { display:flex; align-items:center; gap:10px; font-weight:900; font-size:17px; color:#14213D; }
.logo { width:34px; height:34px; border-radius:9px; background:#E53935; color:#fff; display:flex; align-items:center; justify-content:center; font-size:22px; font-weight:900; }
.menu a { margin-left:22px; color:#5A6478; text-decoration:none; font-size:14px; font-weight:500; }
.menu a:hover { color:#E53935; }
.hero { background:linear-gradient(120deg,#14213D 0%,#24489A 100%); border-radius:20px; padding:38px 40px; color:#fff; margin-bottom:26px; position:relative; overflow:hidden; }
.hero:after { content:""; position:absolute; right:-60px; top:-60px; width:260px; height:260px; border-radius:50%; background:rgba(255,255,255,.07); }
.hero h1 { color:#fff !important; font-size:34px !important; font-weight:900 !important; margin:6px 0 10px; padding:0 !important; line-height:1.3; }
.hero .eyebrow { color:#AFC3FF; font-weight:700; font-size:14px; letter-spacing:.5px; }
.hero p { color:#DCE4FF; font-size:15px; margin:0 0 20px; max-width:720px; }
.steps { display:flex; gap:10px; flex-wrap:wrap; }
.step { background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.25); padding:8px 14px; border-radius:999px; font-size:13px; font-weight:500; }
.step b { color:#FFD54F; margin-right:6px; }
.sec { font-size:20px; font-weight:900; color:#14213D; margin:6px 0 12px; }
.badge { border-radius:16px; padding:22px 24px; color:#fff; margin-bottom:14px; }
.badge .lv { font-size:15px; opacity:.9; font-weight:500; }
.badge .big { font-size:40px; font-weight:900; line-height:1.15; }
.badge .why { font-size:14px; margin-top:6px; opacity:.95; }
.hcard { border:1px solid #E6E9F0; border-radius:16px; padding:20px 22px; background:#fff; box-shadow:0 4px 16px rgba(20,33,61,.06); }
.hcard .tag { display:inline-block; font-size:12px; font-weight:700; color:#E53935; background:#FDECEC; padding:3px 10px; border-radius:999px; }
.hcard .name { font-size:26px; font-weight:900; color:#14213D; margin:8px 0 2px; }
.hcard .sub { color:#5A6478; font-size:14px; }
.kpis { display:flex; gap:10px; margin:14px 0; }
.kpi { flex:1; background:#F5F7FB; border-radius:12px; padding:10px 12px; }
.kpi .k { font-size:12px; color:#5A6478; }
.kpi .v { font-size:20px; font-weight:900; color:#14213D; }
.btn, .btn:hover { text-decoration:none !important; } .btn { display:inline-block; background:#E53935; color:#fff !important; text-decoration:none; padding:10px 18px; border-radius:10px; font-weight:700; font-size:14px; margin-right:8px; }
.btn.ghost { background:#fff; color:#14213D !important; border:1px solid #CBD2E0; }
.note { background:#FFF8E1; border:1px solid #FFE082; border-radius:12px; padding:12px 14px; font-size:14px; color:#6D4C00; margin-bottom:14px; }
.foot { margin-top:40px; padding:22px 0; border-top:1px solid #E6E9F0; color:#8A93A6; font-size:13px; text-align:center; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px !important; }
.who { font-size:13px; font-weight:900; letter-spacing:.3px; margin-bottom:8px; }
.rule { font-size:13px; color:#5A6478; margin-top:10px; line-height:1.6; }
</style>
""", unsafe_allow_html=True)

html("""
<div class="nav">
  <div class="brand"><div class="logo">+</div>응급환자 KTAS 분류 후 이송 병원 매칭</div>
  <div class="menu"><a href="#ktas">KTAS 판정</a><a href="#compare">두 방식 비교</a><a href="#map">지도·시뮬레이션</a></div>
</div>
<div class="hero">
  <div class="eyebrow">2026 피지컬AI 탐구 프로젝트</div>
  <h1>환자 상태를 입력하면<br>지금 갈 수 있는 가장 가까운 병원을 찾아드립니다</h1>
  <p>센서 측정값과 구급대원 확인 항목으로 KTAS 등급을 판정하고, 위치 · 등급별 수용 · 병상 조건을 모두 만족하는 병원을
  찾습니다. 같은 환자에 대해 장은서 방식과 최민서 방식의 병원 매칭 결과를 나란히 비교합니다.</p>
  <div class="steps">
    <div class="step"><b>01</b>환자 정보 입력</div>
    <div class="step"><b>02</b>센서값 보정 (최근 5개 평균)</div>
    <div class="step"><b>03</b>KTAS 1~5단계 판정</div>
    <div class="step"><b>04</b>두 방식으로 병원 매칭 · 비교</div>
  </div>
</div>
""")


# ───────────────────────── 데이터: 국립중앙의료원 API ─────────────────────────
def service_key():
    try:
        return st.secrets["SERVICE_KEY"]
    except Exception:
        return None


def call_api(operation, params, rows=500):
    items, page = [], 1
    while True:
        p = {"serviceKey": service_key(), "pageNo": page, "numOfRows": rows, **params}
        res = requests.get(BASE + operation, params=p, timeout=15)
        root = ET.fromstring(res.content)
        code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode")
        if code not in (None, "00", "0000"):
            msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg")
            raise RuntimeError(f"API 오류 {code}: {msg}")
        got = [{c.tag: (c.text or "").strip() for c in it} for it in root.iter("item")]
        items += got
        total = int(root.findtext(".//totalCount") or len(items))
        if len(items) >= total or not got:
            return items
        page += 1


def pick(d, *names, default=""):
    for n in names:
        if d.get(n) not in (None, ""):
            return d[n]
    return default


@st.cache_data(ttl=24 * 3600, show_spinner="병원 위치 불러오는 중…")
def load_master(sido):
    raw = call_api("getEgytListInfoInqire", {"Q0": sido})
    df = pd.DataFrame([{
        "hpid": pick(r, "hpid"), "name": pick(r, "dutyName"),
        "type": pick(r, "dutyEmclsName", "dutyEmcls"), "addr": pick(r, "dutyAddr"),
        "tel": pick(r, "dutyTel3", "dutyTel1"),
        "lat": pd.to_numeric(pick(r, "wgs84Lat"), errors="coerce"),
        "lon": pd.to_numeric(pick(r, "wgs84Lon"), errors="coerce"),
    } for r in raw])
    return df.dropna(subset=["lat", "lon"])


@st.cache_data(ttl=300, show_spinner="실시간 병상 불러오는 중…")
def load_realtime(sido):
    raw = call_api("getEmrrmRltmUsefulSckbdInfoInqire", {"STAGE1": sido})
    return {pick(r, "hpid"): r for r in raw}, datetime.now(KST)


def parse_time(s):
    try:
        return datetime.strptime(s[:12], "%Y%m%d%H%M").replace(tzinfo=KST)
    except Exception:
        return None


def build_table(master, rt, now):
    rows = []
    for _, h in master.iterrows():
        r = rt.get(h["hpid"])
        if r is None:
            continue                                     # 가용 병상 자료 없음 → 제외
        beds = int(float(pick(r, "hvec", default="0") or 0))
        ors = int(float(pick(r, "hvoc", default="0") or 0))
        t = parse_time(pick(r, "hvidate"))
        if t is None or (now - t).total_seconds() > FRESH_MIN * 60:
            status = "오래된 정보"
        elif beds <= 0:
            status = "병상 없음"
        else:
            status = "사용 가능"
        rows.append({**h.to_dict(), "beds": beds, "or": ors,
                     "updated": t.strftime("%m-%d %H:%M") if t else "", "status": status})
    return pd.DataFrame(rows)


def demo_table():
    """가상 병원 4곳 (보고서 Ⅵ-6 사례 검증과 같은 값)"""
    now = datetime.now(KST).strftime("%m-%d %H:%M")
    rows = [
        ("V1", "가나대학교병원", "권역응급의료센터", 35.847, 127.140, 2, 6),
        ("V2", "다라병원", "지역응급의료센터", 35.820, 127.110, 4, 3),
        ("V3", "마바병원", "지역응급의료센터", 35.790, 127.160, 0, 2),
        ("V4", "사아의원", "지역응급의료기관", 35.830, 127.170, 3, 1),
    ]
    return pd.DataFrame([{
        "hpid": h, "name": n, "type": t, "addr": "가상 주소", "tel": "000-0000-0000",
        "lat": la, "lon": lo, "beds": b, "or": o, "updated": now,
        "status": "사용 가능" if b > 0 else "병상 없음"} for h, n, t, la, lo, b, o in rows])


# ───────────────────────── [결과 1] KTAS 등급 판정 ─────────────────────────
NORMAL = {"temp": (36.5, 37.5), "pulse": (60, 100), "resp": (12, 20), "sbp": (90, 120), "dbp": (60, 80)}


def propositions(a):
    f = a["temp"] > 38
    m, g, h = a["immuno"], a["sepsis"], a["sick_or_sirs"]
    vitals_ok = all(NORMAL[k][0] <= a[k] <= NORMAL[k][1] for k in NORMAL)
    return {"p1": a["unconscious"] or a["gcs"] <= 8, "p2": a["apnea"] or a["spo2"] < 90,
            "p3": a["no_pulse"] or a["shock"], "q1": a["conscious_change"] and 9 <= a["gcs"] <= 13,
            "q2": 90 <= a["spo2"] < 92, "q3": f and m, "q4": f and g,
            "r1": 92 <= a["spo2"] <= 94, "r2": f and h,
            "s1": a["pain"] < 4 and a["mild_only"] and vitals_ok, "s2": f}


def classify(a):
    p = propositions(a)
    for level, names in [(1, ["p1", "p2", "p3"]), (2, ["q1", "q2", "q3", "q4"]),
                         (3, ["r1", "r2"]), (4, ["s1", "s2"])]:
        hit = [n for n in names if p[n]]
        if hit:
            return level, hit
    return 5, []


# ───────────────────────── [결과 2] 센서 보정 ─────────────────────────
def parse_readings(text):
    return [float(x) for x in text.replace(" ", "").split(",") if x]


def smooth(readings, n=5):
    recent = readings[-n:]
    return sum(recent) / len(recent)


# ───────────────────────── [결과 3] 병원 매칭 ─────────────────────────
K_PRIORITY = {1: ["권역응급의료센터"], 2: ["권역응급의료센터", "지역응급의료센터"],
              3: ["지역응급의료센터"], 4: ["지역응급의료기관"], 5: ["지역응급의료기관"]}


def distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    t = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(t))


def find_T(hosp, level, radius):
    L = set(hosp.loc[hosp["km"] <= radius, "hpid"])
    V = set(hosp.loc[hosp["status"] == "사용 가능", "hpid"])
    for kind in K_PRIORITY[level]:
        K = set(hosp.loc[hosp["type"] == kind, "hpid"])
        T = L & K & V
        if T:
            return kind, hosp[hosp["hpid"].isin(T)].sort_values("km")
    return None, hosp.iloc[0:0]


def match(hosp, level):
    kind, T = find_T(hosp, level, 20)
    if len(T):
        return "지상 이송", 20, kind, T
    kind, T50 = find_T(hosp, level, 50)
    if level <= 2:
        return "닥터헬기 출동 요청 + 지상 대안 준비", 50, kind, T50
    if len(T50):
        return "반경 50 km로 넓혀 지상 이송", 50, kind, T50
    return "상황실에 수용 병원 지정 요청", 50, None, T50


def jang_demo():
    return demo_table()


# ───────────────────────── 최민서 방식 ─────────────────────────
CHOI_ACCEPT_BY_TYPE = {"권역응급의료센터": {1, 2, 3, 4, 5}, "지역응급의료센터": {2, 3, 4, 5},
                       "지역응급의료기관": {3, 4, 5}}   # 실제 병원에 적용할 때의 가정
SENSOR_RANGE = {"spo2": (50, 100), "pulse": (20, 250), "temp": (30, 43), "resp": (4, 60),
                "sbp": (50, 250), "dbp": (30, 150)}


def choi_demo():
    """최민서 Ⅵ-6 병원 조건 표(가상): 가 4 km 3~5단계, 나 6 km 2~5단계, 다 5 km 1~5단계(병상·수술실 불가)"""
    now = datetime.now(KST).strftime("%m-%d %H:%M")
    rows = [("C1", "가병원", 35.84548, 127.17133, {3, 4, 5}, 3, 1),
            ("C2", "나병원", 35.76921, 127.11727, {2, 3, 4, 5}, 2, 1),
            ("C3", "다병원", 35.84252, 127.09203, {1, 2, 3, 4, 5}, 0, 0)]
    return pd.DataFrame([{
        "hpid": h, "name": n, "type": f"가상({min(acc)}~5단계 수용)", "addr": "가상 주소",
        "tel": "000-0000-0000", "lat": la, "lon": lo, "accept": acc, "beds": b, "or": o,
        "updated": now, "status": "사용 가능" if b > 0 else "병상 없음"} for h, n, la, lo, acc, b, o in rows])


def add_accept(hosp):
    hosp = hosp.copy()
    hosp["accept"] = [CHOI_ACCEPT_BY_TYPE.get(t, set()) for t in hosp["type"]]
    return hosp


def sensor_check(sensors, texts):
    """센서 오류·측정값 누락 확인 → 문제 항목 목록"""
    bad = [k for k, v in texts.items() if not v.strip()]
    bad += [k for k, (lo, hi) in SENSOR_RANGE.items() if k in sensors and not lo <= sensors[k] <= hi]
    return bad


def choi_candidates(hosp, level, R, need_or):
    A = set(hosp.loc[hosp["km"] <= R, "hpid"])
    B = set(hosp.loc[[level in acc for acc in hosp["accept"]], "hpid"])
    ok = (hosp["status"] == "사용 가능") & ((hosp["or"] > 0) if need_or else True)
    C = set(hosp.loc[ok, "hpid"])
    return hosp[hosp["hpid"].isin(A & B & C)]


def choi_match(hosp, level, need_or):
    """기본 반경 10 km, 후보가 없으면 5 km씩 최대 2번 확대 → 예상 이동시간이 가장 짧은 병원"""
    hosp = hosp.assign(minutes=hosp["km"] / SPEED_KMH * 60)
    R = 10
    for _ in range(3):
        cand = choi_candidates(hosp, level, R, need_or).sort_values("minutes")
        if len(cand):
            return R, cand
        R += 5
    return R - 5, hosp.iloc[0:0]


# ───────────────────────── 이송 중 시뮬레이션 ─────────────────────────
def jang_trace(base):
    hosp = jang_demo()
    hosp["km"] = [distance_km(*DEMO_CENTER, a, b) for a, b in zip(hosp["lat"], hosp["lon"])]
    log = [94, 93, 94, 93, 93, 88, 93, 91, 90, 90, 90]
    rows, prev, dest = [], None, None
    for t in range(5, len(log) + 1):
        if t == 11:
            hosp.loc[hosp["name"] == "가나대학교병원", ["beds", "status"]] = [0, "병상 없음"]
        s = round(smooth(log[:t]))
        level, hit = classify({**base, "spo2": s})
        bed0 = dest is not None and hosp.loc[hosp["hpid"] == dest, "status"].iloc[0] != "사용 가능"
        why = "첫 판정" if prev is None else "등급 변경" if level != prev else "목적지 병상 0" if bed0 else ""
        if why:
            mode, radius, kind, T = match(hosp, level)
            dest = T.iloc[0]["hpid"] if len(T) else None
            act = f"{T.iloc[0]['name']}({T.iloc[0]['km']:.1f} km)로 {'출발' if prev is None else '변경'}" if len(T) else mode
        else:
            act = "유지"
        rows.append({"시점": f"{t}분", "최근 5개 SpO2": ", ".join(map(str, log[t - 5:t])), "보정값": f"{s}%",
                     "참인 명제": ", ".join(hit), "단계": level, "매칭": why or "-", "목적지·조치": act})
        prev = level
    return pd.DataFrame(rows)


def josa(word, with_final, without_final):
    """받침 여부에 따라 조사를 고른다 (예: 병원+으로, 의원+으로, 나+로)"""
    c = word[-1]
    has_final = "가" <= c <= "힣" and (ord(c) - 0xAC00) % 28 != 0
    return word + (with_final if has_final else without_final)


def choi_trace(base):
    hosp = choi_demo()
    hosp["km"] = [distance_km(*DEMO_CENTER, a, b) for a, b in zip(hosp["lat"], hosp["lon"])]
    windows = [("t0", [93, 94, 92, 93, 93]), ("t1", [91, 92, 90, 91, 91]), ("t2", [89, 90, 88, 89, 89])]
    rows, k, dest, better = [], None, None, 0
    for name, w in windows:
        s = round(smooth(w))
        k_new, hit = classify({**base, "spo2": s})
        changed = False
        if k is None or k_new < k:                 # 첫 판정, 악화는 즉시 반영
            changed = k is not None
            k, better = k_new, 0
        elif k_new > k:                             # 호전은 연속 m회 확인 후 반영
            better += 1
            if better >= M_CONFIRM:
                k, better, changed = k_new, 0, True
        else:
            better = 0
        R, cand = choi_match(hosp, k, need_or=False)
        names = [n for n in cand["name"]]
        if dest is None and len(cand):
            dest = cand.iloc[0]["name"]
            act = f"이동시간이 가장 짧은 {josa(dest, '으로', '로')} 출발"
        elif not len(cand):
            act, dest = "후보 없음 → 상황실에 병원 지정 요청", None
        elif dest not in names:
            old, dest = dest, cand.iloc[0]["name"]
            act = f"{josa(old, '이', '가')} 후보에서 빠져 {josa(dest, '으로', '로')} 목적지 변경"
        else:
            cur = cand.loc[cand["name"] == dest, "minutes"].iloc[0]
            if cand.iloc[0]["minutes"] <= cur - D_MIN:
                dest = cand.iloc[0]["name"]
                act = f"{D_MIN}분 이상 빠른 {josa(dest, '으로', '로')} 변경"
            else:
                act = f"{dest} 유지"
        rows.append({"시점": name, "최근 5초 SpO2": ", ".join(map(str, w)), "이동평균": f"{s}%",
                     "만족 명제": ", ".join(hit), "KTAS 단계": k, "후보 병원": ", ".join(n.replace("병원", "") for n in names) or "∅",
                     "조치": act})
    return pd.DataFrame(rows)


# ───────────────────────── 입력 ─────────────────────────
left, right = st.columns([1.05, 1], gap="large")

with left:
    st.markdown('<div class="sec" id="ktas">환자 정보 입력</div>', unsafe_allow_html=True)
    with st.container(border=True):
        tab1, tab2, tab3 = st.tabs(["📟 센서 측정", "🧑‍⚕️ 구급대원 확인", "📍 위치 · 데이터"])
        with tab1:
            st.caption("최근 측정값을 쉼표로 입력하면 평균으로 보정합니다. 한 개만 넣어도 됩니다.")
            c1, c2 = st.columns(2)
            texts = {"spo2": c1.text_input("산소포화도 SpO2 (%)", "94, 93, 94, 93, 93"),
                     "pulse": c2.text_input("맥박 (회/분)", "88, 90, 89, 91, 90"),
                     "temp": c1.text_input("체온 (°C)", "36.8"),
                     "resp": c2.text_input("호흡수 (회/분)", "16"),
                     "sbp": c1.text_input("수축기 혈압 (mmHg)", "115"),
                     "dbp": c2.text_input("이완기 혈압 (mmHg)", "75")}
        with tab2:
            gcs = st.slider("GCS (의식 수준 점수)", 3, 15, 15)
            pain = st.slider("통증 점수 NRS", 0, 10, 2)
            c3, c4 = st.columns(2)
            unconscious = c3.checkbox("무의식")
            conscious_change = c3.checkbox("의식 변화")
            apnea = c3.checkbox("자발호흡 없음")
            no_pulse = c3.checkbox("맥박 촉지 안 됨")
            shock = c3.checkbox("쇼크 징후")
            immuno = c4.checkbox("면역저하 상태")
            sepsis = c4.checkbox("패혈증 의심")
            sick_or_sirs = c4.checkbox("아파 보임 / SIRS 2개 이상")
            mild_only = c4.checkbox("경증 소견만 있음")
            need_or = st.checkbox("수술이 필요할 수 있음 (최민서 방식: 수술실 조건 적용)")
        with tab3:
            mode_sel = st.radio("병원 데이터", ["실시간 (국립중앙의료원)", "가상 병원 (시연용)"], horizontal=True)
            demo = mode_sel.startswith("가상")
            if demo:
                lat0, lon0 = DEMO_CENTER
                sido = None
                st.caption("가상 병원은 각자 보고서 Ⅵ-6의 병원을 씁니다. (장은서: 4곳, 최민서: 가·나·다 3곳)")
            else:
                sido = st.selectbox("시·도", SIDO_LIST)
                lat0, lon0 = SIDO_CENTER[sido]
                try:
                    from streamlit_js_eval import get_geolocation
                    if st.checkbox("내 위치 사용 (브라우저 위치 권한 필요)"):
                        loc = get_geolocation()
                        if loc and "coords" in loc:
                            lat0, lon0 = loc["coords"]["latitude"], loc["coords"]["longitude"]
                except Exception:
                    pass
            c5, c6 = st.columns(2)
            lat = c5.number_input("현재 위치 위도", value=float(lat0), format="%.5f", key=f"lat_{demo}_{sido}")
            lon = c6.number_input("현재 위치 경도", value=float(lon0), format="%.5f", key=f"lon_{demo}_{sido}")

# 센서값 보정
try:
    sensors = {k: smooth(parse_readings(v)) for k, v in texts.items()}
    sensors = {k: (round(v, 1) if k == "temp" else round(v)) for k, v in sensors.items()}
    sensor_error = None
except Exception:
    sensor_error = "센서값은 숫자를 쉼표로 구분해 입력해 주세요."

# 병원 데이터
notice = None
if not demo:
    try:
        if not service_key():
            raise RuntimeError("인증키가 설정되지 않았습니다")
        master = load_master(sido)
        rt, fetched_at = load_realtime(sido)
        real = build_table(master, rt, fetched_at)
        excluded = len(master) - len(real)
        if real.empty:
            raise RuntimeError("가용 병상 자료가 있는 병원이 없습니다")
        hosp_j, hosp_c = real, add_accept(real)
    except Exception as e:
        notice = (f"실시간 데이터를 받지 못해 <b>가상 병원(시연용)</b>으로 보여 드립니다. "
                  f"<span style='opacity:.75'>({e})</span>")
        demo = True
        lat, lon = DEMO_CENTER
if demo:
    hosp_j, hosp_c, fetched_at, excluded = jang_demo(), choi_demo(), datetime.now(KST), 0
for h in (hosp_j, hosp_c):
    h["km"] = [distance_km(lat, lon, a, b) for a, b in zip(h["lat"], h["lon"])]

# ───────────────────────── KTAS 판정 (두 방식 공통) ─────────────────────────
with right:
    st.markdown('<div class="sec">KTAS 판정 결과</div>', unsafe_allow_html=True)
    if notice:
        st.markdown(f'<div class="note">{notice}</div>', unsafe_allow_html=True)
    if sensor_error:
        st.error(sensor_error)
        st.stop()
    patient = dict(unconscious=unconscious, gcs=gcs, conscious_change=conscious_change, apnea=apnea,
                   no_pulse=no_pulse, shock=shock, immuno=immuno, sepsis=sepsis,
                   sick_or_sirs=sick_or_sirs, pain=pain, mild_only=mild_only, **sensors)
    level, hit = classify(patient)
    col = LEVEL_COLOR[level]
    html(f"""
    <div class="badge" style="background:linear-gradient(120deg,{col},{col}CC)">
      <div class="lv">[결과 1] 두 방식 공통</div>
      <div class="big">{level}단계 · {LEVEL_NAME[level]}</div>
      <div class="why">참인 명제: <b>{', '.join(hit) if hit else '없음 (나머지 → 5단계)'}</b>
      &nbsp;|&nbsp; 보정값 SpO2 {sensors['spo2']}% · 맥박 {sensors['pulse']} · 체온 {sensors['temp']}°C</div>
    </div>""")
    st.caption("두 사람 모두 위급한 단계부터 검사해 처음 참이 되는 단계로 확정하므로 등급은 같습니다. "
               "병원을 고르는 방법([결과 2]·[결과 3])이 다릅니다.")

# ───────────────────────── 두 방식 비교 ─────────────────────────
st.write("")
st.markdown('<div class="sec" id="compare">추천 병원 · 두 방식 비교</div>', unsafe_allow_html=True)
cj, cc = st.columns(2, gap="large")


def hospital_card(who, color, tag, h, kpis, rule, maps=None):
    kpi_html = "".join(f'<div class="kpi"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in kpis)
    btn = f'<a class="btn" href="{maps}" target="_blank">길안내 시작</a>' if maps else ""
    name = h["name"] if h is not None else "조건에 맞는 병원 없음"
    sub = f"{h['type']} · ☎ {h['tel']}" if h is not None else ""
    html(f"""
    <div class="hcard" style="border-top:5px solid {color}">
      <div class="who" style="color:{color}">{who}</div>
      <span class="tag">{tag}</span>
      <div class="name">{name}</div>
      <div class="sub">{sub}</div>
      <div class="kpis">{kpi_html}</div>
      {btn}
      <div class="rule">{rule}</div>
    </div>""")


def maps_link(h):
    return f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={h['lat']},{h['lon']}"


with cj:
    mode_j, radius_j, kind_j, T_j = match(hosp_j, level)
    dest_j = T_j.iloc[0] if len(T_j) else None
    tag_j = ("🚁 " + mode_j) if (level <= 2 and radius_j == 50) else f"{mode_j} · 후보 {len(T_j)}곳"
    hospital_card(
        "장은서 방식", "#E53935", tag_j, dest_j,
        [("거리 (직선)", f"{dest_j['km']:.1f} km"), ("가용병상", int(dest_j["beds"])),
         ("입력 시각", dest_j["updated"])] if dest_j is not None else [],
        "반경 20 km(없으면 50 km) · 등급별 병원 종류(Pre-KTAS 기준) · 가용병상 있음<br>"
        "→ 세 조건의 교집합 중 <b>가장 가까운</b> 병원 · 후보 없으면 1~2단계는 닥터헬기",
        maps_link(dest_j) if dest_j is not None else None)
    with st.expander("장은서 방식 후보 병원"):
        st.dataframe(T_j[["name", "type", "km", "beds"]].rename(columns={
            "name": "병원", "type": "종류", "km": "거리(km)", "beds": "가용병상"}).round({"거리(km)": 1}),
            hide_index=True, width="stretch")

with cc:
    bad = sensor_check(sensors, texts)
    if bad:
        hospital_card("최민서 방식", "#5E35B1", "⚠ 센서 오류 · 측정값 누락", None, [],
                      f"확인 필요: {', '.join(bad)} → 재측정하고 구급대원이 확인한 뒤 판정합니다.")
        dest_c = None
    else:
        R_c, cand_c = choi_match(hosp_c, level, need_or)
        dest_c = cand_c.iloc[0] if len(cand_c) else None
        tag_c = (f"반경 {R_c} km · 후보 {len(cand_c)}곳 중 이동시간 최단" if dest_c is not None
                 else "후보 없음 → 상황실에 병원 지정 요청")
        hospital_card(
            "최민서 방식", "#5E35B1", tag_c, dest_c,
            [("예상 이동시간", f"{dest_c['minutes']:.0f}분"), ("거리 (직선)", f"{dest_c['km']:.1f} km"),
             ("병상 · 수술실", f"{int(dest_c['beds'])} · {int(dest_c['or'])}")] if dest_c is not None else [],
            f"반경 10 km(5 km씩 최대 2번 확대) · 병원별 수용 가능 단계 · 병상{' 및 수술실' if need_or else ''} 이용 가능<br>"
            f"→ 세 조건의 교집합 중 <b>예상 이동시간이 가장 짧은</b> 병원 · 후보 없으면 상황실 지정 요청",
            maps_link(dest_c) if dest_c is not None else None)
        with st.expander("최민서 방식 후보 병원"):
            st.dataframe(cand_c[["name", "type", "minutes", "km", "beds", "or"]].rename(columns={
                "name": "병원", "type": "종류", "minutes": "이동시간(분)", "km": "거리(km)",
                "beds": "가용병상", "or": "수술실"}).round({"이동시간(분)": 0, "거리(km)": 1}),
                hide_index=True, width="stretch")

if demo:
    st.caption("가상 병원 모드에서는 두 방식이 각자 보고서의 가상 병원을 쓰므로 추천 병원 이름이 다릅니다. "
               "실시간 모드에서는 같은 실제 병원 목록으로 비교합니다.")
else:
    same = dest_j is not None and dest_c is not None and dest_j["hpid"] == dest_c["hpid"]
    st.info("두 방식이 같은 병원을 추천했습니다." if same else
            "두 방식의 추천 병원이 다릅니다. 반경·병원 수용 기준·최종 선택 기준(거리 vs 이동시간)의 차이 때문입니다.")
st.caption(f"최민서 방식의 가정값: 평균 속도 시속 {SPEED_KMH} km(이동시간 계산), 호전 확인 {M_CONFIRM}회, 목적지 변경 기준 {D_MIN}분"
           + ("" if demo else ", 실제 병원의 수용 가능 단계는 권역 1~5 · 지역센터 2~5 · 지역기관 3~5단계로 가정"))

# ───────────────────────── 지도 · 시뮬레이션 · 현황 · 알고리즘 ─────────────────────────
st.write("")
st.markdown('<div class="sec" id="map">지도 · 이송 중 시뮬레이션</div>', unsafe_allow_html=True)
t_map, t_sim, t_status, t_about = st.tabs(["🗺️ 지도", "⏱️ 이송 중 시뮬레이션", "🏥 병원 현황", "📘 알고리즘 비교"])

with t_map:
    fmap = folium.Map(location=[lat, lon], zoom_start=12 if demo else 11, tiles="OpenStreetMap")
    folium.Marker([lat, lon], tooltip="현재 위치", icon=folium.Icon(color="black", icon="user")).add_to(fmap)
    folium.Circle([lat, lon], radius=20000, color="#E53935", fill=False, tooltip="장은서 기본 반경 20 km").add_to(fmap)
    folium.Circle([lat, lon], radius=10000, color="#5E35B1", fill=False, dash_array="6",
                  tooltip="최민서 기본 반경 10 km").add_to(fmap)
    color = {"사용 가능": "green", "병상 없음": "red", "오래된 정보": "gray"}
    shown = set()
    for who, h_df, dest, star in (("장은서", hosp_j, dest_j, "red"), ("최민서", hosp_c, dest_c, "purple")):
        for _, h in h_df.iterrows():
            is_dest = dest is not None and h["hpid"] == dest["hpid"]
            if h["hpid"] in shown and not is_dest:
                continue
            shown.add(h["hpid"])
            folium.Marker([h["lat"], h["lon"]],
                          tooltip=f"{h['name']} ({h['type']}) · 병상 {h['beds']} · {h['status']}"
                                  + (f" ← {who} 방식 추천" if is_dest else ""),
                          icon=folium.Icon(color=star if is_dest else color.get(h["status"], "gray"),
                                           icon="star" if is_dest else "plus")).add_to(fmap)
    st_folium(fmap, height=460, use_container_width=True, returned_objects=[])
    st.caption("빨간 별: 장은서 방식 추천 · 보라 별: 최민서 방식 추천 · 초록: 사용 가능 · 회색: 병상 없음·오래된 정보 · "
               "빨간 원: 반경 20 km · 보라 점선: 반경 10 km")

with t_sim:
    base_pt = {**patient, "mild_only": False}
    st.markdown("**장은서 방식** · 1분마다 측정, 최근 5개 평균 · 11분에 가나대학교병원 병상이 0이 됨 (가상)")
    st.dataframe(jang_trace(base_pt), hide_index=True, width="stretch")
    st.markdown("**최민서 방식** · 5초 동안 측정한 값의 평균을 30초마다 반영 · 악화는 즉시, 호전은 연속 "
                f"{M_CONFIRM}회 확인 후 반영 (가상)")
    st.dataframe(choi_trace(base_pt), hide_index=True, width="stretch")
    st.caption("두 표 모두 SpO2만 떨어지고 나머지 조건은 그대로라고 가정한 각자 보고서 Ⅵ-6의 사례입니다. "
               "위에서 입력한 SpO2 외의 환자 정보가 함께 반영됩니다.")

with t_status:
    if demo:
        st.caption("가상 병원(시연용)")
        st.dataframe(pd.concat([hosp_j.assign(방식="장은서"), hosp_c.assign(방식="최민서")])[
            ["방식", "name", "type", "status", "beds", "or", "km"]].rename(columns={
                "name": "병원", "type": "종류", "status": "상태", "beds": "가용병상", "or": "수술실",
                "km": "거리(km)"}).round({"거리(km)": 1}), hide_index=True, width="stretch")
    else:
        st.caption(f"{sido} · 국립중앙의료원 실시간 · 기준 {fetched_at.strftime('%Y-%m-%d %H:%M')} · "
                   f"5분마다 갱신 · 가용병상 자료가 없는 {excluded}곳 제외")
        st.dataframe(hosp_j.sort_values("km")[["name", "type", "status", "beds", "or", "km", "updated"]].rename(columns={
            "name": "병원", "type": "종류", "status": "상태", "beds": "가용병상", "or": "수술실",
            "km": "거리(km)", "updated": "입력 시각"}).round({"거리(km)": 1}), hide_index=True, width="stretch")
        if st.button("실시간 병상 새로 받기"):
            load_realtime.clear()
            st.rerun()

with t_about:
    st.markdown("**[결과 1] KTAS 등급 판정 (공통)**")
    st.code("if p1∨p2∨p3 → 1단계\nelse if q1∨q2∨q3∨q4 → 2단계\nelse if r1∨r2 → 3단계\n"
            "else if s1∨s2 → 4단계\nelse → 5단계", language=None)
    st.dataframe(pd.DataFrame([
        ["센서 보정", "1분마다, 최근 5개 평균", "5초 동안 모은 값의 평균, 30초마다 반영"],
        ["센서 오류", "-", "오류·누락 시 재측정, 구급대원 확인"],
        ["병원 조건", "반경 · 등급별 병원 종류 · 가용병상", "반경 · 병원별 수용 가능 단계 · 병상(및 수술실)"],
        ["검색 반경", "20 km → 50 km", "10 km에서 5 km씩 최대 2번"],
        ["최종 선택", "가장 가까운 거리", "예상 이동시간이 가장 짧은 병원"],
        ["후보 없음", "1~2단계 닥터헬기 + 지상 대안", "상황실 병원 지정 요청"],
        ["등급 변경", "바뀌면 바로 재매칭", "악화 즉시, 호전은 m회 확인 후"],
        ["목적지 변경", "등급 변경, 목적지 병상 0", "목적지가 후보에서 빠짐, d분 이상 빠른 병원"],
    ], columns=["항목", "장은서", "최민서"]), hide_index=True, width="stretch")

html("""
<div class="foot">
  응급환자 KTAS 분류 후 이송 병원 매칭 · 2026 피지컬AI 탐구 프로젝트 (장은서 · 최민서)<br>
  데이터 출처: 국립중앙의료원 전국 응급의료기관 정보 조회 서비스(공공데이터포털) ·
  학습용 모델이며 실제 이송 판단은 119와 해당 병원 확인이 필요합니다.
</div>""")
