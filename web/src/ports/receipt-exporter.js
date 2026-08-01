// L1 port: exporting a receipt (D24, D26). `print` opens the browser's print dialog (the
// passenger saves it as a PDF over a `@media print` stylesheet that shows only the
// receipt); `downloadQrPng` rasterizes the QR matrix into a PNG download. Both touch
// browser globals (window, canvas, an anchor click), so both come through a port - the
// fake records calls instead of touching the DOM.
//
// @typedef {object} ReceiptExporter
// @property {() => void} print
// @property {(matrix: {size:number, isDark:(r:number,c:number)=>boolean}, filename: string) => void} downloadQrPng

export const ReceiptExporter = {};

/** The one place the downloaded QR's filename is decided, so the UI and both adapters
 * agree without repeating the convention. */
export function qrFilename(reference) {
  return `${reference}-qr.png`;
}
