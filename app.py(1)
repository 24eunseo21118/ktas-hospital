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

st.set_page_config(page_title="응급환자 KTAS 분류 후 이송 병원 매칭", page_icon="🚑", layout="wide")

KST = ZoneInfo("Asia/Seoul")
BASE = "http://apis.data.go.kr/B552657/ErmctInfoInqireService/"
SIDO_LIST = ["울산광역시", "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시",
             "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도", "전북특별자치도",
             "전라남도", "경상북도", "경상남도", "제주특별자치도"]
FRESH_MIN = 60          # 입력 시각이 이보다 오래되면 '오래된 정보'
LEVEL_NAME = {1: "소생", 2: "긴급", 3: "응급", 4: "준응급", 5: "비응급"}
LEVEL_COLOR = {1: "#d32f2f", 2: "#f57c00", 3: "#fbc02d", 4: "#388e3c", 5: "#1976d2"}


# ───────────────────────── 데이터: 국립중앙의료원 API ─────────────────────────
def service_key():
    try:
        return st.secrets["SERVICE_KEY"]
    except Exception:
        return None


def call_api(operation, params, rows=500):
    """API를 호출해 <item> 목록을 딕셔너리로 돌려준다 (여러 쪽이면 모두)."""
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
    """[고정 데이터] 병원 이름·종류·주소·전화·위도·경도 (하루 한 번)"""
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
    """[실시간 데이터] 응급실 가용병상·수술실·입력 시각 (5분마다 새로)"""
    raw = call_api("getEmrrmRltmUsefulSckbdInfoInqire", {"STAGE1": sido})
    return {pick(r, "hpid"): r for r in raw}, datetime.now(KST)


def parse_time(s):
    try:
        return datetime.strptime(s[:12], "%Y%m%d%H%M").replace(tzinfo=KST)
    except Exception:
        return None


def build_table(master, rt, now):
    """고정 + 실시간을 합치고 상태를 분류한다. '자료 없음'은 표에서 뺀다."""
    rows = []
    for _, h in master.iterrows():
        r = rt.get(h["hpid"])
        if r is None:
            continue                                    # 가용 병상 자료 없음 → 제외
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
def smooth(readings, n=5):
    recent = readings[-n:]
    return round(sum(recent) / len(recent))


def parse_readings(text):
    vals = [float(x) for x in text.replace(" ", "").split(",") if x]
    return vals


# ───────────────────────── [결과 3] 병원 매칭 T = L ∩ K ∩ V ─────────────────────────
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


# ───────────────────────── 화면 ─────────────────────────
st.title("🚑 응급환자 KTAS 분류 후 이송 병원 매칭")
st.caption("환자 정보와 센서값으로 KTAS 등급을 판정하고, 가까움(L)·등급별 수용(K)·가용 병상(V)을 "
           "모두 만족하는 병원(T = L ∩ K ∩ V) 중 가장 가까운 병원을 찾습니다. "
           "학습용 모델이며, 실제 이송은 119와 병원 확인이 필요합니다.")

if not service_key():
    st.error("인증키가 없습니다. Streamlit의 Secrets에 SERVICE_KEY를 넣어 주세요 (README 참고).")
    st.stop()

# ── 사이드바: 지역·현재 위치 ──
with st.sidebar:
    st.header("① 지역과 현재 위치")
    sido = st.selectbox("시·도", SIDO_LIST)
    lat0, lon0 = 35.5384, 129.3114
    try:
        from streamlit_js_eval import get_geolocation
        if st.checkbox("내 위치 사용 (브라우저 위치 권한 필요)"):
            loc = get_geolocation()
            if loc and "coords" in loc:
                lat0, lon0 = loc["coords"]["latitude"], loc["coords"]["longitude"]
                st.success("현재 위치를 받았습니다.")
            else:
                st.info("위치 권한을 허용해 주세요. 받지 못하면 아래에 직접 입력하세요.")
    except Exception:
        pass
    lat = st.number_input("위도", value=float(lat0), format="%.5f")
    lon = st.number_input("경도", value=float(lon0), format="%.5f")
    if st.button("실시간 병상 새로 받기"):
        load_realtime.clear()

try:
    master = load_master(sido)
    rt, fetched_at = load_realtime(sido)
except Exception as e:
    st.error(f"데이터를 받지 못했습니다: {e}")
    st.stop()

hosp = build_table(master, rt, fetched_at)
if hosp.empty:
    st.warning("가용 병상 자료가 있는 병원이 없습니다.")
    st.stop()
hosp["km"] = [distance_km(lat, lon, a, b) for a, b in zip(hosp["lat"], hosp["lon"])]
excluded = len(master) - len(hosp)

# ── 환자 정보 입력 ──
st.subheader("② 환자 정보")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**센서 측정값** — 최근 측정값을 쉼표로 입력하면 최근 5개 평균으로 보정합니다 [결과 2]")
    spo2_txt = st.text_input("산소포화도 SpO2 (%)", "94, 93, 94, 93, 93")
    pulse_txt = st.text_input("맥박 (회/분)", "88, 90, 89, 91, 90")
    temp_txt = st.text_input("체온 (°C)", "36.8")
    sbp_txt = st.text_input("수축기 혈압 (mmHg)", "115")
    dbp_txt = st.text_input("이완기 혈압 (mmHg)", "75")
    resp_txt = st.text_input("호흡수 (회/분)", "16")
