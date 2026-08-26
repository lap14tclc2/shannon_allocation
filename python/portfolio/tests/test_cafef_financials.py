from portfolio.cafef_financials import _find, _latest_table, _number


def test_cafef_vietnamese_numbers_and_statement_rows():
    html = """
    <table>
      <tr><th>Chỉ tiêu</th><th>2024</th><th>2025</th></tr>
      <tr><td>Lợi nhuận sau thuế công ty mẹ</td><td>8.100.000.000</td><td>9.413.589.732.469</td></tr>
      <tr><td>Vốn chủ sở hữu</td><td>29.000.000.000</td><td>30.684.837.000</td></tr>
      <tr><td>Dòng khác</td><td>1</td><td>2</td></tr>
      <tr><td>Dòng khác 2</td><td>1</td><td>2</td></tr>
      <tr><td>Dòng khác 3</td><td>1</td><td>2</td></tr>
    </table>
    """
    frame, column = _latest_table(html)
    assert column == 2
    assert _find(frame, column, "lợi nhuận sau thuế công ty mẹ") == 9_413_589_732_469
    assert _number("131.249,2") == 131_249.2


def test_cafef_parser_does_not_reuse_another_symbol_value():
    first = _number("62.800")
    second = _number("21.850")
    assert first == 62_800
    assert second == 21_850
    assert first != second
