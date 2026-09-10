import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';

export default function CapitalPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [showConfigForm, setShowConfigForm] = useState(false);

  // Form fields
  const [monthlyNetIncome, setMonthlyNetIncome] = useState('');
  const [monthlyEssentialSpending, setMonthlyEssentialSpending] = useState('');
  const [safeLiquidAssets, setSafeLiquidAssets] = useState('');
  const [nearTermLiabilities, setNearTermLiabilities] = useState('');

  const fetchCapitalData = () => {
    setLoading(true);
    fetch('/api/portfolio/capital')
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) {
          setData(res);
          if (res.personal_finance_input) {
            setMonthlyNetIncome(res.personal_finance_input.monthly_net_income || '');
            setMonthlyEssentialSpending(res.personal_finance_input.monthly_essential_spending || '');
            setSafeLiquidAssets(res.personal_finance_input.safe_liquid_assets || '');
            setNearTermLiabilities(res.personal_finance_input.near_term_liabilities || '');
          }
          if (!res.configured) {
            setShowConfigForm(true);
          }
        } else {
          setError(res.error || 'Không thể tải dữ liệu vốn cá nhân.');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCapitalData();
  }, []);

  const handleSavePersonalFinance = (e) => {
    e.preventDefault();
    setSaving(true);
    const payload = {
      monthly_net_income: Number(monthlyNetIncome) || 0,
      monthly_essential_spending: Number(monthlyEssentialSpending) || 0,
      safe_liquid_assets: Number(safeLiquidAssets) || 0,
      near_term_liabilities: Number(nearTermLiabilities) || 0,
    };

    fetch('/api/portfolio/personal-finance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) {
          setShowConfigForm(false);
          fetchCapitalData();
        } else {
          alert(res.error || 'Lỗi khi lưu bảng cân đối cá nhân');
        }
      })
      .catch((err) => alert(err.message))
      .finally(() => setSaving(false));
  };

  const isConfigured = data?.configured && data?.durability?.survival_reserve_status !== 'UNKNOWN';

  return (
    <div className="wealth-app-shell">
      <AppNav active="allocation" />
      <main className="wealth-main-content">
        <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="eyebrow">Không Gian Quản Lý Vốn Cá Nhân</span>
            <h1>Phân Bổ Vốn & Độ Bền Pháo Đài</h1>
          </div>
          {isConfigured && !showConfigForm && (
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => setShowConfigForm(true)}
              style={{ padding: '8px 16px', cursor: 'pointer' }}
            >
              [Cập nhật Bảng Cân Đối Cá Nhân]
            </button>
          )}
        </header>

        {loading && <div className="loading-state">Đang tải cấu trúc nguồn vốn cá nhân...</div>}
        {error && <div className="error-box">Lỗi: {error}</div>}

        {data && (
          <div className="capital-grid">
            {/* Setup Form View */}
            {(!isConfigured || showConfigForm) && (
              <section className="card personal-finance-config-card" style={{ marginBottom: '24px' }}>
                <div className="card-header">
                  <h3>Cấu Hình Bảng Cân Đối Cá Nhân</h3>
                  <span className={`status-badge ${data.durability?.survival_reserve_status || 'UNKNOWN'}`}>
                    Dự phòng: {data.durability?.survival_reserve_status || 'UNKNOWN'}
                  </span>
                </div>
                {!isConfigured && (
                  <p className="muted" style={{ marginBottom: '16px' }}>
                    Bạn chưa cấu hình Bảng Cân Đối Cá Nhân. Mọi hành động MUA / MUA THÊM cổ phiếu hiện bị cấm (BUILD_RESERVE_FIRST) để bảo vệ pháo đài sinh tồn.
                  </p>
                )}
                <form onSubmit={handleSavePersonalFinance} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}>Thu nhập ròng hàng tháng (VND)</label>
                      <input
                        type="number"
                        value={monthlyNetIncome}
                        onChange={(e) => setMonthlyNetIncome(e.target.value)}
                        placeholder="Ví dụ: 50000000"
                        style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                        required
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}>Chi tiêu thiết yếu hàng tháng (VND)</label>
                      <input
                        type="number"
                        value={monthlyEssentialSpending}
                        onChange={(e) => setMonthlyEssentialSpending(e.target.value)}
                        placeholder="Ví dụ: 20000000"
                        style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                        required
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}>Tài sản thanh khoản an toàn (Dự phòng) (VND)</label>
                      <input
                        type="number"
                        value={safeLiquidAssets}
                        onChange={(e) => setSafeLiquidAssets(e.target.value)}
                        placeholder="Ví dụ: 240000000"
                        style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                        required
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}>Nghĩa vụ nợ ngắn hạn (VND)</label>
                      <input
                        type="number"
                        value={nearTermLiabilities}
                        onChange={(e) => setNearTermLiabilities(e.target.value)}
                        placeholder="Ví dụ: 0"
                        style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                      />
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button
                      type="submit"
                      disabled={saving}
                      style={{ padding: '10px 20px', background: '#0284c7', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 600, cursor: 'pointer' }}
                    >
                      {saving ? 'Đang lưu...' : '[Lưu cấu hình tài chính cá nhân]'}
                    </button>
                    {isConfigured && showConfigForm && (
                      <button
                        type="button"
                        onClick={() => setShowConfigForm(false)}
                        style={{ padding: '10px 20px', background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        Hủy
                      </button>
                    )}
                  </div>
                </form>
              </section>
            )}

            {/* Buckets Card */}
            <section className="card buckets-card">
              <div className="card-header">
                <h3>4 Ngăn Vốn Cá Nhân</h3>
              </div>
              <div className="metric-grid">
                <div className="metric-item">
                  <small>Dự phòng sinh tồn (Survival Reserve)</small>
                  <strong>{Number(data.buckets?.survival_reserve || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item">
                  <small>Tài sản tích sản (Compounding Asset)</small>
                  <strong>{Number(data.buckets?.compounding_asset || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item">
                  <small>Quỹ nghĩa vụ ngắn hạn</small>
                  <strong>{Number(data.buckets?.near_term_liability_fund || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item highlight">
                  <small>Vốn khả dụng dài hạn (Buy Capital)</small>
                  <strong>{Number(data.buckets?.available_long_term_capital || 0).toLocaleString()} VND</strong>
                </div>
              </div>
            </section>

            {/* Invariant Note */}
            <section className="card invariant-note-card">
              <div className="card-header">
                <h3>Quy Tắc Quản Lý Vốn Bất Biến</h3>
              </div>
              <p>
                <strong>Vốn khả dụng dài hạn</strong> = (Tiền mặt khả dụng + Thu nhập mới + Cổ tức) - (Mục tiêu Quỹ dự phòng sinh tồn + Nghĩa vụ ngắn hạn).
                QPort đảm bảo tiền mặt dự phòng không bao giờ bị sử dụng nhầm làm vốn mua cổ phiếu.
              </p>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
