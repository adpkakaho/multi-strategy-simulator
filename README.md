# 멀티자문형 랩 시뮬레이터

「멀티자문형랩 구축방안」의 계산 흐름(믹스 → 주문·귀속 → 일별 평가 → 이벤트 → 성과)을 단계별 탭으로 보여주는
Streamlit 앱입니다. 탭마다 위쪽은 고객에게 보이는 화면, 아래쪽은 그 숫자가 나온 계산 과정입니다.

> 화면의 종목·비중·가격은 산식 설명을 위한 가상 예시이며 실제 시세·추천과 무관합니다.

현재 구현된 단계는 **1 믹스(합성 MP)** 와 **2 주문·귀속** 입니다. 나머지 탭은 자리만 잡혀 있습니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Community Cloud에서는 메인 파일로 `app.py`를 지정하면 됩니다. 별도 Secrets는 필요하지 않습니다.

## 구조

```
app.py                          # 탭 프레임 (개요 / 1 믹스 / 2 주문·귀속 / ...)
ui/theme.py                     # 공통 스타일 (구축방안 문서의 흑백 톤)
ui/tab_overview.py              # 개요 탭, 미구현 탭 안내
ui/tab_mix.py                   # 1 믹스 탭
ui/tab_orders.py                # 2 주문·귀속 탭
simulator/mix.py                # 합성 MP 계산 (구축방안 4.1)
simulator/orders.py             # 계좌 주문과 전략별 귀속수량·현금 (구축방안 4.2)
simulator/scenario.py           # 구축방안 4장의 가상 예시 데이터
simulator/engine.py             # 초기 기획(사후 비례배분) 시뮬레이터의 계산 엔진
pages/legacy_day_simulator.py   # 초기 기획 시뮬레이터 화면 (비교용으로 보존)
tests/                          # 계산 단위 테스트와 화면 스모크 테스트
```

## 테스트

```bash
pip install -r requirements-dev.txt
pytest -q
```

구축방안 문서의 예시 숫자를 테스트로 고정해 두었습니다(예: 4.1 합성 목표비중).
push와 pull request마다 GitHub Actions에서 같은 테스트가 실행됩니다.
