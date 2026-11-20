// Bundles the Function (src/index.ts, which already carries the browser bundle as a string) into ONE ES module, dist/index.mjs,
// and zips it as dist/function.zip - exactly the archive Neon's deploy endpoint expects (entry file named index.mjs). This is
// the same bundle `neon deploy` builds; it exists so a deploy can be made with the Neon API alone, from a container that has
// no neon CLI session (scripts/deploy-api.sh). The banner restores require / __filename / __dirname for the CommonJS packages
// inside the bundle (pg uses them); without it the runtime fails with "Dynamic require of ... is not supported".
import { build } from "esbuild";
import { mkdirSync, writeFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateRawSync, crc32 } from "node:zlib";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = resolve(root, "dist/index.mjs");
mkdirSync(dirname(out), { recursive: true });
const result = await build({
  entryPoints: [resolve(root, "src/index.ts")],
  bundle: true,
  platform: "node",
  target: "node24",
  format: "esm",
  minify: true,
  legalComments: "none",
  write: false,
  banner: { js: "import{createRequire as ___cr}from'module';import{fileURLToPath as ___f}from'url';import{dirname as ___d}from'path';const require=___cr(import.meta.url);const __filename=___f(import.meta.url);const __dirname=___d(__filename);" },
});
const js = Buffer.from(result.outputFiles[0].contents);
writeFileSync(out, js);

// a one-file ZIP (deflate), written by hand so the build needs no zip binary and no extra package
const name = Buffer.from("index.mjs");
const data = deflateRawSync(js, { level: 9 });
const crc = crc32(js) >>> 0;
const u16 = (n) => { const b = Buffer.alloc(2); b.writeUInt16LE(n); return b; };
const u32 = (n) => { const b = Buffer.alloc(4); b.writeUInt32LE(n >>> 0); return b; };
const DOS_TIME = u16(0), DOS_DATE = u16(((2026 - 1980) << 9) | (1 << 5) | 1);            // a fixed stamp keeps the archive reproducible
const local = Buffer.concat([u32(0x04034b50), u16(20), u16(0), u16(8), DOS_TIME, DOS_DATE, u32(crc), u32(data.length), u32(js.length), u16(name.length), u16(0), name]);
const central = Buffer.concat([u32(0x02014b50), u16(20), u16(20), u16(0), u16(8), DOS_TIME, DOS_DATE, u32(crc), u32(data.length), u32(js.length), u16(name.length), u16(0), u16(0), u16(0), u16(0), u32(0o100644 << 16), u32(0), name]);
const end = Buffer.concat([u32(0x06054b50), u16(0), u16(0), u16(1), u16(1), u32(central.length), u32(local.length + data.length), u16(0)]);
const zip = resolve(root, "dist/function.zip");
writeFileSync(zip, Buffer.concat([local, data, central, end]));
console.log("function bundle: %d KB -> dist/index.mjs ; zip %d KB -> dist/function.zip", Math.round(js.length / 1024), Math.round(statSync(zip).size / 1024));
