// Yamibo (百合会) LNReader Plugin
// 薄代理层 — 所有数据通过 Python 后端 REST API 获取
// 放置于 LNReader 插件的 plugins/chinese/ 目录

import { Plugin } from '@/types/plugin';
import { FilterTypes, Filters } from '@/libs/filterInputs';
import { storage } from '@/libs/storage';
import { defaultCover } from '@/libs/defaultCover';

class YamiboPlugin implements Plugin.PluginBase {
    id = 'yamibo';
    name = 'Yamibo (百合会)';
    icon = 'src/chinese/yamibo/icon.png';
    site = 'https://bbs.yamibo.com';
    version = '1.0.0';

    pluginSettings = {
        backend_url: {
            value: 'http://192.168.1.100:8000',
            label: 'Backend URL',
            type: 'Text',
        },
    };

    get baseUrl(): string {
        return (storage.get('backend_url') || 'http://192.168.1.100:8000') + '/api/v1/source';
    }

    async request(path: string): Promise<any> {
        const res = await fetch(this.baseUrl + path);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    async popularNovels(
        page: number,
        options: Plugin.PopularNovelsOptions<typeof this.filters>
    ): Promise<Plugin.NovelItem[]> {
        return this.request(`/popular?page=${page}`);
    }

    async parseNovel(novelPath: string): Promise<Plugin.SourceNovel> {
        return this.request(`/novel/${novelPath}`);
    }

    async parseChapter(chapterPath: string): Promise<string> {
        const res = await fetch(this.baseUrl + `/chapter/${chapterPath}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
    }

    async searchNovels(
        searchTerm: string,
        page: number
    ): Promise<Plugin.NovelItem[]> {
        return this.request(`/search?q=${encodeURIComponent(searchTerm)}&page=${page}`);
    }
}

export default new YamiboPlugin();
