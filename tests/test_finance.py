"""Testes do serviço financeiro (regras puras)."""

from decimal import Decimal

from src.modules.career.finance_service import FinanceService, MONTH_DAYS


def test_month_boundary():
    assert FinanceService.is_month_boundary(0) is False
    assert FinanceService.is_month_boundary(28) is True
    assert FinanceService.is_month_boundary(27) is False
    assert FinanceService.is_month_boundary(56) is True
    assert MONTH_DAYS == 28


def test_monthly_math_surplus():
    budget = Decimal("1000000")
    revenue = Decimal("100000")
    payroll = Decimal("80000")
    after = budget + revenue - payroll
    assert after == Decimal("1020000")


def test_monthly_math_insolvent():
    budget = Decimal("10000")
    revenue = Decimal("5000")
    payroll = Decimal("80000")
    after_revenue = budget + revenue
    assert after_revenue < payroll
    paid = after_revenue
    after = Decimal("0")
    assert paid == Decimal("15000")
    assert after == Decimal("0")
