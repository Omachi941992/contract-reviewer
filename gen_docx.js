const path = require("path");
const gm = "C:/Users/LAP60461/AppData/Roaming/npm/node_modules";
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
        ShadingType, ExternalHyperlink } = require(path.join(gm, "docx"));
const fs = require("fs");

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
    shading: { fill: "2E75B6", type: ShadingType.CLEAR },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: "FFFFFF" })] })],
  });
}
function cell(text, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text, bold: !!opts.bold })] })],
  });
}

const CW = 9360;

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER,
        children: [new TextRun("TÓM TẮT BIỂU PHÍ & ĐỐI SOÁT")] }),

      // 1. ZNS/ZBS
      new Paragraph({ heading: HeadingLevel.HEADING_2,
        children: [new TextRun("1. Giá tin ZNS / ZBS (gửi qua số điện thoại)")] }),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [5400, 3960],
        rows: [
          new TableRow({ tableHeader: true, children: [headerCell("Mức sử dụng", 5400), headerCell("Đơn giá", 3960)] }),
          new TableRow({ children: [cell("Có hoặc không có nút CTA", 5400), cell("85% đơn giá", 3960, { bold: true })] }),
          new TableRow({ children: [cell("≤ 5.000 tin/tháng", 5400), cell("Miễn phí", 3960, { bold: true, fill: "E2EFDA" })] }),
          new TableRow({ children: [cell("Từ tin thứ 5.001/tháng trở đi (áp dụng cho cả ZNS/ZBS và CTA)", 5400), cell("70% đơn giá công khai trên zalo.cloud", 3960, { bold: true })] }),
        ],
      }),

      // 2. UID
      new Paragraph({ heading: HeadingLevel.HEADING_2,
        children: [new TextRun("2. Tin nhắn UID")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Tính 100% đơn giá.")] }),

      // 3. Thay đổi phí
      new Paragraph({ heading: HeadingLevel.HEADING_2,
        children: [new TextRun("3. Thay đổi Phí Dịch Vụ")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Bên B báo trước cho Bên A qua email đầu mối liên hệ, ít nhất 15 ngày trước ngày áp dụng mức phí mới.")] }),

      // 4. Đối soát
      new Paragraph({ heading: HeadingLevel.HEADING_2,
        children: [new TextRun("4. Đối soát & Thanh toán")] }),
      new Table({
        width: { size: CW, type: WidthType.DXA }, columnWidths: [6000, 3360],
        rows: [
          new TableRow({ tableHeader: true, children: [headerCell("Bước", 6000), headerCell("Thời hạn", 3360)] }),
          new TableRow({ children: [cell("Gửi đối soát sau mỗi tháng", 6000), cell("03 ngày đầu tháng sau", 3360, { bold: true })] }),
          new TableRow({ children: [cell("Phản hồi/xác nhận sau khi nhận email đối soát", 6000), cell("03 ngày", 3360, { bold: true })] }),
          new TableRow({ children: [cell("Nếu không đồng ý về số liệu đối soát", 6000), cell("Đối soát tiếp trong 07 ngày", 3360, { bold: true })] }),
          new TableRow({ children: [cell("Nếu còn chênh lệch với hóa đơn đã xuất", 6000), cell("Chuyển phần chênh lệch sang kỳ đối soát sau", 3360, { bold: true })] }),
        ],
      }),
    ],
  }],
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("D:/clawcode/Tom_tat_bieu_phi.docx", buf);
  console.log("written");
});
