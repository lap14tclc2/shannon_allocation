import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import MetricCard from '../components/MetricCard.jsx';
import ValuationDetailOverlay from '../components/ValuationDetailOverlay.jsx';
import { simulatePortfolioAllocation } from '../lib/api.js';
import { formatWeight, pct } from '../lib/format.js';
import {
  ACTION_LABEL_VI,
  ACTION_TONE,
  CONFIDENCE_LABEL_VI,
  CONVICTION_LABEL_VI,
  ELIGIBILITY_LABEL_VI,
  FIT_LABEL_VI,
  POSTURE_LABEL_VI,
  reasonCodeVi,
} from '../lib/allocationLabels.js';
import '../valuation-page.css';

const VERDICT_LABEL_VI = {
  NO_ACTION_REQUIRED: 'Không cần hành động',
  SELECTIVE_ACTION: 'Hành động chọn lọc',
};

function ActionPill({ action }) {
  const tone = ACTION_TONE[action] || 'hold';
  return <span className={`allocation-action-pill allocation-action-${tone}`}>{ACTION_LABEL_VI[action] || action}</span>;
}

function HoldingRow({ decision }) {
  const reasons = (decision.reason_codes || []).slice(0, 3);
  let bandText = '—';
  if (decision.action === 'SELL') {
    bandText = '0.0%';
  } else if (decision.target_min != null && decision.target_mid != null) {
    bandText = `${formatWeight(decision.target_min)} – ${formatWeight(decision.target_max)}`;
  }
  return (
    <tr>
      <td className="allocation-symbol">{decision.symbol}</td>
      <td><ActionPill action={decision.action} /></td>
      <td data-sensitive>{formatWeight(decision.current_weight)}</td>
      <td data-sensitive>{bandText}</td>
      <td>{CONFIDENCE_LABEL_VI[decision.confidence] || decision.confidence}</td>
      <td className="allocation-reasons">
        {reasons.length ? reasons.map(code => (
          <span className="allocation-reason" key={code}>{reasonCodeVi(code)}</span>
        )) : <span className="muted">Không có lý do đặc biệt</span>}
      </td>
    </tr>
  );
}

function OpportunityCard({ opportunity, onViewValuation }) {
  const fit = opportunity.portfolio_fit || {};
  const sizing = opportunity.sizing || {};
  const reasons = (opportunity.reason_codes || []).slice(0, 3);
  const bandText = sizing.target_min != null
    ? `${formatWeight(sizing.target_min)} – ${formatWeight(sizing.target_max)}`
    : '—';
  return (
    <article className="allocation-opportunity-card">
      <div className="allocation-opportunity-head">
        <strong className="allocation-symbol">{opportunity.symbol}</strong>
        <span className="allocation-rank">Cơ hội #{opportunity.candidate_rank}</span>
      </div>
      <div className="allocation-opportunity-action">
        {opportunity.decision?.action ? <ActionPill action={opportunity.decision.action} /> : <ActionPill action="WATCH" />}
      </div>
      <div className="allocation-opportunity-body">
        <div className="allocation-opp-grid">
          <span>Phù hợp danh mục</span><strong>{FIT_LABEL_VI[fit.fit] || fit.fit}</strong>
          <span>Vị thế đề xuất</span><strong data-sensitive>{bandText}</strong>
          <span>Mức tin cậy</span><strong>{CONVICTION_LABEL_VI[sizing.conviction_tier] || sizing.conviction_tier}</strong>
          <span>Tương quan</span><strong data-sensitive>{fit.average_correlation_to_portfolio == null ? '—' : pct(fit.average_correlation_to_portfolio)}</strong>
        </div>
        <div className="allocation-reasons">
          {reasons.map(code => <span className="allocation-reason" key={code}>{reasonCodeVi(code)}</span>)}
        </div>
      </div>
      <div className="allocation-opportunity-foot">
        <button type="button" className="btn-secondary btn-small" onClick={() => onViewValuation(opportunity.symbol)}>Xem định giá</button>
      </div>
    </article>
  );
}

