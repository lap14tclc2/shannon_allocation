import React from 'react';
import AppNav from '../components/AppNav.jsx';

function Step({ number, title, children }) {
  return (
    <section className="guide-step-card">
      <span className="guide-step-number">{number}</span>
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
    </section>
  );
}

function PageCard({ href, title, question, children }) {
  return (
    <a className="guide-page-card" href={href}>
      <div>
        <h3>{title}</h3>
        <span>{question}</span>
      </div>
      <p>{children}</p>
      <b>→</b>
    </a>
  );
}

export default function GuidePage({ locale = 'vi' }) {
  return (
    <div className="page guide-page">
      <AppNav active="guide" locale={locale} />

      <header className="page-head guide-hero">
        <div>
          <div className="eyebrow">Hướng dẫn sử dụng QPort</div>
          <h1>Quản lý Danh mục & Định giá Doanh nghiệp Chuẩn xác</h1>
          <p className="muted">
            QPort là hệ thống thông tin phục vụ triết lý nắm giữ dài hạn (Buy & Hold) và định giá giá trị thực theo phương pháp Buffett–Munger. Dưới đây là lộ trình từ thiết lập danh mục đến khai thác toàn bộ công cụ phân tích.
          </p>
        </div>
      </header>

      <section className="guide-intro-card">
        <strong>Nguyên tắc Cốt lõi của QPort</strong>
        <p>
          QPort <b>không tự ý phát sinh lệnh Mua/Bán</b>. Biến động thị trường, thông tin rủi ro hay thời gian trôi qua không làm thay đổi số lượng cổ phiếu của bạn. Số dư chỉ thay đổi khi bạn chủ động ghi nhận giao dịch hoặc sự kiện quyền cụ thể.
        </p>
      </section>

      {/* 01: Setup */}
      <section className="guide-section">
        <div className="guide-section-head">
          <div><span>01</span><h2>Thiết lập lần đầu</h2></div>
          <p>Bắt đầu từ đúng trạng thái tài sản thực tế bạn đang nắm giữ tại các công ty chứng khoán.</p>
        </div>
        <div className="guide-start-grid">
          <Step number="1" title="Chọn danh mục">
            Sau khi đăng nhập, bạn có thể tạo và chuyển đổi linh hoạt giữa các danh mục độc lập tại trang <b>Danh mục</b> (ví dụ: Danh mục Cổ tức, Danh mục Tăng trưởng, Danh mục Hưu trí...).
          </Step>
          <Step number="2" title="Nhập cổ phiếu ban đầu">
            Vào <b>Giao dịch → Nhập danh mục ban đầu</b>. Với mỗi mã cổ phiếu, nhập đúng số lượng và giá vốn bình quân thực tế sau chia tách.
          </Step>
          <Step number="3" title="Nhập tiền mặt nếu muốn theo dõi">
            Nếu tài khoản còn số dư tiền mặt muốn tính vào Tổng tài sản (NAV), hãy tạo giao dịch <b>Nạp tiền</b> tương ứng.
          </Step>
          <Step number="4" title="Đối chiếu và Quan sát">
            Quay lại trang <b>Tổng quan</b> để kiểm tra số lượng, giá vốn, giá trị thị trường, tỷ trọng và lãi/lỗ tạm tính trước khi xem phần phân tích chuyên sâu.
          </Step>
        </div>
      </section>

      {/* 02: Page Directory */}
      <section className="guide-section">
        <div className="guide-section-head">
          <div><span>02</span><h2>Bản đồ tính năng: Mỗi trang dùng để làm gì?</h2></div>
          <p>Truy cập nhanh từng trang chức năng theo câu hỏi bạn muốn giải quyết.</p>
        </div>
        <div className="guide-page-grid">
          <PageCard href="/" title="Tổng quan" question="Hiện tại tôi đang sở hữu những gì?">
            Xem tổng tài sản, tiền mặt, lãi/lỗ danh mục, danh sách mã cổ phiếu nắm giữ, tỷ trọng và các điểm cần chú ý.
          </PageCard>
          <PageCard href="/portfolios" title="Các danh mục" question="Tôi đang quản lý những không gian nào?">
            Tạo mới, đổi tên, sao lưu và chuyển nhanh giữa các danh mục đầu tư độc lập.
          </PageCard>
          <PageCard href="/transactions" title="Giao dịch" question="Điều gì đã làm danh mục thay đổi?">
            Ghi nhận hoạt động mua/bán, nạp/rút tiền, điều chỉnh sai sót và xem toàn bộ nhật ký giao dịch kèm lý do.
          </PageCard>
          <PageCard href="/valuation" title="Định giá" question="Cổ phiếu tôi nắm giữ có giá trị thực là bao nhiêu?">
            Báo cáo tài chính kiểm toán, 40 mô hình định giá chuyên biệt (DCF chu kỳ, RIM Ngân hàng, SOTP...), dải 3 kịch bản giá trị và biên an toàn.
          </PageCard>
          <PageCard href="/screener" title="Bộ lọc Screener" question="Thị trường có những doanh nghiệp nào hảo hạng?">
            Sàng lọc 100 điểm chất lượng Buffett–Munger toàn thị trường Việt Nam (HOSE, HNX, UPCOM) và soi định giá chi tiết trực tiếp tại chỗ.
          </PageCard>
          <PageCard href="/dividends" title="Cổ tức" question="Dòng tiền cổ tức thực nhận của tôi như thế nào?">
            Theo dõi sự kiện chi trả cổ tức tiền mặt & cổ phiếu, đối soát khoản thực nhận về tài khoản và tính tỷ suất cổ tức thực tế.
          </PageCard>
          <PageCard href="/performance" title="Hiệu quả" question="Danh mục tăng trưởng ra sao theo thời gian?">
            Đo lường tỷ suất sinh lời TWR, XIRR, lợi suất từ đầu năm (YTD), mức sụt giảm tối đa từ đỉnh (Max Drawdown) và biểu đồ NAV.
          </PageCard>
          <PageCard href="/risk" title="Phân tích Rủi ro" question="Danh mục có những điểm rủi ro tiềm ẩn nào?">
            Phân tích mức độ tập trung tài sản, tương quan giữa các mã, ma trận biến động và đóng góp rủi ro (VaR, CVaR).
          </PageCard>
          <PageCard href="/snapshots" title="Nhật ký NAV" question="Lịch sử giá trị tài sản chính thức qua các mốc?">
            Xem lại các mốc snapshot tài sản được chốt chính thức theo ngày và chuỗi tăng trưởng lịch sử.
          </PageCard>
        </div>
      </section>

      {/* 03: Valuation Methodology */}
      <section className="guide-section">
        <div className="guide-section-head">
          <div><span>03</span><h2>Phương pháp Định giá Doanh nghiệp Buffett–Munger</h2></div>
          <p>Cách QPort tính toán Giá trị Nội tại (Intrinsic Value) và Biên An Toàn (Margin of Safety).</p>
        </div>
        <div className="guide-start-grid">
          <Step number="1" title="40 Mô hình Bản chất Kinh tế Chuyên biệt">
            Mỗi ngành có đặc thù sinh lời khác nhau. QPort không dùng công thức rập khuôn mà định tuyến tự động: Thu nhập Thặng dư (RIM) cho Ngân hàng; Dòng tiền Hợp đồng Thuê đất & RNAV cho BĐS KCN; Concession DCF (TV = 0) cho Tiện ích & Hạ tầng; DCF Chuẩn hóa chu kỳ cho Doanh nghiệp Sản xuất.
          </Step>
          <Step number="2" title="Bóc tách Lợi nhuận Thực (Owner Earnings)">
            QPort bóc tách lợi nhuận thực tế thuộc về chủ doanh nghiệp: <code>Owner Earnings = LNST + Khấu hao (D&A) - CapEx Bảo trì</code>, loại bỏ chi phí vốn mở rộng và các thủ thuật kế toán ghi nhận doanh thu ảo.
          </Step>
          <Step number="3" title="Dải 3 Kịch bản Giá trị Thực">
            Thay vì đưa ra 1 con số duy nhất, hệ thống xây dựng 3 kịch bản: <b>Thận trọng (Bear IV)</b>, <b>Cơ sở (Base IV)</b>, và <b>Lạc quan (Bull IV)</b> để nhà đầu tư có góc nhìn toàn diện trong các điều kiện vĩ mô khác nhau.
          </Step>
          <Step number="4" title="Thước đo Biên An Toàn Động (Margin of Safety)">
            Biên An Toàn (MoS) được xác định dựa trên 7 trụ cột chất lượng (Hào kinh tế Moat, Chất lượng tiền mặt, Pháo đài tài chính, Hiệu quả phân bổ vốn...). Doanh nghiệp càng chất lượng và dự đoán được, mức MoS yêu cầu càng tối ưu (20% – 50%).
          </Step>
        </div>
      </section>

      {/* 04: Recording Transactions Correctly */}
      <section className="guide-section">
        <div className="guide-section-head">
          <div><span>04</span><h2>Ghi nhận Giao dịch & Cổ tức đúng cách</h2></div>
          <p>Các quy tắc giúp số liệu danh mục luôn chính xác tuyệt đối.</p>
        </div>
        <div className="guide-task-list">
          <details open>
            <summary>Nhập danh mục ban đầu: Giá vốn sau điều chỉnh</summary>
            <p>
              Khi bắt đầu dùng QPort với danh mục đã có sẵn, hãy nhập <b>Số dư hiện tại</b> với giá vốn bình quân thực tế đã phản ánh các đợt chia tách / cổ tức cổ phiếu trong quá khứ. Đơn vị giá là <b>VND đầy đủ trên mỗi cổ phiếu</b> (ví dụ: <code>72000</code>, không nhập <code>72</code>).
            </p>
          </details>
          <details>
            <summary>Mua thêm hoặc Bán bớt cổ phiếu</summary>
            <p>
              Khi thực hiện giao dịch tại CTCK, hãy vào <b>Giao dịch → Mua thêm cổ phiếu</b> hoặc <b>Bán cổ phiếu</b>. Nhập ngày, số lượng và giá khớp lệnh thực tế. Hệ thống sẽ tự động tính lại số lượng tồn kho và lãi/lỗ đã chốt theo phương pháp FIFO.
            </p>
          </details>
          <details>
            <summary>Nhận Cổ tức Tiền mặt và Cổ phiếu</summary>
            <p>
              Tại trang <b>Cổ tức</b>, hệ thống ghi nhận các đợt trả cổ tức từ dữ liệu doanh nghiệp niêm yết. Cổ tức tiền mặt tự động tính thuế thu nhập cá nhân 5% và ghi nhận số tiền thực nhận; cổ tức cổ phiếu làm tăng số lượng nắm giữ và điều chỉnh giá vốn bình quân tương ứng.
            </p>
          </details>
          <details>
            <summary>Sửa đổi hoặc Hủy bỏ giao dịch nhập nhầm</summary>
            <p>
              Mọi chỉnh sửa trong Lịch sử giao dịch đều được ghi vết (Audit trail). Bạn có thể sửa giá, số lượng hoặc loại bỏ giao dịch sai kèm lý do để đối soát sau này.
            </p>
          </details>
        </div>
      </section>

      {/* 05: Habits & FAQ */}
      <section className="guide-section">
        <div className="guide-section-head">
          <div><span>05</span><h2>Thói quen sử dụng đơn giản</h2></div>
          <p>Nhà đầu tư dài hạn không cần mở bảng điện liên tục trong ngày.</p>
        </div>
        <div className="guide-faq-grid">
          <div>
            <h3>Sau khi phát sinh giao dịch</h3>
            <p>Ghi lại lệnh mua/bán hoặc nạp/rút tiền vào QPort để số dư luôn đồng bộ với tài khoản chứng khoán.</p>
          </div>
          <div>
            <h3>Sau giờ đóng cửa phiên</h3>
            <p>Nhấn nút <b>Đồng bộ dữ liệu</b> nếu muốn cập nhật thị giá mới nhất từ sàn giao dịch.</p>
          </div>
          <div>
            <h3>Khi mùa BCTC công bố</h3>
            <p>Mở trang <b>Định giá</b> hoặc <b>Bộ lọc Screener</b> để cập nhật lại kết quả kinh doanh, điểm chất lượng và giá trị thực mới của doanh nghiệp.</p>
          </div>
          <div>
            <h3>Định kỳ hàng quý</h3>
            <p>Đối chiếu lại tổng tài sản và số lượng cổ phiếu với sao kê CTCK để đảm bảo không bỏ sót sự kiện quyền nào.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
