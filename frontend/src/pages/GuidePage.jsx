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
    <div className="card guide-principle"><h3>{t('guide.principle')}</h3><p>{text('QPort is a Buy & Hold institutional-lite portfolio book. Only explicit ledger actions change shares/cash. Market data, risk, recommendations and corporate-action discovery never create trades automatically.','QPort là sổ danh mục Buy & Hold institutional-lite. Chỉ hành động ledger rõ ràng mới đổi cổ phiếu/tiền. Market data, risk, recommendation và corporate-action discovery không bao giờ tự tạo giao dịch.')}</p></div>
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

    <div className="card"><h3>{text('Institutional-lite daily workflow','Quy trình institutional-lite hàng ngày')}</h3><pre className="guide-code"><code>{text(`Record/import trade\n      ↓\nTrade-date position\n      ↓\nConfirm settlement\n      ↓\nReconcile broker cash + quantities\n      ↓\nReview corporate actions\n      ↓\nVerify with VSDC / HOSE / HNX\n      ↓\nRecord actual entitlement receipt\n      ↓\nExplicitly post reconciled receipt to ledger\n      ↓\nReview exceptions\n      ↓\nLock official NAV`,`Ghi/import giao dịch\n      ↓\nVị thế theo ngày giao dịch\n      ↓\nXác nhận settlement\n      ↓\nĐối soát tiền + số lượng với broker\n      ↓\nReview quyền doanh nghiệp\n      ↓\nXác minh bằng VSDC / HOSE / HNX\n      ↓\nGhi thực nhận quyền\n      ↓\nChủ động post thực nhận đã đối soát vào ledger\n      ↓\nReview ngoại lệ\n      ↓\nKhóa NAV chính thức`)}</code></pre></div>

    <div className="card"><h3>{text('What Operations means','Trang Vận hành dùng để làm gì')}</h3><div className="rule-list">
      <div>✓ {text('Tax lots: the underlying accounting book keeps acquisition lots and uses FIFO for SELL; average cost is only a display metric.','Tax lot: sổ kế toán giữ từng lot mua và SELL dùng FIFO; giá vốn bình quân chỉ là metric hiển thị.')}</div>
      <div>✓ {text('Settlement: positions are recognized on trade date. Cash is split into settled, receivable/payable and projected cash. Blank settlement dates are only estimated T+2 weekdays until confirmed.','Settlement: vị thế ghi nhận theo ngày giao dịch. Tiền được tách settled, receivable/payable và projected cash. Ngày settlement để trống chỉ được ước tính T+2 ngày làm việc đến khi xác nhận.')}</div>
      <div>✓ {text('Reconciliation: compare QPort with broker settled cash and quantities. A mismatch creates an exception and never silently changes the ledger.','Reconciliation: đối chiếu QPort với tiền settled và số lượng theo broker. Sai lệch tạo exception và không bao giờ âm thầm sửa ledger.')}</div>
      <div>✓ {text('Corporate actions: Vnstock is discovery only. VERIFIED requires an authoritative VSDC/HOSE/HNX URL. Actual receipt must be reconciled before the user may post it to the ledger.','Corporate action: Vnstock chỉ dùng để phát hiện. VERIFIED yêu cầu URL authoritative VSDC/HOSE/HNX. Thực nhận phải được đối soát trước khi user được post vào ledger.')}</div>
      <div>✓ {text('NAV controls: historical corrections can mark later NAVs as RESTATEMENT_REQUIRED. Resolve only after reviewing the rebuilt book.','Kiểm soát NAV: correction lịch sử có thể đánh dấu NAV sau đó là RESTATEMENT_REQUIRED. Chỉ resolve sau khi review sổ đã rebuild.')}</div>
      <div>✓ {text('Exception queue: treat it like a back-office work queue. Clear data/settlement/reconciliation/restatement exceptions before relying on the book.','Exception queue: dùng như hàng đợi back-office. Xử lý ngoại lệ data/settlement/reconciliation/restatement trước khi tin vào sổ.')}</div>
    </div></div>

    <div className="card"><h3>{text('Data integrity rules','Quy tắc giữ dữ liệu sạch')}</h3><div className="rule-list">
      <div>✓ {text('Prices use full VND/share: 72,000, not 72.','Giá dùng VND đầy đủ/cổ phiếu: 72.000, không phải 72.')}</div>
      <div>✓ {text('BUY/SELL event_date is the trade date; optional settlement_date cannot be earlier than it.','event_date của BUY/SELL là ngày giao dịch; settlement_date nếu có không được sớm hơn.')}</div>
      <div>✓ {text('Edit/Delete is append-only correction. Original rows remain auditable and the full chronological ledger is revalidated.','Sửa/Xóa là correction append-only. Dòng gốc vẫn audit được và toàn bộ ledger theo thời gian được validate lại.')}</div>
      <div>✓ {text('A historical correction does not silently rewrite a previously official book: it opens NAV restatement control when applicable.','Correction lịch sử không âm thầm viết lại sổ đã official: nó mở kiểm soát restatement NAV khi có liên quan.')}</div>
      <div>✓ {text('Reference weights must cover all current holdings and total 100%; no equal-weight policy is invented.','Tỷ trọng tham chiếu phải bao phủ mọi vị thế và tổng 100%; QPort không tự bịa chính sách equal-weight.')}</div>
    </div></div>

    <div className="card"><h3>{text('Performance and AI export','Hiệu suất và AI export')}</h3><div className="rule-list">
      <div>✓ {text('MONITOR is not HOLD. Missing drawdown/TWR/XIRR evidence stays N/A, never false zero.','MONITOR không phải HOLD. Thiếu bằng chứng drawdown/TWR/XIRR thì giữ N/A, không giả thành 0.')}</div>
      <div>✓ {text('Opening imports establish current holdings/cost basis but do not prove historical investor cash-flow dates.','Opening import xác lập vị thế/giá vốn hiện tại nhưng không chứng minh ngày dòng tiền lịch sử.')}</div>
      <div>✓ {text('Export for AI now includes institutional book data: lots, settlement, reconciliation, corporate actions, NAV controls, exceptions and correction audit.','Xuất dữ liệu cho AI giờ gồm dữ liệu institutional book: lots, settlement, reconciliation, corporate actions, NAV controls, exceptions và correction audit.')}</div>
    </div></div>

    <div className="card warning-card"><h3>{t('guide.warning_title')}</h3><div className="rule-list">{WARNINGS.map(k=><div key={k}>✓ {t(k)}</div>)}</div></div>
    <div className="card"><h3>{t('guide.full_docs')}</h3><div className="button-row"><a className="btn-export" href="https://github.com/lap14tclc2/shannon_allocation/blob/main/docs/USER_GUIDE_EN.md">{t('guide.english_doc')}</a><a className="btn-variant" href="https://github.com/lap14tclc2/shannon_allocation/blob/main/docs/USER_GUIDE_VI.md">{t('guide.vietnamese_doc')}</a></div></div>
  </div>;
}
