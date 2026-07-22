import * as esbuild from "esbuild";

await esbuild.build({
  entryPoints: ["chinese/yamibo.ts"],
  bundle: true,
  platform: "neutral",
  format: "cjs",
  target: "es2020",
  outfile: "../server/static/yamibo.js",
  external: [
    "@/types/plugin",
    "@/libs/*",
    "cheerio",
    "htmlparser2",
    "dayjs",
    "urlencode",
    "@libs/*",
  ],
});

console.log("yamibo.js → server/static/yamibo.js 构建完成");
