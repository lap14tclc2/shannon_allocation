import React from 'react';
import AppNav from '../components/AppNav.jsx';

function Step({ number, title, children }) {
  return <section className="guide-step-card">
    <span className="guide-step-number">{number}</span>
    <div><h3>{title}</h3><p>{children}</p></div>
  </section>;
}

function PageCard({ href, title, question, children, advanced = false }) {
  return <a className={`guide-page-card${advanced ? ' is-advanced' : ''}`} href={href}>
    <div><h3>{title}</h3><span>{question}</span></div>
    <p>{children}</p>
    <b>→</b>
  </a>;
}

export default function GuidePage({ locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;

  return <div className="page guide-page">
    <AppNav active="guide" locale={locale} />

    <header className="page-head guide-hero">
      <div>
        <div className="eyebrow">{text('QPort user guide', 'Hướng dẫn sử dụng QPort')}</div>
        <h1>{text('Use QPort with confidence', 'Dùng QPort một cách tự tin')}</h1>
        <p className="muted">{text(
          'You do not need portfolio-management or technical knowledge to use QPort. Start with your real holdings, keep transactions accurate, and let the system build the history around them.',
          'Bạn không cần kiến thức quản lý quỹ hay kỹ thuật để dùng QPort. Hãy bắt đầu từ danh mục thực tế, ghi giao dịch chính xác và để hệ thống tự xây dựng lịch sử xung quanh danh mục.'
        )}</p>
      </div>
    </header>

    <section className="guide-intro-card">
      <strong>{text('The one rule to remember', 'Một nguyên tắc cần nhớ')}</strong>
      <p>{text(
        'QPort records what actually happened. Prices, Risk and Performance explain your portfolio, but they do not change your shares or automatically trade for you.',
        'QPort ghi lại những gì thực sự đã xảy ra. Giá, Risk và Performance giúp giải thích danh mục, nhưng không tự thay đổi số cổ phiếu hay giao dịch thay bạn.'
      )}</p>
    </section>

    <section className="guide-section">
      <div className="guide-section-head">
        <div><span>01</span><h2>{text('Start here', 'Bắt đầu từ đây')}</h2></div>
        <p>{text('A new portfolio only needs four steps.', 'Một danh mục mới chỉ cần bốn bước.')}</p>
      </div>
      <div className="guide-start-grid">
        <Step number="1" title={text('Sign in', 'Đăng nhập')}>
          {text('Use your username. If it is new, QPort will create a private portfolio for that username.', 'Dùng username của bạn. Nếu username chưa tồn tại, QPort sẽ tạo một portfolio riêng cho username đó.')}
        </Step>
        <Step number="2" title={text('Enter what you already own', 'Nhập danh mục đang sở hữu')}>
          {text('Open Transactions and use Position import for existing holdings. Enter the real shares, average cost, broker and account. Add existing cash separately if you want QPort to track it.', 'Mở Transactions và dùng Position import cho các mã đang sở hữu. Nhập đúng số cổ phiếu, giá vốn, broker và account. Nếu muốn QPort theo dõi tiền mặt, hãy nhập cash hiện có riêng.')}
        </Step>
        <Step number="3" title={text('Check Portfolio', 'Kiểm tra Portfolio')}>
          {text('Return to Portfolio and compare shares, cost value, market value and P/L with your broker. D1 market history will build in the background when needed.', 'Quay lại Portfolio và đối chiếu số cổ phiếu, giá vốn, giá trị thị trường và P/L với broker. Lịch sử D1 sẽ tự xây dựng nền khi cần.')}
        </Step>
        <Step number="4" title={text('Trust analytics only after the book is correct', 'Chỉ tin analytics sau khi sổ đã đúng')}>
          {text('If Holdings do not match your broker, fix Transactions first. Risk and Performance are useful only after the underlying portfolio is accurate.', 'Nếu Holdings chưa khớp broker, hãy sửa Transactions trước. Risk và Performance chỉ có ý nghĩa khi dữ liệu danh mục nền đã chính xác.')}
        </Step>
      </div>
    </section>

    <section className="guide-section">
      <div className="guide-section-head">
        <div><span>02</span><h2>{text('What each page answers', 'Mỗi trang trả lời câu hỏi gì')}</h2></div>
        <p>{text('Think in questions, not system modules.', 'Hãy nghĩ theo câu hỏi, không cần nghĩ theo module kỹ thuật.')}</p>
      </div>
      <div className="guide-page-grid">
        <PageCard href="/" title="Portfolio" question={text('What do I own now?', 'Hiện tại tôi đang sở hữu gì?')}>
          {text('Your holdings, NAV, P/L, cash, dividend history, market-data status and the concise fund-manager review.', 'Holdings, NAV, P/L, cash, lịch sử cổ tức, trạng thái market data và nhận xét ngắn gọn từ góc nhìn nhà quản lý quỹ.')}
        </PageCard>
        <PageCard href="/transactions" title="Transactions" question={text('What changed my portfolio?', 'Điều gì đã làm danh mục thay đổi?')}>
          {text('Import existing positions, record BUY/SELL, cash movements, fees and corrections. This is where you fix accounting mistakes.', 'Import vị thế hiện có, ghi BUY/SELL, dòng tiền, phí và correction. Đây là nơi bạn sửa sai lệch kế toán.')}
        </PageCard>
        <PageCard href="/performance" title="Performance" question={text('How has the portfolio performed?', 'Danh mục đã hoạt động như thế nào?')}>
          {text('Actual tracked return, drawdown, history maturity and income. Performance grows from the day QPort can truly observe your portfolio.', 'Return thực tế đã tracking, drawdown, độ trưởng thành lịch sử và thu nhập. Performance tăng dần từ ngày QPort thực sự theo dõi được danh mục.')}
        </PageCard>
        <PageCard href="/risk" title="Risk" question={text('Where can the portfolio hurt me?', 'Danh mục có thể gây rủi ro ở đâu?')} advanced>
          {text('Plain-language concentration, co-movement, volatility, bad-day risk and risk drivers. Technical metrics are collapsed below for deeper review.', 'Diễn giải dễ hiểu về concentration, mức biến động cùng nhau, volatility, ngày xấu và mã chi phối risk. Metric kỹ thuật nằm collapsed bên dưới để xem sâu hơn.')}
        </PageCard>
      </div>
    </section>

    <section className="guide-section">
      <div className="guide-section-head">
        <div><span>03</span><h2>{text('Common things you will do', 'Những việc thường làm')}</h2></div>
        <p>{text('Use the event that matches what really happened.', 'Chọn đúng loại sự kiện theo những gì thực tế đã xảy ra.')}</p>
      </div>
      <div className="guide-task-list">
        <details open>
          <summary>{text('I already own stocks before using QPort', 'Tôi đã sở hữu cổ phiếu trước khi dùng QPort')}</summary>
          <p>{text('Use Position import. Enter current shares and their real cost basis. Do not create a fake historical BUY just to make Holdings appear.', 'Dùng Position import. Nhập số cổ phiếu hiện có và giá vốn thực. Không tạo BUY giả trong quá khứ chỉ để Holdings xuất hiện.')}</p>
        </details>
        <details>
          <summary>{text('I bought more shares or subscribed to a paid rights/new issue', 'Tôi mua thêm hoặc thực hiện quyền mua/phát hành mới có trả tiền')}</summary>
          <p>{text('Use BUY with the actual shares, actual paid price, broker and account. QPort adds that lot to the same holding.', 'Dùng BUY với đúng số cổ phiếu, giá thực trả, broker và account. QPort sẽ cộng lot đó vào cùng holding.')}</p>
        </details>
        <details>
          <summary>{text('I sold shares', 'Tôi bán cổ phiếu')}</summary>
          <p>{text('Use SELL for the real trade date, quantity, price, broker/account and any broker-reported fee/tax. Holdings will update from the same transaction history.', 'Dùng SELL với đúng ngày giao dịch, số lượng, giá, broker/account và fee/tax broker báo. Holdings sẽ cập nhật từ chính lịch sử transaction đó.')}</p>
        </details>
        <details>
          <summary>{text('I entered something incorrectly', 'Tôi nhập sai dữ liệu')}</summary>
          <p>{text('Edit or delete the transaction from Transactions. QPort keeps the correction auditable and rebuilds the derived portfolio; do not manually patch Holdings.', 'Sửa hoặc xóa transaction trong Transactions. QPort giữ correction để audit và rebuild danh mục dẫn xuất; không chỉnh Holdings thủ công.')}</p>
        </details>
        <details>
          <summary>{text('A dividend was announced or paid', 'Có cổ tức được công bố hoặc chi trả')}</summary>
          <p>{text('Dividend announcements are discovered from providers and deduplicated. Received dividends appear only when QPort has a real posted dividend event; if none has been received, the Received dividends section stays hidden.', 'Thông tin cổ tức được lấy từ provider và loại trùng. Cổ tức đã nhận chỉ hiện khi QPort có dividend event thực sự được ghi nhận; nếu chưa nhận thì section Received dividends sẽ được ẩn.')}</p>
        </details>
      </div>
    </section>

    <section className="guide-section">
      <div className="guide-section-head">
        <div><span>04</span><h2>{text('Understand the status words', 'Hiểu các trạng thái')}</h2></div>
        <p>{text('Most confusion disappears once these four words are clear.', 'Phần lớn nhầm lẫn sẽ biến mất khi hiểu bốn trạng thái này.')}</p>
      </div>
      <div className="guide-status-grid">
        <div><b className="guide-status-ready">READY</b><p>{text('Enough current evidence is available for this part of the system.', 'Phần này đã có đủ bằng chứng hiện tại để sử dụng.')}</p></div>
        <div><b className="guide-status-building">BUILDING</b><p>{text('QPort is still accumulating history. This is not an error and missing values are not zero.', 'QPort vẫn đang tích lũy lịch sử. Đây không phải lỗi và giá trị thiếu không có nghĩa là bằng 0.')}</p></div>
        <div><b className="guide-status-stale">STALE / PARTIAL</b><p>{text('Some data exists, but it is not fully aligned or complete. Read conclusions with extra caution.', 'Đã có dữ liệu nhưng chưa hoàn toàn đồng bộ hoặc đầy đủ. Cần thận trọng hơn khi đọc kết luận.')}</p></div>
        <div><b className="guide-status-error">ERROR</b><p>{text('A provider or operation failed. Existing ledger history is preserved; retry or inspect the visible error.', 'Provider hoặc operation gặp lỗi. Lịch sử ledger hiện có vẫn được giữ; hãy retry hoặc xem lỗi hiển thị.')}</p></div>
      </div>
    </section>

    <section className="guide-section guide-two-column">
      <article className="card guide-friendly-card">
        <div className="eyebrow">{text('Dividends', 'Cổ tức')}</div>
        <h2>{text('What QPort does for you', 'QPort tự làm gì')}</h2>
        <p>{text('QPort can discover cash and stock dividends, merge duplicate provider reports and post eligible received dividends when the required payment/entitlement evidence is available.', 'QPort có thể phát hiện cổ tức tiền/cổ phiếu, gộp báo cáo trùng giữa các provider và ghi nhận cổ tức đã nhận khi có đủ bằng chứng payment/entitlement cần thiết.')}</p>
        <div className="guide-mini-rule">{text('Cash dividend: QPort records gross income, 5% withholding and net cash separately.', 'Cổ tức tiền: QPort ghi riêng gross income, khấu trừ 5% và net cash.')}</div>
        <div className="guide-mini-rule">{text('Stock dividend: shares are added when posted; receipt itself does not add cost basis.', 'Cổ tức cổ phiếu: shares được cộng khi event được post; lúc nhận không làm tăng cost basis.')}</div>
      </article>

      <article className="card guide-friendly-card">
        <div className="eyebrow">Risk + Performance</div>
        <h2>{text('Why they mature differently', 'Vì sao hai phần trưởng thành khác nhau')}</h2>
        <p>{text('Risk may use older D1 market history for the stocks you hold, so it can become useful soon after import. Performance must reflect your actual tracked portfolio and therefore starts from the real tracking period.', 'Risk có thể dùng lịch sử D1 cũ hơn của các mã đang nắm giữ nên có thể hữu ích khá sớm sau khi import. Performance phải phản ánh đúng danh mục thực tế được tracking nên bắt đầu từ giai đoạn theo dõi thật.')}</p>
        <div className="guide-mini-rule">{text('ERC is only an advanced diagnostic reference. It does not set your target allocation or rebalance the portfolio.', 'ERC chỉ là tham chiếu chẩn đoán nâng cao. Nó không đặt target allocation hay rebalance danh mục.')}</div>
      </article>
    </section>

    <section className="guide-section">
      <div className="guide-section-head">
        <div><span>05</span><h2>{text('If something looks wrong', 'Nếu có gì đó trông không đúng')}</h2></div>
        <p>{text('Check the simplest source first.', 'Kiểm tra nguồn đơn giản nhất trước.')}</p>
      </div>
      <div className="guide-faq-grid">
        <div><h3>{text('Shares or cost are wrong', 'Shares hoặc giá vốn sai')}</h3><p>{text('Check Transactions. Holdings are derived from that history.', 'Kiểm tra Transactions. Holdings được derive từ lịch sử đó.')}</p></div>
        <div><h3>{text('Risk says BUILDING', 'Risk báo BUILDING')}</h3><p>{text('Check D1 history status. The background backfill may still be running or the provider may not have enough history.', 'Kiểm tra trạng thái D1 history. Background backfill có thể vẫn đang chạy hoặc provider chưa có đủ lịch sử.')}</p></div>
        <div><h3>{text('Performance has very little history', 'Performance có rất ít lịch sử')}</h3><p>{text('That is expected for a newly tracked portfolio. QPort does not invent historical portfolio performance.', 'Điều này bình thường với portfolio mới tracking. QPort không tự bịa performance lịch sử của danh mục.')}</p></div>
        <div><h3>{text('Dividend history looks duplicated', 'Lịch sử cổ tức trông bị trùng')}</h3><p>{text('Use Refresh canonical source. QPort merges the same economic event across supported providers and preserves alternate evidence for audit.', 'Dùng Refresh canonical source. QPort gộp cùng một economic event giữa các provider được hỗ trợ và vẫn giữ alternate evidence để audit.')}</p></div>
      </div>
    </section>

    <details className="card guide-advanced">
      <summary>{text('Advanced: Data integrity rules', 'Nâng cao: Quy tắc toàn vẹn dữ liệu')}</summary>
      <div className="guide-advanced-body">
        <p>{text('You normally do not need these details, but they explain why QPort may refuse or flag inconsistent data.', 'Bạn thường không cần các chi tiết này, nhưng chúng giải thích vì sao QPort có thể từ chối hoặc cảnh báo dữ liệu không nhất quán.')}</p>
        <ul>
          <li>{text('Prices are full VND/share (for example 72,000, not 72).', 'Giá dùng VND đầy đủ/cổ phiếu (ví dụ 72.000, không phải 72).')}</li>
          <li>{text('BUY/SELL dates are trade dates. Broker/account information should match the real trade.', 'Ngày BUY/SELL là ngày giao dịch. Broker/account nên khớp giao dịch thực tế.')}</li>
          <li>{text('Editing/deleting a transaction creates an auditable correction; QPort does not maintain a separate editable Holdings book.', 'Sửa/xóa transaction tạo correction có thể audit; QPort không duy trì một sổ Holdings chỉnh tay riêng.')}</li>
          <li>{text('Risk information never changes shares, and ERC is diagnostic reference only.', 'Thông tin Risk không bao giờ thay đổi shares và ERC chỉ là tham chiếu chẩn đoán.')}</li>
          <li>{text('Missing evidence is shown as missing/building rather than replaced with a misleading zero.', 'Bằng chứng thiếu được hiển thị là missing/building thay vì bị thay bằng số 0 gây hiểu nhầm.')}</li>
        </ul>
      </div>
    </details>

    <section className="guide-last-note">
      <strong>{text('A good QPort routine', 'Một thói quen dùng QPort tốt')}</strong>
      <p>{text(
        'Record real events → verify Holdings against the broker → let data sync → read the manager review → use Risk/Performance only when you need deeper evidence.',
        'Ghi đúng sự kiện thực tế → đối chiếu Holdings với broker → để dữ liệu sync → đọc Fund manager review → chỉ mở Risk/Performance khi cần bằng chứng sâu hơn.'
      )}</p>
    </section>
  </div>;
}
