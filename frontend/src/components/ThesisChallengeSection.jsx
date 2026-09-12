import React, { useState } from 'react';
import { formatStatus } from '../utils/vietnameseSemantics.js';

export default function ThesisChallengeSection({ challengeData, decision }) {
  const [expandedCards, setExpandedCards] = useState({});

  if (!challengeData || !challengeData.questions) {
    return null;
  }

  const toggleExpand = (qNum) => {
    setExpandedCards((prev) => ({
      ...prev,
      [qNum]: !prev[qNum],
    }));
  };

  const getStatusBadge = (statusKey, statusVi) => {
    const s = String(statusKey || '').toUpperCase();
    let bg = '#6b7280';
    if (s === 'RESILIENT') bg = '#16a34a';
    else if (s === 'WATCH') bg = '#d97706';
    else if (s === 'VULNERABLE') bg = '#dc2626';
    else if (s === 'INSUFFICIENT_DATA') bg = '#4b5563';

    return (
      <span
        style={{
          padding: '3px 10px',
          borderRadius: '4px',
          background: bg,
          color: '#ffffff',
          fontSize: '0.82rem',
          fontWeight: 700,
          display: 'inline-block',
        }}
      >
        {statusVi || formatStatus(s)}
      </span>
    );
  };

  const questions = challengeData.questions || [];

  return (
    <section className="card thesis-challenge-card" style={{ padding: '24px', margin: '24px 0' }}>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.3rem', margin: 0, color: 'var(--text-main, #111827)' }}>
            PHẢN BIỆN LUẬN ĐIỂM ĐẦU TƯ
          </h2>
          {challengeData.status && (
            <div>
              <span style={{ fontSize: '0.85rem', color: '#6b7280', marginRight: '8px' }}>
                Tổng quan chống chịu:
              </span>
              {getStatusBadge(challengeData.status, formatStatus(challengeData.status))}
            </div>
          )}
        </div>
        <p style={{ margin: '6px 0 0 0', fontSize: '0.92rem', color: '#6b7280', fontStyle: 'italic' }}>
          "QPort chủ động tìm những bằng chứng có thể bác bỏ luận điểm đầu tư hiện tại, thay vì chỉ tìm dữ liệu ủng hộ nó."
        </p>
        {challengeData.decision_contradiction && (
          <div
            style={{
              marginTop: '12px',
              padding: '10px 14px',
              background: '#fef2f2',
              borderLeft: '4px solid #dc2626',
              color: '#991b1b',
              fontSize: '0.88rem',
              borderRadius: '4px',
            }}
          >
            <strong>CẢNH BÁO MẪU THUẪN HỆ THỐNG:</strong> {challengeData.contradiction_details}
          </div>
        )}
      </div>

      {/* 8 Question Cards Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {questions.map((q) => {
          const isExpanded = expandedCards[q.question_number];
          const isWarning = q.answer_status === 'WATCH' || q.answer_status === 'VULNERABLE';
          const borderColor = q.answer_status === 'VULNERABLE' ? '#fca5a5' : q.answer_status === 'WATCH' ? '#fde68a' : '#e5e7eb';
          const bgColor = q.answer_status === 'VULNERABLE' ? '#fff5f5' : q.answer_status === 'WATCH' ? '#fffbeb' : 'var(--surface-soft, #f9fafb)';

          return (
            <div
              key={q.question_id || q.question_number}
              style={{
                padding: '16px',
                border: `1px solid ${borderColor}`,
                borderRadius: '8px',
                background: bgColor,
                transition: 'all 0.2s ease',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justify: 'space-between',
                  alignItems: 'flex-start',
                  cursor: 'pointer',
                }}
                onClick={() => toggleExpand(q.question_number)}
              >
                <div style={{ paddingRight: '12px' }}>
                  <h4 style={{ margin: '0 0 6px 0', fontSize: '1.02rem', color: '#1f2937' }}>
                    {q.question_number}. {q.title_vi}
                  </h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: '#374151', lineHeight: 1.5 }}>
                    {q.summary_vi}
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {getStatusBadge(q.answer_status, q.answer_status_vi)}
                  <button
                    type="button"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#6b7280',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      padding: '4px 8px',
                    }}
                  >
                    {isExpanded ? '▲ Thu gọn' : '▼ Chi tiết'}
                  </button>
                </div>
              </div>

              {/* Detailed Evidence & Structured 4-Part Pre-Mortem Accordion */}
              {isExpanded && (
                <div
                  style={{
                    marginTop: '14px',
                    paddingTop: '12px',
                    borderTop: '1px dashed #d1d5db',
                    fontSize: '0.88rem',
                    color: '#4b5563',
                    lineHeight: 1.6,
                  }}
                >
                  <div style={{ display: 'grid', gap: '8px', marginBottom: '10px' }}>
                    <div>
                      <strong>1. Kết Luận:</strong> {q.conclusion_vi || q.summary_vi}
                    </div>
                    <div>
                      <strong>2. Bằng Chứng BCTC (Evidence):</strong> {q.evidence_vi || q.detail_vi}
                    </div>
                    <div>
                      <strong>3. Rủi Ro Tiềm Ẩn (Risk):</strong> {q.risk_vi || 'Cần theo dõi sát biến động tài chính.'}
                    </div>
                    <div>
                      <strong>4. Mức Độ Nghiêm Trọng (Severity):</strong> {q.severity_vi || q.answer_status_vi || formatStatus(q.answer_status)}
                    </div>
                  </div>

                  {/* Measurable invalidation criteria if Q8 */}
                  {q.question_number === 8 && challengeData.invalidation_criteria && (
                    <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(0,0,0,0.02)', borderRadius: '6px' }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>
                        Danh sách tiêu chí kích hoạt bác bỏ luận điểm:
                      </strong>
                      <ul style={{ margin: 0, paddingLeft: '20px' }}>
                        {challengeData.invalidation_criteria.map((item, idx) => (
                          <li key={idx} style={{ marginBottom: '4px' }}>
                            <strong>{item.metric}</strong>: Trigger <code>{item.trigger}</code> — {item.reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {q.limitations && (
                    <p style={{ margin: '8px 0 0 0', fontStyle: 'italic', fontSize: '0.82rem', color: '#6b7280' }}>
                      * Giới hạn phân tích: {q.limitations}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Replaced Qualitative UNKNOWN Section */}
      <div
        style={{
          marginTop: '24px',
          padding: '16px',
          background: 'var(--surface-soft, #f9fafb)',
          border: '1px dashed #d1d5db',
          borderRadius: '8px',
        }}
      >
        <h4 style={{ margin: '0 0 6px 0', fontSize: '0.98rem', color: '#374151' }}>
          Giới Hạn Của Phân Tích Báo Cáo Tài Chính
        </h4>
        <p style={{ margin: 0, fontSize: '0.86rem', color: '#6b7280', lineHeight: 1.5 }}>
          BCTC có thể cung cấp bằng chứng về sức mạnh kinh tế, hiệu quả sử dụng vốn, độ bền lợi nhuận và tính nhất quán kế toán, nhưng không thể trực tiếp chứng minh vùng hiểu biết của nhà đầu tư, lợi thế cạnh tranh định tính hoặc phẩm chất cá nhân của ban quản trị. Các yếu tố này không được sử dụng làm cổng chặn trong mô hình BCTC thuần túy.
        </p>
      </div>
    </section>
  );
}
