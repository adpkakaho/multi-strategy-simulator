# 멀티전략 DAY 시뮬레이터

전략 A/B/C의 비중을 입력하고 DAY를 실행하면, 통합 MP 산출 → 주문 → 가격변동 → AP 잔고 마감 →
전략별 손익 분해까지 하루 단위로 따라가 볼 수 있는 Streamlit 앱입니다.

> 가격은 난수로 생성한 가상 데이터입니다. 학습·검증용이며 투자 조언이 아닙니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Community Cloud에 배포할 때는 이 저장소를 연결하고 메인 파일로 `app.py`를 지정하면 됩니다.
별도 Secrets는 필요하지 않습니다.

## 구조

```
app.py                 # Streamlit 화면 (입력, 표, 차트, 세션 상태)
simulator/engine.py    # 계산 엔진 — Streamlit에 의존하지 않는 순수 로직
tests/test_engine.py   # 엔진 단위 테스트 (정합성, 재현성)
tests/test_app.py      # 화면 스모크 테스트 (버튼을 실제로 눌러 확인)
```

`simulator.engine.run_day()`는 같은 입력과 seed에 대해 항상 같은 결과를 돌려주므로,
화면 없이 스크립트나 노트북에서도 시뮬레이션을 돌릴 수 있습니다.

## 테스트

```bash
pip install -r requirements-dev.txt
pytest -q
```

push와 pull request마다 GitHub Actions에서 같은 테스트가 실행됩니다.
