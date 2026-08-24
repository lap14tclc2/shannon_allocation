import React, { useMemo } from 'react';
import AppNav from '../components/AppNav.jsx';
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

function InsightCard({ question, state, tone = 'neutral', title, children, footer, className = '' }) {
  return <section className={`risk-plain-card ${className}`.trim()}>
    <div className="risk-plain-head"><span className="risk-question">{question}</span><span className={`risk-level risk-level-${tone}`}>{state}</span></div>
    <h3>{title}</h3>
    <div className="risk-plain-copy">{children}</div>
    {footer && <div className="risk-plain-footer">{footer}</div>}
  </section>;
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
  if (Number(metric?.return_observations || 0) < 40) return ['DỮ LIỆU ÍT', 'building'];
  if ((weight != null && weight >= 0.45) || (contribution != null && contribution >= 0.45) || (ratio != null && ratio > 1.20)) {
    return ['CẦN THEO DÕI', 'high'];
  }
  if ((weight != null && weight >= 0.35) || (contribution != null && contribution >= 0.35)) return ['ĐÁNG CHÚ Ý', 'watch'];
  return ['BÌNH THƯỜNG', 'good'];
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
    notes.push(`${symbol} đang chiếm ${pct(weight)} phần giá trị cổ phiếu, nên chỉ riêng biến động của mã này đã có ảnh hưởng lớn đến kết quả chung.`);
  } else if (weight != null) {
    notes.push(`Tỷ trọng hiện tại của ${symbol} là ${pct(weight)} phần giá trị cổ phiếu.`);
  }

  if (contribution != null && weight != null && weight > 0) {
    if (contribution > weight * 1.20) {
      notes.push(`Mã này đóng góp khoảng ${pct(contribution)} rủi ro, cao hơn tỷ trọng vốn ${pct(weight)}; tức là mỗi đồng vốn ở ${symbol} đang làm danh mục biến động mạnh hơn mức trung bình.`);
    } else if (contribution < weight * 0.80) {
      notes.push(`Đóng góp rủi ro khoảng ${pct(contribution)}, thấp hơn tỷ trọng vốn ${pct(weight)}; hiện mã này không khuếch đại biến động danh mục nhiều như tỷ trọng của nó.`);
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

export default function RiskPage({ risk = {}, snapshots = [], locale = 'vi' }) {
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

  const historicalWorstDays = useMemo(() => (snapshots || [])
    .filter(row => row?.official && row.daily_return != null && Number.isFinite(Number(row.daily_return)))
    .sort((a, b) => Number(a.daily_return) - Number(b.daily_return))
    .slice(0, 3), [snapshots]);

  const symbolRows = useMemo(() => Object.entries(symbolMetrics)
    .map(([symbol, metric]) => ({ symbol: String(symbol).toUpperCase(), metric: metric || {} }))
    .sort((a, b) => Number(b.metric.equity_weight || 0) - Number(a.metric.equity_weight || 0)), [symbolMetrics]);

  const dataReady = coverage >= 0.90 && observations >= 20;
  const concentrationState = largestWeight == null ? ['ĐANG TÍNH', 'building'] : largestWeight >= 0.45 ? ['CAO', 'high'] : largestWeight >= 0.35 ? ['ĐÁNG CHÚ Ý', 'watch'] : ['ỔN', 'good'];
  const correlationState = avgCorrelation == null ? ['ĐANG TÍNH', 'building'] : avgCorrelation >= 0.60 ? ['CAO', 'high'] : avgCorrelation >= 0.35 ? ['TRUNG BÌNH', 'watch'] : ['THẤP', 'good'];
  const volatilityState = volatilityRatio == null ? ['ĐANG TÍNH', 'building'] : volatilityRatio > 1.20 ? ['ĐANG TĂNG', 'high'] : volatilityRatio < 0.80 ? ['ĐANG GIẢM', 'good'] : ['GẦN NỀN 1 NĂM', 'neutral'];
  const riskDriverState = largestRisk == null ? ['ĐANG TÍNH', 'building'] : largestRisk > 0.45 ? ['TẬP TRUNG', 'high'] : ['CHƯA TẬP TRUNG CAO', 'good'];
  const overallWatch = [concentrationState[1], correlationState[1], volatilityState[1], riskDriverState[1]].includes('high');

  const concentrationImpact = largestWeight == null ? null : largestWeight * 0.10;
  const concentrationCopy = largestWeight == null
    ? 'Chưa đủ dữ liệu để đánh giá mức tập trung.'
    : <>
      <b>{largestPositionSymbol || 'Mã lớn nhất'}</b> đang chiếm <b>{pct(largestWeight)}</b> phần giá trị cổ phiếu.
      Nếu riêng mã này giảm 10% trong khi các mã khác đứng yên, phần cổ phiếu của danh mục có thể bị kéo giảm khoảng <b>{pct(concentrationImpact)}</b>.
      Mức tập trung cho biết một mã đơn lẻ có thể tác động mạnh đến tổng tài sản đến đâu — không phải để ép các mã phải có tỷ trọng bằng nhau.
    </>;

  const correlationCopy = avgCorrelation == null
    ? 'QPort cần thêm lịch sử giá giao nhau giữa các mã trước khi đánh giá.'
    : avgCorrelation >= 0.60
      ? <>Tương quan trung bình là <b>{num(avgCorrelation)}</b>, khá cao. Điều này có nghĩa các mã thường đi cùng hướng; khi thị trường xấu, nhiều mã có thể giảm cùng lúc nên việc nắm nhiều mã chưa chắc giúp giảm rủi ro nhiều.</>
      : avgCorrelation >= 0.35
        ? <>Tương quan trung bình là <b>{num(avgCorrelation)}</b>, ở mức vừa. Các mã có liên hệ nhất định nhưng vẫn còn khả năng bù trừ cho nhau khi một mã biến động khác hướng.</>
        : <>Tương quan trung bình là <b>{num(avgCorrelation)}</b>, tương đối thấp. Đây thường là điểm có lợi cho đa dạng hóa: khi một mã giảm, các mã khác ít có xu hướng giảm cùng mức và cùng thời điểm hơn.</>;

  const volatilityCopy = volatilityRatio == null
    ? 'Chưa đủ dữ liệu để so sánh biến động gần đây với nền một năm.'
    : <>
      <b>63 phiên (~3 tháng)</b>: {pct(vol63)}. <b>252 phiên (~1 năm)</b>: {pct(vol252)}.
      {' '}Hai số đều là mức biến động quy đổi theo năm, <b>không phải lợi nhuận</b>.
      {volatilityRatio > 1.20 && <> Gần đây biến động cao hơn nền một năm khoảng <b>{pct(volatilityChange)}</b>, nghĩa là danh mục đang rung lắc mạnh hơn bình thường.</>}
      {volatilityRatio < 0.80 && <> Gần đây biến động thấp hơn nền một năm khoảng <b>{pct(Math.abs(volatilityChange))}</b>, nghĩa là danh mục đang dịu hơn so với lịch sử một năm.</>}
      {volatilityRatio >= 0.80 && volatilityRatio <= 1.20 && <> Chênh lệch chỉ khoảng <b>{pct(Math.abs(volatilityChange))}</b>, nên mức rung lắc gần đây chưa khác đáng kể so với nền một năm.</>}
    </>;

  const worstDay = historicalWorstDays[0] || null;
  const driverMetric = risk.largest_risk_symbol ? symbolMetrics[risk.largest_risk_symbol] : null;
  const driverCopy = largestRisk == null
    ? 'Chưa đủ dữ liệu để xác định mã ảnh hưởng rủi ro nhiều nhất.'
    : <>
      <b>{risk.largest_risk_symbol || '-'}</b> hiện đóng góp khoảng <b>{pct(largestRisk)}</b> vào biến động ước tính của phần cổ phiếu.
      {driverMetric?.equity_weight != null && <> Tỷ trọng vốn của mã này là {pct(driverMetric.equity_weight)}. {Number(largestRisk) > Number(driverMetric.equity_weight) * 1.2 ? 'Đóng góp rủi ro cao hơn rõ rệt tỷ trọng vốn, nên đây là mã cần theo dõi kỹ hơn.' : 'Đóng góp rủi ro hiện không lệch quá xa tỷ trọng vốn.'}</>}
    </>;

  return <div className="page risk-readable-page">
    <AppNav active="risk" locale={locale} />

    <header className="page-head risk-readable-head">
      <div>
        <div className="eyebrow">Phân tích danh mục</div>
        <h1>Danh mục có điều gì cần chú ý?</h1>
        <p className="muted">Giải thích tập trung vào tác động thực tế lên danh mục: mã nào ảnh hưởng nhiều, các mã có cùng giảm hay không, biến động đang tăng hay giảm, và các phiên lỗ thực tế đã xảy ra khi nào.</p>
      </div>
    </header>

    <section className="card risk-picture-card">
      <div className="risk-picture-main">
        <div><span className="risk-question">Đánh giá tổng quan</span><strong>{!dataReady ? 'DỮ LIỆU ĐANG HOÀN THIỆN' : overallWatch ? 'CÓ ĐIỂM CẦN THEO DÕI' : 'CHƯA CÓ CẢNH BÁO LỚN'}</strong></div>
        <span className={`risk-level risk-level-${dataReady ? 'good' : 'building'}`}>{dataReady ? 'DỮ LIỆU ĐỦ DÙNG' : 'CHƯA ĐỦ DỮ LIỆU'}</span>
      </div>
      <p>{dataReady ? `QPort đang dùng ${observations} phiên lợi suất với độ phủ ${pct(coverage)} để tính các chỉ số bên dưới.` : `Hiện có ${observations} phiên lợi suất và độ phủ ${pct(coverage)}. Những chỗ chưa đủ dữ liệu sẽ để trống thay vì suy đoán.`}</p>
      {missing.length > 0 && <div className="risk-missing-note">Còn thiếu hoặc chưa đủ lịch sử: <b>{missing.join(', ')}</b></div>}
    </section>

    <div className="risk-plain-grid">
      <InsightCard question="1 · Một mã có đang quá lớn không?" state={concentrationState[0]} tone={concentrationState[1]} title="Tác động của mã lớn nhất" footer="Ví dụ 10% chỉ để giúp hình dung độ nhạy của danh mục, không phải dự báo giá.">{concentrationCopy}</InsightCard>

      <InsightCard question="2 · Các mã có thường tăng/giảm cùng nhau?" state={correlationState[0]} tone={correlationState[1]} title="Tương quan có ý nghĩa gì?" footer="Gần 1: thường cùng hướng · Gần 0: ít quan hệ ổn định · Âm: thường có xu hướng ngược hướng. Tương quan lịch sử có thể thay đổi.">{correlationCopy}</InsightCard>

      <InsightCard question="3 · Gần đây danh mục rung lắc hơn hay ít hơn?" state={volatilityState[0]} tone={volatilityState[1]} title="3 tháng gần đây so với nền 1 năm">{volatilityCopy}</InsightCard>

      <InsightCard question="4 · Những phiên lỗ thực tế đã tệ đến mức nào?" state={worstDay ? 'CÓ LỊCH SỬ' : 'CHƯA ĐỦ SNAPSHOT'} tone={worstDay ? 'neutral' : 'building'} title="Các phiên giảm mạnh đã ghi nhận" className="risk-worst-card" footer="Đây là snapshot thực tế của danh mục tại thời điểm đó. VaR/CVaR mô phỏng được giữ riêng trong phần Nâng cao.">
        {worstDay ? <>
          <p className="risk-worst-summary">
            Phiên xấu nhất trong lịch sử QPort đang lưu là <b>{worstDay.snapshot_date}</b>:
            danh mục giảm <b className="neg">{pct(worstDay.daily_return)}</b>,
            tương đương <b className="neg">{signedMoney(worstDay.daily_pnl, locale)}</b>.
            Giá trị danh mục cuối ngày còn <b>{money(worstDay.nav, locale)}</b>.
          </p>
          <div className="risk-worst-days">
            {historicalWorstDays.map((day, index) => <div className="risk-worst-day-row" key={day.snapshot_date}>
              <span>#{index + 1}</span>
              <b>{day.snapshot_date}</b>
              <strong className={Number(day.daily_return) < 0 ? 'neg' : ''}>{pct(day.daily_return)}</strong>
              <span>{signedMoney(day.daily_pnl, locale)}</span>
              <span>NAV {money(day.nav, locale)}</span>
            </div>)}
          </div>
        </> : <p>Chưa có đủ snapshot chính thức có daily return để gắn một phiên giảm với ngày và giá trị danh mục cụ thể.</p>}
      </InsightCard>

      <InsightCard question="5 · Mã nào đang kéo rủi ro danh mục nhiều nhất?" state={riskDriverState[0]} tone={riskDriverState[1]} title="Ảnh hưởng rủi ro theo mã">{driverCopy}</InsightCard>
    </div>

    <section className="card risk-driver-card risk-symbol-review-card">
      <div className="section-head"><div><div className="eyebrow">Nhận xét từng mã</div><h2>Mỗi mã đang ảnh hưởng danh mục như thế nào?</h2><p className="muted">So sánh tỷ trọng vốn, đóng góp rủi ro, xu hướng biến động và mức liên hệ với các mã còn lại. Đây là nhận xét theo dữ liệu, không phải khuyến nghị mua/bán.</p></div></div>
      {symbolRows.length === 0 ? <div className="empty-state compact-empty">Chưa đủ lịch sử giá để tạo nhận xét riêng cho từng mã.</div> : <div className="risk-symbol-grid">
        {symbolRows.map(({ symbol, metric }) => {
          const tone = symbolTone(metric);
          return <article className="risk-symbol-card" key={symbol}>
            <div className="risk-symbol-head">
              <div><strong>{symbol}</strong><span>{Number(metric.return_observations || 0)} phiên dữ liệu</span></div>
              <span className={`risk-level risk-level-${tone[1]}`}>{tone[0]}</span>
            </div>
            <div className="risk-symbol-metrics">
              <div><span>Tỷ trọng vốn</span><b>{pct(metric.equity_weight)}</b></div>
              <div><span>Đóng góp rủi ro</span><b>{pct(metric.risk_contribution)}</b></div>
              <div><span>Biến động ~3 tháng</span><b>{pct(metric.volatility_63)}</b></div>
              <div><span>Nền ~1 năm</span><b>{pct(metric.volatility_252)}</b></div>
              <div><span>Tương quan với mã khác</span><b>{num(metric.average_correlation_to_others)}</b></div>
            </div>
            <p>{symbolComment(symbol, metric)}</p>
          </article>;
        })}
      </div>}
    </section>

    <details className="card risk-technical-details">
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
        <p className="muted"><b>63 phiên</b> tương đương khoảng 3 tháng giao dịch; <b>252 phiên</b> tương đương khoảng 1 năm. Volatility là độ rung lắc quy đổi theo năm, không phải mức lợi nhuận. VaR/CVaR chỉ mô tả phân phối lịch sử và không phải giới hạn lỗ được đảm bảo.</p>
      </div>
    </details>
  </div>;
}
