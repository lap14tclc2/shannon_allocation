import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';

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
    const coverage = finite(risk.quality?.coverage_weight) ?? 0;
    const returnObs = Number(risk.return_observations || 0);
    const snapshots = Number(perf.official_snapshot_count || 0);
    const riskReady = coverage >= 0.90 && returnObs >= 20;
    const performanceReady = snapshots >= 20;
    const currentDrawdown = finite(perf.current_drawdown);
    const twr = finite(perf.returns?.since_inception);
    const largestRiskContribution = finite(risk.largest_risk_contribution);
    const volatilityRatio = finite(risk.volatility_ratio);
    const cashWeight = finite(portfolio.nav) && Number(portfolio.nav) > 0
      ? Number(portfolio.cash || 0) / Number(portfolio.nav)
      : 0;
    const warnings = (health.flags || []).filter(flag => flag.level === 'WARNING');

    const concentrated = largestWeight >= 0.40 || topTwoWeight >= 0.75;
    const moderatelyConcentrated = !concentrated && (largestWeight >= 0.30 || topTwoWeight >= 0.65);
    const dominantRiskDriver = riskReady && largestRiskContribution != null && largestRiskContribution > 0.45;
    const volatilityRising = riskReady && volatilityRatio != null && volatilityRatio > 1.20;
    const meaningfulDrawdown = performanceReady && currentDrawdown != null && currentDrawdown <= -0.15;

    let state = text('STABLE', 'ỔN ĐỊNH');
    let tone = 'valid';
    if (!riskReady || !performanceReady) {
      state = text('EVIDENCE BUILDING', 'DỮ LIỆU ĐANG XÂY');
      tone = 'building';
    } else if (concentrated || dominantRiskDriver || volatilityRising || meaningfulDrawdown || warnings.length) {
      state = text('WATCH', 'CẦN THEO DÕI');
      tone = 'warning';
    }

    const constructionLabel = concentrated
      ? text('Concentrated', 'Tập trung cao')
      : moderatelyConcentrated
        ? text('Moderately concentrated', 'Tập trung vừa')
        : text('Balanced enough', 'Khá cân bằng');

    const assessment = [];

    if (top) {
      if (concentrated) {
        assessment.push(text(
          `The portfolio is conviction-heavy rather than broadly diversified. ${String(top.symbol || '').toUpperCase()} is the largest holding at ${pct(largestWeight)}, and the two largest positions account for ${pct(topTwoWeight)} of NAV. That structure can work in a long-term portfolio, but only while the investment theses behind the largest positions remain intact.`,
          `Danh mục mang tính tập trung theo conviction hơn là đa dạng hóa rộng. ${String(top.symbol || '').toUpperCase()} là vị thế lớn nhất với ${pct(largestWeight)}, và hai vị thế lớn nhất chiếm ${pct(topTwoWeight)} NAV. Cấu trúc này có thể phù hợp với danh mục dài hạn, nhưng chỉ khi investment thesis của các vị thế lớn vẫn còn nguyên vẹn.`
        ));
      } else {
        assessment.push(text(
          `Portfolio construction is reasonably balanced for a focused buy-and-hold book. The largest holding is ${String(top.symbol || '').toUpperCase()} at ${pct(largestWeight)}. I would still judge diversification by business drivers and thesis overlap, not by ticker count alone.`,
          `Cấu trúc danh mục tương đối cân bằng đối với một buy-and-hold portfolio tập trung. Vị thế lớn nhất là ${String(top.symbol || '').toUpperCase()} với ${pct(largestWeight)}. Tuy vậy, đa dạng hóa nên được đánh giá theo business driver và mức trùng lặp investment thesis, không chỉ theo số lượng mã.`
        ));
      }
    }

    if (!riskReady) {
      assessment.push(text(
        `I would not make a strong risk judgment yet. Market-history evidence is still building (${pct(coverage)} coverage, ${returnObs} usable observations). Treat the current portfolio structure as known, but treat modeled risk conclusions as provisional until the D1 history is complete.`,
        `Tôi chưa đưa ra kết luận mạnh về risk ở thời điểm này. Bằng chứng lịch sử thị trường vẫn đang được xây dựng (${pct(coverage)} độ phủ, ${returnObs} quan sát sử dụng được). Cấu trúc danh mục hiện tại là dữ liệu đã biết, nhưng các kết luận modeled risk vẫn nên xem là tạm thời cho đến khi lịch sử D1 hoàn chỉnh.`
      ));
    } else if (dominantRiskDriver) {
      assessment.push(text(
        `${risk.largest_risk_symbol || 'One holding'} is carrying a disproportionate share of modeled portfolio risk. For a professional manager, the important question is not whether the number is high by itself, but whether that concentration is intentional, understood and still supported by the underlying thesis.`,
        `${risk.largest_risk_symbol || 'Một mã'} đang gánh tỷ trọng modeled risk lớn hơn đáng kể so với phần còn lại của danh mục. Với một nhà quản lý chuyên nghiệp, câu hỏi quan trọng không phải chỉ là con số có cao hay không, mà là mức concentration đó có chủ đích, được hiểu rõ và vẫn được investment thesis hỗ trợ hay không.`
      ));
    } else if (volatilityRising) {
      assessment.push(text(
        `Recent portfolio volatility is running above its longer-term norm. I would treat this as a change in market conditions to monitor, not as a trading signal. The priority is to verify whether the underlying holdings and theses have changed, rather than react to price movement alone.`,
        `Biến động gần đây của danh mục đang cao hơn mức dài hạn. Tôi xem đây là thay đổi điều kiện thị trường cần theo dõi, không phải tín hiệu giao dịch. Ưu tiên là xác minh liệu doanh nghiệp và investment thesis có thay đổi hay không, thay vì phản ứng chỉ với biến động giá.`
      ));
    } else {
      assessment.push(text(
        `The current modeled risk profile does not show an obvious portfolio-level imbalance requiring escalation. I would keep monitoring concentration, co-movement and the largest risk contributor, while leaving position decisions to thesis-level review rather than the risk model itself.`,
        `Risk profile mô hình hiện tại chưa cho thấy mất cân đối cấp danh mục rõ ràng cần escalation. Tôi sẽ tiếp tục theo dõi concentration, co-movement và mã đóng góp risk lớn nhất, nhưng quyết định vị thế vẫn phải dựa trên review investment thesis chứ không dựa riêng vào risk model.`
      ));
    }

    if (!performanceReady) {
      assessment.push(text(
        `Performance history is still too short for a professional judgment on consistency or manager skill (${snapshots} official snapshots). Current accounting P/L is useful for reconciliation, but I would wait for a longer tracked record before judging return quality or drawdown behaviour.`,
        `Lịch sử performance vẫn quá ngắn để đánh giá chuyên nghiệp về tính ổn định hay chất lượng quản lý (${snapshots} official snapshot). Accounting P/L hiện tại hữu ích cho reconciliation, nhưng cần lịch sử theo dõi dài hơn trước khi đánh giá chất lượng return hoặc hành vi drawdown.`
      ));
    } else if ((twr != null && twr < 0) || meaningfulDrawdown) {
      assessment.push(text(
        `Tracked performance deserves a thesis review: since-inception TWR is ${pct(twr)} and current drawdown is ${pct(currentDrawdown)}. A professional response is to identify what drove the weakness and whether fundamentals changed, not to convert drawdown into an automatic sell rule.`,
        `Performance theo dõi hiện đáng để review investment thesis: TWR từ khi theo dõi là ${pct(twr)} và drawdown hiện tại là ${pct(currentDrawdown)}. Phản ứng chuyên nghiệp là xác định nguyên nhân yếu đi và liệu fundamentals có thay đổi hay không, không biến drawdown thành rule bán tự động.`
      ));
    } else {
      assessment.push(text(
        `Tracked performance is mature enough for a basic review and is not currently signaling a portfolio-level problem. I would focus less on short-term P/L and more on whether return is being earned without an unacceptable concentration or drawdown profile.`,
        `Performance theo dõi đã đủ trưởng thành cho review cơ bản và hiện chưa cho thấy vấn đề cấp danh mục. Tôi sẽ ít tập trung vào P/L ngắn hạn hơn và chú ý liệu return có đạt được mà không đi kèm concentration hoặc drawdown không chấp nhận được hay không.`
      ));
    }

    if (cashWeight < 0.02) {
      assessment.push(text(
        `The portfolio is essentially fully invested. That is compatible with buy-and-hold, but it leaves little internal liquidity for fees, corporate actions or opportunistic additions without new external cash.`,
        `Danh mục gần như đã đầu tư toàn bộ vốn. Điều này phù hợp với buy-and-hold, nhưng để lại rất ít thanh khoản nội bộ cho phí, corporate action hoặc cơ hội bổ sung vị thế nếu không có dòng tiền mới từ bên ngoài.`
      ));
    } else if (cashWeight > 0.15) {
      assessment.push(text(
        `Cash is a meaningful part of NAV at ${pct(cashWeight)}. That buffer lowers portfolio participation in market moves, so it should be intentional rather than simply idle capital.`,
        `Cash đang chiếm tỷ trọng đáng kể ${pct(cashWeight)} NAV. Buffer này làm giảm mức tham gia vào biến động thị trường, vì vậy nên là lựa chọn có chủ đích thay vì vốn nhàn rỗi không được giải thích.`
      ));
    }

    const priorities = [];
    const addPriority = value => {
      if (value && !priorities.includes(value) && priorities.length < 3) priorities.push(value);
    };

    if (!riskReady) addPriority(text(
      'Let D1 history finish building before relying on detailed modeled-risk conclusions.',
      'Chờ lịch sử D1 hoàn thiện trước khi dựa vào các kết luận modeled risk chi tiết.'
    ));
    if (!performanceReady) addPriority(text(
      'Build a longer official performance record before judging consistency or drawdown behaviour.',
      'Tích lũy lịch sử performance chính thức dài hơn trước khi đánh giá tính ổn định hoặc hành vi drawdown.'
    ));
    if (concentrated) addPriority(text(
      'Keep the investment theses of the largest two holdings under explicit review because they dominate portfolio outcomes.',
      'Review rõ ràng investment thesis của hai vị thế lớn nhất vì chúng chi phối kết quả danh mục.'
    ));
    if (dominantRiskDriver) addPriority(text(
      `Confirm that the outsized risk contribution from ${risk.largest_risk_symbol || 'the leading risk driver'} is deliberate and still justified.`,
      `Xác nhận rằng mức đóng góp risk lớn từ ${risk.largest_risk_symbol || 'mã dẫn đầu risk'} là có chủ đích và vẫn hợp lý.`
    ));
    if (meaningfulDrawdown) addPriority(text(
      'Review the drivers of drawdown and thesis integrity; do not react to drawdown mechanically.',
      'Review nguyên nhân drawdown và tính toàn vẹn của thesis; không phản ứng máy móc theo drawdown.'
    ));
    if (!priorities.length) addPriority(text(
      'Maintain data freshness and review the portfolio when a thesis, concentration or risk regime materially changes.',
      'Duy trì độ mới dữ liệu và review danh mục khi investment thesis, concentration hoặc risk regime thay đổi đáng kể.'
    ));

    return {
      state,
      tone,
      constructionLabel,
      assessment,
      priorities,
    };
  }, [positions, portfolio, risk, perf, health, locale]);

  if (!target || !positions.length) return null;

  return createPortal(
    <section className="card fund-manager-review-card" data-testid="fund-manager-review">
      <div className="section-head fm-review-head">
        <div>
          <div className="eyebrow">{text('Professional judgment', 'Góc nhìn chuyên nghiệp')}</div>
          <h2>{text('Fund manager review', 'Nhận xét của nhà quản lý quỹ')}</h2>
          <p className="muted">{text(
            'A concise portfolio-level judgment from the evidence already stored in QPort. Detailed quantitative diagnostics belong in Risk.',
            'Nhận xét cô đọng ở cấp danh mục từ bằng chứng đã lưu trong QPort. Chẩn đoán định lượng chi tiết được đặt trong trang Risk.'
          )}</p>
        </div>
        <div className="fm-review-state">
          <Pill tone={review.tone}>{review.state}</Pill>
          <span className="muted">{dashboard.today || market.market_date || '-'}</span>
        </div>
      </div>

      <div className="fm-manager-summary">
        <span>{text('Portfolio construction', 'Cấu trúc danh mục')}</span>
        <b>{review.constructionLabel}</b>
      </div>

      <section className="fm-manager-assessment">
        <h3>{text('Manager assessment', 'Đánh giá của nhà quản lý')}</h3>
        {review.assessment.map((paragraph, index) => <p key={index}>{paragraph}</p>)}
      </section>

      <section className="fm-priorities">
        <h3>{text('What I would monitor', 'Điều tôi sẽ theo dõi')}</h3>
        <ol>{review.priorities.map((item, index) => <li key={index}>{item}</li>)}</ol>
      </section>

      <div className="fm-review-foot">
        <a className="text-link" href="/risk">{text('View detailed risk analysis →', 'Xem phân tích risk chi tiết →')}</a>
        <span className="muted">{text(
          'Information only. This review does not create BUY/SELL actions.',
          'Chỉ mang tính thông tin. Review này không tạo hành động BUY/SELL.'
        )}</span>
      </div>
    </section>,
    target
  );
}
