import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { navigate } from '../lib/navigation.js';
import { formatNumber as num, money, pct, signedMoney } from '../lib/format.js';

function SeverityPill({ severity = 'NORMAL' }) {
  const toneMap = {
    HIGH_RISK: 'high',
    WARNING: 'high',
    ATTENTION: 'watch',
    NORMAL: 'good',
  };
  const labelMap = {
    HIGH_RISK: 'Nguy cơ cao',
    WARNING: 'Cảnh báo',
    ATTENTION: 'Cần chú ý',
    NORMAL: 'Bình thường',
  };
  const tone = toneMap[severity] || 'neutral';
  const label = labelMap[severity] || severity;
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

  const tone = severity === 'HIGH_RISK' || severity === 'WARNING' ? 'high' : severity === 'ATTENTION' ? 'watch' : 'good';

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
              Tác động đến danh mục
            </span>
            <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: 'var(--text)' }}>{impact}</p>
          </div>
        )}

        {review_guidance && (
          <div className="risk-guidance-box" style={{ background: 'color-mix(in srgb, var(--accent, #0055ff) 8%, transparent)', padding: '12px 14px', borderRadius: '8px', borderLeft: '3px solid var(--accent, #0055ff)' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent, #0055ff)', display: 'block', marginBottom: '4px' }}>
              Khuyến nghị xem xét tiếp theo
            </span>
            <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: 'var(--text)' }}>{review_guidance}</p>
          </div>
        )}
      </div>

      <div className="risk-insight-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>Phân tích chẩn đoán · Không tự phát sinh lệnh</span>
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

function correlationMeaning(value) {
  if (value == null || !Number.isFinite(Number(value))) return 'Chưa đủ dữ liệu để so sánh với các mã còn lại.';
  if (Number(value) >= 0.60) return 'Mức liên hệ cao: mã này thường đi cùng hướng với phần còn lại, nên khi thị trường xấu lợi ích đa dạng hóa giảm.';
  if (Number(value) >= 0.35) return 'Mức liên hệ vừa: mã này có lúc đi cùng phần còn lại nhưng vẫn tạo được một phần đa dạng hóa.';
  return 'Mức liên hệ thấp: mã này ít đi cùng phần còn lại hơn, nhờ đó có thể giúp danh mục bớt cùng tăng/cùng giảm một lúc.';
}

function symbolTone(metric) {
  const weight = metric?.equity_weight == null ? null : Number(metric.equity_weight);
  const contribution = metric?.risk_contribution == null ? null : Number(metric.risk_contribution);
  const ratio = metric?.volatility_ratio == null ? null : Number(metric.volatility_ratio);
  if (Number(metric?.return_observations || 0) < 40) return ['Dữ liệu ít', 'building'];
  if ((weight != null && weight >= 0.40) || (contribution != null && contribution >= 0.45) || (ratio != null && ratio > 1.25)) {
    return ['Cần theo dõi', 'high'];
  }
  if ((weight != null && weight >= 0.25) || (contribution != null && contribution >= 0.35)) return ['Đáng chú ý', 'watch'];
  return ['Bình thường', 'good'];
}

