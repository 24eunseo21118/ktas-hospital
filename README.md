# 응급환자 KTAS 분류 후 이송 병원 매칭

환자 정보와 센서값으로 KTAS 등급을 판정하고, 국립중앙의료원 실시간 병상 정보로
T = L ∩ K ∩ V (반경 20 km 안 · 등급별 수용 종류 · 가용 병상 있음) 중 가장 가까운 병원을 찾아 주는 사이트입니다.
가용 병상 자료가 없는 병원은 제외합니다. 학습용 모델입니다.

## 파일
- `app.py` : 사이트 코드
- `requirements.txt` : 필요한 라이브러리 목록

## 배포 순서 (무료, 약 15분)

1. **GitHub**
   - github.com 가입 → 오른쪽 위 `+` → **New repository**
   - 이름 예: `ktas-hospital-matching`, Public 선택 → Create
   - **Add file → Upload files**로 `app.py`, `requirements.txt`, `README.md`를 올리고 Commit
   - 인증키는 파일에 절대 쓰지 않습니다.

2. **Streamlit Community Cloud**
   - share.streamlit.io 에서 GitHub 계정으로 가입
   - **Create app → Deploy a public app from GitHub**
   - Repository: 방금 만든 저장소, Branch: `main`, Main file path: `app.py`
   - **Advanced settings → Secrets** 칸에 아래 한 줄을 넣습니다 (공공데이터포털 **Decoding 키**)
     ```
     SERVICE_KEY = "여기에_Decoding_키"
     ```
   - **Deploy** → 몇 분 뒤 `https://○○○.streamlit.app` 주소가 생깁니다.

3. **확인**
   - 왼쪽에서 시·도를 고르면 그 지역 병원의 실시간 병상이 표시됩니다.
   - "내 위치 사용"을 켜면 브라우저가 위치 권한을 묻습니다. 허용하지 않으면 위도·경도를 직접 넣으면 됩니다.

## 내 컴퓨터에서 먼저 실행해 보기 (선택)
```
pip install -r requirements.txt
mkdir .streamlit
echo SERVICE_KEY = "여기에_Decoding_키" > .streamlit/secrets.toml
streamlit run app.py
```

## 문제가 생기면
- "API 오류 ... SERVICE_KEY_IS_NOT_REGISTERED" : 키 확인 (Decoding 키인지, 활용신청 승인됐는지)
- "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS" : 하루 호출 한도 초과 → 다음 날 다시
- 병원 목록이 비어 있음 : 시·도 이름이 API와 다른지 확인 (예: 전북특별자치도, 강원특별자치도)
