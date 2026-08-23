import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

const STEPS = [
  ['guide.step1', 'guide.step1_body'],
  ['guide.step2', 'guide.step2_body'],
  ['guide.step3', 'guide.step3_body'],
  ['guide.step4', 'guide.step4_body'],
  ['guide.step5', 'guide.step5_body'],
  ['guide.step6', 'guide.step6_body'],
  ['guide.step7', 'guide.step7_body'],
  ['guide.step8', 'guide.step8_body'],
  ['guide.step9', 'guide.step9_body'],
  ['guide.step10', 'guide.step10_body'],
];

const WARNINGS = ['guide.warning_1', 'guide.warning_2', 'guide.warning_3'];

export default function GuidePage({ locale = 'en' }) {
  const { t } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  return (
    <div className="page">
      <AppNav active="guide" locale={locale} />
      <header className="page-head"><div><h1>{t('guide.title')}</h1><p className="muted">{t('guide.subtitle')}</p></div></header>

      <div className="card guide-principle"><h3>{t('guide.principle')}</h3><p>{text('QPort is a Buy & Hold portfolio information system. Only explicit ledger events change shares or cash. Market prices, risk metrics and calendar time never create trades.', 'QPort là hệ thống thông tin danh mục Buy & Hold. Chỉ các sự kiện sổ cái rõ ràng mới thay đổi cổ phiếu hoặc tiền mặt. Giá thị trường, chỉ số rủi ro và thời gian không bao giờ tự tạo giao dịch.')}</p></div>

      <div className="card"><div className="section-head"><div><h3>{t('guide.quick_start')}</h3><div className="muted">QPort operational workflow</div></div></div><pre className="guide-code"><code>{`cd frontend\nnpm ci\nnpm run build\nnpm run build:ssr\n\ncd ../python\npip install -r requirements.txt\npython serve.py`}</code></pre></div>

      <div className="guide-steps">{STEPS.map(([titleKey, bodyKey]) => <section className="card" key={titleKey}><h3>{t(titleKey)}</h3><p>{t(bodyKey)}</p></section>)}</div>

      <div className="card"><h3>{text('Data integrity rules', 'Quy tắc giữ dữ liệu sạch')}</h3><div className="rule-list">
        <div>✓ {text('Trade/import prices use full VND per share: enter 72,000, not 72. Suspicious sub-1,000 VND values are rejected.', 'Giá giao dịch/nhập vị thế dùng VND đầy đủ mỗi cổ phiếu: nhập 72.000, không phải 72. Giá đáng ngờ dưới 1.000 VND sẽ bị từ chối.')}</div>
        <div>✓ {text('Future-dated ledger events are rejected. Quantity, price, cash amount and split ratio must be positive when required.', 'Sự kiện sổ cái ở ngày tương lai bị từ chối. Số lượng, giá, số tiền và tỷ lệ split phải lớn hơn 0 khi được yêu cầu.')}</div>
        <div>✓ {text('Ticker symbols are normalized to uppercase letters/digits; notes are limited to 500 characters; irrelevant form fields are discarded before writing the ledger.', 'Mã cổ phiếu được chuẩn hóa thành chữ hoa/số; ghi chú tối đa 500 ký tự; các field không liên quan bị loại trước khi ghi ledger.')}</div>
        <div>✓ {text('Reference weights must cover every current holding and total exactly 100%.', 'Tỷ trọng tham chiếu phải bao phủ toàn bộ mã đang nắm giữ và cộng đúng 100%.')}</div>
      </div></div>

      <div className="card"><h3>{text('Understand MONITOR, cash and performance', 'Hiểu THEO DÕI, tiền mặt và hiệu suất')}</h3><div className="rule-list">
        <div>✓ {text('MONITOR means no explicit strategic target is configured. It is not a HOLD recommendation.', 'THEO DÕI nghĩa là chưa có mục tiêu chiến lược rõ ràng. Đây không phải khuyến nghị GIỮ.')}</div>
        <div>✓ {text('Available cash is not automatically deployable. QPort only computes deployable cash after you explicitly set a strategic cash reserve and target weights. Enter reserve 0 only if that is intentional.', 'Tiền mặt khả dụng không tự động là tiền có thể phân bổ. QPort chỉ tính tiền có thể phân bổ sau khi bạn đặt rõ mức dự trữ tiền mặt và tỷ trọng mục tiêu. Chỉ đặt dự trữ 0 khi đó là chủ ý.')}</div>
        <div>✓ {text('If there are fewer than two official snapshots, drawdown is N/A — never a false 0%.', 'Nếu có ít hơn hai snapshot chính thức, drawdown là N/A — không bao giờ giả thành 0%.')}</div>
        <div>✓ {text('Opening-position imports establish current shares/cost basis, but do not prove historical cash-flow dates. XIRR remains unavailable until cash-flow history is trustworthy.', 'Nhập vị thế ban đầu xác lập số cổ phiếu/giá vốn hiện tại nhưng không chứng minh ngày dòng tiền lịch sử. XIRR chưa được tính cho đến khi lịch sử dòng tiền đáng tin cậy.')}</div>
      </div></div>

      <div className="card"><h3>{text('Three actions new users usually miss', 'Ba thao tác người dùng mới thường bỏ sót')}</h3><div className="rule-list"><div>✓ {text('Record portfolio cash on the Portfolio page or as a Cash deposit event. Without it, BUY transactions correctly fail for insufficient cash.', 'Ghi số tiền mặt của danh mục ngay trên trang Danh mục hoặc bằng sự kiện Nạp tiền. Nếu chưa có tiền, giao dịch MUA sẽ bị từ chối đúng quy tắc.')}</div><div>✓ {text('After importing holdings, run Sync. Performance tracking starts only from valid market sessions on or after the ledger effective date; QPort does not invent pre-import performance history.', 'Sau khi nhập vị thế, chạy Đồng bộ. Theo dõi hiệu suất chỉ bắt đầu từ phiên thị trường hợp lệ bằng hoặc sau ngày hiệu lực trong ledger; QPort không bịa lịch sử hiệu suất trước ngày nhập.')}</div><div>✓ {text('When you want an AI to review the portfolio, click “Export for AI” on Portfolio. Upload the generated Markdown file instead of sending screenshots. Schema v2 includes separate portfolio/market/performance dates, methodology, data lineage and machine-readable JSON.', 'Khi muốn AI đánh giá danh mục, bấm “Xuất dữ liệu cho AI” trên trang Danh mục. Tải file Markdown lên AI thay vì gửi screenshot. Schema v2 tách ngày trạng thái danh mục/dữ liệu thị trường/hiệu suất, kèm methodology, data lineage và JSON machine-readable.')}</div></div></div>

      <div className="card warning-card"><h3>{t('guide.warning_title')}</h3><div className="rule-list">{WARNINGS.map((key) => <div key={key}>✓ {t(key)}</div>)}</div></div>

      <div className="card"><h3>{t('guide.full_docs')}</h3><div className="button-row"><a className="btn-export" href="https://github.com/lap14tclc2/shannon_allocation/blob/refactor-buy-hold/docs/USER_GUIDE_EN.md">{t('guide.english_doc')}</a><a className="btn-variant" href="https://github.com/lap14tclc2/shannon_allocation/blob/refactor-buy-hold/docs/USER_GUIDE_VI.md">{t('guide.vietnamese_doc')}</a></div></div>
    </div>
  );
}
