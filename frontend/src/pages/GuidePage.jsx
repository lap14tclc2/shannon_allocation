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

function ActionStep({ step, title, action, expected }) {
  return (
    <div className="guide-action-step-card">
      <div className="step-head">
        <span className="step-badge">{step}</span>
        <h3>{title}</h3>
      </div>
      <div className="step-details">
        <div className="step-box">
          <small>Thao tác của bạn</small>
          <div>{action}</div>
        </div>
        <div className="step-box">
          <small>Kết quả hiển thị</small>
          <div>{expected}</div>
        </div>
      </div>
    </div>
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
          <h1>Quản lý Danh mục &amp; Định giá Doanh nghiệp Chuẩn xác</h1>
          <p className="muted">
            QPort là hệ thống thông tin phục vụ triết lý nắm giữ dài hạn (Buy &amp; Hold) và định giá giá trị thực theo phương pháp Buffett–Munger. Dưới đây là tài liệu hướng dẫn toàn diện từ cách thao tác trên QPort Terminal đến khai thác 12 chiều chất lượng tài chính và định giá chuyên sâu.
          </p>
        </div>
      </header>

      {/* Core Principle Callout */}
      <section className="guide-intro-card">
        <strong>Nguyên tắc Bất biến của Sổ cái QPort (Buy &amp; Hold Invariant)</strong>
        <p>
          QPort <b>không tự ý phát sinh lệnh Mua/Bán</b>. Biến động giá thị trường, thông tin rủi ro hay thời gian trôi qua không làm thay đổi số lượng cổ phiếu của bạn. Số dư cổ phiếu và tiền mặt chỉ thay đổi khi bạn chủ động ghi nhận giao dịch hoặc cập nhật vị thế.
        </p>
      </section>

      {/* Navigation Pills (TOC) */}
      <nav className="guide-nav-pills" aria-label="Mục lục hướng dẫn">
        <a className="guide-pill" href="#terminal"><span>01</span> QPort Terminal</a>
        <a className="guide-pill" href="#quickstart"><span>02</span> Khởi động nhanh (Quick Start)</a>
        <a className="guide-pill" href="#portfolio-example"><span>03</span> Ví dụ danh mục</a>
        <a className="guide-pill" href="#positions"><span>04</span> Quản lý vị thế &amp; Tiền mặt</a>
        <a className="guide-pill" href="#fields"><span>05</span> Các cột dữ liệu Terminal</a>
        <a className="guide-pill" href="#financial-data"><span>06</span> Dữ liệu BCTC &amp; SSI</a>
        <a className="guide-pill" href="#buffett-munger"><span>07</span> Phân tích Buffett–Munger &amp; Bẫy giá trị</a>
        <a className="guide-pill" href="#comparison"><span>08</span> So sánh Terminal vs Web UI</a>
        <a className="guide-pill" href="#corporate-actions"><span>09</span> Giá sau chia &amp; Cổ tức</a>
        <a className="guide-pill" href="#common-mistakes"><span>10</span> Các lỗi thường gặp</a>
        <a className="guide-pill" href="#pages"><span>11</span> Bản đồ tính năng</a>
      </nav>

      {/* 01: QPORT TERMINAL OVERVIEW */}
      <section id="terminal" className="guide-section">
        <div className="guide-section-head">
          <div><span>01</span><h2>QPort Terminal — Trung tâm Quyết định Vốn Cá nhân</h2></div>
          <p>Bảng điều khiển trung tâm tích hợp quản lý danh mục và định giá doanh nghiệp.</p>
        </div>
        <div className="guide-start-grid">
          <Step number="1" title="Quản lý vị thế danh mục một chạm">
            Xem toàn bộ danh mục thực tế đang nắm giữ, thêm cổ phiếu mới qua thanh tìm kiếm thông minh, chỉnh sửa số lượng, cập nhật giá vốn hoặc xóa vị thế nhanh chóng.
          </Step>
          <Step number="2" title="Quản lý số dư tiền mặt">
            Ghi nhận và cập nhật lượng tiền mặt khả dụng để hệ thống tính toán chính xác tổng tài sản danh mục (NAV) và tỷ trọng phân bổ giữa các tài sản.
          </Step>
          <Step number="3" title="Pháo đài tài chính cá nhân">
            Đo lường số tháng sinh tồn của quỹ dự phòng, vốn khả dụng dài hạn, tiền mặt cơ hội và trạng thái nghĩa vụ nợ ngắn hạn trước khi giải ngân.
          </Step>
          <Step number="4" title="Ma trận quyết định Buffett–Munger">
            Tự động tổng hợp chất lượng 12 chiều, giá trị nội tại cơ sở (Base IV), biên an toàn thực tế và cảnh báo bẫy giá trị cho từng mã trong danh mục.
          </Step>
        </div>
      </section>

      {/* 02: QUICK START (9 STEPS) */}
      <section id="quickstart" className="guide-section">
        <div className="guide-section-head">
          <div><span>02</span><h2>Hướng dẫn Khởi động Nhanh (9 Bước)</h2></div>
          <p>Từ thiết lập danh mục đầu tiên đến đọc báo cáo phân tích giá trị.</p>
        </div>
        <div className="guide-step-action-grid">
          <ActionStep
            step="1"
            title="Mở QPort Terminal"
            action="Truy cập đường dẫn trang chủ (/) hoặc chọn 'Terminal' từ menu điều hướng trên thanh tiêu đề."
            expected="Màn hình Terminal hiển thị bảng 'Danh Mục', Pháo đài tài chính cá nhân và Ma trận quyết định."
          />
          <ActionStep
            step="2"
            title="Xem danh mục hiện tại"
            action="Quan sát bảng 'Danh Mục' ở đầu trang để kiểm tra các mã cổ phiếu đang nắm giữ."
            expected="Nếu chưa có cổ phiếu nào, hệ thống thông báo 'Chưa có vị thế nào — Nhấn + Thêm vị thế để bắt đầu'."
          />
          <ActionStep
            step="3"
            title="Thêm một mã cổ phiếu"
            action="Nhấn nút '+ Thêm vị thế' ở góc trên bên phải bảng danh mục để mở hộp thoại thêm mới."
            expected="Hộp thoại 'Thêm vị thế' xuất hiện với ô tìm kiếm mã cổ phiếu (Symbol Suggest) tự động gợi ý."
          />
          <ActionStep
            step="4"
            title="Chọn mã &amp; Nhập số lượng"
            action="Gõ mã chứng khoán (ví dụ: FPT) hoặc tên công ty, chọn mã và nhập số lượng cổ phiếu nắm giữ (ví dụ: 3000)."
            expected="Hệ thống tự động điền mã chứng khoán viết hoa và kiểm tra số lượng phải lớn hơn 0."
          />
          <ActionStep
            step="5"
            title="Nhập giá vốn bình quân"
            action="Nhập giá vốn bình quân thực tế theo đơn vị VND đầy đủ trên mỗi cổ phiếu (ví dụ: 73800, không nhập 73.8)."
            expected="Hệ thống xác thực giá vốn tối thiểu từ 1,000 VND và kích hoạt nút 'Thêm vị thế'."
          />
          <ActionStep
            step="6"
            title="Xem lại danh mục"
            action="Nhấn 'Thêm vị thế' để lưu. Bảng danh mục sẽ tự động làm mới số liệu."
            expected="Dòng cổ phiếu hiển thị đầy đủ: Số lượng, Giá vốn, Giá thị trường, Vốn đầu tư, Giá trị TT, Lãi/Lỗ và Tỷ trọng."
          />
          <ActionStep
            step="7"
            title="Xóa một mã nếu cần"
            action="Tại dòng cổ phiếu muốn gỡ bỏ, nhấn nút 'Xóa', sau đó nhấn xác nhận 'Xóa' trong hộp thoại."
            expected="Vị thế được xóa khỏi danh mục cá nhân. Dữ liệu phân tích tài chính của mã trong cơ sở dữ liệu vẫn được bảo lưu an toàn."
          />
          <ActionStep
            step="8"
            title="Cập nhật số dư tiền mặt"
            action="Tại phần tóm tắt chân bảng, nhấn nút 'Sửa' cạnh mục 'Tiền mặt', nhập số tiền khả dụng (ví dụ: 100000000) và nhấn 'Lưu'."
            expected="Số dư tiền mặt được cập nhật, Tổng danh mục (NAV) và Tỷ trọng các mã tự động tính toán lại."
          />
          <ActionStep
            step="9"
            title="Chạy &amp; Xem phân tích giá trị"
            action="Cuộn xuống các khối phân tích bên dưới: Lời khuyên HLV Buffett &amp; Munger, Pháo đài tài chính, Cần chú ý đặc biệt và Ma trận quyết định."
            expected="Toàn bộ khuyến nghị nắm giữ, giá trị thực, biên an toàn và chẩn đoán bẫy giá trị được cập nhật theo danh mục của bạn."
          />
        </div>
      </section>

      {/* 03: PORTFOLIO EXAMPLE */}
      <section id="portfolio-example" className="guide-section">
        <div className="guide-section-head">
          <div><span>03</span><h2>Ví dụ Minh họa Danh mục Đầu tư</h2></div>
          <p>Mô phỏng cơ cấu danh mục thực tế của một nhà đầu tư dài hạn.</p>
        </div>
        <div className="guide-example-box">
          <h4>Ví dụ Cơ cấu Danh mục Minh họa</h4>
          <div className="guide-table-wrap" style={{ margin: '8px 0 12px' }}>
            <table className="guide-table">
              <thead>
                <tr>
                  <th>Tài sản</th>
                  <th style={{ textAlign: 'right' }}>Số lượng</th>
                  <th style={{ textAlign: 'right' }}>Giá vốn bình quân</th>
                  <th style={{ textAlign: 'right' }}>Tổng vốn đầu tư</th>
                  <th>Ghi chú</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>FPT</strong></td>
                  <td style={{ textAlign: 'right' }}>3,000 cổ phiếu</td>
                  <td style={{ textAlign: 'right' }}>73,800 ₫</td>
                  <td style={{ textAlign: 'right' }}>221,400,000 ₫</td>
                  <td>Cổ phiếu công nghệ hàng đầu</td>
                </tr>
                <tr>
                  <td><strong>ACB</strong></td>
                  <td style={{ textAlign: 'right' }}>19,210 cổ phiếu</td>
                  <td style={{ textAlign: 'right' }}>19,780 ₫</td>
                  <td style={{ textAlign: 'right' }}>379,973,800 ₫</td>
                  <td>Ngân hàng quản trị rủi ro thận trọng</td>
                </tr>
                <tr>
                  <td><strong>Tiền mặt</strong></td>
                  <td style={{ textAlign: 'right' }}>—</td>
                  <td style={{ textAlign: 'right' }}>—</td>
                  <td style={{ textAlign: 'right' }}>100,000,000 ₫</td>
                  <td>Dự phòng cơ hội giải ngân</td>
                </tr>
                <tr style={{ fontWeight: 700 }}>
                  <td>Tổng danh mục</td>
                  <td style={{ textAlign: 'right' }}>22,210 cổ phiếu</td>
                  <td style={{ textAlign: 'right' }}>—</td>
                  <td style={{ textAlign: 'right' }}>701,373,800 ₫</td>
                  <td>Vốn cổ phiếu (601.37 tr) + Tiền mặt (100 tr)</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>
            <em>* Lưu ý: Đây là ví dụ trực quan nhằm minh họa cách thức hiển thị và tính toán trong QPort Terminal. Hệ thống không hard-code các giá trị này vào mã nguồn ứng dụng.</em>
          </p>
        </div>
      </section>

      {/* 04: ADD / EDIT / REMOVE POSITIONS & CASH */}
      <section id="positions" className="guide-section">
        <div className="guide-section-head">
          <div><span>04</span><h2>Thao tác Vị thế &amp; Quản lý Tiền mặt</h2></div>
          <p>Quy chuẩn nhập liệu chính xác để bảo toàn tính toàn vẹn số liệu.</p>
        </div>

        <div className="guide-two-column">
          <div className="guide-status-grid">
            <div>
              <b>1. Thêm vị thế mới</b>
              <p>
                Nhấn <b>+ Thêm vị thế</b>. Sử dụng ô tìm kiếm để gõ mã chứng khoán (ví dụ: FPT, HPG, MBB) hoặc tên công ty. Nhập số lượng và giá vốn bình quân thực tế sau chia tách.
              </p>
            </div>
            <div>
              <b>2. Chỉnh sửa vị thế hiện có</b>
              <p>
                Tại bảng danh mục, nhấn nút <b>Sửa</b> tại dòng cổ phiếu tương ứng để điều chỉnh lại số lượng cổ phiếu nắm giữ hoặc cập nhật lại giá vốn bình quân khi có biến động.
              </p>
            </div>
            <div>
              <b>3. Xóa vị thế an toàn</b>
              <p>
                Nhấn nút <b>Xóa</b> và xác nhận trong hộp thoại. Thao tác này loại bỏ vị thế khỏi danh mục đầu tư cá nhân của bạn trên Terminal.
              </p>
            </div>
            <div>
              <b>4. Quản lý Tiền mặt (Cash)</b>
              <p>
                Tiền mặt là một loại tài sản trong portfolio, không phải một mã cổ phiếu. Nhấn nút <b>Sửa</b> tại ô Tiền mặt ở chân bảng để cập nhật số dư khả dụng (VND).
              </p>
            </div>
          </div>
        </div>

        <div className="guide-callout warning">
          <strong>Phân biệt rõ ràng: Vị thế Danh mục (Portfolio Position) vs Dữ liệu Tài chính (Financial Data)</strong>
          Khi bạn xóa một vị thế khỏi danh mục đầu tư cá nhân, hệ thống <b>chỉ loại bỏ mã đó khỏi sổ tài sản của bạn</b>. Toàn bộ dữ liệu BCTC, lịch sử cổ tức, mô hình định giá và phân tích 12 chiều của mã cổ phiếu đó trong cơ sở dữ liệu hệ thống <b>vẫn được lưu trữ đầy đủ và nguyên vẹn</b>.
        </div>

        <div className="guide-callout">
          <strong>Quy tắc Kiểm tra Tính Hợp lệ Khi Nhập Liệu (Validation Rules)</strong>
          <ul style={{ margin: '6px 0 0', paddingLeft: 20 }}>
            <li><b>Mã cổ phiếu (Symbol):</b> Bắt buộc từ 2 đến 10 ký tự chữ hoặc số viết hoa (ví dụ: <code>FPT</code>, <code>VND</code>, <code>TCB</code>).</li>
            <li><b>Số lượng (Quantity):</b> Bắt buộc là số dương lớn hơn 0 (ví dụ: <code>3000</code>).</li>
            <li><b>Giá vốn bình quân (Average Cost):</b> Phải là số dương từ <code>1,000 VND</code> trở lên. Nhập đầy đủ đơn vị VND (ví dụ: <code>73800</code>, không nhập <code>73.8</code> hay <code>73.8k</code>).</li>
          </ul>
        </div>
      </section>

      {/* 05: TERMINAL OUTPUT FIELDS EXPLAINED */}
      <section id="fields" className="guide-section">
        <div className="guide-section-head">
          <div><span>05</span><h2>Ý nghĩa Các Cột Thông tin trên QPort Terminal</h2></div>
          <p>Hiểu chính xác từng chỉ số hiển thị trên bảng danh mục.</p>
        </div>
        <div className="guide-table-wrap">
          <table className="guide-table">
            <thead>
              <tr>
                <th>Cột thông tin</th>
                <th>Tên tiếng Anh</th>
                <th>Ý nghĩa và Công thức tính</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Mã</strong></td>
                <td>Symbol</td>
                <td>Mã chứng khoán niêm yết trên các sàn HOSE, HNX hoặc UPCOM.</td>
              </tr>
              <tr>
                <td><strong>SL</strong></td>
                <td>Shares / Quantity</td>
                <td>Số lượng cổ phiếu thực tế bạn đang nắm giữ trong danh mục.</td>
              </tr>
              <tr>
                <td><strong>Giá vốn</strong></td>
                <td>Average Cost</td>
                <td>Giá vốn bình quân trên mỗi cổ phiếu (đã bao gồm phí và phản ánh các đợt chia tách).</td>
              </tr>
              <tr>
                <td><strong>Giá TT</strong></td>
                <td>Market Price</td>
                <td>Giá thị trường gần nhất được cập nhật từ sàn giao dịch (hoặc thông báo <em>Chưa có giá TT</em>).</td>
              </tr>
              <tr>
                <td><strong>Vốn đầu tư</strong></td>
                <td>Invested Value</td>
                <td>Tổng số tiền vốn bạn đã bỏ ra để mua số cổ phiếu này (<code>Vốn đầu tư = SL × Giá vốn</code>).</td>
              </tr>
              <tr>
                <td><strong>Giá trị TT</strong></td>
                <td>Market Value</td>
                <td>Tổng giá trị tài sản tính theo thị giá hiện hành (<code>Giá trị TT = SL × Giá TT</code>).</td>
              </tr>
              <tr>
                <td><strong>Lãi / Lỗ</strong></td>
                <td>Unrealized P/L</td>
                <td>Số tiền lãi hoặc lỗ tạm tính chưa thực hiện (<code>Lãi / Lỗ = Giá trị TT - Vốn đầu tư</code>).</td>
              </tr>
              <tr>
                <td><strong>L/L%</strong></td>
                <td>Unrealized P/L %</td>
                <td>Tỷ lệ phần trăm sinh lời tạm tính trên vốn (<code>L/L% = (Lãi / Lỗ) / Vốn đầu tư × 100%</code>).</td>
              </tr>
              <tr>
                <td><strong>Tỷ trọng</strong></td>
                <td>Portfolio Weight</td>
                <td>Tỷ lệ phần trăm giá trị của mã cổ phiếu trên tổng giá trị toàn bộ danh mục (bao gồm cả tiền mặt).</td>
              </tr>
              <tr>
                <td><strong>Tiền mặt</strong></td>
                <td>Cash Reserve</td>
                <td>Lượng tiền mặt sẵn sàng giải ngân hoặc dự phòng sinh tồn trong danh mục.</td>
              </tr>
              <tr>
                <td><strong>Tổng danh mục</strong></td>
                <td>Total Portfolio Value</td>
                <td>Tổng tài sản ròng (NAV) của danh mục (<code>Tổng danh mục = Tổng Giá trị TT các mã + Tiền mặt</code>).</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 06: FINANCIAL DATA & SSI SUBSECTION */}
      <section id="financial-data" className="guide-section">
        <div className="guide-section-head">
          <div><span>06</span><h2>Nguồn Dữ liệu Tài chính &amp; Luồng Xử lý</h2></div>
          <p>Mối liên hệ giữa danh mục cá nhân và kho dữ liệu BCTC chuẩn hóa.</p>
        </div>
        <div className="guide-start-grid">
          <Step number="1" title="Luồng phân tích từ Danh mục đến Quyết định">
            <p>
              <code>Danh mục cá nhân → Mã cổ phiếu chọn lọc → Dữ liệu BCTC chuẩn hóa → Phân tích 12 chiều Buffett/Munger → Mô hình Định giá → Hỗ trợ Quyết định Vốn</code>
            </p>
          </Step>
          <Step number="2" title="Nguồn Dữ liệu BCTC SSI Đã Chuẩn Hóa">
            <p>
              QPort sử dụng dữ liệu Báo cáo Tài chính từ SSI đã được nhập khẩu và chuẩn hóa (canonicalize) vào cơ sở dữ liệu. Dữ liệu tập trung vào chuỗi BCTC kiểm toán thường niên lịch sử (FY2011–FY2025). Hệ thống không yêu cầu người dùng phải tải lên lại tập tin Excel mỗi lần sử dụng.
            </p>
          </Step>
          <Step number="3" title="Độc lập giữa Sổ tài sản và Dữ liệu Doanh nghiệp">
            <p>
              Dữ liệu vị thế cá nhân trong Terminal hoàn toàn tách biệt với dữ liệu báo cáo tài chính của doanh nghiệp. Bạn có thể tự do thêm/bớt vị thế trong danh mục mà không làm thay đổi các chỉ số tài chính nền tảng của doanh nghiệp trong kho dữ liệu.
            </p>
          </Step>
          <Step number="4" title="Phân tích Hỗ trợ, Không phải Lệnh Tự động">
            <p>
              Mọi kết quả phân tích chất lượng, giá trị nội tại và khuyến nghị đều là công cụ hỗ trợ tư duy đầu tư theo triết lý Buffett–Munger, không phải hệ thống giao dịch tự động hay lời khuyên đầu tư ủy thác.
            </p>
          </Step>
        </div>
      </section>

      {/* 07: BUFFETT / MUNGER ANALYSIS & VALUE TRAP */}
      <section id="buffett-munger" className="guide-section">
        <div className="guide-section-head">
          <div><span>07</span><h2>12 Chiều Chất lượng Tài chính &amp; Nhận diện Bẫy Giá Trị</h2></div>
          <p>Khung phân tích toàn diện phòng vệ rủi ro và nhận diện doanh nghiệp hảo hạng.</p>
        </div>

        <div className="guide-two-column">
          <div className="guide-step-card">
            <span className="guide-step-number">12D</span>
            <div>
              <h3>12 Trụ cột Đánh giá Doanh nghiệp Buffett–Munger</h3>
              <p>
                Hệ thống thẩm định toàn diện: (1) Tăng trưởng Doanh thu &amp; LNST, (2) Tỷ suất sinh lời ROE/ROIC, (3) Độ bền lợi nhuận qua chu kỳ, (4) Chất lượng lợi nhuận (CFO/PAT), (5) Sức mạnh Bảng cân đối kế toán, (6) Nợ vay và Thanh khoản, (7) Hiệu quả sử dụng tài sản, (8) Phân bổ vốn &amp; Lợi nhuận giữ lại, (9) Kiểm soát pha loãng cổ phiếu, (10) Tính nhất quán kế toán, (11) Dấu hiệu điều tra tài chính (Forensic), và (12) Dòng tiền thực tế của chủ doanh nghiệp (Owner Earnings).
              </p>
            </div>
          </div>
          <div className="guide-step-card">
            <span className="guide-step-number">VT</span>
            <div>
              <h3>Kiểm tra Bẫy Giá Trị (Value Trap Engine)</h3>
              <p>
                Tránh mua phải cổ phiếu có định giá P/E hay P/B tưởng chừng rẻ nhưng tiềm ẩn nguy cơ suy thoái cấu trúc hoặc thao túng số liệu kế toán. Toàn bộ chẩn đoán được giải thích bằng ngôn ngữ tài chính trực quan, không dùng mã kỹ thuật.
              </p>
            </div>
          </div>
        </div>

        <div className="guide-table-wrap" style={{ marginTop: 16 }}>
          <table className="guide-table">
            <thead>
              <tr>
                <th>Dấu hiệu Bẫy Giá Trị</th>
                <th>Giải thích Ngữ nghĩa Tiếng Việt</th>
                <th>Tác động đến Doanh nghiệp</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span className="guide-tag">Dòng tiền suy yếu</span></td>
                <td><strong>Lợi nhuận tăng nhưng dòng tiền không theo kịp</strong></td>
                <td>Doanh nghiệp báo lãi trên sổ sách nhưng tiền mặt thực nhận từ kinh doanh âm hoặc quá thấp so với lợi nhuận sau thuế.</td>
              </tr>
              <tr>
                <td><span className="guide-tag">Khoản phải thu</span></td>
                <td><strong>Khoản phải thu tăng nhanh hơn doanh thu</strong></td>
                <td>Dấu hiệu nới lỏng chính sách tín dụng thương mại để đẩy doanh thu ảo hoặc khách hàng chậm thanh toán kéo dài.</td>
              </tr>
              <tr>
                <td><span className="guide-tag">Hàng tồn kho</span></td>
                <td><strong>Hàng tồn kho tích tụ bất thường</strong></td>
                <td>Hàng hóa ứ đọng không tiêu thụ được, gây chôn vốn và đối mặt rủi ro trích lập giảm giá tài sản.</td>
              </tr>
              <tr>
                <td><span className="guide-tag">Đòn bẩy tài chính</span></td>
                <td><strong>Đòn bẩy nợ vay quá mức</strong></td>
                <td>Tổng nợ vay vượt xa lượng tiền mặt hiện có và dòng tiền kinh doanh, gia tăng chi phí lãi vay và rủi ro thanh khoản.</td>
              </tr>
              <tr>
                <td><span className="guide-tag">Pha loãng</span></td>
                <td><strong>Pha loãng cổ phiếu liên tục</strong></td>
                <td>Phát hành thêm cổ phiếu vô tội vạ mà không mang lại tăng trưởng lợi nhuận tương xứng trên mỗi cổ phần (EPS).</td>
              </tr>
              <tr>
                <td><span className="guide-tag">An toàn cấu trúc</span></td>
                <td><strong>Chưa phát hiện suy giảm cấu trúc</strong></td>
                <td>Nền tảng kinh doanh cốt lõi vững mạnh, biên lợi nhuận và sức mạnh tài chính duy trì ổn định qua nhiều năm.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 08: TERMINAL VS WEB UI COMPARISON */}
      <section id="comparison" className="guide-section">
        <div className="guide-section-head">
          <div><span>08</span><h2>So sánh Chức năng: QPort Terminal vs Giao diện Web Chuyên trang</h2></div>
          <p>Lựa chọn không gian làm việc phù hợp với nhu cầu của bạn.</p>
        </div>
        <div className="guide-table-wrap">
          <table className="guide-table">
            <thead>
              <tr>
                <th>Tính năng</th>
                <th style={{ textAlign: 'center' }}>QPort Terminal (Trang chủ /)</th>
                <th style={{ textAlign: 'center' }}>Giao diện Web Chuyên trang</th>
                <th>Mô tả chi tiết</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Xem tổng quan danh mục &amp; vị thế</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có</td>
                <td>Terminal hiển thị bảng vị thế nhanh kèm tỷ trọng; Trang Tổng quan &amp; Lịch sử hiển thị biểu đồ và chi tiết giao dịch.</td>
              </tr>
              <tr>
                <td><strong>Thêm cổ phiếu mới</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Modal nhanh)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (/transactions)</td>
                <td>Terminal hỗ trợ thêm nhanh một chạm với Symbol Suggest; Trang Giao dịch hỗ trợ ghi nhận nhật ký chi tiết.</td>
              </tr>
              <tr>
                <td><strong>Chỉnh sửa số lượng / giá vốn</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Sửa trực tiếp)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Sửa giao dịch)</td>
                <td>Sửa nhanh số dư trên Terminal hoặc chỉnh sửa từng giao dịch gốc có lưu vết (Audit Trail).</td>
              </tr>
              <tr>
                <td><strong>Xóa cổ phiếu khỏi danh mục</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Xác nhận an toàn)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Xóa giao dịch)</td>
                <td>Gỡ bỏ vị thế khỏi danh mục cá nhân mà không làm mất dữ liệu tài chính của mã trong cơ sở dữ liệu.</td>
              </tr>
              <tr>
                <td><strong>Cập nhật tiền mặt (Cash)</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Sửa số dư)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Nạp/Rút tiền)</td>
                <td>Cập nhật số tiền mặt trực tiếp trên Terminal hoặc ghi nhận giao dịch nạp/rút tiền trên trang Giao dịch.</td>
              </tr>
              <tr>
                <td><strong>Pháo đài tài chính cá nhân</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Thẻ Pháo đài)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (/capital)</td>
                <td>Xem tháng sinh tồn, vốn dài hạn và tiền mặt cơ hội ngay trên Terminal hoặc cấu hình chuyên sâu tại trang Vốn cá nhân.</td>
              </tr>
              <tr>
                <td><strong>Ma trận quyết định Buffett–Munger</strong></td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (Bảng tổng hợp)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (/valuation, /business)</td>
                <td>Tổng hợp khuyến nghị hành động, Base IV và Biên an toàn cho danh mục. Click vào mã để mở trang Doanh nghiệp.</td>
              </tr>
              <tr>
                <td><strong>Soi 12 chiều BCTC &amp; Forensic chi tiết</strong></td>
                <td style={{ textAlign: 'center', color: '#a0aec0' }}>Xem tóm tắt (Click mã)</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có đầy đủ (/business/:id)</td>
                <td>Trang Doanh nghiệp cung cấp báo cáo chi tiết 10 năm, phân tích Moat, chất lượng và thử thách luận điểm đầu tư.</td>
              </tr>
              <tr>
                <td><strong>Bộ lọc cổ phiếu toàn thị trường</strong></td>
                <td style={{ textAlign: 'center', color: '#e53e3e' }}>✕ Không</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (/screener)</td>
                <td>Sàng lọc toàn bộ cổ phiếu trên 3 sàn theo điểm chất lượng Buffett–Munger và biên an toàn tại trang Screener.</td>
              </tr>
              <tr>
                <td><strong>Phân tích rủi ro biến động &amp; VaR</strong></td>
                <td style={{ textAlign: 'center', color: '#e53e3e' }}>✕ Không</td>
                <td style={{ textAlign: 'center', color: '#48bb78', fontWeight: 700 }}>✓ Có (/risk)</td>
                <td>Đo lường ma trận tương quan giữa các mã, độ biến động và mức độ tập trung danh mục tại trang Phân tích rủi ro.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 09: CORPORATE ACTIONS & DIVIDEND NORMALIZATION */}
      <section id="corporate-actions" className="guide-section">
        <div className="guide-section-head">
          <div><span>09</span><h2>Giá Cổ Phiếu Sau Chia Tách &amp; Chuẩn Hóa Cổ Tức</h2></div>
          <p>Bản chất kinh tế của các sự kiện quyền và cách QPort xử lý nhất quán.</p>
        </div>
        <div className="guide-start-grid">
          <Step number="1" title="Bản chất của Chia tách Cổ phiếu (Stock Split)">
            Chia tách cổ phiếu hoặc phát hành cổ phiếu thưởng làm tăng số lượng cổ phiếu lưu hành và giảm giá thị giá tương ứng, nhưng <b>không tự tạo ra thêm bất kỳ giá trị kinh tế nào</b> cho doanh nghiệp. Một chiếc bánh cắt thành 4 phần hay 8 phần thì tổng khối lượng bánh vẫn không đổi.
          </Step>
          <Step number="2" title="Chuẩn hóa Thống nhất một Cơ sở Cổ phần (Share Basis)">
            Để tránh hiện tượng sụt giảm EPS hay DPS ảo sau các đợt chia tách, QPort chuẩn hóa toàn bộ chuỗi số liệu tài chính lịch sử, thị giá và số lượng cổ phiếu theo cùng một cơ sở cổ phần hiện hành.
          </Step>
          <Step number="3" title="Phân biệt Cổ tức Tiền mặt vs Cổ tức Cổ phiếu">
            Cổ tức tiền mặt là dòng tiền thực phân phối từ lợi nhuận cho cổ đông; cổ tức cổ phiếu thực chất là việc điều chuyển kế toán từ lợi nhuận giữ lại sang vốn góp. QPort theo dõi riêng biệt hai sự kiện này để phản ánh đúng dòng tiền thực nhận.
          </Step>
          <Step number="4" title="Không Cộng Trùng (Double-Counting) trong Định giá">
            Các mô hình định giá DCF, RIM và SOTP của QPort ước tính giá trị doanh nghiệp dựa trên dòng tiền tự do hoặc lợi nhuận thặng dư trước phân phối, tuyệt đối không cộng thêm cổ tức vào giá trị nội tại để tránh tính kép.
          </Step>
        </div>
      </section>

      {/* 10: COMMON MISTAKES */}
      <section id="common-mistakes" className="guide-section">
        <div className="guide-section-head">
          <div><span>10</span><h2>Các Lỗi Thường Gặp Cần Tránh</h2></div>
          <p>8 hiểu lầm phổ biến của nhà đầu tư mới khi sử dụng hệ thống.</p>
        </div>
        <div className="guide-faq-grid">
          <div>
            <h3>1. Nhập giá vốn thay vì giá thị trường (hoặc ngược lại)</h3>
            <p><b>Giá vốn bình quân</b> là số tiền thực tế bạn đã bỏ ra mua mỗi cổ phiếu. <b>Giá thị trường</b> là thị giá hiện tại trên sàn giao dịch. Hãy nhập đúng giá vốn của bạn để QPort tính chính xác Lãi/Lỗ.</p>
          </div>
          <div>
            <h3>2. Nhập sai số lượng cổ phiếu</h3>
            <p>Nhập đúng số lượng cổ phiếu thực tế nắm giữ (ví dụ: <code>3000</code>). Không nhập theo số lô chẵn (như nhập <code>30</code> cho 3,000 cổ phiếu).</p>
          </div>
          <div>
            <h3>3. Xóa vị thế tưởng rằng đã xóa dữ liệu doanh nghiệp</h3>
            <p>Xóa một mã khỏi Terminal chỉ là gỡ bỏ khỏi danh mục cá nhân của bạn. Toàn bộ dữ liệu BCTC và định giá của mã đó vẫn được lưu trữ nguyên vẹn trong hệ thống.</p>
          </div>
          <div>
            <h3>4. Nhầm lẫn Tiền mặt với một mã cổ phiếu</h3>
            <p>Tiền mặt là tài sản dự phòng/thanh khoản trong danh mục, không phải là một mã chứng khoán. Bạn quản lý tiền mặt qua ô <b>Sửa Tiền mặt</b> ở chân bảng.</p>
          </div>
          <div>
            <h3>5. Nhầm lẫn Giá trị Nội tại (IV) với Thị giá (Price)</h3>
            <p>Giá thị trường là những gì bạn phải trả, Giá trị nội tại là những gì bạn nhận được. Cổ phiếu có giá thấp chưa chắc đã rẻ nếu giá trị thực của doanh nghiệp thấp hơn nhiều.</p>
          </div>
          <div>
            <h3>6. Nghĩ rằng chia tách cổ phiếu làm doanh nghiệp rẻ đi</h3>
            <p>Thị giá giảm một nửa sau đợt chia tách tỷ lệ 1:1 không có nghĩa là cổ phiếu rẻ đi gấp đôi. Giá trị nội tại trên mỗi cổ phần cũng giảm tương ứng theo tỷ lệ chia.</p>
          </div>
          <div>
            <h3>7. Nghĩ rằng tỷ suất cổ tức cao tự động là cổ phiếu tốt</h3>
            <p>Một số doanh nghiệp có tỷ suất cổ tức cao bất thường do bán tài sản một lần hoặc giá cổ phiếu đang lao dốc do suy thoái cấu trúc kinh doanh. Luôn kiểm tra 12 chiều chất lượng.</p>
          </div>
          <div>
            <h3>8. Chỉ nhìn EPS mà bỏ qua Dòng tiền và Bảng cân đối</h3>
            <p>EPS có thể bị thổi phồng qua các thủ thuật ghi nhận doanh thu ảo. QPort luôn đối chiếu lợi nhuận sau thuế với dòng tiền kinh doanh (CFO) và nợ vay để phòng tránh bẫy giá trị.</p>
          </div>
        </div>
      </section>

      {/* 11: PAGE DIRECTORY */}
      <section id="pages" className="guide-section">
        <div className="guide-section-head">
          <div><span>11</span><h2>Bản đồ Tính năng Toàn Hệ thống QPort</h2></div>
          <p>Truy cập nhanh từng không gian làm việc theo nhu cầu của bạn.</p>
        </div>
        <div className="guide-page-grid">
          <PageCard href="/" title="Terminal" question="Quản lý danh mục & Ma trận quyết định vốn?">
            Giao diện trung tâm để xem và chỉnh sửa vị thế cổ phiếu, cập nhật tiền mặt, theo dõi Pháo đài tài chính và nhận khuyến nghị hành động tức thì.
          </PageCard>
          <PageCard href="/business" title="Doanh nghiệp" question="Doanh nghiệp có lợi thế cạnh tranh bền vững không?">
            Phân tích chuyên sâu 12 chiều chất lượng tài chính, kiểm tra Hào kinh tế (Moat), soi Bẫy giá trị và chạy thử thách luận điểm đầu tư tự động.
          </PageCard>
          <PageCard href="/capital" title="Vốn cá nhân" question="Sức chịu đựng tài chính cá nhân đến đâu?">
            Cấu hình chi phí sinh hoạt hàng tháng, quỹ dự phòng sinh tồn, vốn khả dụng dài hạn và theo dõi các nghĩa vụ nợ ngắn hạn.
          </PageCard>
          <PageCard href="/history" title="Lịch sử tích sản" question="Hiệu quả đầu tư tăng trưởng ra sao theo thời gian?">
            Theo dõi lợi suất tích sản thực tế qua chỉ số TWR và XIRR, so sánh với VN-Index và xem nhật ký giao dịch chi tiết.
          </PageCard>
          <PageCard href="/valuation" title="Định giá" question="Giá trị thực của cổ phiếu là bao nhiêu?">
            Khám phá 40 mô hình định giá bản chất kinh tế (DCF chu kỳ, RIM Ngân hàng, SOTP...) kèm dải 3 kịch bản giá trị thực và biên an toàn.
          </PageCard>
          <PageCard href="/screener" title="Bộ lọc Screener" question="Thị trường có những cơ hội đầu tư hảo hạng nào?">
            Sàng lọc toàn diện cổ phiếu trên sàn HOSE, HNX, UPCOM theo 100 điểm chất lượng Buffett–Munger và biên an toàn hấp dẫn.
          </PageCard>
          <PageCard href="/dividends" title="Cổ tức" question="Dòng tiền cổ tức thực nhận về tài khoản ra sao?">
            Theo dõi lịch chi trả cổ tức tiền mặt &amp; cổ phiếu, tính toán thuế TNCN 5% và tỷ suất sinh lời từ cổ tức thực tế.
          </PageCard>
          <PageCard href="/risk" title="Phân tích Rủi ro" question="Danh mục có những nguy cơ biến động nào?">
            Chẩn đoán tương quan giữa các mã, mức độ tập trung danh mục và đo lường tổn thất tối đa tiềm ẩn (VaR/CVaR).
          </PageCard>
          <PageCard href="/portfolios" title="Quản lý Danh mục" question="Chuyển đổi giữa các không gian đầu tư độc lập?">
            Tạo mới, đổi tên và quản lý nhiều danh mục riêng biệt (ví dụ: Danh mục Cổ tức, Danh mục Hưu trí, Danh mục Tăng trưởng).
          </PageCard>
        </div>
      </section>

      {/* 12: HABITS & FAQ */}
      <section className="guide-section">
        <div className="guide-section-head">
          <div><span>12</span><h2>Thói quen Sử dụng Đơn giản cho Nhà Đầu tư Giá trị</h2></div>
          <p>Nhà đầu tư dài hạn không cần theo dõi bảng điện liên tục trong phiên.</p>
        </div>
        <div className="guide-faq-grid">
          <div>
            <h3>Sau khi phát sinh giao dịch</h3>
            <p>Mở QPort Terminal để thêm vị thế hoặc chỉnh sửa số lượng, giá vốn tương ứng để số dư luôn khớp với tài khoản chứng khoán.</p>
          </div>
          <div>
            <h3>Sau giờ đóng cửa phiên</h3>
            <p>Nhấn nút <b>Đồng bộ dữ liệu</b> nếu muốn cập nhật thị giá đóng cửa mới nhất từ các sở giao dịch.</p>
          </div>
          <div>
            <h3>Khi mùa BCTC công bố</h3>
            <p>Mở trang <b>Doanh nghiệp</b> hoặc <b>Định giá</b> để cập nhật kết quả kinh doanh mới nhất, điểm chất lượng và giá trị thực mới của cổ phiếu.</p>
          </div>
          <div>
            <h3>Định kỳ hàng quý</h3>
            <p>Đối chiếu lại tổng tài sản và số lượng cổ phiếu với sao kê CTCK để đảm bảo không bỏ sót sự kiện chia tách hoặc cổ tức nào.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
