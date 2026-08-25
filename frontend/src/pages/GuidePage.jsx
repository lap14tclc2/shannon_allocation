import React from 'react';
import AppNav from '../components/AppNav.jsx';

function Step({ number, title, children }) {
  return <section className="guide-step-card"><span className="guide-step-number">{number}</span><div><h3>{title}</h3><p>{children}</p></div></section>;
}

function PageCard({ href, title, question, children }) {
  return <a className="guide-page-card" href={href}><div><h3>{title}</h3><span>{question}</span></div><p>{children}</p><b>→</b></a>;
}

export default function GuidePage({ locale = 'vi' }) {
  return <div className="page guide-page">
    <AppNav active="guide" locale={locale} />

    <header className="page-head guide-hero">
      <div>
        <div className="eyebrow">Hướng dẫn sử dụng QPort</div>
        <h1>Bắt đầu quản lý danh mục trong vài bước</h1>
        <p className="muted">QPort dành cho việc theo dõi danh mục bạn thực sự sở hữu. Hãy nhập đúng cổ phiếu, giá vốn và giao dịch; hệ thống sẽ tự tính giá trị, lãi/lỗ và lịch sử.</p>
      </div>
    </header>

    <section className="guide-intro-card">
      <strong>Một nguyên tắc cần nhớ</strong>
      <p>QPort không tự mua bán thay bạn. Số cổ phiếu chỉ thay đổi khi có giao dịch hoặc sự kiện doanh nghiệp thực sự được ghi nhận.</p>
    </section>

    <section className="guide-section">
      <div className="guide-section-head"><div><span>01</span><h2>Thiết lập lần đầu</h2></div><p>Nếu bạn đã có cổ phiếu ở CTCK, hãy bắt đầu từ đúng trạng thái hiện tại.</p></div>
      <div className="guide-start-grid">
        <Step number="1" title="Chọn danh mục">Sau khi đăng nhập, dùng bộ chuyển danh mục trên thanh điều hướng. Dữ liệu cũ nằm trong “Danh mục mặc định”; có thể tạo thêm không gian độc lập tại trang Danh mục.</Step>
        <Step number="2" title="Nhập cổ phiếu đang sở hữu">Vào Giao dịch → Nhập danh mục ban đầu. Với mỗi mã, nhập đúng số lượng và giá vốn đang theo dõi tại CTCK.</Step>
        <Step number="3" title="Nhập tiền mặt nếu muốn theo dõi">Nếu tài khoản còn tiền mặt và bạn muốn QPort tính vào tổng tài sản, hãy ghi một giao dịch Nạp tiền tương ứng.</Step>
        <Step number="4" title="Đối chiếu với CTCK">Quay lại Danh mục và kiểm tra số lượng, giá vốn, giá trị hiện tại, lãi/lỗ và tiền mặt. Chỉ dùng phần phân tích sau khi các số này đã đúng.</Step>
      </div>
    </section>

    <section className="guide-section">
      <div className="guide-section-head"><div><span>02</span><h2>Mỗi trang dùng để làm gì?</h2></div><p>Chọn trang theo câu hỏi bạn muốn trả lời.</p></div>
      <div className="guide-page-grid">
        <PageCard href="/portfolios" title="Các danh mục" question="Tôi đang quản lý những tài sản nào?">Tạo, đổi tên và chuyển nhanh giữa các danh mục độc lập theo mục tiêu hoặc tài khoản.</PageCard>
        <PageCard href="/" title="Danh mục" question="Hiện tại tôi đang có gì?">Xem tổng tài sản, tiền mặt, lãi/lỗ, từng mã cổ phiếu và những điểm đáng chú ý.</PageCard>
        <PageCard href="/transactions" title="Giao dịch" question="Điều gì đã làm danh mục thay đổi?">Thêm mua/bán, nạp/rút tiền, nhập danh mục ban đầu và sửa dữ liệu nếu nhập nhầm.</PageCard>
        <PageCard href="/performance" title="Hiệu quả" question="Danh mục của tôi đã tăng trưởng thế nào?">Xem tổng lãi/lỗ, lợi suất từ đầu năm, mức giảm từ đỉnh và biểu đồ giá trị danh mục.</PageCard>
        <PageCard href="/risk" title="Phân tích" question="Danh mục có điểm nào đáng lo?">Xem mức tập trung, tương quan giữa các mã, biến động và mã ảnh hưởng rủi ro nhiều nhất.</PageCard>
      </div>
    </section>

    <section className="guide-section">
      <div className="guide-section-head"><div><span>03</span><h2>Ghi giao dịch đúng cách</h2></div><p>Chọn loại giao dịch khớp với điều thực sự xảy ra.</p></div>
      <div className="guide-task-list">
        <details open><summary>Tôi đã có cổ phiếu trước khi dùng QPort</summary><p>Dùng <b>Nhập danh mục ban đầu</b>. Nhập số lượng hiện có và giá vốn thực tế. Không cần tạo các lệnh mua giả trong quá khứ.</p></details>
        <details><summary>Tôi vừa mua thêm cổ phiếu</summary><p>Dùng <b>Mua thêm cổ phiếu</b>, nhập ngày giao dịch, mã, số lượng và giá mua thực tế. Có thể bổ sung CTCK, tài khoản, phí và thuế.</p></details>
        <details><summary>Tôi vừa bán cổ phiếu</summary><p>Dùng <b>Bán cổ phiếu</b> với ngày, số lượng và giá bán thực tế. QPort sẽ tính lại số lượng còn lại và lãi/lỗ đã chốt.</p></details>
        <details><summary>Tôi nhập sai một giao dịch</summary><p>Trong Lịch sử giao dịch, chọn <b>Sửa</b> hoặc <b>Loại bỏ</b>. QPort yêu cầu lý do để bạn có thể kiểm tra lại lịch sử thay đổi sau này.</p></details>
        <details><summary>Tôi nhận cổ tức</summary><p>QPort có thể lấy thông tin cổ tức từ nguồn dữ liệu và ghi nhận khoản đã nhận khi có đủ thông tin. Cổ tức tiền mặt được tính riêng phần trước thuế, thuế khấu trừ và số tiền thực nhận.</p></details>
      </div>
    </section>

    <section className="guide-section guide-two-column">
      <article className="card guide-friendly-card">
        <div className="eyebrow">Lãi/lỗ</div>
        <h2>Đọc các con số trên Danh mục</h2>
        <div className="guide-mini-rule"><b>Giá vốn:</b> số tiền bình quân bạn đã bỏ ra cho mỗi cổ phiếu đang còn nắm giữ.</div>
        <div className="guide-mini-rule"><b>Giá trị:</b> số lượng cổ phiếu × giá thị trường gần nhất.</div>
        <div className="guide-mini-rule"><b>Lãi/lỗ tạm tính:</b> chênh lệch giữa giá trị hiện tại và giá vốn của phần cổ phiếu chưa bán.</div>
        <div className="guide-mini-rule"><b>Tỷ trọng:</b> phần giá trị của một mã so với toàn bộ danh mục.</div>
      </article>

      <article className="card guide-friendly-card">
        <div className="eyebrow">Phân tích</div>
        <h2>Khi nào nên xem phần nâng cao?</h2>
        <p>Phần lớn thời gian bạn chỉ cần Danh mục và Giao dịch. Mở Phân tích khi muốn kiểm tra danh mục có quá tập trung, các mã có biến động cùng nhau hay mức biến động gần đây có tăng mạnh hay không.</p>
        <div className="guide-mini-rule">Các chỉ số như TWR, XIRR, VaR hay CVaR vẫn được giữ cho người cần phân tích sâu, nhưng không cần hiểu chúng để sử dụng QPort hằng ngày.</div>
      </article>
    </section>

    <section className="guide-section">
      <div className="guide-section-head"><div><span>04</span><h2>Thói quen sử dụng đơn giản</h2></div><p>Không cần mở QPort liên tục trong ngày.</p></div>
      <div className="guide-start-grid">
        <Step number="1" title="Sau khi có giao dịch">Ghi mua/bán hoặc dòng tiền vào QPort để danh mục luôn khớp với tài khoản thực tế.</Step>
        <Step number="2" title="Sau khi thị trường đóng cửa">Nhấn Cập nhật dữ liệu nếu muốn lấy giá mới ngay. Hệ thống cũng có thể đồng bộ theo lịch cấu hình.</Step>
        <Step number="3" title="Kiểm tra điểm cần chú ý">Nếu Dashboard xuất hiện cảnh báo, mở Phân tích để hiểu nguyên nhân. Không coi cảnh báo là lệnh bán tự động.</Step>
        <Step number="4" title="Định kỳ">Đối chiếu số lượng và giá vốn với CTCK, đặc biệt sau cổ tức cổ phiếu, quyền mua, tách/gộp hoặc chuyển chứng khoán.</Step>
      </div>
    </section>

    <section className="guide-section">
      <div className="guide-section-head"><div><span>05</span><h2>Nếu số liệu trông không đúng</h2></div><p>Kiểm tra từ nguồn đơn giản nhất.</p></div>
      <div className="guide-faq-grid">
        <div><h3>Số lượng hoặc giá vốn sai</h3><p>Kiểm tra Lịch sử giao dịch trước. Danh mục được tính từ các giao dịch đã ghi.</p></div>
        <div><h3>Giá hiện tại chưa đúng</h3><p>Nhấn Cập nhật dữ liệu. Nếu một mã chưa có giá mới, QPort sẽ không tự thay đổi số cổ phiếu của bạn.</p></div>
        <div><h3>Lợi nhuận khác CTCK</h3><p>Kiểm tra giá vốn, phí, thuế, cổ tức và cách CTCK đang tính giá vốn. Đây là các nguyên nhân phổ biến gây chênh lệch.</p></div>
        <div><h3>Phân tích chưa có số liệu</h3><p>Danh mục mới có thể chưa đủ lịch sử giá. Các chỉ số sẽ xuất hiện dần khi QPort có thêm dữ liệu.</p></div>
      </div>
    </section>
  </div>;
}
