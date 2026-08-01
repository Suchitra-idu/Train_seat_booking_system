// L2: real receipt export. `print()` opens the browser print dialog; `app/app.css`'s
// `@media print` rule shows only the receipt card. `downloadQrPng` draws the QR matrix
// onto an off-screen canvas and triggers a file download, no image library needed for a
// grid of black/white squares.

const MODULE_PX = 8; // upscale each QR module so the PNG isn't a postage stamp
const QUIET_ZONE = 4; // modules of white border, per the QR spec

export class RealReceiptExporter {
  print() {
    window.print();
  }

  downloadQrPng(matrix, filename) {
    const { size, isDark } = matrix;
    const side = (size + QUIET_ZONE * 2) * MODULE_PX;
    const canvas = document.createElement("canvas");
    canvas.width = side;
    canvas.height = side;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, side, side);
    ctx.fillStyle = "#000000";
    for (let row = 0; row < size; row++) {
      for (let col = 0; col < size; col++) {
        if (!isDark(row, col)) continue;
        ctx.fillRect(
          (col + QUIET_ZONE) * MODULE_PX,
          (row + QUIET_ZONE) * MODULE_PX,
          MODULE_PX,
          MODULE_PX,
        );
      }
    }

    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = filename;
    link.click();
  }
}
