import { describe, it, expect } from "vitest";
import { qrMatrix } from "./qr.js";

describe("qrMatrix main path", () => {
  it("encodes a reference into a square boolean matrix", () => {
    const { size, isDark } = qrMatrix("SLR-7K3M-92");
    expect(size).toBeGreaterThan(0);
    let darkCount = 0;
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (isDark(r, c)) darkCount++;
      }
    }
    expect(darkCount).toBeGreaterThan(0);
  });
});