with col2:
    st.markdown("**구급대원 확인 항목**")
    gcs = st.slider("GCS (의식 수준 점수)", 3, 15, 15)
    pain = st.slider("통증 점수 NRS", 0, 10, 2)
    c3, c4 = st.columns(2)
    with c3:
        unconscious = st.checkbox("무의식")
        conscious_change = st.checkbox("의식 변화")
        apnea = st.checkbox("자발호흡 없음")
        no_pulse = st.checkbox("맥박 촉지 안 됨")
        shock = st.checkbox("쇼크 징후")
    with c4:
        immuno = st.checkbox("면역저하 상태")
        sepsis = st.checkbox("패혈증 의심")
        sick_or_sirs = st.checkbox("아파 보임 / SIRS 2개 이상")
        mild_only = st.checkbox("경증 소견만 있음")

try:
    sensors = {k: smooth(parse_readings(v)) for k, v in
               {"spo2": spo2_txt, "pulse": pulse_txt, "resp": resp_txt, "sbp": sbp_txt, "dbp": dbp_txt}.items()}
    temp_vals = parse_readings(temp_txt)
    sensors["temp"] = round(sum(temp_vals[-5:]) / len(temp_vals[-5:]), 1)
except Exception:
    st.error("센서값은 숫자를 쉼표로 구분해 입력해 주세요.")
    st.stop()

patient = dict(unconscious=unconscious, gcs=gcs, conscious_change=conscious_change, apnea=apnea,
               no_pulse=no_pulse, shock=shock, immuno=immuno, sepsis=sepsis,
               sick_or_sirs=sick_or_sirs, pain=pain, mild_only=mild_only, **sensors)
level, hit = classify(patient)

# ── 결과 ──
st.subheader("③ 판정 결과와 추천 병원")
st.markdown(
    f"<div style='padding:14px 18px;border-radius:10px;background:{LEVEL_COLOR[level]}22;"
    f"border-left:8px solid {LEVEL_COLOR[level]}'>"
    f"<span style='font-size:26px;font-weight:700'>KTAS {level}단계 ({LEVEL_NAME[level]})</span>"
    f"<br>참인 명제: <b>{', '.join(hit) if hit else '없음 (5단계)'}</b> &nbsp;·&nbsp; "
    f"보정값 SpO2 {sensors['spo2']}%, 맥박 {sensors['pulse']}, 체온 {sensors['temp']}°C</div>",
    unsafe_allow_html=True)

mode, radius, kind, T = match(hosp, level)
dest = T.iloc[0] if len(T) else None
st.write("")
if dest is not None:
    if level <= 2 and radius == 50:
        st.warning(f"20 km 안에 수용 가능한 병원이 없습니다 → **{mode}**")
    else:
        st.success(f"**{mode}** · T = L({radius} km) ∩ K({kind}) ∩ V → 후보 {len(T)}곳 중 가장 가까운 병원")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("추천 병원", dest["name"])
    m2.metric("거리 (직선)", f"{dest['km']:.1f} km")
    m3.metric("응급실 가용병상", int(dest["beds"]))
    m4.metric("입력 시각", dest["updated"])
    st.write(f"{dest['type']} · {dest['addr']} · ☎ {dest['tel']}")
    st.link_button("길안내 (구글 지도)",
                   f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}"
                   f"&destination={dest['lat']},{dest['lon']}")
    with st.expander(f"후보 병원 T ({len(T)}곳)"):
        st.dataframe(T[["name", "type", "km", "beds", "or", "updated", "tel"]].rename(columns={
            "name": "병원", "type": "종류", "km": "거리(km)", "beds": "가용병상", "or": "수술실",
            "updated": "입력 시각", "tel": "전화"}).round({"거리(km)": 1}), hide_index=True)
else:
    if level <= 2:
        st.error(f"**{mode}** — 50 km 안에도 지상 이송 가능한 병원이 없습니다. 상황실에 병원 지정을 함께 요청하세요.")
    else:
        st.error(f"**{mode}** — 50 km 안에 조건에 맞는 병원이 없습니다.")

# ── 지도 ──
st.subheader("④ 지도")
fmap = folium.Map(location=[lat, lon], zoom_start=12)
folium.Marker([lat, lon], tooltip="현재 위치", icon=folium.Icon(color="black", icon="user")).add_to(fmap)
folium.Circle([lat, lon], radius=20000, color="#1976d2", fill=False, tooltip="반경 20 km (L)").add_to(fmap)
color = {"사용 가능": "green", "병상 없음": "red", "오래된 정보": "gray"}
for _, h in hosp.iterrows():
    is_dest = dest is not None and h["hpid"] == dest["hpid"]
    folium.Marker([h["lat"], h["lon"]],
                  tooltip=f"{h['name']} ({h['type']}) · 병상 {h['beds']} · {h['status']}" + (" ← 추천" if is_dest else ""),
                  icon=folium.Icon(color="blue" if is_dest else color[h["status"]],
                                   icon="star" if is_dest else "plus")).add_to(fmap)
st_folium(fmap, height=480, use_container_width=True, returned_objects=[])
st.caption("파란 별: 추천 병원 · 초록: 사용 가능 · 빨강: 병상 없음(0 이하) · 회색: 입력 1시간 넘음")

# ── 병원 현황 ──
st.subheader(f"⑤ {sido} 병원 실시간 현황")
st.caption(f"수집 {fetched_at.strftime('%Y-%m-%d %H:%M')} · 5분마다 새로 받음 · "
           f"가용 병상 자료가 없는 {excluded}곳은 제외 · 출처: 국립중앙의료원(공공데이터포털)")
st.dataframe(hosp.sort_values("km")[["name", "type", "status", "beds", "or", "km", "updated"]].rename(columns={
    "name": "병원", "type": "종류", "status": "상태", "beds": "가용병상", "or": "수술실",
    "km": "거리(km)", "updated": "입력 시각"}).round({"거리(km)": 1}), hide_index=True, width="stretch")
