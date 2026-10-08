# -*- coding: utf-8 -*-
"""Star placement must not leak state between charts (shared Sao singletons)."""
from tuvi_mcp._engine.DiaBan import cungDiaBan
from tuvi_mcp._engine.Sao import saoThienRieu
from tuvi_mcp.horoscope import Horoscope


def _chart():
    return Horoscope.from_birth(
        name="Nguyễn Văn A", day=15, month=8, year=1995, hour=10, gender="Nam"
    ).chart().to_dict()


def test_dac_tinh_does_not_leak_from_previous_chart():
    before = _chart()
    # Giáp Tuất places Thiên riêu where it is Đắc; the next chart has it at a None slot.
    Horoscope.from_birth(
        name="Giáp Tuất", day=18, month=11, year=1994, hour=5, gender="Nam"
    ).chart()
    assert _chart() == before


def test_them_sao_does_not_mutate_singleton():
    sao = saoThienRieu
    original = dict(sao.__dict__)
    cung_dac = cungDiaBan(3)
    cung_none = cungDiaBan(1)
    cung_dac.themSao(sao)
    cung_none.themSao(sao)
    assert sao.__dict__ == original
    assert cung_dac.cungSao[0]["saoDacTinh"] == "Đ"
    assert cung_none.cungSao[0]["saoDacTinh"] is None
    assert cung_dac.cungSao[0] is not cung_none.cungSao[0]