function RiskRow({ label, before, after, fmt }) {
  return (
    <tr>
      <td>{label}</td>
      <td data-sensitive>{fmt(before)}</td>
      <td data-sensitive>{fmt(after)}</td>
      <td data-sensitive>{fmt(after)}</td>
    </tr>
  );
}

export default function AllocationPage({ allocation: initialAllocation = null, locale = 'vi' }) {
  const [allocation, setAllocation] = useState(initialAllocation || null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [simSymbol, setSimSymbol] = useState('');
  const [simWeight, setSimWeight] = useState('');
  const [simResult, setSimResult] = useState(null);
  const [simError, setSimError] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  useEffect(() => {
    if (initialAllocation) {
      setAllocation(initialAllocation);
      setSimResult(null);
    }
  }, [initialAllocation]);

  const report = useMemo(() => allocation?.allocation || null, [allocation]);
  const holdings = report?.holdings || [];
  const opportunities = report?.opportunities || [];
  const risk = report?.risk_summary || {};

  const proposedChanges = useMemo(() => {
    const changes = [];
    for (const d of holdings) {
      if (d.action === 'REDUCE' || d.action === 'SELL') {
        changes.push({
          symbol: d.symbol,
          action: d.action,
          current_weight: d.current_weight,
          target: d.target_mid,
          reason: d.reason_codes?.length ? reasonCodeVi(d.reason_codes[0]) : ''
        });
      }
    }
    for (const opp of opportunities) {
      if (opp.decision?.action === 'BUY_MORE') {
        changes.push({
          symbol: opp.symbol,
          action: 'BUY_MORE',
          current_weight: 0,
          target: opp.decision.target_mid,
          reason: opp.reason_codes?.length ? reasonCodeVi(opp.reason_codes[0]) : ''
        });
      }
    }
    return changes;
  }, [holdings, opportunities]);

  function runSimulation(event) {
    event.preventDefault();
    const symbol = String(simSymbol || '').trim().toUpperCase();
    const weight = Number(simWeight);
    if (!symbol || !Number.isFinite(weight) || weight <= 0 || weight > 100) {
      setSimError('Nhập mã cổ phiếu và tỷ trọng mục tiêu từ 0 đến 100%.');
      return;
    }
    setSimLoading(true);
    setSimError(null);
    setSimResult(null);
    simulatePortfolioAllocation([{ symbol, target_weight: weight / 100 }])
      .then(res => setSimResult(res))
      .catch(err => setSimError(err.message || 'Không thể mô phỏng.'))
      .finally(() => setSimLoading(false));
  }

  const simAllocation = simResult?.allocation || null;
  const beforeRisk = simAllocation?.simulation?.risk_before || {};
  const afterRisk = simAllocation?.simulation?.risk_after || {};

  const fmtWeight = value => (value == null ? '—' : formatWeight(value));
  const fmtCorr = value => (value == null ? '—' : pct(value));

  if (!report) {
    return (
      <div className="page allocation-page">
        <AppNav active="allocation" locale={locale} />
        <main className="page-content allocation-content">
          <div className="allocation-empty">
            <h1>Phân bổ vốn</h1>
            <p className="muted">Đang chờ dữ liệu danh mục…</p>
          </div>
        </main>
      </div>
    );
  }

  const noAction = Boolean(report.no_action_required);
  const posture = report.posture || 'KEEP_CASH';

  return (
    <div className="page allocation-page">
      <AppNav active="allocation" locale={locale} />
      <main className="page-content allocation-content">
        <header className="allocation-header">
          <div>
            <div className="eyebrow">QPort · Phân bổ vốn</div>
            <h1>Phân bổ vốn</h1>
            <p className="muted">Khuyến nghị dài hạn theo triết lý Buffett Core + Thorp Overlay. Không tự động giao dịch.</p>
          </div>
          <a className="header-link" href="/transactions">Ghi giao dịch thực tế →</a>
        </header>

        {noAction && (
          <section className="allocation-no-action-hero" role="status">
            <div className="allocation-no-action-badge">✓</div>
            <div>
              <h2>KHÔNG CẦN HÀNH ĐỘNG</h2>
              <p>Danh mục hiện tại vẫn phù hợp. Chưa có cơ hội nào chứng minh là tốt hơn hẳn việc giữ nguyên và để thời gian phát huy.</p>
            </div>
          </section>
        )}

        <section className="allocation-section">
          <h2 className="allocation-section-title">1 · Nhận định danh mục</h2>
          <div className="allocation-verdict-grid">
            <MetricCard label="Tư thế danh mục" value={POSTURE_LABEL_VI[posture] || posture} note={VERDICT_LABEL_VI[report.verdict] || report.verdict} dataSensitive={false} />
            <MetricCard label="Tiền mặt hiện tại" value={formatWeight(report.cash_current)} note={`Khuyến nghị giữ ${formatWeight((report.cash_suggested_range || [0, 0])[0])} – ${formatWeight((report.cash_suggested_range || [0, 0])[1])}`} dataSensitive />
            <MetricCard label="Độ tin cậy" value={CONFIDENCE_LABEL_VI[report.confidence] || report.confidence} note="Dựa trên mức đủ dữ liệu định giá & rủi ro" dataSensitive={false} />
            <MetricCard label="Rủi ro danh mục (252D)" value={fmtWeight(risk.volatility_252)} note={`Tương quan TB ${fmtCorr(risk.average_correlation)}`} dataSensitive />
          </div>
        </section>

        <section className="allocation-section">
          <h2 className="allocation-section-title">2 · Vị thế hiện tại</h2>
          {holdings.length === 0 ? (
            <p className="muted">Danh mục chưa có cổ phiếu nào.</p>
          ) : (
            <div className="allocation-table-wrap">
              <table className="allocation-table">
                <thead>
                  <tr>
                    <th>Mã</th><th>Khuyến nghị</th><th>Tỷ trọng</th><th>Khoảng mục tiêu</th><th>Tin cậy</th><th>Lý do</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map(decision => <HoldingRow key={decision.symbol} decision={decision} />)}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="allocation-section">
          <h2 className="allocation-section-title">3 · Cơ hội mới (nghiên cứu)</h2>
          {opportunities.length === 0 ? (
            <div className="allocation-no-opportunities">
              <strong>Chưa có cơ hội vượt trội</strong>
              <p className="muted">Không có ứng viên nào từ bộ lọc vượt qua ngưỡng chất lượng + định giá + phù hợp danh mục. Giữ tiền mặt là lựa chọn hợp lệ.</p>
              <a className="btn-secondary btn-small" href="/screener">Mở bộ lọc cổ phiếu</a>
            </div>
          ) : (
            <div className="allocation-opportunity-grid">
              {opportunities.map(opp => (
                <OpportunityCard key={opp.symbol} opportunity={opp} onViewValuation={setSelectedSymbol} />
              ))}
            </div>
          )}
        </section>

        <section className="allocation-section">
          <h2 className="allocation-section-title">4 · Thay đổi đề xuất</h2>
          {proposedChanges.length === 0 ? (
            <div className="allocation-no-changes">
              <strong>{noAction ? 'Không cần hành động' : 'Không có thay đổi bắt buộc'}</strong>
              <p className="muted">Các khuyến nghị bên trên chỉ là thông tin. Mọi thay đổi danh mục đều do bạn ghi nhận giao dịch thực tế.</p>
            </div>
          ) : (
            <ul className="allocation-change-list">
              {proposedChanges.map(change => {
                let targetText = '';
                if (change.action === 'REDUCE') {
                  targetText = change.target != null
                    ? `${formatWeight(change.current_weight)} → ${formatWeight(change.target)}`
                    : '';
                } else if (change.action === 'SELL') {
                  targetText = `${formatWeight(change.current_weight)} → 0.0%`;
                } else if (change.action === 'BUY_MORE') {
                  targetText = change.target != null ? `→ ${formatWeight(change.target)}` : '';
                }
                return (
                  <li key={change.symbol}>
                    <strong>{change.symbol}</strong> <ActionPill action={change.action} />
                    {targetText ? <span data-sensitive>{targetText}</span> : null}
                    <span className="muted">{change.reason}</span>
                  </li>
                );
              })}
            </ul>
          )}

          <div className="allocation-handoff">
            <a className="btn-secondary btn-small" href="/transactions">Tạo bản nháp giao dịch</a>
            <a className="btn-secondary btn-small" href="/risk">Xem phân tích rủi ro</a>
          </div>
        </section>

        <section className="allocation-section">
          <h2 className="allocation-section-title">5 · Mô phỏng thay đổi (trước / sau rủi ro)</h2>
          <form className="allocation-sim-form" onSubmit={runSimulation}>
            <label>
              <span>Mã cổ phiếu</span>
              <input value={simSymbol} onChange={e => setSimSymbol(e.target.value)} placeholder="VD: VNM" />
            </label>
            <label>
              <span>Tỷ trọng mục tiêu (%)</span>
              <input type="number" min="0" max="100" step="0.5" value={simWeight} onChange={e => setSimWeight(e.target.value)} placeholder="VD: 8" />
            </label>
            <button type="submit" className="btn-primary" disabled={simLoading}>{simLoading ? 'Đang mô phỏng…' : 'Mô phỏng'}</button>
          </form>
          {simError && <p className="error">{simError}</p>}
          {simAllocation && (
            <div className="allocation-sim-result">
              <p className="muted">Chỉ mô phỏng trong bộ nhớ — không lưu giao dịch.</p>
              <div className="allocation-table-wrap">
                <table className="allocation-table">
                  <thead><tr><th>Chỉ số rủi ro</th><th>Trước</th><th>Sau</th></tr></thead>
                  <tbody>
                    <RiskRow label="Biến động 252D" before={beforeRisk.volatility_252} after={afterRisk.volatility_252} fmt={fmtWeight} />
                    <RiskRow label="Tương quan trung bình" before={beforeRisk.average_correlation} after={afterRisk.average_correlation} fmt={fmtCorr} />
                    <RiskRow label="Tỷ lệ đa dạng hóa" before={beforeRisk.diversification_ratio} after={afterRisk.diversification_ratio} fmt={v => (v == null ? '—' : v.toFixed(2))} />
                    <RiskRow label="Vị thế hiệu quả" before={beforeRisk.effective_positions} after={afterRisk.effective_positions} fmt={v => (v == null ? '—' : v.toFixed(1))} />
                    <RiskRow label="VaR 95% (ngày)" before={beforeRisk.daily_var_95} after={afterRisk.daily_var_95} fmt={v => (v == null ? '—' : pct(v))} />
                  </tbody>
                </table>
              </div>
              {simAllocation.no_action_required && (
                <div className="allocation-sim-note">Kết quả: <strong>Không cần hành động</strong> — thay đổi đề xuất không tốt hơn rõ rệt.</div>
              )}
            </div>
          )}
        </section>

        <section className="allocation-section">
          <h2 className="allocation-section-title">6 · Bằng chứng & chất lượng dữ liệu</h2>
          <div className="allocation-evidence">
            <div>
              <h3>Lý do khuyến nghị</h3>
              <ul className="allocation-evidence-list">
                {(report.reason_codes || []).map(code => <li key={code}>{reasonCodeVi(code)}</li>)}
              </ul>
            </div>
            <div>
              <h3>Chất lượng dữ liệu</h3>
              <ul className="allocation-evidence-list">
                <li>Định giá: {report.data_quality?.valuation_coverage?.holdings_with_signal ?? 0}/{report.data_quality?.valuation_coverage?.holdings_total ?? 0} mã có tín hiệu</li>
                <li>Rủi ro: {report.data_quality?.risk_status || 'Chưa xác định'}{report.data_quality?.risk_coverage != null ? ` (độ phủ ${pct(report.data_quality.risk_coverage)})` : ''}</li>
                <li>Mã thiếu định giá: {(report.data_quality?.valuation_coverage?.missing_valuation_symbols || []).join(', ') || 'Không có'}</li>
              </ul>
            </div>
          </div>
        </section>
      </main>

      {selectedSymbol && (
        <ValuationDetailOverlay
          symbol={selectedSymbol}
          locale={locale}
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </div>
  );
}
