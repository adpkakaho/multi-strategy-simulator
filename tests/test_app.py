"""Streamlit 화면 스모크 테스트 — 버튼을 실제로 눌러 오류 없이 그려지는지 확인한다."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    return at.run()


def set_weights(at, values):
    for widget, value in zip(at.number_input, values):
        widget.set_value(value)
    return at.run()


def test_run_days_renders_without_error():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    at = set_weights(at, [40, 30, 20])
    at = click(at, "DAY 실행")
    at = click(at, "3일 연속 실행")
    assert not at.exception
    assert len(at.session_state.history) == 4


def test_all_zero_weights_does_not_crash():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at = click(at, "DAY 실행")
    assert not at.exception
    assert len(at.session_state.history) == 1


def test_reset_clears_history():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at = set_weights(at, [50, 50, 0])
    at = click(at, "DAY 실행")
    at = click(at, "시뮬레이션 초기화")
    assert not at.exception
    assert at.session_state.history == []
    assert at.session_state.day_no == 1
