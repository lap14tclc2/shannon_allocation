import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }
function num(v, digits = 2) { return v == null ? '-' : Number(v).toFixed(digits); }

export default function RiskPage({ risk = {}, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const contributions = risk.risk_contributions || {};
  const erc = risk.erc_reference_weights || {};
  const symbols = [...new Set([...Object.keys(contributions), ...Object.keys(erc)])].sort();
  const quality = risk.quality || {};

  return (
    <div className="page">
      <AppNav active="risk" locale={locale} />
      <header className="page-head"><div><h1>{t('risk.title')}</h1><p className="muted">{t('risk.subtitle')}</p></div></header>

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">{t('risk.status')}</div><div className="metric-value">{status(risk.status || 'UNAVAILABLE')}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.vol63')}</div><div className="metric-value">{pct(risk.volatility_63)}</div><div className="muted">{text('Short-term realized risk', 'Rủi ro thực tế ngắn hạn')}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.vol252')}</div><div className="metric-value">{pct(risk.volatility_252)}</div><div className="muted">{text('1-year realized risk', 'Rủi ro thực tế 1 năm')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Volatility trend', 'Xu hướng biến động')}</div><div className="metric-value">{num(risk.volatility_ratio)}×</div><div className="muted">63D / 252D</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.largest')}</div><div className="metric-value">{pct(risk.max_position_weight)}</div><div className="muted">{text('Capital concentration', 'Mức tập trung vốn')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Effective positions', 'Số vị thế hiệu dụng')}</div><div className="metric-value">{num(risk.effective_positions, 1)}</div><div className="muted">1 / HHI</div></div>
        <div className="metric-card"><div className="metric-label">{text('Average correlation', 'Tương quan trung bình')}</div><div className="metric-value">{num(risk.average_correlation)}</div><div className="muted">{text('252D pairwise', 'Cặp mã 252 ngày')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Max correlation', 'Tương quan lớn nhất')}</div><div className="metric-value">{num(risk.max_correlation)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</div><div className="metric-value">{num(risk.diversification_ratio)}</div><div className="muted">{text('Higher usually means more diversification benefit', 'Cao hơn thường cho thấy lợi ích đa dạng hóa lớn hơn')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Daily VaR 95%', 'VaR ngày 95%')}</div><div className="metric-value">{pct(risk.daily_var_95)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Daily CVaR 95%', 'CVaR ngày 95%')}</div><div className="metric-value">{pct(risk.daily_cvar_95)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Downside volatility', 'Biến động phía giảm')}</div><div className="metric-value">{pct(risk.downside_volatility)}</div></div>
      </div>

      <div className="expand-grid">
        <div className="card"><h3>{text('Concentration & diversification', 'Tập trung & đa dạng hóa')}</h3><div className="diag-row"><span>HHI</span><b>{num(risk.hhi, 3)}</b></div><div className="diag-row"><span>{text('Effective positions', 'Số vị thế hiệu dụng')}</span><b>{num(risk.effective_positions, 1)}</b></div><div className="diag-row"><span>{text('Largest capital position', 'Vị thế vốn lớn nhất')}</span><b>{pct(risk.max_position_weight)}</b></div><div className="diag-row"><span>{text('Largest risk contributor', 'Mã đóng góp rủi ro lớn nhất')}</span><b>{risk.largest_risk_symbol || '-'} {pct(risk.largest_risk_contribution)}</b></div><div className="diag-row"><span>{text('Risk-contribution HHI', 'HHI đóng góp rủi ro')}</span><b>{num(risk.risk_contribution_hhi, 3)}</b></div><div className="diag-row"><span>{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</span><b>{num(risk.diversification_ratio)}</b></div></div>
        <div className="card"><h3>{text('Tail-risk diagnostics', 'Chẩn đoán rủi ro đuôi')}</h3><div className="diag-row"><span>{text('Historical daily VaR 95%', 'VaR lịch sử ngày 95%')}</span><b>{pct(risk.daily_var_95)}</b></div><div className="diag-row"><span>{text('Historical daily CVaR 95%', 'CVaR lịch sử ngày 95%')}</span><b>{pct(risk.daily_cvar_95)}</b></div><div className="diag-row"><span>{text('Worst observed day', 'Ngày xấu nhất quan sát được')}</span><b>{pct(risk.max_daily_loss)}</b></div><div className="diag-row"><span>{text('Positive-day ratio', 'Tỷ lệ ngày tăng')}</span><b>{pct(risk.positive_day_ratio)}</b></div><div className="diag-row"><span>{text('Return observations', 'Số quan sát lợi suất')}</span><b>{risk.return_observations ?? '-'}</b></div><p className="muted">{text('Historical VaR/CVaR describes the stored sample; it is not a forecast or loss limit.', 'VaR/CVaR lịch sử mô tả mẫu dữ liệu đang lưu; đây không phải dự báo hay giới hạn thua lỗ.')}</p></div>
      </div>

      <div className="card">
        <h3>{t('risk.contrib_erc')}</h3><p className="muted">{t('risk.erc_note')}</p>
        {symbols.length === 0 ? <div className="muted">{t('risk.not_enough')}</div> : <div className="table-scroll"><table className="ranking"><thead><tr><th>{t('risk.ticker')}</th><th>{t('risk.current_contrib')}</th><th>{t('risk.equal_reference')}</th><th>{t('risk.interpretation')}</th></tr></thead><tbody>{symbols.map((s) => {
          const rc = contributions[s]; const ew = erc[s]; const interpretation = rc == null ? status('NO_DATA') : Number(rc) > 0.35 ? status('HIGH_RISK_CONTRIBUTION') : status('NORMAL');
          return <tr key={s}><td><b>{s}</b></td><td>{pct(rc)}</td><td>{pct(ew)}</td><td>{interpretation}</td></tr>;
        })}</tbody></table></div>}
      </div>

      <div className="card"><h3>{t('risk.data_quality')}</h3><div className="diag-row"><span>{t('common.as_of')}</span><b>{risk.as_of || '-'}</b></div><div className="diag-row"><span>{t('risk.requested_symbols')}</span><b>{quality.requested_symbols ?? '-'}</b></div><div className="diag-row"><span>{t('risk.eligible_symbols')}</span><b>{quality.eligible_symbols ?? '-'}</b></div><div className="diag-row"><span>{t('risk.coverage')}</span><b>{pct(quality.coverage_weight)}</b></div><div className="diag-row"><span>{t('risk.missing_covariance')}</span><b>{quality.missing_covariance_cells ?? '-'}</b></div>{(quality.missing_symbols || []).length > 0 && <div className="run-message">{t('risk.missing_history', { symbols: quality.missing_symbols.join(', ') })}</div>}</div>
    </div>
  );
}
