import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

async function addCanvasPaginated(pdf: any, canvas: HTMLCanvasElement, margin = 24) {
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const imageWidth = pageWidth - margin * 2;
  const imageHeight = (canvas.height * imageWidth) / canvas.width;

  pdf.addImage(canvas.toDataURL('image/png'), 'PNG', margin, margin, imageWidth, Math.min(imageHeight, pageHeight - margin * 2));

  let remainingHeight = imageHeight - (pageHeight - margin * 2);
  if (remainingHeight <= 0) return;

  let sourceY = (canvas.height * (pageHeight - margin * 2)) / imageHeight;
  while (remainingHeight > 0) {
    pdf.addPage();
    const sliceHeight = Math.min(remainingHeight, pageHeight - margin * 2);
    const sliceCanvas = document.createElement('canvas');
    sliceCanvas.width = canvas.width;
    sliceCanvas.height = (canvas.height * sliceHeight) / imageHeight;
    const ctx = sliceCanvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(
        canvas,
        0,
        sourceY,
        canvas.width,
        sliceCanvas.height,
        0,
        0,
        sliceCanvas.width,
        sliceCanvas.height,
      );
      pdf.addImage(sliceCanvas.toDataURL('image/png'), 'PNG', margin, margin, imageWidth, sliceHeight);
    }
    remainingHeight -= sliceHeight;
    sourceY += sliceCanvas.height;
  }
}

export async function exportContainerToPdf(containerId: string, filename = 'report.pdf') {
  const element = document.getElementById(containerId);
  if (!element) {
    throw new Error(`#${containerId} introuvable`);
  }
  element.style.background = element.style.background || '#0b1220';
  const canvas = await html2canvas(element, { backgroundColor: '#0b1220', scale: 2, useCORS: true });
  const pdf = new jsPDF({ orientation: 'p', unit: 'pt', format: 'a4' });
  await addCanvasPaginated(pdf, canvas);
  pdf.save(filename);
}

export async function exportSectionsToPdf(sectionIds: string[], filename = 'report.pdf') {
  const pdf = new jsPDF({ orientation: 'p', unit: 'pt', format: 'a4' });
  let firstPage = true;

  for (const id of sectionIds) {
    const element = document.getElementById(id);
    if (!element) continue;
    element.style.background = element.style.background || '#0b1220';
    const canvas = await html2canvas(element, { backgroundColor: '#0b1220', scale: 2, useCORS: true });
    if (!firstPage) pdf.addPage();
    await addCanvasPaginated(pdf, canvas);
    firstPage = false;
  }

  pdf.save(filename);
}
