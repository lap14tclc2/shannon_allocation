import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }
function num(v, digits = 2) { return v == null || !Number.isFinite(Number(v)) ? '-' : Number(v).toFixed(digits); }

export default function RiskPage({ risk = {}, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const contributions = risk.risk_contributions || {};
  const erc = risk.erc_reference_weights || {};
  const symbols = [...new Set([...Object.keys(contributions), ...Object.keys(erc)])].sort();
  const quality = risk.quality || {};
  const equalRisk = risk.equal_risk_contribution;
  const highRiskCutoff = equalRisk == null ? 0.45 : Math.max(0.45, 1.5 * Number(equalRisk));
  const coverage = Number(quality.coverage_weight || 0);
  const missing = quality.missing_symbols || [];
  const actualPositions = Number(risk.n_positions || 0);

  const concentrationInterpretation = risk.effective_position_ratio == null
    ? text('Waiting for position weights.', 'Đang chờ tỷ trọng vị thế.')
    : Number(risk.effective_position_ratio) < 0.75
      ? text(`Concentrated: ${num(risk.effective_positions)} effective positions from ${actualPositions} actual holdings.`, `Tập trung: ${num(risk.effective_positions)} vị thế hiệu dụng trên ${actualPositions} mã thực tế.`)
      : text(`Diversification is reasonably distributed across ${num(risk.effective_positions)} effective positions.`, `Đa dạng hóa đang phân bổ tương đối tốt trên ${num(risk.effective_positions)} vị thế hiệu dụng.`);

  const correlationInterpretation = risk.average_correlation == null
    ? text('Correlation is unavailable until enough overlapping D1 history exists.', 'Tương quan chưa khả dụng cho đến khi đủ lịch sử D1 giao nhau.')
    : Number(risk.average_correlation) >= 0.60
      ? text(`High common-move risk: average correlation ${num(risk.average_correlation)}.`, `Rủi ro cùng chiều cao: tương quan trung bình ${num(risk.average_correlation)}.`)
      : Number(risk.average_correlation) >= 0.35
        ? text(`Moderate common-move risk: average correlation ${num(risk.average_correlation)}.`, `Rủi ro cùng chiều trung bình: tương quan ${num(risk.average_correlation)}.`)
        : text(`Low average correlation ${num(risk.average_correlation)} supports diversification.`, `Tương quan trung bình thấp ${num(risk.average_correlation)} hỗ trợ đa dạng hóa.`);

  const volatilityInterpretation = risk.volatility_ratio == null
    ? text('Volatility regime is unavailable until both 63D and 252D windows are populated.', 'Regime biến động chưa khả dụng cho đến khi đủ cả cửa sổ 63D và 252D.')
    : Number(risk.volatility_ratio) > 1.20
      ? text(`Short-term volatility is ${num(risk.volatility_ratio)}× the 1-year level: risk is accelerating.`, `Biến động ngắn hạn bằng ${num(risk.volatility_ratio)}× mức 1 năm: rủi ro đang tăng tốc.`)
      : Number(risk.volatility_ratio) < 0.80
        ? text(`Short-term volatility is ${num(risk.volatility_ratio)}× the 1-year level: conditions are calmer than the long window.`, `Biến động ngắn hạn bằng ${num(risk.volatility_ratio)}× mức 1 năm: thị trường đang yên hơn cửa sổ dài.`)
        : text(`Short- and long-window volatility are broadly aligned (${num(risk.volatility_ratio)}×).`, `Biến động ngắn và dài hạn tương đối đồng pha (${num(risk.volatility_ratio)}×).`);

  return (
    <div className="page">
      <AppNav active="risk" locale={locale} />
      <header className="page-head"><div><h1>{t('risk.title')}</h1><p className="muted">{text('Portfolio-level concentration, volatility, correlation and tail-risk diagnostics. Risk never creates a BUY/SELL transaction.', 'Chẩn đoán tập trung, biến động, tương quan và tail risk ở cấp danh mục. Risk không bao giờ tự tạo transaction BUY/SELL.')}</p></div></header>

      <div className="card">
        <div className="section-head"><div><div className="eyebrow">{text('What matters now', 'Điều quan trọng hiện tại')}</div><h3>{text('Risk interpretation', 'Diễn giải rủi ro')}</h3></div><span className={`status-pill status-${String(risk.status || 'missing').toLowerCase()}`}>{status(risk.status || 'UNAVAILABLE')}</span></div>
        <div className="diag-row"><span>{text('Capital concentration', 'Tập trung vốn')}</span><b>{concentrationInterpretation}</b></div>
        <div className="diag-row"><span>{text('Correlation regime', 'Regime tương quan')}</span><b>{correlationInterpretation}</b></div>
        <div className="diag-row"><span>{text('Volatility regime', 'Regime biến động')}</span><b>{volatilityInterpretation}</b></div>
        <div className="diag-row"><span>{text('Data readiness', 'Độ sẵn sàng dữ liệu')}</span><b>{pct(coverage)} {text('risk coverage', 'độ phủ risk')}{missing.length ? ` · ${text('missing', 'thiếu')}: ${missing.join(', ')}` : ''}</b></div>
        <p className="muted">{text('When coverage is below 90%, missing risk values are intentionally suppressed rather than replaced with misleading zeros.', 'Khi độ phủ dưới 90%, các chỉ số risk thiếu dữ liệu được chủ động để trống thay vì thay bằng số 0 gây hiểu nhầm.')}</p>
      </div>

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">{t('risk.vol63')}</div><div className="metric-value">{pct(risk.volatility_63)}</div><div className="muted">{text('Short-term annualized volatility', 'Biến động năm hóa ngắn hạn')}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.vol252')}</div><div className="metric-value">{pct(risk.volatility_252)}</div><div className="muted">{text('1-year annualized volatility', 'Biến động năm hóa 1 năm')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Volatility trend', 'Xu hướng biến động')}</div><div className="metric-value">{num(risk.volatility_ratio)}×</div><div className="muted">63D / 252D</div></div>
        <div className="metric-card"><div className="metric-label">{text('Risk coverage', 'Độ phủ risk')}</div><div className="metric-value">{pct(coverage)}</div><div className="muted">{quality.eligible_symbols ?? 0}/{quality.requested_symbols ?? actualPositions} {text('eligible holdings', 'mã đủ dữ liệu')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Largest equity weight', 'Tỷ trọng CP lớn nhất')}</div><div className="metric-value">{pct(risk.max_equity_weight)}</div><div className="muted">{text('Concentration excluding cash', 'Tập trung không tính cash')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Effective equity positions', 'Số vị thế CP hiệu dụng')}</div><div className="metric-value">{num(risk.effective_positions, 2)}</div><div className="muted">{pct(risk.effective_position_ratio)} {text('of actual count', 'so với số mã thực tế')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Average / max correlation', 'Tương quan TB / lớn nhất')}</div><div className="metric-value">{num(risk.average_correlation)} / {num(risk.max_correlation)}</div><div className="muted">{text('252D pairwise', 'Cặp mã 252 ngày')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</div><div className="metric-value">{num(risk.diversification_ratio)}</div><div className="muted">{text('>1 implies diversification benefit', '>1 cho thấy có lợi ích đa dạng hóa')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Largest risk contribution', 'Đóng góp rủi ro lớn nhất')}</div><div className="metric-value">{pct(risk.largest_risk_contribution)}</div><div className="muted">{risk.largest_risk_symbol || '-'} · {num(risk.risk_concentration_ratio, 2)}× {text('equal-risk share', 'mức cân bằng')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Daily VaR 95%', 'VaR ngày 95%')}</div><div className="metric-value">{pct(risk.daily_var_95)}</div><div className="muted">{text('Historical 5th percentile', 'Phân vị lịch sử 5%')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Daily CVaR 95%', 'CVaR ngày 95%')}</div><div className="metric-value">{pct(risk.daily_cvar_95)}</div><div className="muted">{text('Average of worst 5% days', 'Trung bình 5% ngày xấu nhất')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Worst observed day', 'Ngày xấu nhất')}</div><div className="metric-value">{pct(risk.max_daily_loss)}</div><div className="muted">{risk.return_observations ?? 0} {text('return observations', 'quan sát lợi suất')}</div></div>
      </div>

      <div className="expand-grid">
        <div className="card"><h3>{text('Concentration & diversification', 'Tập trung & đa dạng hóa')}</h3><div className="diag-row"><span>{text('Equity HHI', 'HHI phần cổ phiếu')}</span><b>{num(risk.equity_hhi, 3)}</b></div><div className="diag-row"><span>{text('Effective positions', 'Số vị thế hiệu dụng')}</span><b>{num(risk.effective_positions, 2)}</b></div><div className="diag-row"><span>{text('Effective / actual ratio', 'Tỷ lệ hiệu dụng / thực tế')}</span><b>{pct(risk.effective_position_ratio)}</b></div><div className="diag-row"><span>{text('Largest NAV position', 'Vị thế NAV lớn nhất')}</span><b>{pct(risk.max_position_weight)}</b></div><div className="diag-row"><span>{text('Largest equity weight', 'Tỷ trọng cổ phiếu lớn nhất')}</span><b>{pct(risk.max_equity_weight)}</b></div><div className="diag-row"><span>{text('Largest risk contributor', 'Mã đóng góp rủi ro lớn nhất')}</span><b>{risk.largest_risk_symbol || '-'} {pct(risk.largest_risk_contribution)}</b></div><div className="diag-row"><span>{text('Risk contribution HHI', 'HHI đóng góp rủi ro')}</span><b>{num(risk.risk_contribution_hhi, 3)}</b></div><div className="diag-row"><span>{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</span><b>{num(risk.diversification_ratio)}</b></div></div>
        <div className="card"><h3>{text('Tail-risk diagnostics', 'Chẩn đoán rủi ro đuôi')}</h3><div className="diag-row"><span>{text('Historical daily VaR 95%', 'VaR lịch sử ngày 95%')}</span><b>{pct(risk.daily_var_95)}</b></div><div className="diag-row"><span>{text('Historical daily CVaR 95%', 'CVaR lịch sử ngày 95%')}</span><b>{pct(risk.daily_cvar_95)}</b></div><div className="diag-row"><span>{text('Worst observed day', 'Ngày xấu nhất quan sát được')}</span><b>{pct(risk.max_daily_loss)}</b></div><div className="diag-row"><span>{text('Downside volatility', 'Biến động phía giảm')}</span><b>{pct(risk.downside_volatility)}</b></div><div className="diag-row"><span>{text('Positive-day ratio', 'Tỷ lệ ngày tăng')}</span><b>{pct(risk.positive_day_ratio)}</b></div><div className="diag-row"><span>{text('Return observations', 'Số quan sát lợi suất')}</span><b>{risk.return_observations ?? '-'}</b></div><p className="muted">{text('Historical VaR/CVaR describes the stored sample; it is not a forecast or guaranteed loss limit.', 'VaR/CVaR lịch sử mô tả mẫu dữ liệu đang lưu; đây không phải dự báo hay giới hạn thua lỗ được đảm bảo.')}</p></div>
      </div>

      <div className="card">
        <h3>{t('risk.contrib_erc')}</h3><p className="muted">{t('risk.erc_note')}</p>
        <p className="muted">{text(`Risk-concentration warning threshold: greater than ${pct(highRiskCutoff)} (max of 45% or 1.5× equal-risk share).`, `Ngưỡng cảnh báo tập trung rủi ro: lớn hơn ${pct(highRiskCutoff)} (lớn hơn giữa 45% và 1,5× mức rủi ro cân bằng).`)}</p>
        {symbols.length === 0 ? <div className="muted">{t('risk.not_enough')}</div> : <div className="table-scroll"><table className="ranking"><thead><tr><th>{t('risk.ticker')}</th><th>{t('risk.current_contrib')}</th><th>{text('Equal-risk contribution', 'Đóng góp rủi ro cân bằng')}</th><th>{text('ERC capital reference', 'Tham chiếu vốn ERC')}</th><th>{t('risk.interpretation')}</th></tr></thead><tbody>{symbols.map((s) => {
          const rc = contributions[s]; const ew = erc[s]; const interpretation = rc == null ? status('NO_DATA') : Number(rc) > highRiskCutoff ? status('HIGH_RISK_CONTRIBUTION') : status('NORMAL');
          return <tr key={s}><td><b>{s}</b></td><td>{pct(rc)}</td><td>{pct(equalRisk)}</td><td>{pct(ew)}</td><td>{interpretation}</td></tr>;
        })}</tbody></table></div>}
      </div>

      <div className="card"><h3>{t('risk.data_quality')}</h3><div className="diag-row"><span>{t('common.as_of')}</span><b>{risk.as_of || '-'}</b></div><div className="diag-row"><span>{t('risk.requested_symbols')}</span><b>{quality.requested_symbols ?? '-'}</b></div><div className="diag-row"><span>{t('risk.eligible_symbols')}</span><b>{quality.eligible_symbols ?? '-'}</b></div><div className="diag-row"><span>{t('risk.coverage')}</span><b>{pct(quality.coverage_weight)}</b></div><div className="diag-row"><span>{t('risk.missing_covariance')}</span><b>{quality.missing_covariance_cells ?? '-'}</b></div><div className="diag-row"><span>{text('Concentration basis', 'Cơ sở tính tập trung')}</span><b>{risk.methodology?.concentration_basis || '-'}</b></div>{missing.length > 0 && <div className="run-message">{t('risk.missing_history', { symbols: missing.join(', ') })}</div>}</div>
    </div>
  );
}
