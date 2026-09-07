import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { navigate } from '../lib/navigation.js';
import { formatNumber as num, money, pct, signedMoney } from '../lib/format.js';

function SeverityPill({ severity = 'NORMAL', labelOverride }) {
  const toneMap = {
    HIGH_RISK: 'high',
    HIGH: 'high',
    WARNING: 'high',
    ELEVATED: 'high',
    ATTENTION: 'watch',
    MODERATE: 'watch',
    NORMAL: 'good',
    LOW: 'good',
    UNKNOWN: 'building',
  };
  const labelMap = {
    HIGH_RISK: 'Cảnh báo cao',
    HIGH: 'Cao',
    WARNING: 'Cảnh báo',
    ELEVATED: 'Đáng chú ý',
    ATTENTION: 'Cần chú ý',
    MODERATE: 'Trung bình',
    NORMAL: 'Bình thường',
    LOW: 'Thấp',
    UNKNOWN: 'Chưa đủ dữ liệu',
  };
  const tone = toneMap[severity] || 'neutral';
  const label = labelOverride || labelMap[severity] || severity;
  return <span className={`risk-level risk-level-${tone}`}>{label}</span>;
}

function RiskWarningCard({ warning }) {
  const {
    id,
    category,
    severity,
    title,
    summary,
    affected_symbols = [],
    impact,
    review_guidance,
  } = warning;

  const tone = severity === 'HIGH_RISK' || severity === 'WARNING' || severity === 'HIGH'
    ? 'high'
    : severity === 'ATTENTION' || severity === 'ELEVATED' || severity === 'MODERATE'
    ? 'watch'
    : 'good';

  return (
    <article className={`risk-insight-card risk-tone-${tone} risk-warning-item`} key={id}>
      <div className="risk-insight-top">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span className="eyebrow" style={{ margin: 0, textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.05em' }}>
            {category.replace(/_/g, ' ')}
          </span>
          {affected_symbols.length > 0 && affected_symbols.map(s => (
            <span key={s} style={{ background: 'var(--surface-soft, rgba(0,0,0,0.06))', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 700 }}>
              {s}
            </span>
          ))}
        </div>
        <SeverityPill severity={severity} />
      </div>

      <div className="risk-insight-content" style={{ padding: '16px 20px' }}>
        <h3 style={{ margin: '0 0 8px', fontSize: '16.5px', color: 'var(--text)' }}>{title}</h3>
        <p className="risk-insight-copy" style={{ fontWeight: 500, fontSize: '13.5px', marginBottom: '14px', color: 'var(--text)' }}>{summary}</p>

        {impact && (
          <div className="risk-impact-box" style={{ background: 'var(--surface-soft, rgba(0,0,0,0.03))', padding: '12px 14px', borderRadius: '8px', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
              Tác động biến động danh mục
            </span>
            <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: 'var(--text)' }}>{impact}</p>
          </div>
        )}

        {review_guidance && (
          <div className="risk-guidance-box" style={{ background: 'color-mix(in srgb, var(--accent, #0055ff) 8%, transparent)', padding: '12px 14px', borderRadius: '8px', borderLeft: '3px solid var(--accent, #0055ff)' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent, #0055ff)', display: 'block', marginBottom: '4px' }}>
              Hướng dẫn kiểm tra tiếp theo
            </span>
            <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: 'var(--text)' }}>{review_guidance}</p>
          </div>
        )}
      </div>

      <div className="risk-insight-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>Chẩn đoán rủi ro · Không tự động phát sinh lệnh</span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => navigate('/allocation')}
          style={{ cursor: 'pointer', fontSize: '12px', padding: '4px 10px', fontWeight: 600 }}
        >
          Giả lập trong Phân bổ vốn →
        </button>
      </div>
    </article>
  );
}

export default function RiskPage({ risk = {}, snapshots: initialSnapshots = [], locale = 'vi' }) {
  const [snapshots, setSnapshots] = useState(initialSnapshots || []);
  const [showAllWarnings, setShowAllWarnings] = useState(false);

  const quality = risk.quality || {};
  const coverage = Number(quality.coverage_weight || 0);
  const observations = Number(risk.return_observations || 0);
  const missing = quality.missing_symbols || [];
  const largestWeight = risk.max_equity_weight == null ? null : Number(risk.max_equity_weight);
  const largestPositionSymbol = String(risk.largest_position_symbol || '').toUpperCase() || null;
  const effectivePositions = risk.effective_positions == null ? null : Number(risk.effective_positions);
  const avgCorrelation = risk.average_correlation == null ? null : Number(risk.average_correlation);
  const vol63 = risk.volatility_63 == null ? null : Number(risk.volatility_63);
  const vol252 = risk.volatility_252 == null ? null : Number(risk.volatility_252);
  const largestRisk = risk.largest_risk_contribution == null ? null : Number(risk.largest_risk_contribution);
  const symbolMetrics = risk.symbol_metrics || {};
  const symbolRiskMap = risk.symbol_risk || {};

  const riskCoverageStatus = risk.risk_coverage_status || (coverage >= 0.90 && observations >= 20 ? 'COMPLETE' : coverage > 0 ? 'PARTIAL' : 'INSUFFICIENT');
  const riskEligibleSymbols = risk.risk_eligible_symbols || [];
  const riskTotalSymbols = risk.risk_total_symbols || Object.keys(symbolMetrics).length;
  const riskEligibleNavWeight = risk.risk_eligible_nav_weight != null ? Number(risk.risk_eligible_nav_weight) : coverage;

  const marketRiskSummary = risk.risk_summary?.market_risk || risk.market_risk || {
    overall_severity: largestWeight >= 0.40 || largestRisk >= 0.45 ? 'HIGH_RISK' : largestWeight >= 0.30 ? 'WARNING' : 'NORMAL',
    overall_severity_text: largestWeight >= 0.40 || largestRisk >= 0.45 ? 'Cảnh báo cao' : largestWeight >= 0.30 ? 'Cần chú ý' : 'Bình thường',
    headline: 'Biến động đang tập trung ở các vị thế chính',
  };

  const permRiskSummary = risk.risk_summary?.permanent_loss_risk || risk.permanent_loss_risk || {
    overall_severity: 'MODERATE',
    overall_severity_text: 'Trung bình',
    headline: 'Chưa thấy thesis break rõ ràng ở các vị thế chính',
    high_risk_count: 0,
    elevated_count: 0,
  };

  const warnings = useMemo(() => risk.warnings || [], [risk.warnings]);
  const visibleWarnings = showAllWarnings ? warnings : warnings.slice(0, 4);

  useEffect(() => {
    if (initialSnapshots && initialSnapshots.length > 0) {
      setSnapshots(initialSnapshots);
    }
  }, [initialSnapshots]);

  const symbolRows = useMemo(() => {
    const symbols = Array.from(new Set([...Object.keys(symbolMetrics), ...Object.keys(symbolRiskMap)]));
    return symbols
      .map(symbol => {
        const symUpper = String(symbol).toUpperCase();
        const metric = symbolMetrics[symUpper] || symbolMetrics[symbol] || {};
        const symRisk = symbolRiskMap[symUpper] || symbolRiskMap[symbol] || {};
        return {
          symbol: symUpper,
          metric,
          marketRisk: symRisk.market_risk || {},
          permRisk: symRisk.permanent_loss_risk || {},
        };
      })
      .sort((a, b) => Number(b.metric.weight ?? b.metric.nav_weight ?? b.metric.equity_weight ?? 0) - Number(a.metric.weight ?? a.metric.nav_weight ?? a.metric.equity_weight ?? 0));
  }, [symbolMetrics, symbolRiskMap]);

  const historicalWorstDays = useMemo(() => (snapshots || [])
    .filter(row => row?.official && row.daily_return != null && Number.isFinite(Number(row.daily_return)))
    .sort((a, b) => Number(a.daily_return) - Number(b.daily_return))
    .slice(0, 3), [snapshots]);

  const dataReady = riskCoverageStatus === 'COMPLETE';

  return (
    <div className="page risk-readable-page">
      <AppNav active="risk" locale={locale} />

      <header className="risk-page-hero">
        <div>
          <div className="eyebrow">Phân tách Rủi ro Định lượng & Rủi ro Doanh nghiệp</div>
          <h1>Chẩn đoán Biến động & Rủi ro Mất vốn Vĩnh viễn</h1>
          <p>
            Phân biệt rõ ràng giữa <b>Biến động giá thị trường (NAV fluctuation)</b> và <b>Rủi ro suy giảm tài sản vĩnh viễn (Permanent Capital Loss)</b> theo triết lý đầu tư Buffett & Munger.
          </p>
        </div>
      </header>

      {/* RISK DATA COVERAGE WARNING BANNER */}
      {riskCoverageStatus !== 'COMPLETE' && (
        <div className="risk-coverage-banner" style={{ background: 'color-mix(in srgb, var(--warning, #f59e0b) 12%, transparent)', border: '1px solid var(--warning, #f59e0b)', padding: '16px 20px', borderRadius: '10px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span className="risk-level risk-level-watch" style={{ fontWeight: 800 }}>
              {riskCoverageStatus === 'INSUFFICIENT' ? 'CHƯA ĐỦ DỮ LIỆU TOÀN DANH MỤC' : 'DỮ LIỆU RỦI RO BÁN PHẦN'}
            </span>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text)' }}>
              Chỉ {riskEligibleSymbols.length}/{riskTotalSymbols} vị thế ({pct(riskEligibleNavWeight)} NAV) có đủ lịch sử giá để tính ma trận rủi ro.
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text)', lineHeight: 1.5 }}>
            <b>Có đủ dữ liệu:</b> {riskEligibleSymbols.join(', ') || 'Không có'}. &nbsp;·&nbsp;
            <b>Thiếu dữ liệu:</b> {missing.join(', ') || 'Không có'}. <br />
            Do đó QPort chưa đưa ra kết luận đáng tin cậy về: <i>risk contribution toàn danh mục</i>, <i>correlation trung bình</i>, <i>portfolio volatility</i>. Mức đóng góp biến động chỉ đo lường trên phần danh mục có đủ dữ liệu.
          </p>
        </div>
      )}

      {/* TOP DUAL SUMMARY CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {/* Market Risk Summary */}
        <section className="risk-overview-card" style={{ margin: 0, padding: '20px 24px' }}>
          <div className="risk-overview-summary" style={{ marginBottom: '14px' }}>
            <div>
              <span className="risk-overview-label" style={{ color: 'var(--text-secondary)', textTransform: 'uppercase', fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em' }}>
                1. Biến động & Tập trung Danh mục
              </span>
              <h2 style={{ fontSize: '18px', margin: '4px 0 2px' }}>{marketRiskSummary.headline}</h2>
              <small style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Cho biết NAV có thể dao động như thế nào và mã nào chi phối biến động.</small>
            </div>
            <SeverityPill severity={marketRiskSummary.overall_severity} labelOverride={marketRiskSummary.overall_severity_text} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '12.5px', background: 'var(--surface-soft, rgba(0,0,0,0.03))', padding: '12px', borderRadius: '8px' }}>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Biến động 252D:</span>{' '}
              <b>
                {riskCoverageStatus === 'INSUFFICIENT'
                  ? 'Chưa đủ dữ liệu'
                  : vol252 == null
                  ? '-'
                  : `${pct(vol252)}${riskCoverageStatus === 'PARTIAL' ? ' (phần đo lường)' : '/năm'}`}
              </b>
            </div>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Mã kéo biến động chính:</span>{' '}
              <b>
                {risk.largest_risk_symbol || '-'}{' '}
                {largestRisk == null ? '' : `(${pct(largestRisk)}${riskCoverageStatus !== 'COMPLETE' ? ' đo lường được' : ''})`}
              </b>
            </div>
            <div><span style={{ color: 'var(--text-secondary)' }}>Vị thế hiệu dụng:</span> <b>{effectivePositions == null ? '-' : num(effectivePositions, 1)} mã</b></div>
            <div><span style={{ color: 'var(--text-secondary)' }}>Tương quan trung bình:</span> <b>{avgCorrelation == null ? 'Chưa đủ dữ liệu' : num(avgCorrelation, 2)}</b></div>
          </div>
        </section>

        {/* Permanent Loss Risk Summary */}
        <section className="risk-overview-card" style={{ margin: 0, padding: '20px 24px', borderLeft: '4px solid var(--accent, #0055ff)' }}>
          <div className="risk-overview-summary" style={{ marginBottom: '14px' }}>
            <div>
              <span className="risk-overview-label" style={{ color: 'var(--accent, #0055ff)', textTransform: 'uppercase', fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em' }}>
                2. Rủi ro Mất vốn Vĩnh viễn
              </span>
              <h2 style={{ fontSize: '18px', margin: '4px 0 2px' }}>{permRiskSummary.headline}</h2>
              <small style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Đánh giá rủi ro từ chất lượng doanh nghiệp, bảng cân đối, độ bền lợi nhuận & thesis.</small>
            </div>
            <SeverityPill severity={permRiskSummary.overall_severity} labelOverride={permRiskSummary.overall_severity_text} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '12.5px', background: 'var(--surface-soft, rgba(0,0,0,0.03))', padding: '12px', borderRadius: '8px' }}>
            <div><span style={{ color: 'var(--text-secondary)' }}>Thesis bị đe dọa:</span> <b style={{ color: permRiskSummary.high_risk_count > 0 ? 'var(--danger, #e53935)' : 'var(--text)' }}>{permRiskSummary.high_risk_count} vị thế</b></div>
            <div><span style={{ color: 'var(--text-secondary)' }}>Cần chú ý đệm an toàn:</span> <b>{permRiskSummary.elevated_count} vị thế</b></div>
            <div style={{ gridColumn: 'span 2' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Kết luận Buffett:</span>{' '}
              <b style={{ color: 'var(--text)' }}>
                {permRiskSummary.top_concerns && permRiskSummary.top_concerns.length > 0
                  ? permRiskSummary.top_concerns.join('; ')
                  : 'Chưa thấy vi phạm thesis ở các mã nắm giữ chính.'}
              </b>
            </div>
          </div>
        </section>
      </div>

      {/* SECTION 1: MARKET & PORTFOLIO BEHAVIOR */}
      <section className="risk-section-block" style={{ marginBottom: '36px' }}>
        <div className="risk-section-heading">
          <div>
            <span className="eyebrow" style={{ color: 'var(--text-secondary)' }}>PHẦN 1</span>
            <h2>Biến động & Tập trung Danh mục</h2>
          </div>
          <p>Cho biết NAV có thể dao động như thế nào và mã nào đang chi phối biến động ngắn/trung hạn.</p>
        </div>

        {/* Priority Market Warnings */}
        {warnings.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <div className="risk-section-heading" style={{ marginBottom: '12px' }}>
              <div>
                <span className="eyebrow">Điểm cần hiểu</span>
                <h2>Bốn góc nhìn quan trọng</h2>
              </div>
              <p>Tác động của mã lớn nhất và đóng góp rủi ro thực tế của từng mã.</p>
            </div>
            <div className="risk-insight-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              {visibleWarnings.map(w => (
                <RiskWarningCard key={w.id} warning={w} />
              ))}
            </div>
          </div>
        )}

        {warnings.length > 4 && (
          <div style={{ textAlign: 'center', marginTop: '12px', marginBottom: '20px' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowAllWarnings(!showAllWarnings)}
              style={{ cursor: 'pointer', padding: '8px 18px', fontSize: '13px' }}
            >
              {showAllWarnings ? 'Thu gọn cảnh báo biến động' : `Xem thêm ${warnings.length - 4} cảnh báo biến động khác ↓`}
            </button>
          </div>
        )}

        {/* Per-Symbol Volatility Breakdown */}
        {symbolRows.length > 0 && (
          <div className="risk-symbol-review-card" style={{ marginTop: '20px', marginBottom: '20px' }}>
            <div className="risk-section-heading">
              <div>
                <span className="eyebrow">Nhận xét từng mã</span>
                <h2>Mỗi mã đang ảnh hưởng danh mục như thế nào?</h2>
              </div>
              <p>Tác động của mã lớn nhất và so sánh giữa tỷ trọng vốn và đóng góp biến động thực tế.</p>
            </div>
          </div>
        )}

        {/* Correlation Matrix Table */}
        <div className="risk-correlation-card" style={{ marginTop: '20px' }}>
          <div className="risk-section-heading">
            <div>
              <span className="eyebrow">Đa dạng hóa</span>
              <h2>Ma trận tương quan</h2>
            </div>
            <p style={{ margin: 0, fontSize: '12.5px' }}>Phản ánh mức độ đồng pha biến động giá giữa các cổ phiếu.</p>
          </div>
          <div className="risk-correlation-scroll">
            <table className="risk-correlation-matrix">
              <thead>
                <tr>
                  <th>Mã</th>
                  {symbolRows.map(r => <th key={r.symbol}>{r.symbol}</th>)}
                </tr>
              </thead>
              <tbody>
                {symbolRows.map(rowA => (
                  <tr key={rowA.symbol}>
                    <th>{rowA.symbol}</th>
                    {symbolRows.map(rowB => {
                      const isSame = rowA.symbol === rowB.symbol;
                      const rawVal = isSame ? 1.0 : risk.correlation_matrix?.[rowA.symbol]?.[rowB.symbol];
                      const corrVal = rawVal != null ? Number(rawVal) : null;
                      return (
                        <td
                          key={rowB.symbol}
                          className={
                            isSame
                              ? 'corr-high'
                              : corrVal == null
                              ? 'corr-null'
                              : corrVal > 0.7
                              ? 'corr-very-high'
                              : corrVal > 0.4
                              ? 'corr-mid'
                              : 'corr-low'
                          }
                          style={corrVal == null ? { color: 'var(--text-muted, #94a3b8)' } : undefined}
                        >
                          {corrVal == null ? '-' : corrVal.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Tail Risk Stats */}
        <div className="risk-history-card" style={{ marginTop: '20px' }}>
          <div className="risk-section-heading risk-history-heading">
            <div>
              <span className="eyebrow">Thống kê đuôi rủi ro</span>
              <h2>Những phiên giảm mạnh đã xảy ra</h2>
            </div>
            <span className="risk-level risk-level-neutral">Mô hình thống kê</span>
          </div>

          <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '14px' }}>
            <div className="metric-card">
              <div className="metric-label">VaR ngày 95%</div>
              <div className="metric-value">{pct(risk.daily_var_95)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">CVaR ngày 95%</div>
              <div className="metric-value">{pct(risk.daily_cvar_95)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Biến động sụt giảm</div>
              <div className="metric-value">{pct(risk.downside_volatility)}</div>
            </div>
          </div>

          <div className="risk-impact-box" style={{ background: 'var(--surface-soft, rgba(0,0,0,0.03))', padding: '12px 14px', borderRadius: '8px' }}>
            <strong style={{ fontSize: '12.5px', color: 'var(--text)', display: 'block', marginBottom: '2px' }}>
              Lưu ý quan trọng về VaR / CVaR:
            </strong>
            <p style={{ margin: 0, fontSize: '12px', lineHeight: 1.4, color: 'var(--text-secondary)' }}>
              VaR/CVaR mô tả mẫu dữ liệu lịch sử, <b>không phải hạn mức tổn thất tối đa</b> hay dự báo thiên nga đen. Mức lỗ thực tế trong ngày xấu có thể lớn hơn.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 2: PERMANENT CAPITAL LOSS RISK */}
      <section className="risk-section-block" style={{ marginBottom: '36px' }}>
        <div className="risk-section-heading" style={{ borderLeft: '4px solid var(--accent, #0055ff)', paddingLeft: '14px' }}>
          <div>
            <span className="eyebrow" style={{ color: 'var(--accent, #0055ff)' }}>PHẦN 2</span>
            <h2>Rủi ro Mất vốn Vĩnh viễn (Permanent Capital Loss Risk)</h2>
          </div>
          <p>
            Đánh giá rủi ro thực sự từ <b>Chất lượng doanh nghiệp, Bảng cân đối tài chính, Độ bền lợi nhuận, Lợi thế cạnh tranh (Moat), Định giá & Luận điểm đầu tư (Thesis)</b>.
          </p>
        </div>

        {symbolRows.length === 0 ? (
          <div className="empty-state compact-empty">Chưa có vị thế cổ phiếu active trong danh mục.</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
            {symbolRows.map(({ symbol, metric, marketRisk, permRisk }) => {
              const navWeight = metric.weight ?? metric.nav_weight ?? 0;
              const equityWeight = metric.equity_weight ?? metric.equity_normalized_weight ?? null;
              const rc = metric.risk_contribution != null ? Number(metric.risk_contribution) : 0;
              const severity = permRisk.severity || 'UNKNOWN';
              const severityText = permRisk.severity_text || 'Chưa đủ dữ liệu';
              const stressTest = permRisk.stress_test;

              return (
                <article
                  key={symbol}
                  className="risk-symbol-card"
                  style={{
                    background: 'var(--surface, #fff)',
                    border: '1px solid var(--border, #e2e8f0)',
                    borderRadius: '12px',
                    padding: '20px 24px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
                  }}
                >
                  {/* Symbol Card Top Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px', borderBottom: '1px solid var(--border-soft, #edf2f7)', paddingBottom: '12px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: 'var(--text)' }}>{symbol}</h3>
                        {metric.current_price != null && (
                          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)', background: 'var(--surface-soft, rgba(0,0,0,0.06))', padding: '2px 8px', borderRadius: '4px' }}>
                            {money(metric.current_price, locale)}
                          </span>
                        )}
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          Tỷ trọng: <b>{pct(navWeight)} NAV</b> {equityWeight != null && Math.abs(equityWeight - navWeight) > 0.001 ? `(Cổ phiếu: ${pct(equityWeight)})` : ''} · Đóng góp biến động: <b>{pct(rc)} {riskCoverageStatus !== 'COMPLETE' ? '(đo lường được)' : ''}</b>
                        </span>
                      </div>
                      <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                        {marketRisk.explanation || `${symbol} đang đóng góp ${pct(rc)} vào biến động chung của danh mục.`}
                      </p>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 700, marginBottom: '2px' }}>
                        Rủi ro mất vốn vĩnh viễn
                      </span>
                      <SeverityPill severity={severity} labelOverride={severityText} />
                    </div>
                  </div>

                  {/* 6 Fundamental Dimensions Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.02))', padding: '10px 12px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Chất lượng doanh nghiệp</span>
                      <strong style={{ fontSize: '13.5px', color: 'var(--text)' }}>{permRisk.business_quality_text || 'Tốt'}</strong>
                      {permRisk.business_quality_evidence && (
                        <small style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{permRisk.business_quality_evidence}</small>
                      )}
                    </div>
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.02))', padding: '10px 12px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Bảng cân đối tài chính</span>
                      <strong style={{ fontSize: '13.5px', color: 'var(--text)' }}>{permRisk.balance_sheet_text || 'An toàn'}</strong>
                      {permRisk.balance_sheet_evidence && (
                        <small style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{permRisk.balance_sheet_evidence}</small>
                      )}
                    </div>
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.02))', padding: '10px 12px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Độ bền lợi nhuận</span>
                      <strong style={{ fontSize: '13.5px', color: 'var(--text)' }}>{permRisk.earnings_durability_text || 'Ổn định'}</strong>
                    </div>
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.02))', padding: '10px 12px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Lợi thế cạnh tranh (Moat)</span>
                      <strong style={{ fontSize: '13.5px', color: 'var(--text)' }}>{permRisk.moat_text || 'Chưa đủ dữ liệu'}</strong>
                      {permRisk.moat_evidence && (
                        <small style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{permRisk.moat_evidence}</small>
                      )}
                    </div>
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.02))', padding: '10px 12px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Định giá (Margin of Safety)</span>
                      <strong style={{ fontSize: '13.5px', color: 'var(--text)' }}>{permRisk.valuation_risk_text || 'Biên an toàn tích cực'}</strong>
                      {permRisk.valuation_evidence && (
                        <small style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{permRisk.valuation_evidence}</small>
                      )}
                    </div>
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.02))', padding: '10px 12px', borderRadius: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Trạng thái Thesis</span>
                      <strong style={{ fontSize: '13.5px', color: permRisk.thesis_status === 'BROKEN' ? 'var(--danger, #e53935)' : 'var(--text)' }}>
                        {permRisk.thesis_status_text || 'Chưa thấy dấu hiệu gãy'}
                      </strong>
                      {permRisk.thesis_evidence && (
                        <small style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{permRisk.thesis_evidence}</small>
                      )}
                    </div>
                  </div>

                  {/* Main Concerns / Warnings */}
                  {permRisk.main_concerns && permRisk.main_concerns.length > 0 && (
                    <div style={{ background: 'color-mix(in srgb, var(--accent, #0055ff) 5%, transparent)', padding: '10px 14px', borderRadius: '8px', marginBottom: '12px', borderLeft: '3px solid var(--accent, #0055ff)' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent, #0055ff)', display: 'block', marginBottom: '2px' }}>
                        Điểm cần theo dõi về mặt kinh doanh:
                      </span>
                      <p style={{ margin: 0, fontSize: '12.5px', color: 'var(--text)', lineHeight: 1.4 }}>
                        {permRisk.main_concerns.join('; ')}
                      </p>
                    </div>
                  )}

                  {/* Concentrated Thesis Risk Notice */}
                  {permRisk.concentrated_thesis_risk && (
                    <div style={{ background: 'color-mix(in srgb, var(--warning, #f59e0b) 10%, transparent)', padding: '10px 14px', borderRadius: '8px', marginBottom: '12px', borderLeft: '3px solid var(--warning, #f59e0b)' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--warning-dark, #b45309)', display: 'block', marginBottom: '2px' }}>
                        Cảnh báo tập trung vị thế lớn (Concentrated Thesis Risk)
                      </span>
                      <p style={{ margin: 0, fontSize: '12.5px', color: 'var(--text)', lineHeight: 1.4 }}>
                        {permRisk.concentrated_thesis_risk}
                      </p>
                    </div>
                  )}

                  {/* Position Stress Scenario Box */}
                  {stressTest && (
                    <div style={{ background: 'var(--surface-soft, rgba(0,0,0,0.03))', padding: '12px 14px', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                          Giả lập tác động NAV nếu thesis bị sai ({stressTest.label})
                        </span>
                        <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Chưa tính tương quan mã khác</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                        {stressTest.shocks.map(s => (
                          <div key={s.price_shock_pct} style={{ background: 'var(--surface, #fff)', padding: '6px 10px', borderRadius: '6px', fontSize: '12px', border: '1px solid var(--border-soft, #edf2f7)' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>Giá {symbol} giảm {Math.abs(s.price_shock_pct * 100)}%:</span>{' '}
                            <strong style={{ color: 'var(--danger, #e53935)' }}>NAV {pct(s.nav_impact_pct)}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* ADVANCED TECHNICAL DETAILS */}
      <details className="risk-technical-details">
        <summary>
          <div>
            <span className="eyebrow">Nâng cao</span>
            <b>Chỉ số kỹ thuật & Phương pháp tính</b>
            <small>Dành cho nhà đầu tư muốn kiểm tra sâu cấu trúc ma trận rủi ro định lượng.</small>
          </div>
          <span className="risk-details-toggle">+</span>
        </summary>
        <div className="risk-technical-body">
          <div className="metric-grid risk-technical-metrics">
            <div className="metric-card"><div className="metric-label">Biến động 63 phiên</div><div className="metric-value">{pct(risk.volatility_63)}</div></div>
            <div className="metric-card"><div className="metric-label">Biến động 252 phiên</div><div className="metric-value">{pct(risk.volatility_252)}</div></div>
            <div className="metric-card"><div className="metric-label">Tương quan trung bình / cao nhất</div><div className="metric-value">{num(risk.average_correlation)} / {num(risk.max_correlation)}</div></div>
            <div className="metric-card"><div className="metric-label">Số vị thế hiệu dụng (Effective N)</div><div className="metric-value">{num(effectivePositions)}</div></div>
            <div className="metric-card"><div className="metric-label">Tỷ lệ đa dạng hóa (Diversification Ratio)</div><div className="metric-value">{num(risk.diversification_ratio)}</div></div>
            <div className="metric-card"><div className="metric-label">Chỉ số HHI đóng góp rủi ro</div><div className="metric-value">{num(risk.risk_contribution_hhi)}</div></div>
          </div>
          <p className="muted" style={{ marginTop: '12px' }}>
            <b>Phương pháp tính:</b> Chuỗi lợi suất log 252 phiên với ma trận hiệp phương sở được điều chỉnh co ngót (shrinkage 10%). Đóng góp rủi ro biên (ERC) được giải bằng thuật toán lặp chẩn đoán. Mọi phép tính đều có tính tư vấn diagnostic và không can thiệp vào tài khoản hay tạo lệnh tự động.
          </p>
        </div>
      </details>
    </div>
  );
}