function symbolComment(symbol, metric) {
  if (!metric || Number(metric.return_observations || 0) < 20) {
    return `Chưa đủ lịch sử giá để nhận xét đáng tin cậy cho ${symbol}.`;
  }

  const notes = [];
  const weight = metric.equity_weight == null ? null : Number(metric.equity_weight);
  const contribution = metric.risk_contribution == null ? null : Number(metric.risk_contribution);
  const ratio = metric.volatility_ratio == null ? null : Number(metric.volatility_ratio);
  const avgCorr = metric.average_correlation_to_others == null ? null : Number(metric.average_correlation_to_others);

  if (weight != null && weight >= 0.40) {
    notes.push(`${symbol} đang chiếm ${pct(weight)} phần giá trị cổ phiếu, khiến biến động riêng của mã này chi phối kết quả chung.`);
  } else if (weight != null) {
    notes.push(`Tỷ trọng hiện tại của ${symbol} là ${pct(weight)} NAV cổ phiếu.`);
  }

  if (contribution != null && weight != null && weight > 0) {
    if (contribution > weight * 1.15) {
      notes.push(`Đóng góp rủi ro ${pct(contribution)} cao hơn tỷ trọng vốn ${pct(weight)}; mỗi đồng vốn ở ${symbol} đang làm danh mục biến động mạnh hơn mức trung bình.`);
    } else if (contribution < weight * 0.85) {
      notes.push(`Đóng góp rủi ro ${pct(contribution)} thấp hơn tỷ trọng vốn ${pct(weight)}; mã này hiện không khuếch đại biến động danh mục nhiều.`);
    } else {
      notes.push(`Đóng góp rủi ro ${pct(contribution)} khá tương xứng với tỷ trọng vốn ${pct(weight)}.`);
    }
  }

  if (ratio != null) {
    const change = ratio - 1;
    if (ratio > 1.20) notes.push(`Biến động 3 tháng gần đây cao hơn nền 1 năm khoảng ${pct(change)}: rủi ro ngắn hạn đang tăng.`);
    else if (ratio < 0.80) notes.push(`Biến động 3 tháng gần đây thấp hơn nền 1 năm khoảng ${pct(Math.abs(change))}: giá đang dịu hơn so với lịch sử một năm.`);
    else notes.push('Biến động 3 tháng gần đây chưa lệch nhiều so with nền 1 năm.');
  }

  notes.push(correlationMeaning(avgCorr));
  return notes.join(' ');
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

  const summary = risk.risk_summary || {
    overall_severity: largestWeight >= 0.40 || largestRisk >= 0.45 ? 'HIGH_RISK' : largestWeight >= 0.30 ? 'WARNING' : 'NORMAL',
    headline: 'Đánh giá rủi ro danh mục',
    total_warning_count: (risk.warnings || []).length,
    high_risk_count: (risk.warnings || []).filter(w => w.severity === 'HIGH_RISK').length,
    top_concerns: [],
  };

  const warnings = useMemo(() => risk.warnings || [], [risk.warnings]);
  const visibleWarnings = showAllWarnings ? warnings : warnings.slice(0, 4);

  useEffect(() => {
    if (initialSnapshots && initialSnapshots.length > 0) {
      setSnapshots(initialSnapshots);
    }
  }, [initialSnapshots]);

  const symbolRows = useMemo(() => Object.entries(symbolMetrics)
    .map(([symbol, metric]) => ({ symbol: String(symbol).toUpperCase(), metric: metric || {} }))
    .sort((a, b) => Number(b.metric.equity_weight || 0) - Number(a.metric.equity_weight || 0)), [symbolMetrics]);

  const historicalWorstDays = useMemo(() => (snapshots || [])
    .filter(row => row?.official && row.daily_return != null && Number.isFinite(Number(row.daily_return)))
    .sort((a, b) => Number(a.daily_return) - Number(b.daily_return))
    .slice(0, 3), [snapshots]);

  const dataReady = coverage >= 0.90 && observations >= 20;

  return (
    <div className="page risk-readable-page">
      <AppNav active="risk" locale={locale} />

      <header className="risk-page-hero">
        <div>
          <div className="eyebrow">Giải thích rủi ro định lượng</div>
          <h1>Chẩn đoán & Cảnh báo rủi ro danh mục</h1>
          <p>Nhận biết rủi ro nghĩa là gì, vì sao đáng quan tâm, mức độ nghiêm trọng và những điểm nên kiểm tra tiếp theo.</p>
        </div>
      </header>

      {/* 1. PORTFOLIO RISK SUMMARY BANNER */}
      <section className="risk-overview-card" style={{ marginBottom: '24px' }}>
        <div className="risk-overview-summary">
          <div>
            <span className="risk-overview-label">Tổng quan mức độ rủi ro</span>
            <h2>{summary.headline || (summary.overall_severity === 'HIGH_RISK' ? 'Có cảnh báo rủi ro cao' : 'Rủi ro ở mức kiểm soát')}</h2>
            <p>
              {dataReady
                ? `Phân tích dựa trên ${observations} phiên lịch sử, độ phủ dữ liệu ${pct(coverage)}.`
                : `Dữ liệu hiện đạt độ phủ ${pct(coverage)} trên ${observations} phiên. Các mã thiếu dữ liệu sẽ hiển thị cảnh báo chất lượng.`}
            </p>
          </div>
          <SeverityPill severity={summary.overall_severity} />
        </div>

        <div className="risk-overview-metrics">
          <div className="risk-overview-metric">
            <span>Mã tập trọng vốn lớn nhất</span>
            <strong>{largestPositionSymbol || '-'}</strong>
            <small>{pct(largestWeight)} NAV cổ phiếu</small>
          </div>
          <div className="risk-overview-metric">
            <span>Tương quan trung bình</span>
            <strong>{num(avgCorrelation)}</strong>
            <small>{avgCorrelation >= 0.60 ? 'Tương quan cao' : avgCorrelation >= 0.35 ? 'Tương quan vừa' : 'Tương quan thấp'}</small>
          </div>
          <div className="risk-overview-metric">
            <span>Số vị thế hiệu dụng</span>
            <strong>{num(effectivePositions)}</strong>
            <small>trên {symbolRows.length} mã nắm giữ</small>
          </div>
          <div className="risk-overview-metric">
            <span>Nguồn kéo rủi ro chính</span>
            <strong>{risk.largest_risk_symbol || '-'}</strong>
            <small>{pct(largestRisk)} biến động danh mục</small>
          </div>
        </div>

        {missing.length > 0 && (
          <div className="risk-missing-note">
            Thiếu hoặc chưa đủ lịch sử giá: <b>{missing.join(', ')}</b> (UNKNOWN != SAFE - dữ liệu thiếu không được coi là an toàn).
          </div>
        )}
      </section>

      {/* 3. FOUR IMPORTANT INSIGHTS SECTION */}
      <section className="risk-section-block" style={{ marginBottom: '32px' }}>
        <div className="risk-section-heading">
          <div>
            <span className="eyebrow">Điểm cần hiểu</span>
            <h2>Bốn góc nhìn quan trọng</h2>
          </div>
          <p>Tác động thực tế lên danh mục thay vì chỉ hiển thị chỉ số kỹ thuật thuần túy.</p>
        </div>

        {warnings.length > 0 && (
          <div className="risk-insight-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '20px' }}>
            {visibleWarnings.map(w => (
              <RiskWarningCard key={w.id} warning={w} />
            ))}
          </div>
        )}

        {warnings.length > 4 && (
          <div style={{ textAlign: 'center', marginTop: '12px', marginBottom: '20px' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowAllWarnings(!showAllWarnings)}
              style={{ cursor: 'pointer', padding: '8px 18px', fontSize: '13px' }}
            >
              {showAllWarnings ? 'Thu gọn danh sách cảnh báo' : `Xem thêm ${warnings.length - 4} cảnh báo rủi ro khác ↓`}
            </button>
          </div>
        )}
      </section>

      {/* 4. SYMBOL RISK REVIEW & DRIVERS */}
      <section className="risk-symbol-review-card" style={{ marginBottom: '32px' }}>
        <div className="risk-section-heading">
          <div>
            <span className="eyebrow">Nhận xét từng mã</span>
            <h2>Mỗi mã đang ảnh hưởng danh mục như thế nào?</h2>
          </div>
          <p>Tác động của mã lớn nhất và so sánh giữa tỷ trọng tiền đầu tư và mức độ đóng góp rủi ro thực tế của từng mã.</p>
        </div>


        {symbolRows.length === 0 ? (
          <div className="empty-state compact-empty">Chưa đủ lịch sử giá để tạo nhận xét riêng cho từng mã.</div>
        ) : (
          <div className="risk-symbol-grid">
            {symbolRows.map(({ symbol, metric }) => {
              const tone = symbolTone(metric);
              const gap = metric.risk_contribution != null && metric.equity_weight != null
                ? Number(metric.risk_contribution) - Number(metric.equity_weight)
                : null;
              return (
                <article className={`risk-symbol-card risk-tone-${tone[1]}`} key={symbol}>
                  <div className="risk-symbol-head">
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <strong>{symbol}</strong>
                        {metric.current_price != null && (
                          <span style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text)', background: 'var(--surface-soft, rgba(0,0,0,0.06))', padding: '2px 6px', borderRadius: '4px' }}>
                            {money(metric.current_price, locale)}
                          </span>
                        )}
                      </div>
                      <span>{Number(metric.return_observations || 0)} phiên dữ liệu</span>
                    </div>
                    <span className={`risk-level risk-level-${tone[1]}`}>{tone[0]}</span>
                  </div>
                  <div className="risk-symbol-keyline">
                    <div><span>Tỷ trọng vốn</span><strong>{pct(metric.equity_weight)}</strong></div>
                    <div><span>Đóng góp rủi ro</span><strong>{pct(metric.risk_contribution)}</strong></div>
                    <div><span>Chênh lệch</span><strong className={gap != null && gap > 0.05 ? 'neg' : ''}>{gap == null ? '-' : pct(gap)}</strong></div>
                  </div>
                  <div className="risk-symbol-metrics">
                    <div><span>Biến động ~3 tháng</span><b>{pct(metric.volatility_63)}</b></div>
                    <div><span>Nền ~1 năm</span><b>{pct(metric.volatility_252)}</b></div>
                    <div><span>Tương quan trung bình</span><b>{num(metric.average_correlation_to_others)}</b></div>
                    <div><span>Phiên giảm lớn nhất</span><b>{pct(metric.worst_daily_return)}</b></div>
                  </div>
                  <p>{symbolComment(symbol, metric)}</p>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* 4. DIVERSIFICATION & CORRELATION MATRIX */}
      <section className="risk-correlation-card" style={{ marginBottom: '32px' }}>
        <div className="risk-section-heading">
          <div>
            <span className="eyebrow">Đa dạng hóa</span>
            <h2>Ma trận tương quan</h2>
          </div>
          <p>Tương quan phản ánh mức độ cùng tăng/giảm giữa các cặp mã trong điều kiện bình thường.</p>
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
                    const corrVal = isSame ? 1.0 : (risk.correlation_matrix?.[rowA.symbol]?.[rowB.symbol] ?? rowA.metric?.average_correlation_to_others ?? 0.35);
                    return (
                      <td key={rowB.symbol} className={isSame ? 'corr-high' : corrVal > 0.7 ? 'corr-very-high' : corrVal > 0.4 ? 'corr-mid' : 'corr-low'}>
                        {Number(corrVal).toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. TAIL RISK & HISTORICAL DOWNSIDE */}
      <section className="risk-history-card" style={{ marginBottom: '32px' }}>
        <div className="risk-section-heading risk-history-heading">
          <div>
            <span className="eyebrow">Lịch sử thực tế</span>
            <h2>Những phiên giảm mạnh đã xảy ra</h2>
          </div>
          <span className="risk-level risk-level-neutral">Mô hình thống kê</span>
        </div>

        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '16px' }}>
          <div className="metric-card">
            <div className="metric-label">VaR ngày 95%</div>
            <div className="metric-value">{pct(risk.daily_var_95)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">CVaR ngày 95%</div>
            <div className="metric-value">{pct(risk.daily_cvar_95)}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Biến động sụt giảm (Downside Volatility)</div>
            <div className="metric-value">{pct(risk.downside_volatility)}</div>
          </div>
        </div>

        <div className="risk-impact-box" style={{ background: 'var(--surface-soft, rgba(0,0,0,0.03))', padding: '14px 16px', borderRadius: '8px', marginBottom: '16px' }}>
          <strong style={{ fontSize: '13px', color: 'var(--text)', display: 'block', marginBottom: '4px' }}>
            Lưu ý quan trọng về VaR / CVaR:
          </strong>
          <p style={{ margin: 0, fontSize: '12.5px', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
            VaR/CVaR là thống kê định lượng dựa trên phân phối dữ liệu lịch sử, <b>không phải mức lỗ tối đa có thể xảy ra</b>. Khi xuất hiện các biến cố thiên nga đen hoặc khủng hoảng thị trường bất ngờ, tổn thất thực tế trong ngày có thể vượt xa con số ước tính này.
          </p>
        </div>

        {historicalWorstDays.length > 0 && (
          <>
            <div style={{ marginTop: '16px', marginBottom: '10px', fontSize: '13px', fontWeight: 700, color: 'var(--text)' }}>
              Các phiên sụt giảm mạnh thực tế đã ghi nhận trong nhật ký:
            </div>
            <div className="risk-worst-days">
              {historicalWorstDays.map((day, index) => (
                <div className="risk-worst-day-row" key={day.snapshot_date}>
                  <span className="risk-worst-rank">{index + 1}</span>
                  <div><span>Ngày</span><b>{day.snapshot_date}</b></div>
                  <div><span>Mức giảm</span><strong className={Number(day.daily_return) < 0 ? 'neg' : ''}>{pct(day.daily_return)}</strong></div>
                  <div><span>Lãi/lỗ</span><strong data-sensitive="pnl">{signedMoney(day.daily_pnl, locale)}</strong></div>
                  <div><span>NAV cuối ngày</span><strong data-sensitive="money">{money(day.nav, locale)}</strong></div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* 6. ADVANCED TECHNICAL DETAILS */}
      <details className="risk-technical-details">
        <summary>
          <div>
            <span className="eyebrow">Nâng cao</span>
            <b>Chỉ số kỹ thuật & Phương pháp tính</b>
            <small>Dành cho nhà đầu tư muốn kiểm tra sâu cấu trúc ma trận rủi ro.</small>
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
