/**
 * PDF Export Utility for Reports
 * Uses jsPDF and html2canvas to export any DOM element to PDF
 */

import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

/**
 * Export a DOM element to PDF
 * @param elementId The ID of the element to export
 * @param filename The filename for the PDF
 */
export async function exportElementToPdf(elementId: string, filename: string = 'report.pdf'): Promise<void> {
  try {
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error(`Element with ID "${elementId}" not found`);
    }

    // Use html2canvas to capture the element
    const canvas = await html2canvas(element, {
      scale: 2,  // Higher resolution
      useCORS: true,  // Enable cross-origin resource sharing
      allowTaint: true,  // Allow cross-origin images
      backgroundColor: '#ffffff',  // White background
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    
    const imgWidth = 210; // A4 width in mm
    const pageHeight = 297; // A4 height in mm
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;
    let position = 0;

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    // Add more pages if content is taller than A4
    while (heightLeft >= 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    // Save the PDF
    pdf.save(filename);
  } catch (error) {
    console.error('Error exporting to PDF:', error);
    throw error;
  }
}

/**
 * Export report section to PDF with title
 * @param elementId Element ID to export 
 * @param title Report title
 * @param filename Output filename
 */
export async function exportReportToPdf(elementId: string, title: string, filename: string): Promise<void> {
  try {
    // Create a temporary wrapper with title
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error(`Element with ID "${elementId}" not found`);
    }

    // Clone the element and add a title header
    const clone = element.cloneNode(true) as HTMLElement;
    const titleHeader = document.createElement('div');
    titleHeader.innerHTML = `
      <div style="padding: 20px 0; margin-bottom: 20px; border-bottom: 2px solid #ccc;">
        <h1 style="font-size: 24px; margin: 0; color: #333;">${title}</h1>
        <p style="margin-top: 8px; color: #666; font-size: 14px;">Generated on: ${new Date().toLocaleString()}</p>
      </div>
    `;
    
    // Insert the title header at the beginning of the cloned element
    clone.insertBefore(titleHeader.firstChild!.cloneNode(true), clone.firstChild);
    
    // Temporarily add the clone to the body to make it renderable
    const tempContainer = document.createElement('div');
    tempContainer.id = 'pdf-temp-container';
    tempContainer.style.position = 'absolute';
    tempContainer.style.left = '-9999px';
    tempContainer.style.width = '210mm'; // A4 width
    tempContainer.appendChild(clone);
    document.body.appendChild(tempContainer);

    await exportElementToPdf('pdf-temp-container', filename);
    
    // Remove temporary container
    document.body.removeChild(tempContainer);
    
    // Remove temporary container
    document.body.removeChild(tempContainer);
  } catch (error) {
    console.error('Error exporting report to PDF:', error);
    throw error;
  }
}

/**
 * Export current page to PDF
 */
export async function exportCurrentPageToPdf(filename: string = 'current-page.pdf'): Promise<void> {
  return exportElementToPdf('root', filename); // Export main content area
}

/**
 * Export selected HTML content to PDF
 * @param htmlContent Raw HTML content to export
 * @param filename Output filename
 * @param title Optional title to add above content
 */
export async function exportHtmlToPdf(htmlContent: string, filename: string, title?: string): Promise<void> {
  try {
    // Create a temporary element with the HTML content
    const tempDiv = document.createElement('div');
    tempDiv.id = 'pdf-temp-content';
    tempDiv.style.width = '210mm'; // A4 width
    tempDiv.style.padding = '20px';
    tempDiv.style.backgroundColor = '#fff';
    
    if (title) {
      tempDiv.innerHTML = `
        <div style="padding-bottom: 20px; margin-bottom: 20px; border-bottom: 2px solid #ccc;">
          <h1 style="font-size: 24px; margin: 0; color: #333;">${title}</h1>
          <p style="margin-top: 8px; color: '#666'; font-size: 14px;">Generated on: ${new Date().toLocaleString()}</p>
        </div>
        ${htmlContent}
      `;
    } else {
      tempDiv.innerHTML = htmlContent;
    }
    
    document.body.appendChild(tempDiv);
    
    await exportElementToPdf('pdf-temp-content', filename);
    
    // Remove temporary element
    document.body.removeChild(tempDiv);
  } catch (error) {
    console.error('Error exporting HTML to PDF:', error);
    throw error;
  }
}

export default {
  exportElementToPdf,
  exportReportToPdf: exportReportToPdf,
  exportCurrentPageToPdf: exportCurrentPageToPdf,
  exportHtmlToPdf
};