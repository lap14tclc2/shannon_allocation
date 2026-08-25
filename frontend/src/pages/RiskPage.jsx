import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { listPortfolioSnapshots } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

function num(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : Number(value).toFixed(digits);
}

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

function signedMoney(value, locale = 'vi') {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  return `${Number(value) >= 0 ? '+' : ''}${money(value, locale)}`;
}

function StatusPill({ children, tone = 'neutral' }) {
  return <span className={`risk-level risk-level-${tone}`}>{children}</span>;
}

function InsightCard({ index, question, state, tone = 'neutral', title, highlight, highlightNote, children, footer }) {
  return <article className={`risk-insight-card risk-tone-${tone}`}>
    <div className="risk-insight-top">
      <span className="risk-insight-index">{String(index).padStart(2, '0')}</span>
      <span className="risk-insight-question">{question}</span>
      <StatusPill tone={tone}>{state}</StatusPill>
    </div>
    <div className="risk-insight-content">
      <h3>{title}</h3>
      {highlight != null && <div className="risk-insight-highlight">
        <strong>{highlight}</strong>
        {highlightNote && <span>{highlightNote}</span>}
      </div>}
      <div className="risk-insight-copy">{children}</div>
    </div>
    {footer && <div className="risk-insight-footer">{footer}</div>}
  </article>;
}

function BlockMeter({ value, max = 1, threshold = null, label }) {
  const normalized = value == null || !Number.isFinite(Number(value)) ? 0 : Math.max(0, Math.min(1, Number(value) / max));
  const active = Math.round(normalized * 12);
  return <div className="risk-block-meter" aria-label={label}>
    <div className="risk-block-meter-track">{Array.from({ length: 12 }, (_, index) => <i className={index < active ? 'active' : ''} key={index} />)}</div>
    <div><span>{label}</span>{threshold != null && <small>Ngưỡng theo dõi {threshold}</small>}</div>
  </div>;
}

function correlationCellTone(value) {
  if (value == null || !Number.isFinite(Number(value))) return 'missing';
  const number = Number(value);
  if (number >= 0.70) return 'very-high';
  if (number >= 0.45) return 'high';
  if (number >= 0.20) return 'mid';
  if (number >= 0) return 'low';
  return 'negative';
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
  if ((weight != null && weight >= 0.45) || (contribution != null && contribution >= 0.45) || (ratio != null && ratio > 1.20)) {
    return ['Cần theo dõi', 'high'];
  }
  if ((weight != null && weight >= 0.35) || (contribution != null && contribution >= 0.35)) return ['Đáng chú ý', 'watch'];
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
    notes.push(`${symbol} đang chiếm ${pct(weight)} phần giá trị cổ phiếu, nên biến động riêng của mã này có ảnh hưởng lớn đến kết quả chung.`);
  } else if (weight != null) {
    notes.push(`Tỷ trọng hiện tại của ${symbol} là ${pct(weight)} phần giá trị cổ phiếu.`);
  }

  if (contribution != null && weight != null && weight > 0) {
    if (contribution > weight * 1.20) {
      notes.push(`Đóng góp rủi ro ${pct(contribution)} cao hơn tỷ trọng vốn ${pct(weight)}; mỗi đồng vốn ở ${symbol} đang làm danh mục biến động mạnh hơn mức trung bình.`);
    } else if (contribution < weight * 0.80) {
      notes.push(`Đóng góp rủi ro ${pct(contribution)} thấp hơn tỷ trọng vốn ${pct(weight)}; mã này hiện không khuếch đại biến động danh mục nhiều như tỷ trọng của nó.`);
    } else {
      notes.push(`Đóng góp rủi ro ${pct(contribution)} khá tương xứng với tỷ trọng vốn ${pct(weight)}.`);
    }
  }

  if (ratio != null) {
    const change = ratio - 1;
    if (ratio > 1.20) notes.push(`Biến động 3 tháng gần đây cao hơn nền 1 năm khoảng ${pct(change)}: rủi ro ngắn hạn đang tăng.`);
    else if (ratio < 0.80) notes.push(`Biến động 3 tháng gần đây thấp hơn nền 1 năm khoảng ${pct(Math.abs(change))}: giá đang dịu hơn so với lịch sử một năm.`);
    else notes.push('Biến động 3 tháng gần đây chưa lệch nhiều so với nền 1 năm.');
  }

  notes.push(correlationMeaning(avgCorr));
  return notes.join(' ');
}

