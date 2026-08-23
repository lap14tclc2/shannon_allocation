import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

const STEPS=[['guide.step1','guide.step1_body'],['guide.step2','guide.step2_body'],['guide.step3','guide.step3_body'],['guide.step4','guide.step4_body'],['guide.step5','guide.step5_body'],['guide.step6','guide.step6_body'],['guide.step7','guide.step7_body'],['guide.step8','guide.step8_body'],['guide.step9','guide.step9_body'],['guide.step10','guide.step10_body']];
const WARNINGS=['guide.warning_1','guide.warning_2','guide.warning_3'];

export default function GuidePage({locale='en'}){
  const {t}=useI18n(locale); const text=(en,vi)=>locale==='vi'?vi:en;
  return <div className="page">
    <AppNav active="guide" locale={locale}/>
    <header className="page-head"><div><h1>{t('guide.title')}</h1><p className="muted">{t('guide.subtitle')}</p></div></header>
    <div className="card guide-principle"><h3>{t('guide.principle')}</h3><p>{text('QPort is a Buy & Hold institutional-lite portfolio book. Only validated ledger events change shares/cash. Market data and risk never create trades; due verified/discovered dividend entitlements may create system corporate-action ledger events automatically on payment date.','QPort là sổ danh mục Buy & Hold institutional-lite. Chỉ ledger event đã validate mới đổi cổ phiếu/tiền. Market data và risk không tự tạo giao dịch; quyền cổ tức đủ dữ liệu có thể tạo corporate-action ledger event tự động vào ngày thanh toán.')}</p></div>
    <div className="card"><h3>{t('guide.quick_start')}</h3><pre className="guide-code"><code>{`cd frontend\nnpm ci\nnpm run build\nnpm run build:ssr\n\ncd ../python\npip install -r requirements.txt\n# Optional Vnstock + corporate actions:\n# pip install -r requirements-vnstock.txt\npython serve.py`}</code></pre></div>

    <div className="card"><h3>{text('Authentication & first sign-in','Xác thực & đăng nhập lần đầu')}</h3><div className="rule-list">
      <div>✓ {text('Normal users sign in with a unique username only. No password is required for a normal user.','User thường đăng nhập chỉ bằng username duy nhất. User thường không cần password.')}</div>
      <div>✓ {text('If the username does not exist, QPort shows a registration field. Register it once, then the system creates an isolated private portfolio database for that user.','Nếu username chưa tồn tại, QPort sẽ hiện ô đăng ký. Đăng ký một lần, sau đó hệ thống tạo database danh mục riêng cho user đó.')}</div>
      <div>✓ {text('Admin requires its password, but QPort never displays the credential in the sign-in page, Admin page, guide or startup output.','Admin cần password riêng, nhưng QPort không hiển thị credential trên trang đăng nhập, trang Admin, hướng dẫn hoặc startup output.')}</div>
      <div>✓ {text('Admin is administration-only. After login it always stays on /admin and cannot access portfolio pages or portfolio APIs.','Admin chỉ dùng để quản trị. Sau khi đăng nhập admin luôn ở /admin và không thể truy cập portfolio pages hoặc portfolio APIs.')}</div>
      <div>✓ {text('Admin can remove a normal user. Removing the user also invalidates their sessions and deletes their complete portfolio SQLite database.','Admin có thể xóa user thường. Xóa user đồng thời vô hiệu session và xóa toàn bộ SQLite database danh mục của user đó.')}</div>
      <div>✓ {text('Portfolio, transactions, prices, snapshots, dividends, operations and logs are all resolved from the currently authenticated normal-user database.','Portfolio, giao dịch, giá, snapshot, cổ tức, operations và logs đều được đọc/ghi từ database của normal user đang đăng nhập.')}</div>
    </div></div>

    <div className="guide-steps">{STEPS.map(([a,b])=><section className="card" key={a}><h3>{t(a)}</h3><p>{t(b)}</p></section>)}</div>

    <div className="card"><h3>{text('Institutional-lite daily workflow','Quy trình institutional-lite hàng ngày')}</h3><pre className="guide-code"><code>{text(`Record/import trade with broker/account\n      ↓\nLedger immediately rebuilds Holdings + derived history\n      ↓\nTrade-date position / settlement tracking\n      ↓\nDaily D1 sync + risk-history backfill when needed\n      ↓\nCorporate-action discovery\n      ↓\nPayment date reached?\n      ↓ yes\nAuto-post CASH_DIVIDEND / STOCK_DIVIDEND once\n      ↓\nApply dividend tax policy + refresh Holdings/Performance\n      ↓\nReview reconciliation / exceptions\n      ↓\nLock official NAV when appropriate`,`Ghi/import giao dịch kèm broker/account\n      ↓\nLedger lập tức rebuild Holdings + lịch sử dẫn xuất\n      ↓\nTheo dõi vị thế trade-date / settlement\n      ↓\nSync D1 hàng ngày + backfill lịch sử risk khi cần\n      ↓\nPhát hiện corporate action\n      ↓\nĐã đến payment date?\n      ↓ có\nTự post CASH_DIVIDEND / STOCK_DIVIDEND đúng một lần\n      ↓\nÁp dụng tax policy cổ tức + cập nhật Holdings/Performance\n      ↓\nReview đối soát / ngoại lệ\n      ↓\nKhóa NAV chính thức khi phù hợp`)}</code></pre></div>

    <div className="card"><h3>{text('Dividend and tax behavior','Cổ tức và cách tính thuế')}</h3><div className="rule-list">
      <div>✓ {text('Cash dividend is recorded gross; QPort withholds 5% and adds only net cash to the portfolio while preserving gross dividend income and the tax amount separately.','Cổ tức tiền mặt được ghi gross; QPort khấu trừ 5% và chỉ cộng tiền net vào portfolio, đồng thời giữ riêng gross dividend income và số thuế.')}</div>
      <div>✓ {text('Stock dividend adds shares without changing cost basis and has no investment-income tax at receipt.','Cổ tức cổ phiếu làm tăng shares nhưng không tăng cost basis và chưa tính thuế đầu tư vốn lúc nhận.')}</div>
      <div>✓ {text('When taxable stock-dividend shares are sold, QPort adds 5% investment-income tax using par value, or the lower transfer price when the stock is sold below par. Ordinary securities-transfer tax remains separate/additive.','Khi bán số cổ phiếu cổ tức còn chịu thuế, QPort cộng thuế đầu tư vốn 5% theo mệnh giá, hoặc theo giá chuyển nhượng thấp hơn nếu giá bán dưới mệnh giá. Thuế chuyển nhượng chứng khoán thông thường vẫn là khoản riêng/cộng thêm.')}</div>
      <div>✓ {text('The received-dividend table is ledger-based and expandable by ticker, showing gross cash, withholding, net cash, stock shares and source transaction.','Bảng cổ tức đã nhận lấy từ ledger và expand theo mã, hiển thị tiền gross, thuế khấu trừ, tiền net, cổ phiếu nhận và transaction nguồn.')}</div>
    </div></div>

    <div className="card"><h3>{text('What Operations means','Trang Vận hành dùng để làm gì')}</h3><div className="rule-list">
      <div>✓ {text('Tax lots: the underlying accounting book keeps acquisition lots and uses FIFO for SELL; average cost is only a display metric.','Tax lot: sổ kế toán giữ từng lot mua và SELL dùng FIFO; giá vốn bình quân chỉ là metric hiển thị.')}</div>
      <div>✓ {text('Settlement: positions are recognized on trade date. Cash is split into settled, receivable/payable and projected cash. Blank settlement dates are only estimated T+2 weekdays until confirmed.','Settlement: vị thế ghi nhận theo ngày giao dịch. Tiền được tách settled, receivable/payable và projected cash. Ngày settlement để trống chỉ được ước tính T+2 ngày làm việc đến khi xác nhận.')}</div>
      <div>✓ {text('Reconciliation: compare QPort with broker settled cash and quantities. A mismatch creates an exception and never silently changes the ledger.','Reconciliation: đối chiếu QPort với tiền settled và số lượng theo broker. Sai lệch tạo exception và không bao giờ âm thầm sửa ledger.')}</div>
      <div>✓ {text('Corporate actions: provider data is used for discovery. Due dividend components are posted automatically only when QPort has a payment date and enough entitlement data; posting is idempotent. Operations still exposes verification/reconciliation controls for review.','Corporate action: dữ liệu provider dùng để phát hiện. Thành phần cổ tức đến hạn chỉ được auto-post khi QPort có payment date và đủ dữ liệu quyền; posting là idempotent. Operations vẫn giữ verification/reconciliation controls để review.')}</div>
      <div>✓ {text('NAV controls: historical corrections can mark later NAVs as RESTATEMENT_REQUIRED. Resolve only after reviewing the rebuilt book.','Kiểm soát NAV: correction lịch sử có thể đánh dấu NAV sau đó là RESTATEMENT_REQUIRED. Chỉ resolve sau khi review sổ đã rebuild.')}</div>
      <div>✓ {text('Exception queue: treat it like a back-office work queue. Clear data/settlement/reconciliation/restatement exceptions before relying on the book.','Exception queue: dùng như hàng đợi back-office. Xử lý ngoại lệ data/settlement/reconciliation/restatement trước khi tin vào sổ.')}</div>
    </div></div>

    <div className="card"><h3>{text('Data integrity rules','Quy tắc giữ dữ liệu sạch')}</h3><div className="rule-list">
      <div>✓ {text('Prices use full VND/share: 72,000, not 72.','Giá dùng VND đầy đủ/cổ phiếu: 72.000, không phải 72.')}</div>
      <div>✓ {text('BUY/SELL event_date is the trade date; optional settlement_date cannot be earlier than it.','event_date của BUY/SELL là ngày giao dịch; settlement_date nếu có không được sớm hơn.')}</div>
      <div>✓ {text('Broker is selected; Account is editable free text with PRIMARY only as the default/fallback value.','Broker được chọn; Account là free text có thể sửa, PRIMARY chỉ là giá trị mặc định/fallback.')}</div>
      <div>✓ {text('Create/Edit/Delete changes one effective ledger. Holdings are derived again immediately; there is no separate editable holdings database to drift out of sync.','Create/Edit/Delete thay đổi một effective ledger. Holdings được derive lại ngay; không có database holdings riêng có thể lệch khỏi Transactions.')}</div>
      <div>✓ {text('Edit/Delete is append-only correction. Original rows remain auditable and the full chronological ledger is revalidated.','Sửa/Xóa là correction append-only. Dòng gốc vẫn audit được và toàn bộ ledger theo thời gian được validate lại.')}</div>
      <div>✓ {text('A historical correction does not silently rewrite a previously official book: it opens NAV restatement control when applicable.','Correction lịch sử không âm thầm viết lại sổ đã official: nó mở kiểm soát restatement NAV khi có liên quan.')}</div>
      <div>✓ {text('Reference weights must cover all current holdings and total 100%; no equal-weight policy is invented.','Tỷ trọng tham chiếu phải bao phủ mọi vị thế và tổng 100%; QPort không tự bịa chính sách equal-weight.')}</div>
    </div></div>

    <div className="card"><h3>{text('Risk and performance readiness','Độ sẵn sàng Risk và Performance')}</h3><div className="rule-list">
      <div>✓ {text('Initial market sync backfills about 550 calendar days of D1 data when available so risk is not stuck at 0% coverage after a recent position import.','Initial market sync backfill khoảng 550 ngày lịch D1 khi provider có dữ liệu để risk không bị kẹt ở coverage 0% chỉ vì position mới được import.')}</div>
      <div>✓ {text('Risk explains concentration, correlation, volatility regime and tail risk; missing fields mean insufficient evidence, never false zero.','Risk diễn giải concentration, correlation, volatility regime và tail risk; field trống nghĩa là thiếu bằng chứng, không phải số 0 giả.')}</div>
      <div>✓ {text('Performance shows return, drawdown, best/worst day, history readiness and tax-adjusted dividend cash so the page is useful before a full year of history is available.','Performance hiển thị return, drawdown, best/worst day, history readiness và tiền cổ tức sau thuế để trang vẫn hữu ích trước khi đủ một năm lịch sử.')}</div>
      <div>✓ {text('Opening imports establish current holdings/cost basis but do not prove historical investor cash-flow dates, so XIRR may remain unavailable.','Opening import xác lập vị thế/giá vốn hiện tại nhưng không chứng minh ngày dòng tiền lịch sử, nên XIRR có thể vẫn chưa khả dụng.')}</div>
      <div>✓ {text('Export for AI includes institutional book data: lots, settlement, reconciliation, corporate actions, NAV controls, exceptions and correction audit.','Xuất dữ liệu cho AI gồm dữ liệu institutional book: lots, settlement, reconciliation, corporate actions, NAV controls, exceptions và correction audit.')}</div>
    </div></div>

    <div className="card warning-card"><h3>{t('guide.warning_title')}</h3><div className="rule-list">{WARNINGS.map(k=><div key={k}>✓ {t(k)}</div>)}</div></div>
    <div className="card"><h3>{t('guide.full_docs')}</h3><div className="button-row"><a className="btn-export" href="https://github.com/lap14tclc2/shannon_allocation/blob/main/docs/USER_GUIDE_EN.md">{t('guide.english_doc')}</a><a className="btn-variant" href="https://github.com/lap14tclc2/shannon_allocation/blob/main/docs/USER_GUIDE_VI.md">{t('guide.vietnamese_doc')}</a></div></div>
  </div>;
}
