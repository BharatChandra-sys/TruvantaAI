// Checks extension/manifest.json before it ships: Manifest V3, a semantic
// version, and every file it names exists. With a tag as the first argument
// (for example v2.6.4), the manifest version must match it.
const fs = require("fs");
const path = require("path");

const dir = path.join(__dirname, "..", "..", "extension");
const m = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
const problems = [];

if (m.manifest_version !== 3) problems.push("manifest_version must be 3");
if (!/^\d+\.\d+\.\d+$/.test(m.version)) problems.push(`bad version "${m.version}"`);

const tag = process.argv[2];
if (tag && tag !== `v${m.version}`) problems.push(`tag ${tag} does not match manifest version ${m.version}`);

const files = [
  m.background?.service_worker,
  m.action?.default_popup,
  m.side_panel?.default_path,
  ...Object.values(m.icons || {}),
  ...Object.values(m.action?.default_icon || {}),
  ...(m.content_scripts || []).flatMap((c) => [...(c.js || []), ...(c.css || [])]),
].filter(Boolean);

for (const f of new Set(files)) {
  if (!fs.existsSync(path.join(dir, f))) problems.push(`missing file: ${f}`);
}

if (problems.length) {
  console.error(problems.map((p) => `manifest: ${p}`).join("\n"));
  process.exit(1);
}
console.log(`manifest ok, version ${m.version}, ${new Set(files).size} files present`);
