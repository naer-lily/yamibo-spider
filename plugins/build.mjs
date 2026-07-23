import { copyFileSync } from "fs";

copyFileSync(
  "../server/static/yamibo.js",
  "chinese/yamibo.js"
);

console.log("yamibo.js → plugins/chinese/yamibo.js 同步完成");
console.log("注意: 源文件是 server/static/yamibo.js（手写 JS）");

