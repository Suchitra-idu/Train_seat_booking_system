// L2: records export calls for component tests. Never touches window/canvas/DOM.

export class FakeReceiptExporter {
  constructor() {
    this.printed = 0;
    this.downloads = [];
  }

  print() {
    this.printed += 1;
  }

  downloadQrPng(matrix, filename) {
    this.downloads.push({ filename, size: matrix.size });
  }
}
