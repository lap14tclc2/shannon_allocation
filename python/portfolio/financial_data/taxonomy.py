"""
Taxonomy and line-item catalog for Vietnamese financial statements (QFD-240, QFD-260).

Enforces:
- Balance sheet items strictly use PeriodType.INSTANT.
- Income statement and Cash flow use period durations (QUARTER, YTD, FY).
- Taxonomies for Normal Enterprise, Bank, Securities, Insurance.
"""
from __future__ import annotations

from typing import Dict
from .models import EntityType, PeriodType, StatementType

# Core line items for Normal Enterprise
NORMAL_ENTERPRISE_TAXONOMY: Dict[str, Dict[str, str]] = {
    # Income Statement (Durations)
    "IS.REVENUE.GROSS": {"statement": StatementType.INCOME_STATEMENT, "name": "Tổng doanh thu bán hàng & CCDV"},
    "IS.REVENUE.DEDUCTIONS": {"statement": StatementType.INCOME_STATEMENT, "name": "Các khoản giảm trừ doanh thu"},
    "IS.REVENUE.NET": {"statement": StatementType.INCOME_STATEMENT, "name": "Doanh thu thuần"},
    "IS.COGS": {"statement": StatementType.INCOME_STATEMENT, "name": "Giá vốn hàng bán"},
    "IS.PROFIT.GROSS": {"statement": StatementType.INCOME_STATEMENT, "name": "Lợi nhuận gộp"},
    "IS.PROFIT.OPERATING": {"statement": StatementType.INCOME_STATEMENT, "name": "Lợi nhuận từ HĐKD"},
    "IS.PROFIT.PRETAX": {"statement": StatementType.INCOME_STATEMENT, "name": "Tổng lợi nhuận trước thuế"},
    "IS.PROFIT.NET": {"statement": StatementType.INCOME_STATEMENT, "name": "Lợi nhuận sau thuế TNDN"},
    "IS.PROFIT.ATTRIBUTABLE": {"statement": StatementType.INCOME_STATEMENT, "name": "LNST của Cổ đông Công ty mẹ"},

    # Balance Sheet (Strictly INSTANT)
    "BS.ASSETS.TOTAL": {"statement": StatementType.BALANCE_SHEET, "name": "Tổng cộng tài sản"},
    "BS.ASSETS.CURRENT": {"statement": StatementType.BALANCE_SHEET, "name": "Tài sản ngắn hạn"},
    "BS.ASSETS.NON_CURRENT": {"statement": StatementType.BALANCE_SHEET, "name": "Tài sản dài hạn"},
    "BS.CASH_EQUIVALENTS": {"statement": StatementType.BALANCE_SHEET, "name": "Tiền và tương đương tiền"},
    "BS.INVENTORY": {"statement": StatementType.BALANCE_SHEET, "name": "Hàng tồn kho"},
    "BS.LIABILITIES.TOTAL": {"statement": StatementType.BALANCE_SHEET, "name": "Nợ phải trả"},
    "BS.EQUITY.TOTAL": {"statement": StatementType.BALANCE_SHEET, "name": "Vốn chủ sở hữu"},
    "BS.DEBT.TOTAL": {"statement": StatementType.BALANCE_SHEET, "name": "Tổng nợ vay tài chính"},

    # Cash Flow (Durations)
    "CF.OPERATING.NET": {"statement": StatementType.CASH_FLOW, "name": "Lưu chuyển tiền tệ thuần từ HĐKD"},
    "CF.INVESTING.NET": {"statement": StatementType.CASH_FLOW, "name": "Lưu chuyển tiền tệ thuần từ HĐĐT"},
    "CF.FINANCING.NET": {"statement": StatementType.CASH_FLOW, "name": "Lưu chuyển tiền tệ thuần từ HĐTC"},
    "CF.CAPEX": {"statement": StatementType.CASH_FLOW, "name": "Tiền chi mua sắm TSCĐ (Capex)"},
}

# Bank Extensions
BANK_TAXONOMY: Dict[str, Dict[str, str]] = {
    "IS.BANK.INTEREST_INCOME": {"statement": StatementType.INCOME_STATEMENT, "name": "Thu nhập lãi và các khoản tương tự"},
    "IS.BANK.INTEREST_EXPENSE": {"statement": StatementType.INCOME_STATEMENT, "name": "Chi phí lãi và các khoản tương tự"},
    "IS.BANK.NII": {"statement": StatementType.INCOME_STATEMENT, "name": "Thu nhập lãi thuần (NII)"},
    "IS.BANK.PROVISION": {"statement": StatementType.INCOME_STATEMENT, "name": "Chi phí dự phòng rủi ro tín dụng"},
    "BS.BANK.LOANS_CUSTOMER": {"statement": StatementType.BALANCE_SHEET, "name": "Cho vay khách hàng"},
    "BS.BANK.DEPOSITS_CUSTOMER": {"statement": StatementType.BALANCE_SHEET, "name": "Tiền gửi của khách hàng"},
    "BS.BANK.NPL": {"statement": StatementType.BALANCE_SHEET, "name": "Nợ xấu (Nhóm 3-5)"},
}

# Securities Extensions
SECURITIES_TAXONOMY: Dict[str, Dict[str, str]] = {
    "IS.SEC.BROKERAGE_REV": {"statement": StatementType.INCOME_STATEMENT, "name": "Doanh thu môi giới chứng khoán"},
    "IS.SEC.FVTPL_GAIN": {"statement": StatementType.INCOME_STATEMENT, "name": "Lãi từ các TSTC FVTPL"},
    "BS.SEC.MARGIN_LOANS": {"statement": StatementType.BALANCE_SHEET, "name": "Các khoản cho vay ký quỹ (Margin)"},
    "BS.SEC.FVTPL_ASSETS": {"statement": StatementType.BALANCE_SHEET, "name": "Tài sản tài chính FVTPL"},
}

# Insurance Extensions (QFD-260)
INSURANCE_TAXONOMY: Dict[str, Dict[str, str]] = {
    "IS.INS.PREMIUM_GROSS": {"statement": StatementType.INCOME_STATEMENT, "name": "Doanh thu phí bảo hiểm gốc"},
    "IS.INS.PREMIUM_NET": {"statement": StatementType.INCOME_STATEMENT, "name": "Doanh thu thuần HĐ kinh doanh bảo hiểm"},
    "IS.INS.CLAIMS_EXPENSE": {"statement": StatementType.INCOME_STATEMENT, "name": "Chi phí bồi thường bảo hiểm"},
    "BS.INS.TECHNICAL_RESERVES": {"statement": StatementType.BALANCE_SHEET, "name": "Dự phòng nghiệp vụ bảo hiểm"},
}


def get_taxonomy_for_entity(entity_type: EntityType) -> Dict[str, Dict[str, str]]:
    base = dict(NORMAL_ENTERPRISE_TAXONOMY)
    if entity_type == EntityType.BANK:
        base.update(BANK_TAXONOMY)
    elif entity_type == EntityType.SECURITIES:
        base.update(SECURITIES_TAXONOMY)
    elif entity_type == EntityType.INSURANCE:
        base.update(INSURANCE_TAXONOMY)
    return base


def get_required_period_type(statement_type: StatementType, default_period: PeriodType = PeriodType.QUARTER) -> PeriodType:
    """
    Enforces QFD-240 reporting period semantics.
    Balance sheet is always INSTANT.
    """
    if statement_type == StatementType.BALANCE_SHEET:
        return PeriodType.INSTANT
    return default_period
