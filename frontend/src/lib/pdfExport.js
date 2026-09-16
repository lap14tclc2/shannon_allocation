import html2canvas from 'html2canvas-pro';
import { jsPDF } from 'jspdf';

/**
 * Directly export an HTML DOM element to a downloadable multi-page A4 PDF file.
 * Triggers direct browser download without opening any print dialogs.
 * 
 * Features:
 * - Smart page-break algorithm: scans child cards/sections and avoids slicing through text or borders.
 * - Slices high-resolution source canvas at clean boundaries with whitespace padding.
 * - Exports sharp 2x resolution multi-page A4 PDF.
 *
 * @param {HTMLElement} element The root container to capture
 * @param {string} filename The downloaded file name (e.g. Bao_Cao_Munger_FPT_2026-09-16.pdf)
 */
export async function exportElementToPDF(element, filename = 'Bao_Cao_Munger.pdf') {
  if (!element) {
    throw new Error('Không tìm thấy nội dung để xuất PDF.');
  }

  // 1. Hide action buttons, search inputs, and non-printable elements
  const noPrintElements = Array.from(element.querySelectorAll('.no-print'));
  const originalDisplays = noPrintElements.map((el) => el.style.display);
  noPrintElements.forEach((el) => {
    el.style.display = 'none';
  });

  try {
    // 2. Capture high-res canvas at 2x scale for crisp retina vector-like text
    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
      windowWidth: 1240, // standard desktop width
    });

    const scale = 2;
    const elementRect = element.getBoundingClientRect();

    // 3. Find vertical split boundaries of cards and sections
    // Standard section/card selectors that should not be sliced in half
    const breakCandidates = Array.from(
      element.querySelectorAll(
        '.card, section, .dim-card, tr, .evidence-conclusion-box, .dimension-grid > div, [style*="borderRadius"]'
      )
    );

    const safeCutPoints = new Set([0, canvas.height]);
    breakCandidates.forEach((el) => {
      const rect = el.getBoundingClientRect();
      const topPx = Math.round((rect.top - elementRect.top) * scale);
      const bottomPx = Math.round((rect.bottom - elementRect.top) * scale);
      if (topPx > 0 && topPx < canvas.height) safeCutPoints.add(topPx);
      if (bottomPx > 0 && bottomPx < canvas.height) safeCutPoints.add(bottomPx);
    });

    const sortedCuts = Array.from(safeCutPoints).sort((a, b) => a - b);

    // 4. A4 Dimensions in PDF mm
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfPageWidth = 210;
    const pdfPageHeight = 297;
    const margin = 10; // 10mm margins
    const printableWidth = pdfPageWidth - margin * 2;
    const printableHeight = pdfPageHeight - margin * 2;

    // Maximum canvas height that fits in one A4 page without overflowing
    const maxPageCanvasHeight = Math.floor((printableHeight * canvas.width) / printableWidth);

    let currentY = 0;
    let pageCount = 0;

    while (currentY < canvas.height) {
      let targetY = currentY + maxPageCanvasHeight;

      if (targetY >= canvas.height) {
        targetY = canvas.height;
      } else {
        // Find the best cut point before targetY that leaves at least 50% of the page utilized
        const minAcceptableCut = currentY + Math.floor(maxPageCanvasHeight * 0.45);
        let bestCut = -1;

        for (let i = sortedCuts.length - 1; i >= 0; i--) {
          const cut = sortedCuts[i];
          if (cut <= targetY && cut >= minAcceptableCut) {
            bestCut = cut;
            break;
          }
        }

        if (bestCut !== -1) {
          targetY = bestCut;
        }
      }

      const sliceHeight = targetY - currentY;
      if (sliceHeight <= 0) break;

      // Create a page canvas for this slice
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = sliceHeight;
      const ctx = pageCanvas.getContext('2d');

      // Draw white background
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);

      // Draw the exact slice from master canvas
      ctx.drawImage(
        canvas,
        0, currentY, canvas.width, sliceHeight, // source slice
        0, 0, canvas.width, sliceHeight         // destination
      );

      const pageImgData = pageCanvas.toDataURL('image/jpeg', 0.95);
      const renderHeightInPdf = (sliceHeight * printableWidth) / canvas.width;

      if (pageCount > 0) {
        pdf.addPage();
      }

      pdf.addImage(pageImgData, 'JPEG', margin, margin, printableWidth, renderHeightInPdf);

      currentY = targetY;
      pageCount++;
    }

    // 5. Direct trigger file download
    pdf.save(filename);
    return filename;
  } finally {
    // Restore elements visibility
    noPrintElements.forEach((el, index) => {
      el.style.display = originalDisplays[index];
    });
  }
}
