import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import MetricCard from '../components/MetricCard.jsx';
import ValuationDetailOverlay from '../components/ValuationDetailOverlay.jsx';
import { simulatePortfolioAllocation } from '../lib/api.js';
import { formatWeight, pct } from '../lib/format.js';
import {
  ACTION_LABEL_VI,
  ACTION_TONE,
  ALLOCATION_TOOLTIPS_VI,
  CONFIDENCE_LABEL_VI,
  CONVICTION_LABEL_VI,
  CURRENT_WEIGHT_LABEL_VI,
  FIT_LABEL_VI,
  NEW_POSITION_GUIDANCE_LABEL_VI,
  POSTURE_LABEL_VI,
  POST_ACTION_WEIGHT_LABEL_VI,
  reasonCodeVi,
} from '../lib/allocationLabels.js';
import '../valuation-page.css';
import '../allocation-page.css';

const VERDICT_LABEL_VI = {
  NO_ACTION_REQUIRED: 'Không cần hành động',
  SELECTIVE_ACTION: 'Hành động chọn lọc',
};

function ActionPill({ action }) {
  const tone = ACTION_TONE[action] || 'hold';
  return <span className={`allocation-action-pill allocation-action-${tone}`}>{ACTION_LABEL_VI[action] || action}</span>;
}

