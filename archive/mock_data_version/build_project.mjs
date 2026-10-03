import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const out = (...parts) => path.join(root, ...parts);
const rng = (() => { let s = 20261003; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); })();
const pick = (a) => a[Math.floor(rng() * a.length)];
const normal = (mean, spread) => { const u = Math.max(rng(), 1e-9), v = rng(); return mean + spread * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
const iso = d => d.toISOString().slice(0, 10);
const addDays = (d, days) => { const n = new Date(d); n.setUTCDate(n.getUTCDate() + Math.round(days)); return n; };
const csv = (rows) => rows.map(row => row.map(v => { const s = v instanceof Date ? iso(v) : String(v ?? ""); return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s; }).join(",")).join("\n") + "\n";

const regions = [
  ["North", "Delhi NCR", 1.1], ["North", "Punjab", 1.0], ["West", "Maharashtra", 1.0],
  ["West", "Gujarat", 1.1], ["South", "Karnataka", 1.0], ["South", "Tamil Nadu", 1.1],
  ["East", "West Bengal", 1.25], ["East", "Odisha", 1.55], ["Central", "Madhya Pradesh", 1.30]
];
const vendors = [
  ["V001", "SwiftCart", 1.00], ["V002", "UrbanDrop", 1.02], ["V003", "PrimeShip", 1.05],
  ["V004", "QuickRoute", 1.32], ["V005", "ValueMart", 1.10], ["V006", "EcoFulfil", 1.18],
  ["V007", "MetroSupply", 0.98], ["V008", "RapidRetail", 1.15]
];
const categories = [["Electronics", 1.25], ["Home & Kitchen", 1.05], ["Fashion", 0.90], ["Beauty", 0.80], ["Grocery", 0.75]];
const headers = ["order_id","order_date","promised_date","shipped_date","delivered_date","status","region","state","vendor_id","vendor_name","category","order_value_inr","fulfillment_cost_inr","delivery_days","sla_breach","cancellation_reason","root_cause","data_quality_flag"];
const orders = [];
for (let i = 1; i <= 12000; i++) {
  const orderDate = addDays(new Date(Date.UTC(2025, 0, 1)), Math.floor(rng() * 365));
  const [region, state, regionalDelay] = pick(regions);
  const [vendorId, vendorName, vendorDelay] = pick(vendors);
  const [category, categoryFactor] = pick(categories);
  const monthPeak = [10, 11].includes(orderDate.getUTCMonth()) ? 0.35 : 0;
  const cancelP = 0.032 + (vendorId === "V004" ? 0.035 : 0) + (region === "East" ? 0.015 : 0) + monthPeak * 0.02;
  const isCancelled = rng() < cancelP;
  const promisedDays = category === "Grocery" ? 3 : 5;
  const promisedDate = addDays(orderDate, promisedDays);
  const shippingLag = Math.max(0, Math.round(normal(1.1 + (vendorId === "V004" ? 0.75 : 0), 0.55)));
  const shippedDate = isCancelled && rng() < 0.62 ? null : addDays(orderDate, shippingLag);
  let deliveryDays = null, deliveredDate = null, rootCause = "";
  let cancellationReason = "";
  if (isCancelled) {
    cancellationReason = pick(["Customer changed mind", "Address not serviceable", "Inventory unavailable", "Payment failure"]);
    rootCause = cancellationReason === "Address not serviceable" ? "Address / serviceability" : cancellationReason === "Inventory unavailable" ? "Inventory availability" : "Customer / payment cancellation";
  } else {
    const weather = (region === "East" && rng() < 0.22) ? 1.8 : 0;
    const vendorIssue = vendorId === "V004" ? 1.65 : vendorId === "V006" ? 0.65 : 0;
    const remote = state === "Odisha" ? 0.85 : 0;
    deliveryDays = Math.max(1, Math.round(normal(3.1 * categoryFactor + regionalDelay + vendorDelay + vendorIssue + weather + remote + monthPeak, 1.15)));
    deliveredDate = addDays(orderDate, deliveryDays);
    rootCause = vendorIssue >= 1 ? "Vendor fulfillment delay" : weather > 0 ? "Regional last-mile disruption" : remote > 0 ? "Regional last-mile disruption" : "Normal operating variation";
  }
  const breach = !isCancelled && deliveredDate > promisedDate ? "Yes" : "No";
  const orderValue = Math.round(Math.max(250, normal(1850 * categoryFactor, 950)));
  const cost = Math.round(Math.max(65, 120 + deliveryDays * 32 + regionalDelay * 24 + vendorDelay * 18 + (breach === "Yes" ? 42 : 0)));
  const dq = i % 997 === 0 ? "Missing optional tracking event" : "Valid";
  orders.push([`ORD${String(i).padStart(5, "0")}`, iso(orderDate), iso(promisedDate), shippedDate ? iso(shippedDate) : "", deliveredDate ? iso(deliveredDate) : "", isCancelled ? "Cancelled" : "Delivered", region, state, vendorId, vendorName, category, orderValue, cost, deliveryDays ?? "", breach, cancellationReason, rootCause, dq]);
}
await Promise.all([out("data", "raw"), out("data", "processed"), out("excel"), out("images")].map(p => fs.mkdir(p, { recursive: true })));
await fs.writeFile(out("data", "raw", "orders.csv"), csv([headers, ...orders]));

const delivered = orders.filter(r => r[5] === "Delivered");
const cancelled = orders.filter(r => r[5] === "Cancelled");
const metrics = {
  totalOrders: orders.length,
  deliveredOrders: delivered.length,
  cancellationRate: cancelled.length / orders.length,
  onTimeRate: delivered.filter(r => r[14] === "No").length / delivered.length,
  avgDeliveryDays: delivered.reduce((s, r) => s + r[13], 0) / delivered.length,
  breachRate: delivered.filter(r => r[14] === "Yes").length / delivered.length,
  costPerOrder: delivered.reduce((s, r) => s + r[12], 0) / delivered.length
};
const group = (rows, keyIndex) => [...rows.reduce((m, r) => { const k = r[keyIndex]; (m.get(k) ?? m.set(k, []).get(k)).push(r); return m; }, new Map()).entries()];
const calc = (name, rows) => { const d = rows.filter(r => r[5] === "Delivered"); const c = rows.filter(r => r[5] === "Cancelled"); return [name, rows.length, d.length, c.length / rows.length, d.filter(r => r[14] === "No").length / d.length, d.filter(r => r[14] === "Yes").length / d.length, d.reduce((s,r)=>s+r[13],0)/d.length, d.reduce((s,r)=>s+r[12],0)/d.length]; };
const vendorSummary = group(orders, 9).map(([k, rs]) => calc(k, rs)).sort((a,b) => a[4]-b[4]);
const regionSummary = group(orders, 6).map(([k, rs]) => calc(k, rs)).sort((a,b) => a[4]-b[4]);
const monthBuckets = orders.reduce((m, r) => { const k = r[1].slice(0, 7); (m.get(k) ?? m.set(k, []).get(k)).push(r); return m; }, new Map());
const monthSummary = [...monthBuckets.entries()].map(([k, rs]) => [k, ...calc(k, rs).slice(1)]).sort((a,b) => a[0].localeCompare(b[0]));
const issueRows = group(orders.filter(r => r[16] !== "Normal operating variation"), 16).map(([k, rs]) => [k, rs.length, rs.filter(r=>r[14]==="Yes").length, rs.filter(r=>r[5]==="Cancelled").length, rs.reduce((s,r)=>s+r[12],0)]).sort((a,b) => (b[2]+b[3])- (a[2]+a[3]));
await fs.writeFile(out("data", "processed", "vendor_performance.csv"), csv([["vendor","total_orders","delivered_orders","cancellation_rate","on_time_rate","sla_breach_rate","avg_delivery_days","cost_per_delivered_order_inr"], ...vendorSummary]));
await fs.writeFile(out("data", "processed", "region_performance.csv"), csv([["region","total_orders","delivered_orders","cancellation_rate","on_time_rate","sla_breach_rate","avg_delivery_days","cost_per_delivered_order_inr"], ...regionSummary]));
await fs.writeFile(out("data", "processed", "monthly_performance.csv"), csv([["month","total_orders","delivered_orders","cancellation_rate","on_time_rate","sla_breach_rate","avg_delivery_days","cost_per_delivered_order_inr"], ...monthSummary]));
await fs.writeFile(out("data", "processed", "root_cause_impact.csv"), csv([["root_cause","affected_orders","sla_breaches","cancellations","fulfillment_cost_inr"], ...issueRows]));
await fs.writeFile(out("data", "processed", "project_metrics.json"), JSON.stringify(metrics, null, 2));

const wb = Workbook.create();
const dash = wb.worksheets.add("Dashboard"), vendor = wb.worksheets.add("Vendor performance"), region = wb.worksheets.add("Region performance"), monthly = wb.worksheets.add("Monthly trend"), causes = wb.worksheets.add("Root causes"), dictionary = wb.worksheets.add("Data dictionary"), raw = wb.worksheets.add("Raw orders");
for (const s of [dash, vendor, region, monthly, causes, dictionary, raw]) { s.showGridLines = false; }
const title = (sheet, text) => { sheet.getRange("A2:H2").merge(); sheet.getRange("A2").values = [[text]]; sheet.getRange("A2").format = {font:{name:"Arial",size:16,bold:true,color:"#1F2937"},horizontalAlignment:"left"}; };
const header = (sheet, range) => { sheet.getRange(range).format = {fill:"#1F4E78",font:{name:"Arial",size:10,bold:true,color:"#FFFFFF"},horizontalAlignment:"center",verticalAlignment:"center",borders:{preset:"all",style:"thin",color:"#FFFFFF"}}; };
const formatTable = (sheet, range) => { sheet.getRange(range).format.font = {name:"Arial",size:10,color:"#1F2937"}; sheet.getRange(range).format.borders = {preset:"outside",style:"thin",color:"#D1D5DB"}; sheet.getRange(range).format.verticalAlignment="center"; };
title(dash, "Delivery Operations Performance Dashboard");
dash.getRange("A4:H4").merge(); dash.getRange("A4").values = [["Simulated 2025 order operations data | All rates use delivered orders unless stated otherwise"]]; dash.getRange("A4").format = {font:{name:"Arial",size:10,italic:true,color:"#4B5563"}};
const kpis = [["Total orders", metrics.totalOrders, "#,##0"],["On-time delivery", metrics.onTimeRate, "0.0%"],["Average delivery time", metrics.avgDeliveryDays, "0.0 \"days\""],["SLA breach rate", metrics.breachRate, "0.0%"],["Cancellation rate", metrics.cancellationRate, "0.0%"],["Cost per delivered order", metrics.costPerOrder, "₹#,##0"]];
kpis.forEach((k,i)=> { const c=i*2; dash.getCell(5,c).values=[[k[0]]]; dash.getCell(6,c).values=[[k[1]]]; dash.getRangeByIndexes(5,c,1,2).merge(); dash.getRangeByIndexes(6,c,1,2).merge(); dash.getRangeByIndexes(5,c,1,2).format={fill:"#DCE6F1",font:{name:"Arial",size:10,bold:true,color:"#1F4E78"},horizontalAlignment:"center"}; dash.getRangeByIndexes(6,c,1,2).format={fill:"#F8FAFC",font:{name:"Arial",size:14,bold:true,color:"#1F2937"},horizontalAlignment:"center",numberFormat:k[2],borders:{preset:"outside",style:"thin",color:"#B8C6D9"}}; });
dash.getRange("A10:E10").values = [["Priority issue","Evidence","Operational impact","Recommended action","Owner"]]; header(dash,"A10:E10");
const recs = [["Vendor fulfillment delay","1,438 affected orders and 1,348 SLA breaches","Late deliveries and escalation risk","Launch vendor recovery plan and weekly SLA review","Vendor Operations"],["Regional last-mile disruption","1,312 affected orders and 1,168 SLA breaches","SLA breaches and higher delivery cost","Rebalance carrier coverage and add route-level monitoring","Logistics"],["Customer / payment cancellation","256 cancelled orders","Preventable cancellations and lost demand","Add payment retry and pre-cancellation support","Customer Experience"]];
dash.getRange("A11:E13").values=recs; formatTable(dash,"A11:E13"); dash.getRange("A11:E13").format.wrapText=true; dash.getRange("A11:E13").format.rowHeight=36;
dash.getRange("G10:H10").values=[["Metric definitions",""]]; dash.getRange("G10:H10").merge(); header(dash,"G10:H10"); dash.getRange("G11:H14").values=[["On-time", "Delivered on/before promised date"],["SLA breach", "Delivered after promised date"],["Cancellation", "Cancelled orders / all orders"],["Cost per order", "Fulfillment cost / delivered orders"]]; formatTable(dash,"G11:H14"); dash.getRange("G11:G14").format.columnWidth=18; dash.getRange("H11:H14").format.columnWidth=34; dash.getRange("H11:H14").format.font={name:"Arial",size:9,color:"#1F2937"};
dash.getRange("S1:T13").values = [["Month","On-time rate"], ...monthSummary.map(r=>[r[0],r[4]])];
const line = dash.charts.add("line", dash.getRange("S1:T13")); line.title="On-time delivery trend"; line.hasLegend=false; line.setPosition("G16","N31"); line.yAxis={numberFormatCode:"0%",numberFormatSourceLinked:false};
dash.getRange("S15:T23").values=[["Vendor","On-time rate"],...vendorSummary.map(r=>[r[0],r[4]])]; const bar=dash.charts.add("bar",dash.getRange("S15:T23")); bar.title="On-time delivery by vendor"; bar.hasLegend=false; bar.setPosition("A16","F31"); bar.yAxis={numberFormatCode:"0%",numberFormatSourceLinked:false};

const makeSummary = (sheet, titleText, rows) => { title(sheet,titleText); const h=["Dimension","Total orders","Delivered orders","Cancellation rate","On-time rate","SLA breach rate","Avg delivery days","Cost / delivered order (INR)"]; sheet.getRange("A4:H4").values=[h]; header(sheet,"A4:H4"); sheet.getRange(`A5:H${4+rows.length}`).values=rows; formatTable(sheet,`A5:H${4+rows.length}`); sheet.getRange(`B5:C${4+rows.length}`).format.numberFormat="#,##0"; sheet.getRange(`D5:F${4+rows.length}`).format.numberFormat="0.0%"; sheet.getRange(`G5:G${4+rows.length}`).format.numberFormat="0.0"; sheet.getRange(`H5:H${4+rows.length}`).format.numberFormat="₹#,##0"; sheet.freezePanes.freezeRows(4); };
makeSummary(vendor,"Vendor Performance",vendorSummary); makeSummary(region,"Regional Performance",regionSummary);
title(monthly,"Monthly Operations Trend"); monthly.getRange("A4:H4").values=[["Month","Total orders","Delivered orders","Cancellation rate","On-time rate","SLA breach rate","Avg delivery days","Cost / delivered order (INR)"]]; header(monthly,"A4:H4"); monthly.getRange("A5:H16").values=monthSummary; formatTable(monthly,"A5:H16"); monthly.getRange("B5:C16").format.numberFormat="#,##0"; monthly.getRange("D5:F16").format.numberFormat="0.0%"; monthly.getRange("G5:G16").format.numberFormat="0.0"; monthly.getRange("H5:H16").format.numberFormat="₹#,##0"; monthly.freezePanes.freezeRows(4);
title(causes,"Root Cause Impact"); causes.getRange("A4:E4").values=[["Root cause","Affected orders","SLA breaches","Cancellations","Fulfillment cost (INR)"]]; header(causes,"A4:E4"); causes.getRange(`A5:E${4+issueRows.length}`).values=issueRows; formatTable(causes,`A5:E${4+issueRows.length}`); causes.getRange(`B5:D${4+issueRows.length}`).format.numberFormat="#,##0"; causes.getRange(`E5:E${4+issueRows.length}`).format.numberFormat="₹#,##0";
title(dictionary,"Data Dictionary"); const dict=[["Field","Definition"],["order_id","Unique order identifier"],["promised_date","Customer-facing delivery commitment"],["delivery_days","Order date to delivery date; blank for cancelled orders"],["sla_breach","Delivered after promised_date"],["root_cause","Simulated operational cause taxonomy"],["data_quality_flag","Record-level quality check output"]]; dictionary.getRange("A4:B10").values=dict; header(dictionary,"A4:B4"); formatTable(dictionary,"A5:B10");
raw.getRangeByIndexes(0,0,orders.length+1,headers.length).values=[headers,...orders]; header(raw,"A1:R1"); raw.getRange(`A2:R${orders.length+1}`).format.font={name:"Arial",size:9,color:"#1F2937"}; raw.freezePanes.freezeRows(1); raw.getRange(`B2:E${orders.length+1}`).format.numberFormat="yyyy-mm-dd";
for (const s of [dash,vendor,region,monthly,causes,dictionary,raw]) { s.getUsedRange().format.autofitColumns(); }
dash.getRange("A1:N31").format.columnWidth = 15; dash.getRange("A1:A31").format.columnWidth=24; dash.getRange("B1:B31").format.columnWidth=18; dash.getRange("C1:C31").format.columnWidth=26; dash.getRange("D1:D31").format.columnWidth=30; dash.getRange("E1:E31").format.columnWidth=20; dash.getRange("K7:L7").format.numberFormat="#,##0 \"INR\"";
wb.recalculate();
const preview = await wb.render({sheetName:"Dashboard",range:"A1:N31",scale:1.2,format:"png"}); await fs.writeFile(out("images","excel_dashboard_preview.png"),new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(wb); await xlsx.save(out("excel","operations_review.xlsx"));
console.log(JSON.stringify({metrics, vendorWorst:vendorSummary[0][0], regionWorst:regionSummary[0][0], issueRows},null,2));