export default function RiskPage({ risk = {}, snapshots: initialSnapshots = [], locale = 'vi' }) {
  const [snapshots, setSnapshots] = useState(initialSnapshots);
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
  const volatilityRatio = vol63 != null && vol252 ? vol63 / vol252 : null;
  const volatilityChange = volatilityRatio == null ? null : volatilityRatio - 1;
  const symbolMetrics = risk.symbol_metrics || {};
  const correlationSymbols = risk.correlation_symbols || [];
  const correlationMatrix = risk.correlation_matrix || {};

  useEffect(() => {
    if (initialSnapshots.length) return undefined;
    let active = true;
    listPortfolioSnapshots()
      .then(rows => { if (active) setSnapshots(rows || []); })
      .catch(() => { if (active) setSnapshots([]); });
    return () => { active = false; };
  }, [initialSnapshots]);

  const historicalWorstDays = useMemo(() => (snapshots || [])
    .filter(row => row?.official && row.daily_return != null && Number.isFinite(Number(row.daily_return)))
    .sort((a, b) => Number(a.daily_return) - Number(b.daily_return))
    .slice(0, 3), [snapshots]);

  const symbolRows = useMemo(() => Object.entries(symbolMetrics)
    .map(([symbol, metric]) => ({ symbol: String(symbol).toUpperCase(), metric: metric || {} }))
    .sort((a, b) => Number(b.metric.equity_weight || 0) - Number(a.metric.equity_weight || 0)), [symbolMetrics]);

  const dataReady = coverage >= 0.90 && observations >= 20;
  const concentrationState = largestWeight == null ? ['Đang tính', 'building'] : largestWeight >= 0.45 ? ['Cao', 'high'] : largestWeight >= 0.35 ? ['Đáng chú ý', 'watch'] : ['Ổn', 'good'];
  const correlationState = avgCorrelation == null ? ['Đang tính', 'building'] : avgCorrelation >= 0.60 ? ['Cao', 'high'] : avgCorrelation >= 0.35 ? ['Trung bình', 'watch'] : ['Thấp', 'good'];
  const volatilityState = volatilityRatio == null ? ['Đang tính', 'building'] : volatilityRatio > 1.20 ? ['Đang tăng', 'high'] : volatilityRatio < 0.80 ? ['Đang giảm', 'good'] : ['Gần nền 1 năm', 'neutral'];
  const riskDriverState = largestRisk == null ? ['Đang tính', 'building'] : largestRisk > 0.45 ? ['Tập trung', 'high'] : ['Chưa tập trung cao', 'good'];
  const overallWatch = [concentrationState[1], correlationState[1], volatilityState[1], riskDriverState[1]].includes('high');

  const concentrationImpact = largestWeight == null ? null : largestWeight * 0.10;
  const riskWeightGap = driverMetricGap(risk.largest_risk_symbol, symbolMetrics, largestRisk);
  const worstDay = historicalWorstDays[0] || null;

  return <div className="page risk-readable-page">
    <AppNav active="risk" locale={locale} />

    <header className="risk-page-hero">
      <div>
        <div className="eyebrow">Phân tích danh mục</div>
        <h1>Rủi ro hiện tại của danh mục</h1>
        <p>Nhìn nhanh mã nào đang chi phối kết quả, các cổ phiếu có thường giảm cùng nhau không và mức rung lắc gần đây đang thay đổi thế nào.</p>
      </div>
    </header>

    <section className="risk-overview-card">
      <div className="risk-overview-summary">
        <div>
          <span className="risk-overview-label">Đánh giá tổng quan</span>
          <h2>{!dataReady ? 'Dữ liệu đang hoàn thiện' : overallWatch ? 'Có điểm cần theo dõi' : 'Chưa có cảnh báo lớn'}</h2>
          <p>{dataReady
            ? `Phân tích dựa trên ${observations} phiên lợi suất, độ phủ ${pct(coverage)}.`
            : `Hiện có ${observations} phiên lợi suất, độ phủ ${pct(coverage)}. Chỉ số thiếu dữ liệu sẽ để trống.`}</p>
        </div>
        <StatusPill tone={!dataReady ? 'building' : overallWatch ? 'watch' : 'good'}>
          {!dataReady ? 'Đang hoàn thiện' : overallWatch ? 'Cần theo dõi' : 'Ổn định'}
        </StatusPill>
      </div>

      <div className="risk-overview-metrics">
        <div className="risk-overview-metric">
          <span>Mã lớn nhất</span>
          <strong>{largestPositionSymbol || '-'}</strong>
          <small>{pct(largestWeight)} phần cổ phiếu</small>
        </div>
        <div className="risk-overview-metric">
          <span>Tương quan trung bình</span>
          <strong>{num(avgCorrelation)}</strong>
          <small>{correlationState[0]}</small>
        </div>
        <div className="risk-overview-metric">
          <span>Biến động ~3 tháng</span>
          <strong>{pct(vol63)}</strong>
          <small>nền 1 năm {pct(vol252)}</small>
        </div>
        <div className="risk-overview-metric">
          <span>Kéo rủi ro nhiều nhất</span>
          <strong>{risk.largest_risk_symbol || '-'}</strong>
          <small>{pct(largestRisk)} rủi ro ước tính</small>
        </div>
      </div>

      {missing.length > 0 && <div className="risk-missing-note">Thiếu hoặc chưa đủ lịch sử: <b>{missing.join(', ')}</b></div>}
    </section>

    <section className="risk-section-block">
      <div className="risk-section-heading">
        <div><span className="eyebrow">Điểm cần hiểu</span><h2>Bốn góc nhìn quan trọng</h2></div>
        <p>Ưu tiên tác động thực tế lên danh mục thay vì chỉ hiển thị chỉ số kỹ thuật.</p>
      </div>

      <div className="risk-insight-grid">
        <InsightCard
          index={1}
          question="Một mã có đang quá lớn không?"
          state={concentrationState[0]}
          tone={concentrationState[1]}
          title="Tác động của mã lớn nhất"
          highlight={largestPositionSymbol ? `${largestPositionSymbol} · ${pct(largestWeight)}` : '-'}
          highlightNote={concentrationImpact == null ? null : `Nếu mã này giảm 10% → phần cổ phiếu của danh mục có thể giảm khoảng ${pct(concentrationImpact)}`}
          footer="Mức tập trung đo tác động của một mã đơn lẻ; không có nghĩa danh mục phải chia đều tỷ trọng."
        >
          <BlockMeter value={largestWeight} max={0.60} threshold="35%" label="Mức tập trung vốn" />
          {largestWeight == null
            ? 'Chưa đủ dữ liệu để đánh giá mức tập trung.'
            : <>Tỷ trọng hiện tại khiến <b>{largestPositionSymbol || 'mã lớn nhất'}</b> có khả năng ảnh hưởng rõ đến kết quả chung. Ví dụ 10% ở trên chỉ để hình dung độ nhạy, không phải dự báo giá.</>}
        </InsightCard>

        <InsightCard
          index={2}
          question="Các mã có thường tăng/giảm cùng nhau?"
          state={correlationState[0]}
          tone={correlationState[1]}
          title="Khả năng đa dạng hóa"
          highlight={num(avgCorrelation)}
          highlightNote="Tương quan trung bình giữa các mã"
          footer="Gần 1: thường cùng hướng · Gần 0: ít quan hệ ổn định · Âm: thường có xu hướng ngược hướng."
        >
          <BlockMeter value={avgCorrelation == null ? null : Math.max(0, avgCorrelation)} max={0.80} threshold="0,60" label="Mức đồng pha" />
          {avgCorrelation == null
            ? 'Chưa đủ lịch sử giao nhau giữa các mã để đánh giá.'
            : avgCorrelation >= 0.60
              ? <>Mức tương quan khá cao. Khi thị trường xấu, nhiều mã có thể giảm cùng lúc nên việc nắm nhiều mã chưa chắc giúp giảm rủi ro nhiều.</>
              : avgCorrelation >= 0.35
                ? <>Mức tương quan vừa. Các mã có liên hệ nhất định nhưng vẫn còn khả năng bù trừ khi một mã biến động khác hướng.</>
                : <>Mức tương quan tương đối thấp. Đây thường là điểm có lợi: khi một mã giảm, các mã khác ít có xu hướng giảm cùng mức và cùng thời điểm hơn.</>}
        </InsightCard>

        <InsightCard
          index={3}
          question="Gần đây danh mục rung lắc hơn hay ít hơn?"
          state={volatilityState[0]}
          tone={volatilityState[1]}
          title="3 tháng gần đây so với nền 1 năm"
          footer="Hai số là độ biến động quy đổi theo năm, không phải mức lợi nhuận."
        >
          {volatilityRatio == null ? 'Chưa đủ dữ liệu để so sánh biến động gần đây với nền một năm.' : <>
            <BlockMeter value={volatilityRatio} max={2} threshold="1,20×" label="63 phiên / 252 phiên" />
            <div className="risk-volatility-compare">
              <div><span>~3 tháng</span><strong>{pct(vol63)}</strong><small>63 phiên</small></div>
              <span className="risk-compare-arrow">→</span>
              <div><span>Nền ~1 năm</span><strong>{pct(vol252)}</strong><small>252 phiên</small></div>
              <div className={`risk-volatility-delta ${volatilityRatio > 1.20 ? 'neg' : volatilityRatio < 0.80 ? 'pos' : ''}`}>
                <span>Chênh lệch</span><strong>{pct(volatilityChange)}</strong>
              </div>
            </div>
            <p className="risk-insight-explain">
              {volatilityRatio > 1.20 && 'Rủi ro ngắn hạn đang tăng: danh mục rung lắc mạnh hơn đáng kể so với nền một năm.'}
              {volatilityRatio < 0.80 && 'Biến động gần đây đang dịu hơn đáng kể so với nền một năm.'}
              {volatilityRatio >= 0.80 && volatilityRatio <= 1.20 && 'Mức rung lắc gần đây chưa khác đáng kể so với nền một năm.'}
            </p>
          </>}
        </InsightCard>

        <InsightCard
          index={4}
          question="Mã nào đang kéo rủi ro nhiều nhất?"
          state={riskDriverState[0]}
          tone={riskDriverState[1]}
          title="Ảnh hưởng rủi ro theo mã"
          highlight={risk.largest_risk_symbol ? `${risk.largest_risk_symbol} · ${pct(largestRisk)}` : '-'}
          highlightNote={riskWeightGap == null ? null : `Cao hơn tỷ trọng vốn khoảng ${pct(riskWeightGap, 2)} điểm % theo thang tỷ lệ`}
          footer="Đóng góp rủi ro đo mức ảnh hưởng đến biến động chung; không phải lãi/lỗ và không phải khuyến nghị bán."
        >
          <BlockMeter value={largestRisk} max={0.60} threshold="45%" label="Mức tập trung rủi ro" />
          {largestRisk == null
            ? 'Chưa đủ dữ liệu để xác định mã ảnh hưởng rủi ro nhiều nhất.'
            : <>{risk.largest_risk_symbol} đang tạo ra phần biến động lớn nhất trong danh mục. {riskWeightGap != null && riskWeightGap > 0.05 ? 'Rủi ro của mã này cao hơn tỷ trọng vốn một khoảng đáng chú ý, nên đây là mã nên theo dõi kỹ hơn.' : 'Đóng góp rủi ro hiện không lệch quá xa tỷ trọng vốn.'}</>}
        </InsightCard>
      </div>
    </section>

    {correlationSymbols.length > 1 && <section className="risk-correlation-card">
      <div className="risk-section-heading">
        <div><span className="eyebrow">Đồng pha theo cặp</span><h2>Ma trận tương quan</h2></div>
        <p>Màu đậm hơn nghĩa là hai mã thường biến động cùng hướng hơn. Ô trống là chưa đủ 40 phiên giao nhau.</p>
      </div>
      <div className="risk-correlation-scroll">
        <table className="risk-correlation-matrix">
          <thead><tr><th aria-label="Mã cổ phiếu" />{correlationSymbols.map(symbol => <th key={symbol}>{symbol}</th>)}</tr></thead>
          <tbody>{correlationSymbols.map(rowSymbol => <tr key={rowSymbol}>
            <th>{rowSymbol}</th>
            {correlationSymbols.map(columnSymbol => {
              const value = correlationMatrix?.[rowSymbol]?.[columnSymbol];
              return <td className={`corr-${correlationCellTone(value)}`} key={columnSymbol} title={`${rowSymbol} / ${columnSymbol}: ${num(value)}`}>{num(value)}</td>;
            })}
          </tr>)}</tbody>
        </table>
      </div>
      <div className="correlation-legend"><span className="corr-negative">Âm</span><span className="corr-low">Thấp</span><span className="corr-mid">Vừa</span><span className="corr-high">Cao</span><span className="corr-very-high">Rất cao</span></div>
    </section>}

    <section className="risk-history-card">
      <div className="risk-section-heading risk-history-heading">
        <div><span className="eyebrow">Lịch sử thực tế</span><h2>Những phiên giảm mạnh đã xảy ra</h2></div>
        <StatusPill tone={worstDay ? 'neutral' : 'building'}>{worstDay ? 'Có dữ liệu' : 'Chưa đủ snapshot'}</StatusPill>
      </div>

      {worstDay ? <>
        <div className="risk-worst-hero">
          <div>
            <span>Phiên xấu nhất đã ghi nhận</span>
            <strong>{worstDay.snapshot_date}</strong>
          </div>
          <div><span>Mức giảm</span><strong className="neg">{pct(worstDay.daily_return)}</strong></div>
          <div><span>Lãi/lỗ trong ngày</span><strong className="neg">{signedMoney(worstDay.daily_pnl, locale)}</strong></div>
          <div><span>NAV cuối ngày</span><strong>{money(worstDay.nav, locale)}</strong></div>
        </div>
        <div className="risk-worst-days">
          {historicalWorstDays.map((day, index) => <div className="risk-worst-day-row" key={day.snapshot_date}>
            <span className="risk-worst-rank">{index + 1}</span>
            <div><span>Ngày</span><b>{day.snapshot_date}</b></div>
            <div><span>Mức giảm</span><strong className={Number(day.daily_return) < 0 ? 'neg' : ''}>{pct(day.daily_return)}</strong></div>
            <div><span>Lãi/lỗ</span><strong>{signedMoney(day.daily_pnl, locale)}</strong></div>
            <div><span>NAV cuối ngày</span><strong>{money(day.nav, locale)}</strong></div>
          </div>)}
        </div>
      </> : <div className="risk-history-empty">
        <div className="risk-history-empty-mark">—</div>
        <div>
          <h3>Chưa có đủ lịch sử để gắn mức giảm với ngày cụ thể</h3>
          <p>QPort cần các snapshot chính thức có lợi suất ngày. Khi dữ liệu hình thành, phần này sẽ hiển thị ngày, mức giảm, số tiền lỗ và NAV cuối ngày thay vì chỉ đưa ra một tỷ lệ ước tính.</p>
        </div>
      </div>}
      <p className="risk-history-footnote">VaR/CVaR được giữ riêng trong phần Nâng cao vì đó là thống kê mô hình, không phải một phiên giao dịch thực tế.</p>
    </section>

    <section className="risk-symbol-review-card">
      <div className="risk-section-heading">
        <div><span className="eyebrow">Nhận xét từng mã</span><h2>Mỗi mã đang ảnh hưởng danh mục như thế nào?</h2></div>
        <p>So sánh tỷ trọng vốn, đóng góp rủi ro, xu hướng biến động và mức liên hệ với các mã còn lại.</p>
      </div>
      {symbolRows.length === 0 ? <div className="empty-state compact-empty">Chưa đủ lịch sử giá để tạo nhận xét riêng cho từng mã.</div> : <div className="risk-symbol-grid">
        {symbolRows.map(({ symbol, metric }) => {
          const tone = symbolTone(metric);
          const gap = metric.risk_contribution != null && metric.equity_weight != null
            ? Number(metric.risk_contribution) - Number(metric.equity_weight)
            : null;
          return <article className={`risk-symbol-card risk-tone-${tone[1]}`} key={symbol}>
            <div className="risk-symbol-head">
              <div><strong>{symbol}</strong><span>{Number(metric.return_observations || 0)} phiên dữ liệu</span></div>
              <StatusPill tone={tone[1]}>{tone[0]}</StatusPill>
            </div>
            <div className="risk-symbol-keyline">
              <div><span>Tỷ trọng vốn</span><strong>{pct(metric.equity_weight)}</strong></div>
              <div><span>Đóng góp rủi ro</span><strong>{pct(metric.risk_contribution)}</strong></div>
              <div><span>Chênh lệch</span><strong className={gap != null && gap > 0.05 ? 'neg' : ''}>{gap == null ? '-' : pct(gap)}</strong></div>
            </div>
            <div className="risk-symbol-metrics">
              <div><span>Biến động ~3 tháng</span><b>{pct(metric.volatility_63)}</b></div>
              <div><span>Nền ~1 năm</span><b>{pct(metric.volatility_252)}</b></div>
              <div><span>Tương quan với mã khác</span><b>{num(metric.average_correlation_to_others)}</b></div>
              <div><span>Phiên giảm mạnh nhất</span><b>{pct(metric.worst_daily_return)}</b></div>
            </div>
            <p>{symbolComment(symbol, metric)}</p>
          </article>;
        })}
      </div>}
    </section>

    <details className="risk-technical-details">
      <summary><div><span className="eyebrow">Nâng cao</span><b>Chỉ số kỹ thuật và phương pháp tính</b><small>Dành cho người muốn kiểm tra sâu mô hình rủi ro.</small></div><span className="risk-details-toggle">+</span></summary>
      <div className="risk-technical-body">
        <div className="metric-grid risk-technical-metrics">
          <div className="metric-card"><div className="metric-label">Biến động 63 phiên</div><div className="metric-value">{pct(risk.volatility_63)}</div></div>
          <div className="metric-card"><div className="metric-label">Biến động 252 phiên</div><div className="metric-value">{pct(risk.volatility_252)}</div></div>
          <div className="metric-card"><div className="metric-label">Tương quan trung bình / cao nhất</div><div className="metric-value">{num(risk.average_correlation)} / {num(risk.max_correlation)}</div></div>
          <div className="metric-card"><div className="metric-label">Số vị thế hiệu dụng</div><div className="metric-value">{num(effectivePositions)}</div></div>
          <div className="metric-card"><div className="metric-label">Tỷ lệ đa dạng hóa</div><div className="metric-value">{num(risk.diversification_ratio)}</div></div>
          <div className="metric-card"><div className="metric-label">VaR ngày 95%</div><div className="metric-value">{pct(risk.daily_var_95)}</div></div>
          <div className="metric-card"><div className="metric-label">CVaR ngày 95%</div><div className="metric-value">{pct(risk.daily_cvar_95)}</div></div>
          <div className="metric-card"><div className="metric-label">Phiên xấu nhất của mô hình</div><div className="metric-value">{pct(risk.max_daily_loss)}</div><div className="metric-note">{risk.max_daily_loss_date || '-'}</div></div>
        </div>
        <p className="muted"><b>63 phiên</b> tương đương khoảng 3 tháng giao dịch; <b>252 phiên</b> tương đương khoảng 1 năm. Volatility là độ rung lắc quy đổi theo năm, không phải lợi nhuận. VaR/CVaR chỉ mô tả phân phối lịch sử và không phải giới hạn lỗ được đảm bảo.</p>
        <p className="muted"><b>Giá và corporate action:</b> NAV luôn dùng giá đóng cửa raw. Chuỗi lợi suất chỉ cộng cổ tức tiền hoặc hệ số cổ tức cổ phiếu vào ngày GDKHQ sau khi sự kiện đã được xác minh; dữ liệu chưa xác minh không tự động sửa lịch sử.</p>
      </div>
    </details>
  </div>;
}

function driverMetricGap(symbol, symbolMetrics, largestRisk) {
  if (!symbol || largestRisk == null) return null;
  const metric = symbolMetrics?.[symbol];
  if (!metric || metric.equity_weight == null) return null;
  return Number(largestRisk) - Number(metric.equity_weight);
}
