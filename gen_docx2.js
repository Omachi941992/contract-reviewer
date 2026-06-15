const path = require("path");
const gm = "C:/Users/LAP60461/AppData/Roaming/npm/node_modules";
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType } = require(path.join(gm, "docx"));
const fs = require("fs");

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };
const CW = 9360;

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
    shading: { fill: "2E75B6", type: ShadingType.CLEAR },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF" })] })],
  });
}
function cell(text, width, opts = {}) {
  const runs = Array.isArray(text)
    ? text.map((t) => new Paragraph({ children: [new TextRun({ text: t, bold: !!opts.bold })] }))
    : [new Paragraph({ children: [new TextRun({ text, bold: !!opts.bold })] })];
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: runs,
  });
}
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] }); }
function bullet(t, level = 0, bold = false) {
  return new Paragraph({ numbering: { reference: "bullets", level },
    children: [new TextRun({ text: t, bold })] });
}
function para(t, opts = {}) {
  return new Paragraph({ spacing: { after: 60 },
    children: [new TextRun({ text: t, bold: !!opts.bold, italics: !!opts.italics, color: opts.color })] });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 280 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 280 } } } },
      ] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER,
        children: [new TextRun("TÓM TẮT BỘ TIÊU CHÍ REVIEW HỢP ĐỒNG / PHỤ LỤC")] }),
      new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER,
        children: [new TextRun("CHƯƠNG TRÌNH KHUYẾN MẠI")] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "Bên A = Đối tác   |   Bên B = Zion", italics: true, color: "595959" })] }),
      new Paragraph({ spacing: { after: 160 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } },
        children: [new TextRun({ text: "Lưu ý: Mỗi tiêu chí có nhiều trường hợp — 1 hợp đồng/phụ lục chỉ áp dụng DUY NHẤT 1 trường hợp, không áp dụng đồng thời.", bold: true, color: "C00000" })] }),

      // 1
      h2("1. Phạm vi hợp tác (chọn 1 trong 4)"),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [1400, 7960],
        rows: [
          new TableRow({ tableHeader: true, children: [headerCell("Trường hợp", 1400), headerCell("Nội dung", 7960)] }),
          new TableRow({ children: [cell("TH1", 1400, { bold: true }), cell("Bên A phối hợp tổ chức, hỗ trợ Bên B triển khai. Bên B tổ chức & triển khai trên hệ thống ZaloPay.", 7960)] }),
          new TableRow({ children: [cell("TH2", 1400, { bold: true }), cell("Bên A tổ chức & triển khai. Bên B thiết lập chương trình trên hệ thống ZaloPay.", 7960)] }),
          new TableRow({ children: [cell("TH3", 1400, { bold: true }), cell("Bên A tổ chức, triển khai & thiết lập trên hệ thống của Bên A. Bên B hỗ trợ Bên A tổ chức.", 7960)] }),
          new TableRow({ children: [cell("TH4", 1400, { bold: true }), cell("Bên A và Bên B phối hợp tổ chức, triển khai trên nền tảng của Bên A.", 7960)] }),
        ],
      }),

      // 2
      h2("2. Thời gian triển khai"),
      bullet("Thời gian phát voucher: từ ngày … đến ngày …"),
      bullet("Thời gian sử dụng voucher: phải LỚN HƠN ngày cuối cùng phát voucher."),

      // 3
      h2("3. Tổng giá trị khuyến mại / tổng ngân sách"),
      bullet("Là số tiền cụ thể, đơn vị VND / VNĐ / đồng."),
      bullet("Phải nêu rõ ĐÃ hay CHƯA bao gồm VAT."),

      // 4
      h2("4. Chi tiết chương trình khuyến mại"),
      bullet("Có thể nêu rõ trong Hợp đồng/Phụ lục, HOẶC nêu chung là hai bên trao đổi qua email."),

      // 5
      h2("5. Số lượng voucher"),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [9360],
        rows: [ new TableRow({ children: [cell("Số lượng voucher = Tổng giá trị KM (TC3) ÷ Giá trị 1 voucher (TC4)", 9360, { bold: true, fill: "E2EFDA" })] }) ],
      }),

      // 6
      h2("6. Hỗ trợ chi phí thực hiện khuyến mại (chọn 1 trong 2)"),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [1400, 7960],
        rows: [
          new TableRow({ tableHeader: true, children: [headerCell("Trường hợp", 1400), headerCell("Nội dung", 7960)] }),
          new TableRow({ children: [cell("TH1", 1400, { bold: true }), cell("Bên A hỗ trợ 100% chi phí.", 7960)] }),
          new TableRow({ children: [cell("TH2", 1400, { bold: true }), cell("Bên A và Bên B chia sẻ chi phí theo tỷ lệ. Chi phí mỗi bên ≤ tổng giá trị/ngân sách × tỷ lệ chia sẻ.", 7960)] }),
        ],
      }),

      // 7
      h2("7. Quy trình đối soát & thanh toán"),
      para("Lưu ý 1 — Kỳ đối soát phụ thuộc thời gian triển khai (TC2):", { bold: true }),
      bullet("≥ 5 tháng: đối soát & thanh toán theo QUÝ.", 1),
      bullet("< 5 tháng: KẾT THÚC chương trình mới đối soát & thanh toán.", 1),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [3120, 6240],
        rows: [
          new TableRow({ tableHeader: true, children: [headerCell("Ví dụ thời gian triển khai", 3120), headerCell("Cách chia đợt đối soát", 6240)] }),
          new TableRow({ children: [cell("01/01 – 31/05/2026 (5 tháng)", 3120), cell(["2 đợt:", "Đợt 1: 01/01 – 31/03/2026", "Đợt 2: 01/04 – 31/05/2026"], 6240)] }),
          new TableRow({ children: [cell("01/02 – 30/06/2026 (5 tháng)", 3120), cell(["2 đợt:", "Đợt 1: 01/02 – 31/03/2026", "Đợt 2: 01/04 – 30/06/2026"], 6240)] }),
          new TableRow({ children: [cell("15/09 – 30/11/2026 (< 5 tháng)", 3120), cell("Kết thúc chương trình mới đối soát & thanh toán.", 6240)] }),
        ],
      }),
      new Paragraph({ spacing: { before: 100, after: 60 },
        children: [new TextRun({ text: "Lưu ý 2 — Bên gửi file đối soát là bên TỔ CHỨC, THIẾT LẬP chương trình:", bold: true })] }),
      bullet("Bên A tổ chức/thiết lập → Bên A gửi đối soát, và ngược lại. Cần wording đúng bên gửi.", 1),

      para("Các bước đối soát & thanh toán:", { bold: true }),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [1400, 7960],
        rows: [
          new TableRow({ tableHeader: true, children: [headerCell("Mốc", 1400), headerCell("Nội dung", 7960)] }),
          new TableRow({ children: [cell("B1", 1400, { bold: true }), cell(["Bên tổ chức gửi số liệu đối soát qua đầu mối liên hệ, gồm:", "– Số GD dùng Thẻ quà tặng thành công; số GD hoàn trả (nếu có)", "– Tổng chi phí Thẻ quà tặng", "– Chi phí hỗ trợ thực tế Bên A phải thanh toán cho Bên B"], 7960)] }),
          new TableRow({ children: [cell("Thời điểm", 1400, { bold: true }), cell("Trong 03 ngày đầu sau khi kết thúc chương trình, HOẶC trong 03 ngày kể từ ngày đầu tháng bắt đầu Quý tiếp theo.", 7960, { fill: "FFF2CC" })] }),
          new TableRow({ children: [cell("B2", 1400, { bold: true }), cell("Trong 03 ngày tiếp theo, bên nhận kiểm tra & phản hồi số liệu qua email.", 7960)] }),
          new TableRow({ children: [cell("→ Thống nhất", 1400, { bold: true }), cell("Bên B xuất hóa đơn theo số liệu đã thống nhất.", 7960)] }),
          new TableRow({ children: [cell("→ Im lặng", 1400, { bold: true }), cell("Quá hạn không phản hồi → xem như đã hoàn thành đối soát, số liệu Bên B là chính xác; Bên B xuất hóa đơn, Bên A thanh toán theo quy định.", 7960)] }),
          new TableRow({ children: [cell("→ Không đồng ý", 1400, { bold: true }), cell("Bên A báo bằng văn bản/email trong thời hạn. Bên B vẫn xuất hóa đơn theo số liệu của mình; hai bên đối soát tiếp 07 ngày làm việc. Nếu chênh lệch → Bên B xuất hóa đơn điều chỉnh; hai bên ký biên bản & điều chỉnh trong 07 ngày tiếp theo.", 7960)] }),
        ],
      }),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("D:/clawcode/Tom_tat_tieu_chi_KM.docx", buf);
  console.log("written");
});
