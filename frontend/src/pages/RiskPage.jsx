import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) {
  return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`;
}

function num(v, digits = 2) {
  return v == null || !Number.isFinite(Number(v)) ? '-' : Number(v).toFixed(digits);
}

function clampPct(value) {
  if (value == null || !Number.isFinite(Number(value))) return 0;
  return Math.max(0, Math.min(100, Number(value) * 100));
}

function PlainRiskCard({ question, state, tone = 'neutral', title, children, footer }) {
  return <section className="risk-plain-card">
    <div className="risk-plain-head">
      <span className="risk-question">{question}</span>
      <span className={`risk-level risk-level-${tone}`}>{state}</span>
    </div>
    <h3>{title}</h3>
    <div className="risk-plain-copy">{children}</div>
    {footer && <div className="risk-plain-footer">{footer}</div>}
  </section>;
}

export default function RiskPage({ risk = {}, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const contributions = risk.risk_contributions || {};
  const erc = risk.erc_reference_weights || {};
  const symbols = [...new Set([...Object.keys(contributions), ...Object.keys(erc)])].sort();
  const contributionRows = Object.entries(contributions)
    .filter(([, value]) => value != null && Number.isFinite(Number(value)))
    .sort((a, b) => Number(b[1]) - Number(a[1]));
  const quality = risk.quality || {};
  const equalRisk = risk.equal_risk_contribution;
  const highRiskCutoff = equalRisk == null ? 0.45 : Math.max(0.45, 1.5 * Number(equalRisk));
  const coverage = Number(quality.coverage_weight || 0);
  const observations = Number(risk.return_observations || 0);
  const missing = quality.missing_symbols || [];
  const actualPositions = Number(risk.n_positions || 0);
  const effectiveRatio = risk.effective_position_ratio == null ? null : Number(risk.effective_position_ratio);
  const largestEquityWeight = risk.max_equity_weight == null ? null : Number(risk.max_equity_weight);
  const avgCorrelation = risk.average_correlation == null ? null : Number(risk.average_correlation);
  const volRatio = risk.volatility_ratio == null ? null : Number(risk.volatility_ratio);
  const largestRiskContribution = risk.largest_risk_contribution == null ? null : Number(risk.largest_risk_contribution);
  const riskConcentrationRatio = risk.risk_concentration_ratio == null ? null : Number(risk.risk_concentration_ratio);

  const confidence = coverage < 0.90 || observations < 20
    ? { key: 'LOW', tone: 'building', label: text('BUILDING', 'ĐANG XÂY DỰNG') }
    : coverage < 1 || observations < 120
      ? { key: 'MEDIUM', tone: 'watch', label: text('MEDIUM', 'TRUNG BÌNH') }
      : { key: 'HIGH', tone: 'good', label: text('HIGH', 'CAO') };

  const concentration = effectiveRatio == null || largestEquityWeight == null
    ? { key: 'BUILDING', tone: 'building', label: text('BUILDING', 'ĐANG XÂY DỰNG') }
    : largestEquityWeight >= 0.45 || effectiveRatio < 0.65
      ? { key: 'HIGH', tone: 'high', label: text('HIGH', 'CAO') }
      : largestEquityWeight >= 0.35 || effectiveRatio < 0.80
        ? { key: 'ELEVATED', tone: 'watch', label: text('ELEVATED', 'ĐÁNG CHÚ Ý') }
        : { key: 'BALANCED', tone: 'good', label: text('BALANCED', 'KHÁ CÂN BẰNG') };

  const coMovement = avgCorrelation == null
    ? { key: 'BUILDING', tone: 'building', label: text('BUILDING', 'ĐANG XÂY DỰNG') }
    : avgCorrelation >= 0.60
      ? { key: 'HIGH', tone: 'high', label: text('HIGH', 'CAO') }
      : avgCorrelation >= 0.35
        ? { key: 'MODERATE', tone: 'watch', label: text('MODERATE', 'TRUNG BÌNH') }
        : { key: 'LOW', tone: 'good', label: text('LOW', 'THẤP') };

  const volatility = volRatio == null
    ? { key: 'BUILDING', tone: 'building', label: text('BUILDING', 'ĐANG XÂY DỰNG') }
    : volRatio > 1.20
      ? { key: 'RISING', tone: 'high', label: text('RISING', 'ĐANG TĂNG') }
      : volRatio < 0.80
        ? { key: 'CALMER', tone: 'good', label: text('CALMER', 'ÊM HƠN') }
        : { key: 'NORMAL', tone: 'neutral', label: text('NORMAL', 'BÌNH THƯỜNG') };

  const riskDriver = largestRiskContribution == null
    ? { key: 'BUILDING', tone: 'building', label: text('BUILDING', 'ĐANG XÂY DỰNG') }
    : largestRiskContribution > highRiskCutoff || (riskConcentrationRatio != null && riskConcentrationRatio > 1.50)
      ? { key: 'DOMINANT', tone: 'high', label: text('DOMINANT', 'CHI PHỐI') }
      : { key: 'DISTRIBUTED', tone: 'good', label: text('DISTRIBUTED', 'PHÂN BỔ') };

  const picture = confidence.key === 'LOW'
    ? { tone: 'building', label: text('EVIDENCE BUILDING', 'DỮ LIỆU ĐANG XÂY DỰNG') }
    : [concentration.key, coMovement.key, volatility.key, riskDriver.key].some(key => ['HIGH', 'RISING', 'DOMINANT'].includes(key))
      ? { tone: 'watch', label: text('WATCH', 'CẦN THEO DÕI') }
      : { tone: 'good', label: text('NORMAL', 'BÌNH THƯỜNG') };

  const confidenceCopy = confidence.key === 'LOW'
    ? text(
        `QPort does not yet have enough overlapping D1 history to treat all model outputs as reliable. Coverage is ${pct(coverage)} with ${observations} usable portfolio-return observations.`,
        `QPort chưa có đủ lịch sử D1 giao nhau để coi toàn bộ output mô hình là đáng tin cậy. Độ phủ hiện là ${pct(coverage)} với ${observations} quan sát lợi suất danh mục có thể dùng.`
      )
    : text(
        `Risk estimates are supported by ${pct(coverage)} portfolio coverage and ${observations} usable return observations. Missing values are still left blank rather than replaced with zero.`,
        `Các ước lượng rủi ro đang được hỗ trợ bởi ${pct(coverage)} độ phủ danh mục và ${observations} quan sát lợi suất sử dụng được. Giá trị thiếu vẫn được để trống thay vì thay bằng số 0.`
      );

  const concentrationCopy = concentration.key === 'BUILDING'
    ? text('Waiting for enough position and market-history evidence.', 'Đang chờ đủ dữ liệu vị thế và lịch sử thị trường.')
    : concentration.key === 'HIGH'
      ? text(
          `A small number of holdings can materially move the whole portfolio. The largest equity position is ${pct(largestEquityWeight)} and ${actualPositions} actual holdings behave like about ${num(risk.effective_positions)} equally sized positions.`,
          `Một số ít mã có thể ảnh hưởng lớn tới toàn danh mục. Vị thế cổ phiếu lớn nhất chiếm ${pct(largestEquityWeight)} và ${actualPositions} mã thực tế đang hành xử tương đương khoảng ${num(risk.effective_positions)} vị thế có quy mô bằng nhau.`
        )
      : text(
          `Capital is not perfectly even, but diversification is meaningful: ${actualPositions} actual holdings behave like about ${num(risk.effective_positions)} equally sized positions. Largest equity weight is ${pct(largestEquityWeight)}.`,
          `Vốn không chia đều tuyệt đối nhưng vẫn có ý nghĩa đa dạng hóa: ${actualPositions} mã thực tế hành xử tương đương khoảng ${num(risk.effective_positions)} vị thế có quy mô bằng nhau. Tỷ trọng cổ phiếu lớn nhất là ${pct(largestEquityWeight)}.`
        );

  const correlationCopy = avgCorrelation == null
    ? text('QPort needs overlapping D1 history before it can judge whether holdings usually move together.', 'QPort cần lịch sử D1 giao nhau trước khi đánh giá các mã có thường biến động cùng nhau hay không.')
    : avgCorrelation >= 0.60
      ? text(
          `Your holdings often move in the same direction. Average relationship is ${num(avgCorrelation)}, so diversification may weaken during broad market moves.`,
          `Các mã thường biến động cùng chiều. Mức tương quan trung bình là ${num(avgCorrelation)}, vì vậy lợi ích đa dạng hóa có thể giảm khi thị trường biến động rộng.`
        )
      : avgCorrelation >= 0.35
        ? text(
            `Your holdings provide some diversification, but common market moves still matter. Average relationship is ${num(avgCorrelation)}.`,
            `Danh mục có một mức đa dạng hóa nhất định nhưng biến động chung của thị trường vẫn đáng kể. Mức tương quan trung bình là ${num(avgCorrelation)}.`
          )
        : text(
            `The holdings have shown relatively low co-movement in the stored sample. Average relationship is ${num(avgCorrelation)}, which supports diversification.`,
            `Các mã cho thấy mức biến động cùng nhau tương đối thấp trong mẫu đang lưu. Tương quan trung bình là ${num(avgCorrelation)}, hỗ trợ đa dạng hóa.`
          );

  const volatilityCopy = volRatio == null
    ? text('Recent versus one-year volatility cannot be compared until both history windows are populated.', 'Chưa thể so sánh biến động gần đây với 1 năm cho đến khi đủ cả hai cửa sổ dữ liệu.')
    : volRatio > 1.20
      ? text(
          `Recent price movement is stronger than the one-year norm. 63D annualized volatility is ${pct(risk.volatility_63)} versus ${pct(risk.volatility_252)} over 252D.`,
          `Biến động giá gần đây mạnh hơn mức 1 năm. Volatility năm hóa 63D là ${pct(risk.volatility_63)} so với ${pct(risk.volatility_252)} ở cửa sổ 252D.`
        )
      : volRatio < 0.80
        ? text(
            `Recent conditions have been calmer than the one-year norm. 63D volatility is ${pct(risk.volatility_63)} versus ${pct(risk.volatility_252)} over 252D.`,
            `Điều kiện gần đây êm hơn mức 1 năm. Volatility 63D là ${pct(risk.volatility_63)} so với ${pct(risk.volatility_252)} ở cửa sổ 252D.`
          )
        : text(
            `Recent and one-year volatility are broadly aligned: ${pct(risk.volatility_63)} over 63D versus ${pct(risk.volatility_252)} over 252D.`,
            `Biến động gần đây và mức 1 năm tương đối đồng pha: ${pct(risk.volatility_63)} ở 63D so với ${pct(risk.volatility_252)} ở 252D.`
          );

  const badDayCopy = risk.daily_var_95 == null || risk.daily_cvar_95 == null
    ? text('Bad-day statistics are still building and are intentionally not replaced with zero.', 'Thống kê ngày xấu vẫn đang được xây dựng và chủ động không được thay bằng số 0.')
    : text(
        `In the stored sample, roughly 1 in 20 trading days was worse than about ${pct(risk.daily_var_95)}. Within those worst days, the average loss was about ${pct(risk.daily_cvar_95)}. Worst observed day: ${pct(risk.max_daily_loss)}.`,
        `Trong mẫu đang lưu, khoảng 1 trong 20 phiên có mức giảm tệ hơn khoảng ${pct(risk.daily_var_95)}. Trong nhóm ngày xấu nhất đó, mức giảm trung bình khoảng ${pct(risk.daily_cvar_95)}. Ngày xấu nhất đã quan sát: ${pct(risk.max_daily_loss)}.`
      );

  const driverCopy = largestRiskContribution == null
    ? text('Risk contribution needs enough covariance history before QPort can identify the main driver.', 'Đóng góp rủi ro cần đủ lịch sử covariance trước khi QPort xác định được mã chi phối.')
    : text(
        `${risk.largest_risk_symbol || '-'} is currently the largest modeled risk contributor at ${pct(largestRiskContribution)} of total modeled portfolio risk${riskConcentrationRatio != null ? `, or ${num(riskConcentrationRatio)}× an equal-risk share` : ''}.`,
        `${risk.largest_risk_symbol || '-'} hiện là mã đóng góp rủi ro mô hình lớn nhất với ${pct(largestRiskContribution)} tổng modeled risk của danh mục${riskConcentrationRatio != null ? `, tương đương ${num(riskConcentrationRatio)}× mức equal-risk` : ''}.`
      );

  return (
    <div className="page risk-readable-page">
      <AppNav active="risk" locale={locale} />

      <header className="page-head risk-readable-head">
        <div>
          <div className="eyebrow">{text('Understand before measuring', 'Hiểu trước, số liệu sau')}</div>
          <h1>{text('Portfolio risk', 'Rủi ro danh mục')}</h1>
          <p className="muted">{text(
            'Start with plain-language answers. Technical metrics remain available below for audit and deeper analysis. Risk is informational and never creates a BUY/SELL transaction.',
            'Bắt đầu bằng câu trả lời dễ hiểu. Các chỉ số kỹ thuật vẫn được giữ bên dưới để audit và phân tích sâu. Risk chỉ mang tính thông tin và không bao giờ tạo transaction BUY/SELL.'
          )}</p>
        </div>
      </header>

      <section className="card risk-picture-card">
        <div className="risk-picture-main">
          <div>
            <span className="risk-question">{text('Portfolio risk picture', 'Bức tranh rủi ro danh mục')}</span>
            <strong>{picture.label}</strong>
          </div>
          <span className={`risk-level risk-level-${picture.tone}`}>{confidence.label} {text('confidence', 'độ tin cậy')}</span>
        </div>
        <p>{confidenceCopy}</p>
        {missing.length > 0 && <div className="risk-missing-note">{text('Still missing D1 history', 'Vẫn thiếu lịch sử D1')}: <b>{missing.join(', ')}</b></div>}
      </section>

      <div className="risk-plain-grid">
        <PlainRiskCard
          question={text('1 · Is the portfolio too concentrated?', '1 · Danh mục có tập trung quá không?')}
          state={concentration.label}
          tone={concentration.tone}
          title={text('Diversification', 'Đa dạng hóa')}
          footer={text(`Largest equity weight ${pct(risk.max_equity_weight)} · Effective positions ${num(risk.effective_positions)} / ${actualPositions || '-'}`, `Tỷ trọng CP lớn nhất ${pct(risk.max_equity_weight)} · Vị thế hiệu dụng ${num(risk.effective_positions)} / ${actualPositions || '-'}`)}
        >{concentrationCopy}</PlainRiskCard>

        <PlainRiskCard
          question={text('2 · Do the holdings move together?', '2 · Các cổ phiếu có thường đi cùng nhau?')}
          state={coMovement.label}
          tone={coMovement.tone}
          title={text('Market co-movement', 'Mức biến động cùng nhau')}
          footer={text(`Average relationship ${num(risk.average_correlation)} · Highest pair ${num(risk.max_correlation)}`, `Tương quan trung bình ${num(risk.average_correlation)} · Cặp cao nhất ${num(risk.max_correlation)}`)}
        >{correlationCopy}</PlainRiskCard>

        <PlainRiskCard
          question={text('3 · Is price movement getting stronger?', '3 · Biến động giá có đang mạnh lên?')}
          state={volatility.label}
          tone={volatility.tone}
          title={text('Volatility trend', 'Xu hướng biến động')}
          footer={text(`Recent ${pct(risk.volatility_63)} · 1-year ${pct(risk.volatility_252)}`, `Gần đây ${pct(risk.volatility_63)} · 1 năm ${pct(risk.volatility_252)}`)}
        >{volatilityCopy}</PlainRiskCard>

        <PlainRiskCard
          question={text('4 · How bad have bad days been?', '4 · Những ngày xấu đã tệ đến mức nào?')}
          state={risk.daily_cvar_95 == null ? text('BUILDING', 'ĐANG XÂY DỰNG') : text('HISTORICAL SAMPLE', 'MẪU LỊCH SỬ')}
          tone={risk.daily_cvar_95 == null ? 'building' : 'neutral'}
          title={text('Bad-day risk', 'Rủi ro ngày xấu')}
          footer={text('Historical evidence, not a forecast or guaranteed loss limit.', 'Bằng chứng lịch sử, không phải dự báo hay giới hạn thua lỗ được đảm bảo.')}
        >{badDayCopy}</PlainRiskCard>

        <PlainRiskCard
          question={text('5 · Which holding drives the most risk?', '5 · Mã nào đang tạo nhiều rủi ro nhất?')}
          state={riskDriver.label}
          tone={riskDriver.tone}
          title={text('Risk by holding', 'Rủi ro theo mã')}
          footer={text('Risk contribution can differ greatly from capital weight.', 'Đóng góp rủi ro có thể khác rất nhiều so với tỷ trọng vốn.')}
        >{driverCopy}</PlainRiskCard>

        <PlainRiskCard
          question={text('Can I trust these conclusions yet?', 'Tôi đã có thể tin các kết luận này chưa?')}
          state={confidence.label}
          tone={confidence.tone}
          title={text('Data confidence', 'Độ tin cậy dữ liệu')}
          footer={`${quality.eligible_symbols ?? 0}/${quality.requested_symbols ?? actualPositions} ${text('holdings eligible', 'mã đủ dữ liệu')} · ${observations} ${text('return observations', 'quan sát lợi suất')}`}
        >{confidenceCopy}</PlainRiskCard>
      </div>

      <section className="card risk-driver-card">
        <div className="section-head">
          <div>
            <div className="eyebrow">{text('Where modeled risk comes from', 'Nguồn gốc modeled risk')}</div>
            <h2>{text('Who drives your risk?', 'Mã nào đang chi phối rủi ro?')}</h2>
            <p className="muted">{text('This is modeled risk contribution, not profit/loss and not a recommendation to trade.', 'Đây là đóng góp rủi ro mô hình, không phải P/L và không phải khuyến nghị giao dịch.')}</p>
          </div>
        </div>
        {contributionRows.length === 0 ? <div className="empty-state compact-empty">{text('Waiting for enough D1 history to calculate risk contribution.', 'Đang chờ đủ lịch sử D1 để tính đóng góp rủi ro.')}</div> : <div className="risk-driver-list">
          {contributionRows.map(([symbol, value]) => <div className="risk-driver-row" key={symbol}>
            <div className="risk-driver-label"><b>{String(symbol).toUpperCase()}</b><span>{pct(value)}</span></div>
            <div className="risk-driver-track" aria-label={`${symbol} ${pct(value)}`}><span style={{ width: `${clampPct(value)}%` }} /></div>
          </div>)}
        </div>}
      </section>

      <details className="card risk-technical-details">
        <summary>
          <div>
            <span className="eyebrow">{text('Advanced', 'Nâng cao')}</span>
            <b>{text('Technical details & methodology', 'Chi tiết kỹ thuật & methodology')}</b>
            <small>{text('For fund-manager review, quant audit and AI export.', 'Dành cho fund-manager review, quant audit và AI export.')}</small>
          </div>
          <span className="risk-details-toggle">+</span>
        </summary>

        <div className="risk-technical-body">
          <div className="card risk-technical-interpretation">
            <h3>{text('Risk interpretation', 'Diễn giải rủi ro')}</h3>
            <div className="diag-row"><span>{text('Capital concentration', 'Tập trung vốn')}</span><b>{concentration.label}</b></div>
            <div className="diag-row"><span>{text('Correlation regime', 'Regime tương quan')}</span><b>{coMovement.label}</b></div>
            <div className="diag-row"><span>{text('Volatility regime', 'Regime biến động')}</span><b>{volatility.label}</b></div>
            <div className="diag-row"><span>{text('Data readiness', 'Độ sẵn sàng dữ liệu')}</span><b>{pct(coverage)} · {observations} {text('observations', 'quan sát')}</b></div>
          </div>

          <div className="metric-grid risk-technical-metrics">
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
            <div className="metric-card"><div className="metric-label">{text('Worst observed day', 'Ngày xấu nhất')}</div><div className="metric-value">{pct(risk.max_daily_loss)}</div><div className="muted">{observations} {text('return observations', 'quan sát lợi suất')}</div></div>
          </div>

          <div className="expand-grid">
            <div className="card">
              <h3>{text('Concentration & diversification', 'Tập trung & đa dạng hóa')}</h3>
              <div className="diag-row"><span>{text('Equity HHI', 'HHI phần cổ phiếu')}</span><b>{num(risk.equity_hhi, 3)}</b></div>
              <div className="diag-row"><span>{text('Effective positions', 'Số vị thế hiệu dụng')}</span><b>{num(risk.effective_positions, 2)}</b></div>
              <div className="diag-row"><span>{text('Effective / actual ratio', 'Tỷ lệ hiệu dụng / thực tế')}</span><b>{pct(risk.effective_position_ratio)}</b></div>
              <div className="diag-row"><span>{text('Largest NAV position', 'Vị thế NAV lớn nhất')}</span><b>{pct(risk.max_position_weight)}</b></div>
              <div className="diag-row"><span>{text('Largest equity weight', 'Tỷ trọng cổ phiếu lớn nhất')}</span><b>{pct(risk.max_equity_weight)}</b></div>
              <div className="diag-row"><span>{text('Risk contribution HHI', 'HHI đóng góp rủi ro')}</span><b>{num(risk.risk_contribution_hhi, 3)}</b></div>
              <div className="diag-row"><span>{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</span><b>{num(risk.diversification_ratio)}</b></div>
            </div>
            <div className="card">
              <h3>{text('Tail-risk diagnostics', 'Chẩn đoán rủi ro đuôi')}</h3>
              <div className="diag-row"><span>{text('Historical daily VaR 95%', 'VaR lịch sử ngày 95%')}</span><b>{pct(risk.daily_var_95)}</b></div>
              <div className="diag-row"><span>{text('Historical daily CVaR 95%', 'CVaR lịch sử ngày 95%')}</span><b>{pct(risk.daily_cvar_95)}</b></div>
              <div className="diag-row"><span>{text('Worst observed day', 'Ngày xấu nhất quan sát được')}</span><b>{pct(risk.max_daily_loss)}</b></div>
              <div className="diag-row"><span>{text('Downside volatility', 'Biến động phía giảm')}</span><b>{pct(risk.downside_volatility)}</b></div>
              <div className="diag-row"><span>{text('Positive-day ratio', 'Tỷ lệ ngày tăng')}</span><b>{pct(risk.positive_day_ratio)}</b></div>
              <div className="diag-row"><span>{text('Return observations', 'Số quan sát lợi suất')}</span><b>{observations}</b></div>
              <p className="muted">{text('Historical VaR/CVaR describes the stored sample; it is not a forecast or guaranteed loss limit.', 'VaR/CVaR lịch sử mô tả mẫu dữ liệu đang lưu; đây không phải dự báo hay giới hạn thua lỗ được đảm bảo.')}</p>
            </div>
          </div>

          <div className="card">
            <h3>{t('risk.contrib_erc')}</h3>
            <p className="muted">{text('ERC is a diagnostic capital reference only. It does not set portfolio targets, rebalance holdings or create trades.', 'ERC chỉ là tham chiếu vốn phục vụ chẩn đoán. Nó không đặt target cho portfolio, không rebalance holdings và không tạo giao dịch.')}</p>
            <p className="muted">{text(`Risk-concentration warning threshold: greater than ${pct(highRiskCutoff)} (max of 45% or 1.5× equal-risk share).`, `Ngưỡng cảnh báo tập trung rủi ro: lớn hơn ${pct(highRiskCutoff)} (lớn hơn giữa 45% và 1,5× mức rủi ro cân bằng).`)}</p>
            {symbols.length === 0 ? <div className="muted">{t('risk.not_enough')}</div> : <div className="table-scroll"><table className="ranking"><thead><tr><th>{t('risk.ticker')}</th><th>{t('risk.current_contrib')}</th><th>{text('Equal-risk contribution', 'Đóng góp rủi ro cân bằng')}</th><th>{text('ERC capital reference', 'Tham chiếu vốn ERC')}</th><th>{t('risk.interpretation')}</th></tr></thead><tbody>{symbols.map(symbol => {
              const rc = contributions[symbol];
              const ew = erc[symbol];
              const interpretation = rc == null ? status('NO_DATA') : Number(rc) > highRiskCutoff ? status('HIGH_RISK_CONTRIBUTION') : status('NORMAL');
              return <tr key={symbol}><td><b>{symbol}</b></td><td>{pct(rc)}</td><td>{pct(equalRisk)}</td><td>{pct(ew)}</td><td>{interpretation}</td></tr>;
            })}</tbody></table></div>}
          </div>

          <div className="card">
            <h3>{t('risk.data_quality')}</h3>
            <div className="diag-row"><span>{t('common.as_of')}</span><b>{risk.as_of || '-'}</b></div>
            <div className="diag-row"><span>{t('risk.requested_symbols')}</span><b>{quality.requested_symbols ?? '-'}</b></div>
            <div className="diag-row"><span>{t('risk.eligible_symbols')}</span><b>{quality.eligible_symbols ?? '-'}</b></div>
            <div className="diag-row"><span>{t('risk.coverage')}</span><b>{pct(quality.coverage_weight)}</b></div>
            <div className="diag-row"><span>{t('risk.missing_covariance')}</span><b>{quality.missing_covariance_cells ?? '-'}</b></div>
            <div className="diag-row"><span>{text('Concentration basis', 'Cơ sở tính tập trung')}</span><b>{risk.methodology?.concentration_basis || '-'}</b></div>
            <div className="diag-row"><span>{text('Return type', 'Loại lợi suất')}</span><b>{risk.methodology?.return_type || '-'}</b></div>
            <div className="diag-row"><span>{text('Annualization', 'Năm hóa')}</span><b>{risk.methodology?.annualization ?? '-'}</b></div>
            <div className="diag-row"><span>{text('Covariance', 'Covariance')}</span><b>{risk.methodology?.covariance || '-'}</b></div>
            <div className="diag-row"><span>{text('ERC policy', 'Chính sách ERC')}</span><b>{risk.methodology?.erc || '-'}</b></div>
            {missing.length > 0 && <div className="run-message">{t('risk.missing_history', { symbols: missing.join(', ') })}</div>}
          </div>
        </div>
      </details>
    </div>
  );
}
