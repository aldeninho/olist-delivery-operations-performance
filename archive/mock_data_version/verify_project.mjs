import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const metrics = JSON.parse(await fs.readFile(`${root}/data/processed/project_metrics.json`, "utf8"));
const causes = (await fs.readFile(`${root}/data/processed/root_cause_impact.csv`, "utf8")).trim().split("\n");
const raw = (await fs.readFile(`${root}/data/raw/orders.csv`, "utf8")).trim().split("\n");
if (raw.length !== 12001) throw new Error(`Expected 12,000 orders, found ${raw.length - 1}`);
if (metrics.deliveredOrders + Math.round(metrics.cancellationRate * metrics.totalOrders) !== metrics.totalOrders) throw new Error("Delivered/cancelled order reconciliation failed");
if (causes.length < 4) throw new Error("Expected at least three root-cause rows");
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(`${root}/excel/operations_review.xlsx`));
const dashboard = await wb.inspect({kind:"table",range:"Dashboard!A1:H14",include:"values,formulas",tableMaxRows:14,tableMaxCols:8,maxChars:8000});
const errors = await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:50},maxChars:3000});
console.log(JSON.stringify({dashboard:dashboard.ndjson,formulaErrorScan:errors.ndjson,checks:"passed"},null,2));
