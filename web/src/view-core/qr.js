// L0 view-core: reference -> QR matrix. Pure - qrcode-generator is a dependency-free
// encoding algorithm (no DOM, no I/O), so building the matrix belongs here; only the UI
// component turns the matrix into an <svg>.

import qrcodeGenerator from "qrcode-generator";

/**
 * @param {string} payload
 * @returns {{size: number, isDark: (row: number, col: number) => boolean}}
 */
export function qrMatrix(payload) {
  const qr = qrcodeGenerator(0, "M");
  qr.addData(String(payload || ""));
  qr.make();
  const size = qr.getModuleCount();
  return { size, isDark: (row, col) => qr.isDark(row, col) };
}
