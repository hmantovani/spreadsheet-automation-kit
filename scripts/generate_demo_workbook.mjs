import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

// The bundled authoring runtime is supplied by Codex, not a project dependency.
const { Workbook, SpreadsheetFile } = await import(process.env.ARTIFACT_TOOL_URL);
const outputDir = new URL('../sample_data/', import.meta.url);
const categories = {
  hardware: ['accessories', 'devices', 'components'],
  service: ['consulting', 'implementation', 'support'],
  software: ['licenses', 'subscriptions', 'training'],
};
const categoryNames = Object.keys(categories);
const channels = ['direct', 'partner', 'online'];
const regions = ['north', 'south', 'east', 'west'];
const customers = Array.from({length: 30}, (_, i) => `Demo Customer ${String(i + 1).padStart(2, '0')}`);
const anomalies = new Map([
  [16, ['MISSING_REQUIRED', row => { row.record_id = ''; }]],
  [74, ['INVALID_DATE', row => { row.transaction_date = '03/04/2026'; }]],
  [87, ['INVALID_DECIMAL', row => { row.amount = 'sem valor'; }]],
  [132, ['INVALID_DECIMAL', row => { row.amount = 'unknown'; }]],
  [145, ['MISSING_REQUIRED', row => { row.customer_name = ''; }]],
  [208, ['INVALID_CATEGORY', row => { row.category = 'other'; }]],
  [233, ['INVALID_SUBCATEGORY', row => { row.subcategory = 'mystery'; }]],
  [274, ['CATEGORY_SUBCATEGORY_MISMATCH', row => { row.subcategory = 'devices'; }]],
  [305, ['MISSING_REQUIRED', row => { row.category = ''; }]],
  [319, ['DUPLICATE_KEY', row => { row.record_id = 'S-1002'; }]],
  [351, ['INVALID_SALES_CHANNEL', row => { row.sales_channel = 'marketplace'; }]],
  [357, ['INVALID_REGION', row => { row.region = 'central'; }]],
]);

function baseRow(i) {
  const category = categoryNames[i % 3];
  const subcategory = categories[category][Math.floor(i / 3) % 3];
  const month = Math.floor(i / 60) + 1;
  const day = 13 + i % 16;
  const cents = [15000, 25000, 12000][i % 3] + (i * 137) % 18000 + (month - 1) * 2200;
  return {
    record_id: `S-${1001 + i}`,
    transaction_date: `2026-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
    customer_name: customers[(i * 7) % customers.length],
    description: `${subcategory[0].toUpperCase()}${subcategory.slice(1)} order`,
    amount: (cents / 100).toFixed(2),
    category,
    subcategory,
    sales_channel: channels[Math.floor(i / 9) % 3],
    region: regions[Math.floor(i / 27) % 4],
  };
}

function csvCell(value) {
  const text = String(value ?? '');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

const csvHeaders = ['Order ID', 'Order Date', 'Customer', 'Item', 'Total', 'Type', 'Subcategory', 'Channel', 'Region'];
const xlsxHeaders = ['Pedido', 'Data venda', 'Cliente', 'Descricao', 'Valor total', 'Categoria', 'Subcategoria', 'Canal', 'Regiao'];
const csvRows = [csvHeaders];
const xlsxRows = [xlsxHeaders];
const exceptionReasons = {};
const acceptedIds = [];
for (let i = 0; i < 360; i++) {
  const row = baseRow(i);
  const anomaly = anomalies.get(i);
  if (anomaly) anomaly[1](row);
  const isCsv = i % 2 === 0;
  const sourceRow = Math.floor(i / 2) + 2;
  const sourceName = isCsv ? 'english_orders.csv' : 'portuguese_orders.xlsx';
  if (anomaly) exceptionReasons[`${sourceName}:${sourceRow}`] = [anomaly[0]];
  else acceptedIds.push(row.record_id);
  const [year, month, day] = row.transaction_date.split('-');
  const date = row.transaction_date === '03/04/2026' ? row.transaction_date :
    isCsv && i % 4 === 2 ? `${month}/${day}/${year}` :
    isCsv ? row.transaction_date : `${day}/${month}/${year}`;
  const amount = /^\d+\.\d{2}$/.test(row.amount) ?
    Number(row.amount).toLocaleString(isCsv ? 'en-US' : 'de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : row.amount;
  const cells = [row.record_id, date, row.customer_name, row.description, amount, row.category, row.subcategory, row.sales_channel, row.region];
  (isCsv ? csvRows : xlsxRows).push(cells);
}

await fs.writeFile(new URL('english_orders.csv', outputDir), csvRows.map(row => row.map(csvCell).join(',')).join('\n') + '\n', 'utf8');
const expected = {
  input: 360, accepted: 348, rejected: 12, duplicates: 1, output: 348,
  accepted_ids: acceptedIds,
  exception_reasons: exceptionReasons,
};
await fs.writeFile(new URL('expected.json', outputDir), JSON.stringify(expected, null, 2) + '\n', 'utf8');

const workbook = Workbook.create();
const sheet = workbook.worksheets.add('Pedidos');
sheet.showGridLines = false;
sheet.getRange(`A1:I${xlsxRows.length}`).values = xlsxRows;
sheet.getRange(`A1:I${xlsxRows.length}`).format.font = {name: 'Arial', size: 10};
sheet.getRange('A1:I1').format = {fill: '#243B53', font: {name: 'Arial', size: 10, bold: true, color: '#FFFFFF'}};
sheet.getRange('A:A').format.columnWidth = 16;
sheet.getRange('B:B').format.columnWidth = 17;
sheet.getRange('C:C').format.columnWidth = 24;
sheet.getRange('D:D').format.columnWidth = 25;
sheet.getRange('E:I').format.columnWidth = 17;
sheet.freezePanes.freezeRows(1);
workbook.recalculate();
const preview = await workbook.render({sheetName: 'Pedidos', range: 'A1:I10', scale: 1.5, format: 'png'});
await fs.writeFile(new URL('.fixture-preview.png', outputDir), new Uint8Array(await preview.arrayBuffer()));
const file = await SpreadsheetFile.exportXlsx(workbook);
await file.save(fileURLToPath(new URL('portuguese_orders.xlsx', outputDir)));
