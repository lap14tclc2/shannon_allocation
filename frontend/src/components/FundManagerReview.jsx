import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { formatMoney } from '../lib/format.js';

function finite(value) {
  const n = Number(value);
  return value == null || !Number.isFinite(n) ? null : n;
}

function pct(value, digits = 1) {
  const n = finite(value);
  return n == null ? '-' : `${(n * 100).toFixed(digits)}%`;
}

function Pill({ tone = 'neutral', children }) {
  return <span className={`fm-pill fm-pill-${tone}`}>{children}</span>;
}

export default function FundManagerReview({ dashboard = {}, locale = 'en' }) {
  const [target, setTarget] = useState(null);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = value => {
    const n = finite(value);
    return n == null ? '-' : `${formatMoney(n, false, locale)} VND`;
  };

  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const risk = dashboard.risk || {};
  const perf = dashboard.performance_summary || {};
  const market = dashboard.market_data || {};
  const health = dashboard.health || {};

  useEffect(() => {
    if (typeof document !== 'undefined') setTarget(document.querySelector('.page'));
  }, []);

  const review = useMemo(() => {
    const sorted = [...positions].sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0));
    const top = sorted[0] || null;
    const largestWeight = finite(top?.weight) ?? 0;
    const topTwoWeight = sorted.slice(0, 2).reduce((sum, row) => sum + Number(row.weight || 0), 0);
    const cashWeight = finite(portfolio.nav) && Number(portfolio.nav) > 0
      ? Number(portfolio.cash || 0) / Number(portfolio.nav)
      : 0;
    const coverage = finite(risk.quality?.coverage_weight) ?? 0;
    const observations = Number(risk.return_observations || 0);
    const snapshots = Number(perf.official_snapshot_count || 0);
    const riskReady = coverage >= 0.90 && observations >= 20;
    const performanceReady = snapshots >= 20;
    const largestRiskContribution = finite(risk.largest_risk_contribution);
    const currentDrawdown = finite(perf.current_drawdown);
    const totalPnl = finite(portfolio.total_pnl);
    const accountingReturn = finite(portfolio.accounting_return);
    const twr = finite(perf.returns?.since_inception);
    const dividendIncome = finite(perf.dividend_income ?? portfolio.dividend_income) ?? 0;
    const warnings = (health.flags || []).filter(flag => flag.level === 'WARNING');

    const concentrationWatch = largestWeight >= 0.40 || topTwoWeight >= 0.75;
    const riskDriverWatch = riskReady && largestRiskContribution != null && largestRiskContribution > 0.45;
    const drawdownWatch = performanceReady && currentDrawdown != null && currentDrawdown <= -0.15;

    let state = text('STABLE', 'ỔN ĐỊNH');
    let tone = 'valid';
    if (!riskReady || !performanceReady) {
      state = text('EVIDENCE BUILDING', 'DỮ LIỆU ĐANG XÂY DỰNG');
      tone = 'building';
    } else if (concentrationWatch || riskDriverWatch || drawdownWatch || warnings.length) {
      state = text('REVIEW', 'CẦN THEO DÕI');
      tone = 'warning';
    }

    let headline;
    if (!riskReady) {
      headline = text(
        'The portfolio structure is clear, but market-risk evidence is still maturing. Avoid strong risk conclusions until D1 history is complete.',
        'Cấu trúc danh mục đã rõ, nhưng bằng chứng rủi ro thị trường vẫn đang hoàn thiện. Chưa nên đưa ra kết luận mạnh về risk trước khi lịch sử D1 đủ.'
      );
    } else if (drawdownWatch) {
      headline = text(
        'The portfolio is in a meaningful drawdown. The priority is to verify whether the investment theses remain intact, not to react mechanically to price.',
        'Danh mục đang ở mức drawdown đáng kể. Ưu tiên là kiểm tra investment thesis còn nguyên vẹn hay không, không phản ứng máy móc theo giá.'
      );
    } else if (concentrationWatch) {
      headline = text(
        'Conviction is concentrated. That can be acceptable in a long-term portfolio, but the largest positions now have an outsized influence on outcomes.',
        'Mức conviction đang tập trung. Điều này có thể chấp nhận được với danh mục dài hạn, nhưng các vị thế lớn nhất đang ảnh hưởng mạnh đến kết quả chung.'
      );
    } else if (riskDriverWatch) {
      headline = text(
        `${risk.largest_risk_symbol || 'One holding'} is carrying a disproportionate share of modeled portfolio risk. The exposure deserves thesis-level review.`,
        `${risk.largest_risk_symbol || 'Một mã'} đang gánh tỷ trọng modeled risk lớn hơn đáng kể so với phần còn lại. Exposure này nên được review ở cấp investment thesis.`
      );
    } else {
      headline = text(
        'The portfolio is broadly stable. The best course is disciplined monitoring: keep the book accurate and review thesis changes rather than daily noise.',
        'Danh mục nhìn chung đang ổn định. Cách quản lý phù hợp là theo dõi có kỷ luật: giữ sổ chính xác và review thay đổi thesis thay vì nhiễu giá hàng ngày.'
      );
    }

    const construction = concentrationWatch
      ? text(
          `${String(top?.symbol || '').toUpperCase()} is the largest holding at ${pct(largestWeight)}, while the two largest positions represent ${pct(topTwoWeight)} of NAV. This is a focused portfolio, so mistakes in the largest businesses matter more than ticker count suggests.`,
          `${String(top?.symbol || '').toUpperCase()} là vị thế lớn nhất với ${pct(largestWeight)}, còn hai vị thế lớn nhất chiếm ${pct(topTwoWeight)} NAV. Đây là danh mục tập trung, vì vậy sai lệch ở các doanh nghiệp lớn nhất sẽ ảnh hưởng nhiều hơn so với việc chỉ nhìn số lượng mã.`
        )
      : text(
          `Capital is reasonably distributed across ${positions.length} holdings. The largest position is ${String(top?.symbol || '').toUpperCase()} at ${pct(largestWeight)}. I would preserve this balance unless the underlying business thesis changes materially.`,
          `Vốn đang được phân bổ tương đối hợp lý trên ${positions.length} mã. Vị thế lớn nhất là ${String(top?.symbol || '').toUpperCase()} với ${pct(largestWeight)}. Tôi sẽ duy trì sự cân bằng này trừ khi thesis doanh nghiệp thay đổi đáng kể.`
        );

    const resilience = !riskReady
      ? text(
          `Risk confidence is still building (${pct(coverage)} coverage). Let QPort finish D1 backfill before treating detailed volatility, co-movement or bad-day estimates as reliable evidence.`,
          `Độ tin cậy của Risk vẫn đang xây dựng (${pct(coverage)} độ phủ). Hãy để QPort hoàn tất backfill D1 trước khi coi volatility, co-movement hoặc bad-day estimate chi tiết là bằng chứng đáng tin cậy.`
        )
      : riskDriverWatch
        ? text(
            `${risk.largest_risk_symbol || '-'} currently contributes about ${pct(largestRiskContribution)} of modeled portfolio risk. I would verify that this concentration is intentional and still supported by conviction and business resilience.`,
            `${risk.largest_risk_symbol || '-'} hiện đóng góp khoảng ${pct(largestRiskContribution)} modeled risk của danh mục. Tôi sẽ kiểm tra mức tập trung này có chủ đích và vẫn được hỗ trợ bởi conviction cùng khả năng chống chịu của doanh nghiệp hay không.`
          )
        : text(
            'Risk is not currently dominated by a single modeled contributor. I would continue watching whether holdings begin moving together more strongly during market stress and whether the risk regime changes materially.',
            'Risk hiện chưa bị một mã duy nhất chi phối rõ rệt. Tôi sẽ tiếp tục theo dõi liệu các mã có bắt đầu biến động cùng nhau mạnh hơn khi thị trường stress và liệu risk regime có thay đổi đáng kể hay không.'
          );

    const performance = !performanceReady
      ? text(
          `Tracked performance is still young with ${snapshots} official snapshots. Accounting P/L is ${money(totalPnl)}${accountingReturn != null ? ` (${pct(accountingReturn)})` : ''}, but I would not judge portfolio quality from short TWR history yet.`,
          `Lịch sử performance còn trẻ với ${snapshots} snapshot chính thức. Accounting P/L hiện là ${money(totalPnl)}${accountingReturn != null ? ` (${pct(accountingReturn)})` : ''}, nhưng chưa nên đánh giá chất lượng danh mục từ lịch sử TWR ngắn.`
        )
      : text(
          `Since tracking began, TWR is ${pct(twr)} and current drawdown is ${pct(currentDrawdown)}. Dividend income recorded is ${money(dividendIncome)}. I would judge return consistency, drawdown behaviour and business fundamentals together—not return alone.`,
          `Từ khi bắt đầu tracking, TWR là ${pct(twr)} và drawdown hiện tại là ${pct(currentDrawdown)}. Cổ tức đã ghi nhận là ${money(dividendIncome)}. Tôi sẽ đánh giá tính ổn định của return, hành vi drawdown và nền tảng doanh nghiệp cùng lúc—không chỉ nhìn return.`
        );

    const priorities = [];
    if (!riskReady) priorities.push(text('Let D1 history finish building before relying on advanced risk conclusions.', 'Để lịch sử D1 hoàn thiện trước khi dựa vào các kết luận risk nâng cao.'));
    if (!performanceReady) priorities.push(text('Let actual performance accumulate naturally; do not backfill portfolio performance before it was truly tracked.', 'Để performance thực tế tích lũy tự nhiên; không backfill performance về trước thời điểm danh mục thực sự được tracking.'));
    if (concentrationWatch) priorities.push(text('Revisit the thesis of the largest two holdings periodically because they drive most portfolio outcomes.', 'Review định kỳ thesis của hai vị thế lớn nhất vì chúng quyết định phần lớn kết quả danh mục.'));
    if (riskDriverWatch) priorities.push(text(`Understand why ${risk.largest_risk_symbol || 'the leading holding'} dominates modeled risk and whether that exposure is intentional.`, `Hiểu rõ vì sao ${risk.largest_risk_symbol || 'mã dẫn đầu'} chi phối modeled risk và mức exposure đó có chủ đích hay không.`));
    if (drawdownWatch) priorities.push(text('Review drawdown drivers and thesis integrity; do not turn drawdown into an automatic sell rule.', 'Review nguyên nhân drawdown và tính toàn vẹn của thesis; không biến drawdown thành rule bán tự động.'));
    if (cashWeight <= 0.01) priorities.push(text('The portfolio is almost fully invested; keep future cash needs, taxes and corporate actions in mind.', 'Danh mục gần như fully invested; lưu ý nhu cầu tiền mặt tương lai, thuế và corporate actions.'));
    if (warnings.length) priorities.push(text('Resolve visible data-quality warnings before treating the review as fully reliable.', 'Xử lý các cảnh báo chất lượng dữ liệu trước khi coi review là hoàn toàn đáng tin cậy.'));
    if (!priorities.length) priorities.push(text('Maintain data freshness and review company theses periodically; no portfolio-level issue currently needs escalation.', 'Duy trì độ mới dữ liệu và review thesis doanh nghiệp định kỳ; hiện chưa có vấn đề cấp danh mục cần escalation.'));

    return { state, tone, headline, construction, resilience, performance, priorities };
  }, [positions, portfolio, risk, perf, health, locale]);

  if (!target || !positions.length) return null;

  return createPortal(
    <section className="card fund-manager-review-card" data-testid="fund-manager-review">
      <div className="section-head fm-review-head">
        <div>
          <div className="eyebrow">{text('Experienced portfolio-manager view', 'Góc nhìn của nhà quản lý danh mục kinh nghiệm')}</div>
          <h2>{text('Fund manager review', 'Nhận xét của nhà quản lý quỹ')}</h2>
          <p className="muted">{text(
            'A concise judgment based on evidence already in QPort. Detailed quantitative diagnostics belong on the Risk page.',
            'Đánh giá cô đọng dựa trên bằng chứng đã có trong QPort. Các chẩn đoán định lượng chi tiết được để ở trang Risk.'
          )}</p>
        </div>
        <div className="fm-review-state">
          <Pill tone={review.tone}>{review.state}</Pill>
          <span className="muted">{dashboard.today || market.market_date || '-'}</span>
        </div>
      </div>

      <div className="fm-manager-verdict">
        <span>{text('Manager view', 'Đánh giá chính')}</span>
        <strong>{review.headline}</strong>
      </div>

      <div className="fm-manager-lenses">
        <section>
          <h3>{text('Portfolio construction', 'Cấu trúc danh mục')}</h3>
          <p>{review.construction}</p>
        </section>
        <section>
          <h3>{text('Risk & resilience', 'Rủi ro & khả năng chống chịu')}</h3>
          <p>{review.resilience}</p>
          <a className="text-link" href="/risk">{text('See detailed risk analysis →', 'Xem phân tích Risk chi tiết →')}</a>
        </section>
        <section>
          <h3>{text('Performance & income', 'Hiệu suất & thu nhập')}</h3>
          <p>{review.performance}</p>
          <a className="text-link" href="/performance">{text('See performance history →', 'Xem lịch sử Performance →')}</a>
        </section>
      </div>

      <div className="fm-priorities">
        <h3>{text('What I would watch next', 'Tôi sẽ theo dõi điều gì tiếp theo')}</h3>
        <ol>{review.priorities.slice(0, 4).map((item, index) => <li key={index}>{item}</li>)}</ol>
      </div>

      <div className="section-foot fm-review-foot">
        <span className="muted">{text(
          'Portfolio oversight only. This does not create allocation or trading instructions.',
          'Chỉ là góc nhìn giám sát danh mục. Phần này không tạo chỉ dẫn phân bổ hay giao dịch.'
        )}</span>
      </div>
    </section>,
    target,
  );
}
