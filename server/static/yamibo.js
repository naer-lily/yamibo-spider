// Yamibo (百合会) LNReader Plugin
// 薄代理层 — 所有数据通过 Python 后端 REST API 获取
// 直接在 LNReader 沙箱中运行，使用 require() 获取内置模块

var storage = require("@/libs/storage").storage;

function YamiboPlugin() {
  this.id = "yamibo";
  this.name = "Yamibo (百合会)";
  this.icon = "src/chinese/yamibo/icon.png";
  this.site = "https://bbs.yamibo.com";
  this.version = "1.0.0";

  this.pluginSettings = {
    backend_url: {
      value: "http://192.168.1.100:8000",
      label: "Backend URL",
      type: "Text",
    },
  };
}

YamiboPlugin.prototype = {
  get baseUrl() {
    return (
      (storage.get("backend_url") || "http://192.168.1.100:8000") +
      "/api/v1/source"
    );
  },

  request: async function (path) {
    var res = await fetch(this.baseUrl + path);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  },

  popularNovels: async function (page, options) {
    return this.request("/popular?page=" + page);
  },

  parseNovel: async function (novelPath) {
    return this.request("/novel/" + novelPath);
  },

  parseChapter: async function (chapterPath) {
    var res = await fetch(this.baseUrl + "/chapter/" + chapterPath);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.text();
  },

  searchNovels: async function (searchTerm, page) {
    return this.request(
      "/search?q=" + encodeURIComponent(searchTerm) + "&page=" + page
    );
  },
};

exports.default = new YamiboPlugin();
