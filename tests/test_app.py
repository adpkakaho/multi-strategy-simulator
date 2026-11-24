"""새 탭 화면 스모크 테스트."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def weight_inputs(at):
    return [w for w in at.number_input if "전략비중" in w.label]


def test_default_renders_doc_example():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert at.session_state.mix_result["mp"]["삼성전자"] == 22
    assert [m.value for m in at.metric][:4] == ["3개", "8개", "2개", "22%"]


def test_weight_sum_over_100_is_blocked():
    at = AppTest.from_file(APP, default_timeout=60).run()
    weight_inputs(at)[0].set_value(80)
    at = at.run()
    assert not at.exception
    assert any("100% 이하" in e.value for e in at.error)


def test_weight_sum_under_100_leaves_cash():
    at = AppTest.from_file(APP, default_timeout=60).run()
    weight_inputs(at)[2].set_value(0)
    at = at.run()
    assert not at.exception
    assert any("현금" in w.value for w in at.warning)
    assert "네이버" not in at.session_state.mix_result["mp"]


def test_calc_toggle_off_still_renders():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.toggle[0].set_value(False)
    at = at.run()
    assert not at.exception


def test_orders_tab_reproduces_doc_4_2():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    result = at.session_state.order_result["result"]
    assert result.account_cash == 534_000
    assert result.books["A"].qty["삼성전자"] == 172 and result.books["B"].qty["삼성전자"] == 99
    assert "534,000원" in [m.value for m in at.metric]


def test_orders_tab_waits_for_valid_mix():
    at = AppTest.from_file(APP, default_timeout=60).run()
    weight_inputs(at)[0].set_value(80)  # 합계 140% → 믹스 단계에서 막힘
    at = at.run()
    assert not at.exception
    assert at.session_state.order_result is None
    assert any("1 믹스" in i.value for i in at.info)


def test_orders_tab_capital_change():
    at = AppTest.from_file(APP, default_timeout=60).run()
    next(w for w in at.number_input if "가입금액" in w.label).set_value(30_000_000)
    at = at.run()
    assert not at.exception
    assert at.session_state.order_result["result"].capital == 30_000_000
