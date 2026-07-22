var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// chinese/yamibo.ts
var yamibo_exports = {};
__export(yamibo_exports, {
  default: () => yamibo_default
});
module.exports = __toCommonJS(yamibo_exports);
var import_storage = require("@/libs/storage");
var YamiboPlugin = class {
  constructor() {
    __publicField(this, "id", "yamibo");
    __publicField(this, "name", "Yamibo (\u767E\u5408\u4F1A)");
    __publicField(this, "icon", "src/chinese/yamibo/icon.png");
    __publicField(this, "site", "https://bbs.yamibo.com");
    __publicField(this, "version", "1.0.0");
    __publicField(this, "pluginSettings", {
      backend_url: {
        value: "http://192.168.1.100:8000",
        label: "Backend URL",
        type: "Text"
      }
    });
  }
  get baseUrl() {
    return (import_storage.storage.get("backend_url") || "http://192.168.1.100:8000") + "/api/v1/source";
  }
  async request(path) {
    const res = await fetch(this.baseUrl + path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
  async popularNovels(page, options) {
    return this.request(`/popular?page=${page}`);
  }
  async parseNovel(novelPath) {
    return this.request(`/novel/${novelPath}`);
  }
  async parseChapter(chapterPath) {
    const res = await fetch(this.baseUrl + `/chapter/${chapterPath}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  }
  async searchNovels(searchTerm, page) {
    return this.request(`/search?q=${encodeURIComponent(searchTerm)}&page=${page}`);
  }
};
var yamibo_default = new YamiboPlugin();
