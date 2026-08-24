import React from 'react';
import AppNav from '../components/AppNav.jsx';

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

function num(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : Number(value).toFixed(digits);
}

function InsightCard({ question, state, tone = 'neutral', title, children, footer }) {
  return <section className="risk-plain-card">
    <div className="risk-plain-head"><span className="risk-question">{question}</span><span className={`risk-level risk-level-${tone}`}>{state}</span></div>
    <h3>{title}</h3>
    <div className="risk-plain-copy">{children}</div>
    {footer && <div className="risk-plain-footer">{footer}</div>}
  </section>;
}

export default function RiskPage({ risk = {}, locale = 'vi' }) {
  const quality = risk.quality || {};
  const coverage = Number(quality.coverage_weight || 0);
  const observations = Number(risk.return_observations || 0);
  const missing = quality.missing_symbols || [];
  const actualPositions = Number(risk.n_positions || 0);
  const largestWeight = risk.max_equity_weight == null ? null : Number(risk.max_equity_weight);
  const effectivePositions = risk.effective_positions == null ? null : Number(risk.effective_positions);
  const avgCorrelation = risk.average_correlation == null ? null : Number(risk.average_correlation);
  const vol63 = risk.volatility_63 == null ? null : Number(risk.volatility_63);
  const vol252 = risk.volatility_252 == null ? null : Number(risk.volatility_252);
  const largestRisk = risk.largest_risk_contribution == null ? null : Number(risk.largest_risk_contribution);
  const contributions = Object.entries(risk.risk_contributions || {})
    .filter(([, value]) => value != null && Number.isFinite(Number(value)))
    .sort((a, b) => Number(b[1]) - Number(a[1]));

  const dataReady = coverage >= 0.90 && observations >= 20;
  const concentrationState = largestWeight == null ? ['ĐANG TÍNH', 'building'] : largestWeight >= 0.45 ? ['CAO', 'high'] : largestWeight >= 0.35 ? ['ĐÁNG CHÚ Ý', 'watch'] : ['ỔN', 'good'];
  const correlationState = avgCorrelation == null ? ['ĐANG TÍNH', 'building'] : avgCorrelation >= 0.60 ? ['CAO', 'high'] : avgCorrelation >= 0.35 ? ['TRUNG BÌNH', 'watch'] : ['THẤP', 'good'];
  const volatilityRatio = vol63 != null && vol252 ? vol63 / vol252 : null;
  const volatilityState = volatilityRatio == null ? ['ĐANG TÍNH', 'building'] : volatilityRatio > 1.20 ? ['ĐANG TĂNG', 'high'] : volatilityRatio < 0.80 ? ['ĐANG GIẢM', 'good'] : ['ỔN ĐỊNH', 'neutral'];
  const riskDriverState = largestRisk == null ? ['ĐANG TÍNH', 'building'] : largestRisk > 0.45 ? ['TẬP TRUNG', 'high'] : ['PHÂN BỔ', 'good'];
  const overallWatch = [concentrationState[1], correlationState[1], volatilityState[1], riskDriverState[1]].includes('high');

  const concentrationCopy = largestWeight == null
    ? 'Chưa đủ dữ liệu để đánh giá mức tập trung.'
    : largestWeight >= 0.45
      ? `Mã lớn nhất đang chiếm ${pct(largestWeight)} phần cổ phiếu của danh mục. Biến động ở một mã có thể ảnh hưởng mạnh đến kết quả chung.`
      : `Mã lớn nhất chiếm ${pct(largestWeight)}. ${actualPositions || '-'} mã hiện tại tương đương khoảng ${num(effectivePositions)} vị thế có quy mô cân bằng về mặt phân bổ.`;

  const correlationCopy = avgCorrelation == null
    ? 'QPort cần thêm lịch sử giá giao nhau giữa các mã trước khi đánh giá mức biến động cùng chiều.'
    : avgCorrelation >= 0.60
      ? `Các mã thường biến động cùng chiều khá mạnh. Tương quan trung bình hiện khoảng ${num(avgCorrelation)}, nên lợi ích đa dạng hóa có thể giảm khi thị trường xấu.`
      : avgCorrelation >= 0.35
        ? `Các mã có mức liên hệ vừa phải, tương quan trung bình khoảng ${num(avgCorrelation)}. Danh mục vẫn có đa dạng hóa nhưng chưa hoàn toàn độc lập.`
        : `Các mã có mức biến động cùng nhau tương đối thấp trong dữ liệu hiện có. Tương quan trung bình khoảng ${num(avgCorrelation)}.`;

  const volatilityCopy = volatilityRatio == null
    ? 'Chưa đủ dữ liệu để so sánh biến động gần đây với mức một năm.'
    : volatilityRatio > 1.20
      ? `Biến động gần đây đang mạnh hơn đáng kể: ${pct(vol63)} trong 63 phiên so với ${pct(vol252)} trong 252 phiên.`
      : volatilityRatio < 0.80
        ? `Biến động gần đây đang dịu hơn: ${pct(vol63)} trong 63 phiên so với ${pct(vol252)} trong 252 phiên.`
        : `Biến động gần đây tương đối gần mức một năm: ${pct(vol63)} so với ${pct(vol252)}.`;

  const badDayCopy = risk.daily_cvar_95 == null
    ? 'Chưa đủ dữ liệu để ước tính các phiên giảm mạnh.'
    : `Trong dữ liệu đã quan sát, ngưỡng của nhóm 5% phiên xấu nhất vào khoảng ${pct(risk.daily_var_95)}; mức giảm trung bình trong chính nhóm này khoảng ${pct(risk.daily_cvar_95)}. Phiên xấu nhất đã ghi nhận: ${pct(risk.max_daily_loss)}.`;

  const driverCopy = largestRisk == null
    ? 'Chưa đủ dữ liệu để xác định mã ảnh hưởng rủi ro nhiều nhất.'
    : `${risk.largest_risk_symbol || '-'} hiện đóng góp khoảng ${pct(largestRisk)} vào rủi ro ước tính của toàn danh mục.`;

  return <div className="page risk-readable-page">
    <AppNav active="risk" locale={locale} />

    <header className="page-head risk-readable-head">
      <div>
        <div className="eyebrow">Phân tích danh mục</div>
        <h1>Danh mục có điều gì cần chú ý?</h1>
        <p className="muted">Phần này giúp bạn hiểu mức tập trung, biến động và sự liên hệ giữa các mã. Đây là thông tin hỗ trợ theo dõi, không phải tín hiệu mua bán tự động.</p>
      </div>
    </header>

    <section className="card risk-picture-card">
      <div className="risk-picture-main">
        <div><span className="risk-question">Đánh giá tổng quan</span><strong>{!dataReady ? 'DỮ LIỆU ĐANG HOÀN THIỆN' : overallWatch ? 'CÓ ĐIỂM CẦN THEO DÕI' : 'CHƯA CÓ CẢNH BÁO LỚN'}</strong></div>
        <span className={`risk-level risk-level-${dataReady ? 'good' : 'building'}`}>{dataReady ? 'DỮ LIỆU ĐỦ DÙNG' : 'CHƯA ĐỦ DỮ LIỆU'}</span>
      </div>
      <p>{dataReady ? `Độ phủ dữ liệu hiện là ${pct(coverage)} với ${observations} quan sát lợi suất có thể sử dụng.` : `QPort mới có ${pct(coverage)} độ phủ và ${observations} quan sát lợi suất. Một số kết luận sẽ tự đầy đủ hơn khi lịch sử giá tiếp tục được bổ sung.`}</p>
      {missing.length > 0 && <div className="risk-missing-note">Còn thiếu hoặc chưa đủ lịch sử: <b>{missing.join(', ')}</b></div>}
    </section>

    <div className="risk-plain-grid">
      <InsightCard question="1 · Danh mục có tập trung quá không?" state={concentrationState[0]} tone={concentrationState[1]} title="Mức tập trung">{concentrationCopy}</InsightCard>
      <InsightCard question="2 · Các cổ phiếu có thường đi cùng nhau?" state={correlationState[0]} tone={correlationState[1]} title="Mức tương quan">{correlationCopy}</InsightCard>
      <InsightCard question="3 · Biến động giá có đang mạnh lên?" state={volatilityState[0]} tone={volatilityState[1]} title="Xu hướng biến động">{volatilityCopy}</InsightCard>
      <InsightCard question="4 · Những phiên xấu đã tệ đến mức nào?" state={risk.daily_cvar_95 == null ? 'ĐANG TÍNH' : 'DỮ LIỆU LỊCH SỬ'} tone={risk.daily_cvar_95 == null ? 'building' : 'neutral'} title="Rủi ro trong phiên giảm mạnh" footer="Số liệu lịch sử không phải dự báo mức lỗ trong tương lai.">{badDayCopy}</InsightCard>
      <InsightCard question="5 · Mã nào ảnh hưởng rủi ro nhiều nhất?" state={riskDriverState[0]} tone={riskDriverState[1]} title="Rủi ro theo mã">{driverCopy}</InsightCard>
      <InsightCard question="6 · Tôi đã có thể tin các số liệu này chưa?" state={dataReady ? 'KHÁ TỐT' : 'ĐANG HOÀN THIỆN'} tone={dataReady ? 'good' : 'building'} title="Độ đầy đủ dữ liệu" footer={`${quality.eligible_symbols ?? 0}/${quality.requested_symbols ?? actualPositions} mã đủ dữ liệu · ${observations} quan sát`}>QPort để trống chỉ số chưa đủ dữ liệu thay vì thay bằng số 0. Điều này giúp tránh kết luận sai khi lịch sử còn ngắn.</InsightCard>
    </div>

    <section className="card risk-driver-card">
      <div className="section-head"><div><div className="eyebrow">Theo từng mã</div><h2>Mã nào đang đóng góp rủi ro nhiều nhất?</h2><p className="muted">Tỷ lệ dưới đây đo mức ảnh hưởng đến biến động chung, không phải lãi/lỗ và không phải khuyến nghị giao dịch.</p></div></div>
      {contributions.length === 0 ? <div className="empty-state compact-empty">Chưa đủ lịch sử giá để tính phần đóng góp rủi ro theo từng mã.</div> : <div className="risk-driver-list">
        {contributions.map(([symbol, value]) => <div className="risk-driver-row" key={symbol}>
          <div className="risk-driver-label"><b>{String(symbol).toUpperCase()}</b><span>{pct(value)}</span></div>
          <div className="risk-driver-track" aria-label={`${symbol} ${pct(value)}`}><span style={{ width: `${Math.max(0, Math.min(100, Number(value) * 100))}%` }} /></div>
        </div>)}
      </div>}
    </section>

    <details className="card risk-technical-details">
      <summary><div><span className="eyebrow">Nâng cao</span><b>Chỉ số kỹ thuật và phương pháp tính</b><small>Dành cho người muốn kiểm tra sâu các mô hình rủi ro.</small></div><span className="risk-details-toggle">+</span></summary>
      <div className="risk-technical-body">
        <div className="metric-grid risk-technical-metrics">
          <div className="metric-card"><div className="metric-label">Biến động 63 phiên</div><div className="metric-value">{pct(risk.volatility_63)}</div></div>
          <div className="metric-card"><div className="metric-label">Biến động 252 phiên</div><div className="metric-value">{pct(risk.volatility_252)}</div></div>
          <div className="metric-card"><div className="metric-label">Tương quan trung bình / cao nhất</div><div className="metric-value">{num(risk.average_correlation)} / {num(risk.max_correlation)}</div></div>
          <div className="metric-card"><div className="metric-label">Số vị thế hiệu dụng</div><div className="metric-value">{num(risk.effective_positions)}</div></div>
          <div className="metric-card"><div className="metric-label">Tỷ lệ đa dạng hóa</div><div className="metric-value">{num(risk.diversification_ratio)}</div></div>
          <div className="metric-card"><div className="metric-label">VaR ngày 95%</div><div className="metric-value">{pct(risk.daily_var_95)}</div></div>
          <div className="metric-card"><div className="metric-label">CVaR ngày 95%</div><div className="metric-value">{pct(risk.daily_cvar_95)}</div></div>
          <div className="metric-card"><div className="metric-label">Biến động phía giảm</div><div className="metric-value">{pct(risk.downside_volatility)}</div></div>
        </div>
        <p className="muted"><b>VaR/CVaR</b> ở đây chỉ mô tả dữ liệu lịch sử đã lưu. Chúng không phải dự báo và không phải giới hạn thua lỗ được đảm bảo.</p>
      </div>
    </details>
  </div>;
}