function HoldingRow({ decision }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const reasons = (decision.reason_codes || []).slice(0, 3);
  const currentWeight = decision.current_weight || 0;
  
  let postText = '—';
  if (decision.action === 'SELL') {
    postText = '0.0%';
  } else if (decision.action === 'HOLD') {
    postText = formatWeight(currentWeight);
  } else if (decision.post_action_target_weight != null) {
    postText = (decision.action === 'REDUCE' ? '~' : '') + formatWeight(decision.post_action_target_weight);
  } else if (decision.target_mid != null) {
    postText = (decision.action === 'REDUCE' ? '~' : '') + formatWeight(decision.target_mid);
  }

  const guidance = decision.new_position_guidance;
  const newBandText = guidance?.min_weight != null && guidance?.max_weight != null
    ? `${formatWeight(guidance.min_weight)} – ${formatWeight(guidance.max_weight)}`
    : (decision.target_min != null && decision.target_max != null ? `${formatWeight(decision.target_min)} – ${formatWeight(decision.target_max)}` : '3–5%');

  return (
    <React.Fragment>
      <tr className={isExpanded ? 'allocation-row-expanded' : ''}>
        <td className="allocation-symbol">
          <button
            type="button"
            className="allocation-symbol-toggle-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title="Bấm để xem/ẩn mức vốn gợi ý khi mở vị thế mới"
          >
            <strong>{decision.symbol}</strong> {isExpanded ? '▲' : '▼'}
          </button>
        </td>
        <td data-sensitive>{formatWeight(currentWeight)}</td>
        <td><ActionPill action={decision.action} /></td>
        <td data-sensitive><strong>{postText}</strong></td>
        <td>{CONFIDENCE_LABEL_VI[decision.confidence] || decision.confidence}</td>
        <td className="allocation-reasons">
          {reasons.length ? reasons.map(code => (
            <span className="allocation-reason" key={code}>{reasonCodeVi(code)}</span>
          )) : <span className="muted">Không có lý do đặc biệt</span>}
        </td>
      </tr>
      {isExpanded && (
        <tr className="allocation-detail-row">
          <td colSpan={6}>
            <div className="allocation-detail-box">
              <div className="allocation-guidance-inline">
                <strong>{NEW_POSITION_GUIDANCE_LABEL_VI}:</strong>{' '}
                <span className="allocation-guidance-badge">{newBandText}</span>
                {guidance?.tier && (
                  <span className="muted font-small"> ({CONVICTION_LABEL_VI[guidance.tier] || guidance.tier})</span>
                )}
                <p className="allocation-guidance-help">
                  Đây là mức sizing tham khảo nếu xây vị thế mới từ đầu theo điều kiện hiện tại. Không phải mục tiêu bắt buộc cho vị thế đang nắm giữ.
                </p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </React.Fragment>
  );
}

function OpportunityCard({ opportunity, onViewValuation }) {
  const fit = opportunity.portfolio_fit || {};
  const sizing = opportunity.sizing || {};
  const evidence = opportunity.selection_evidence || {};
  const reasons = (opportunity.reason_codes || []).slice(0, 3);
  const guidanceText = sizing.target_min != null
    ? `${formatWeight(sizing.target_min)} – ${formatWeight(sizing.target_max)}`
    : '—';
  const plan = opportunity.decision?.execution_plan;
  const showQtyPlan = plan && plan.is_executable && plan.rounded_quantity_change > 0;
  const grossVnd = plan?.gross_trade_value_vnd || plan?.gross_trade_value || 0;
  const cashAfterVnd = plan?.cash_after_vnd || plan?.cash_after || 0;
  const postTradeWeightText = plan?.post_trade_weight != null
    ? formatWeight(plan.post_trade_weight)
    : (opportunity.decision?.post_action_target_weight != null ? formatWeight(opportunity.decision.post_action_target_weight) : guidanceText);

  return (
    <article className="allocation-opportunity-card allocation-card-buy-ready">
      <div className="allocation-opportunity-head">
        <strong className="allocation-symbol">{opportunity.symbol}</strong>
        <span className="allocation-rank">Cơ hội MUA #{opportunity.candidate_rank}</span>
      </div>
      <div className="allocation-opportunity-action">
        <ActionPill action={opportunity.decision?.action || 'BUY_MORE'} />
        {showQtyPlan && (
          <span className="allocation-qty-badge">
            MUA {plan.rounded_quantity_change.toLocaleString('vi-VN')} CP (Lô {plan.lot_size})
          </span>
        )}
      </div>
      <div className="allocation-opportunity-body">
        <div className="allocation-opp-grid">
          <span>Phù hợp danh mục</span><strong>{FIT_LABEL_VI[fit.fit] || fit.fit}</strong>
          <span>Tỷ trọng sau đề xuất</span><strong data-sensitive>{postTradeWeightText}</strong>
          <span>Gợi ý mở vị thế mới</span><strong data-sensitive>{guidanceText}</strong>
          <span>Tương quan</span><strong data-sensitive>{fit.average_correlation_to_portfolio == null ? '—' : pct(fit.average_correlation_to_portfolio)}</strong>
        </div>

        {showQtyPlan && (
          <div className="allocation-opp-trade-summary" data-sensitive>
            <div><strong>Giá trị mua đề xuất:</strong> ~{(grossVnd / 1e6).toFixed(1)} triệu VND</div>
            <div><strong>Tỷ trọng sau mua:</strong> {formatWeight(plan.post_trade_weight)} | <strong>Cash còn lại:</strong> ~{(cashAfterVnd / 1e6).toFixed(1)}M VND</div>
          </div>
        )}

        {evidence.why_selected?.length > 0 && (
          <div className="allocation-why-selected">
            <div className="allocation-why-title">Vì sao đủ điều kiện MUA?</div>
            <ul className="allocation-why-list">
              {evidence.why_selected.map((item, i) => (
                <li key={i}>✓ {item}</li>
              ))}
            </ul>
          </div>
        )}

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

function WatchlistCard({ opportunity, onViewValuation }) {
  const fit = opportunity.portfolio_fit || {};
  const evidence = opportunity.selection_evidence || {};
  const reasons = (opportunity.reason_codes || []).slice(0, 3);
  const maxPrice = opportunity.max_qualifying_price || evidence.max_qualifying_price;

  return (
    <article className="allocation-opportunity-card allocation-card-watchlist">
      <div className="allocation-opportunity-head">
        <strong className="allocation-symbol">{opportunity.symbol}</strong>
        <span className="allocation-rank">Theo dõi #{opportunity.candidate_rank}</span>
      </div>
      <div className="allocation-opportunity-action">
        <ActionPill action="WATCH" />
      </div>
      <div className="allocation-opportunity-body">
        <div className="allocation-opp-grid">
          <span>Chất lượng</span><strong>{opportunity.eligibility.quality_tier || 'WATCH'}</strong>
          <span>MOS hiện tại</span><strong data-sensitive>{opportunity.eligibility.actual_mos_pct != null ? `${opportunity.eligibility.actual_mos_pct.toFixed(1)}%` : '—'}</strong>
          <span>MOS yêu cầu</span><strong data-sensitive>{opportunity.eligibility.required_mos_pct != null ? `${opportunity.eligibility.required_mos_pct.toFixed(1)}%` : '—'}</strong>
          <span>Phù hợp danh mục</span><strong>{FIT_LABEL_VI[fit.fit] || fit.fit}</strong>
        </div>

        {evidence.missing_explanations?.length > 0 && (
          <div className="allocation-missing-gates">
            <div className="allocation-why-title allocation-missing-title">Yếu tố chưa đạt chuẩn MUA:</div>
            <ul className="allocation-why-list allocation-missing-list">
              {evidence.missing_explanations.map((item, i) => (
                <li key={i}>✕ {item}</li>
              ))}
            </ul>
          </div>
        )}

        {maxPrice != null && (
          <div className="allocation-target-price-hint">
            <span>Giá tối đa để đạt MOS yêu cầu:</span>
            <strong data-sensitive> ~{maxPrice.toLocaleString('vi-VN')} VND</strong>
          </div>
        )}

        {evidence.why_selected?.length > 0 && (
          <div className="allocation-why-selected">
            <div className="allocation-why-title">Điểm tích cực:</div>
            <ul className="allocation-why-list">
              {evidence.why_selected.slice(0, 2).map((item, i) => (
                <li key={i}>✓ {item}</li>
              ))}
            </ul>
          </div>
        )}

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
    </tr>
  );
}

export default function AllocationPage({ allocation: initialAllocation = null, locale = 'vi' }) {
  const [allocation, setAllocation] = useState(initialAllocation || null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [showRejected, setShowRejected] = useState(false);
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
  const watchlist = report?.watchlist || [];
  const rejected = report?.rejected || [];
  const risk = report?.risk_summary || {};

  const buyReadyCount = report?.buy_ready_count ?? opportunities.length;
  const watchlistCount = report?.watchlist_count ?? watchlist.length;
  const rejectedCount = report?.rejected_count ?? rejected.length;
  const universeCount = report?.universe_count ?? (buyReadyCount + watchlistCount + rejectedCount);

  const proposedChanges = useMemo(() => {
    const changes = [];
    for (const d of holdings) {
      if (d.action === 'REDUCE' || d.action === 'SELL') {
        changes.push({
          symbol: d.symbol,
          action: d.action,
          current_weight: d.current_weight,
          target: d.target_mid,
          decision: d,
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
          decision: opp.decision,
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
            <div className="allocation-universe-summary">
              <strong>Vũ trụ nghiên cứu ({universeCount} mã):</strong> Đủ điều kiện mua: <span>{buyReadyCount}</span> · Theo dõi: <span>{watchlistCount}</span> · Bị loại: <span>{rejectedCount}</span>
            </div>
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
                    <th>Mã</th>
                    <th title={ALLOCATION_TOOLTIPS_VI.CURRENT_WEIGHT}>Tỷ trọng hiện tại ⓘ</th>
                    <th>Khuyến nghị</th>
                    <th title={ALLOCATION_TOOLTIPS_VI.POST_ACTION_WEIGHT}>Tỷ trọng sau đề xuất ⓘ</th>
                    <th>Tin cậy</th>
                    <th>Lý do</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map(decision => <HoldingRow key={decision.symbol} decision={decision} />)}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Candidate Tiers */}
        <section className="allocation-section">
          <h2 className="allocation-section-title">
            3 · Cơ hội đủ điều kiện MUA
            <span className="allocation-badge-count allocation-count-buy">{buyReadyCount}</span>
          </h2>
          {opportunities.length === 0 ? (
            <div className="allocation-no-opportunities">
              <strong>Chưa có ứng viên đạt chuẩn MUA</strong>
              <p className="muted">Không có ứng viên nào vượt qua đồng thời tất cả các ngưỡng Chất lượng + Biên an toàn (MOS) + Thanh khoản + Phù hợp danh mục. Tiêu chuẩn MUA không bị hạ thấp. Giữ tiền mặt là hợp lệ.</p>
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
          <h2 className="allocation-section-title">
            4 · Gần đạt / Cần theo dõi (Watchlist)
            <span className="allocation-badge-count allocation-count-watch">{watchlistCount}</span>
          </h2>
          {watchlist.length === 0 ? (
            <p className="muted">Không có mã nào thuộc nhóm theo dõi.</p>
          ) : (
            <div className="allocation-opportunity-grid">
              {watchlist.map(opp => (
                <WatchlistCard key={opp.symbol} opportunity={opp} onViewValuation={setSelectedSymbol} />
              ))}
            </div>
          )}
        </section>

        {rejected.length > 0 && (
          <section className="allocation-section">
            <h2 className="allocation-section-title">
              5 · Danh sách bị loại
              <span className="allocation-badge-count allocation-count-rejected">{rejectedCount}</span>
            </h2>
            <div className="allocation-rejected-box">
              <button
                type="button"
                className="btn-secondary btn-small"
                onClick={() => setShowRejected(!showRejected)}
              >
                {showRejected ? 'Ẩn danh sách bị loại ▲' : `Xem ${rejectedCount} mã bị loại (vi phạm loại trừ cứng / chất lượng thấp) ▼`}
              </button>
              {showRejected && (
                <div className="allocation-table-wrap allocation-rejected-table">
                  <table className="allocation-table">
                    <thead>
                      <tr>
                        <th>Mã</th><th>Tầng chất lượng</th><th>Lý do bị loại</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rejected.map(cand => {
                        const rejects = cand.eligibility.hard_rejects?.length
                          ? cand.eligibility.hard_rejects.join(', ')
                          : (cand.failed_gates?.join(', ') || 'QUALITY_LOW');
                        return (
                          <tr key={cand.symbol}>
                            <td className="allocation-symbol">{cand.symbol}</td>
                            <td>{cand.eligibility.quality_tier || 'LOW_QUALITY'}</td>
                            <td className="error">{rejects}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}

        <section className="allocation-section">
          <h2 className="allocation-section-title">6 · Thay đổi đề xuất</h2>
          {proposedChanges.length === 0 ? (
            <div className="allocation-no-changes">
              <strong>{noAction ? 'Không cần hành động' : 'Không có thay đổi bắt buộc'}</strong>
              <p className="muted">Các khuyến nghị bên trên chỉ là thông tin. Mọi thay đổi danh mục đều do bạn ghi nhận giao dịch thực tế.</p>
            </div>
          ) : (
            <ul className="allocation-change-list">
              {proposedChanges.map(change => {
                const plan = change.decision?.execution_plan || {};
                const hasPlan = Boolean(plan.is_executable && plan.rounded_quantity_change);
                const qtyAbs = Math.abs(plan.rounded_quantity_change || 0);

                let labelText = '';
                if (change.action === 'REDUCE') labelText = `GIẢM ${qtyAbs.toLocaleString('vi-VN')} CP`;
                else if (change.action === 'SELL') labelText = `BÁN TOÀN BỘ ${qtyAbs.toLocaleString('vi-VN')} CP`;
                else if (change.action === 'BUY_MORE') labelText = `MUA THÊM ${qtyAbs.toLocaleString('vi-VN')} CP`;

                let targetText = '';
                if (change.action === 'REDUCE') {
                  targetText = change.target != null
                    ? `${formatWeight(change.current_weight)} → ${formatWeight(plan.post_trade_weight || change.target)}`
                    : '';
                } else if (change.action === 'SELL') {
                  targetText = `${formatWeight(change.current_weight)} → 0.0%`;
                } else if (change.action === 'BUY_MORE') {
                  targetText = change.target != null ? `→ ${formatWeight(plan.post_trade_weight || change.target)}` : '';
                }
                const grossVnd = plan.gross_trade_value_vnd || plan.gross_trade_value || 0;
                const costVnd = plan.estimated_total_cost_vnd || plan.estimated_total_cost || 0;
                const cashAfterVnd = plan.cash_after_vnd || plan.cash_after || 0;

                return (
                  <li key={change.symbol} className="allocation-change-item">
                    <div className="allocation-change-main">
                      <strong>{change.symbol}</strong> <ActionPill action={change.action} />
                      {labelText ? <span className="allocation-qty-badge">{labelText}</span> : null}
                      {targetText ? <span data-sensitive className="allocation-target-weight">{targetText}</span> : null}
                    </div>
                    {hasPlan && (
                      <div className="allocation-plan-details">
                        <span>Giá tham chiếu: <strong data-sensitive>{plan.reference_price ? `${plan.reference_price.toLocaleString('vi-VN')} VND` : '—'}</strong></span>
                        <span>Giá trị giao dịch: <strong data-sensitive>{grossVnd ? `~${(grossVnd / 1e6).toFixed(1)} triệu VND` : '—'}</strong></span>
                        <span>Chi phí ước tính: <strong data-sensitive>{costVnd.toLocaleString('vi-VN')} VND</strong></span>
                        <span>Tiền mặt sau giao dịch: <strong data-sensitive>~{(cashAfterVnd / 1e6).toFixed(1)} triệu VND</strong></span>
                        <span>Số lượng & Tỷ trọng sau: <strong data-sensitive>{(plan.post_trade_quantity || 0).toLocaleString('vi-VN')} CP ({formatWeight(plan.post_trade_weight)})</strong></span>
                      </div>
                    )}
                    <span className="muted allocation-change-reason">{change.reason}</span>
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
          <h2 className="allocation-section-title">7 · Mô phỏng thay đổi (trước / sau rủi ro)</h2>
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
          <h2 className="allocation-section-title">8 · Bằng chứng & chất lượng dữ liệu</h2>
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
