"""Playwright 登录 — 浏览器手动登录后写入 cookies.json"""

import asyncio

from playwright.async_api import async_playwright

from server.config import COOKIE_PATH, LOGIN_CHECK_URL
from server.yamibo.client import check_login, save_cookies, yamibo_client


async def do_login(headless: bool = False):
    """打开浏览器让用户手动登录，成功后持久化 Cookie"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        last_cookies = None
        while True:
            if page.url != LOGIN_CHECK_URL:
                await page.goto(LOGIN_CHECK_URL)
            await asyncio.sleep(0.2)

            try:
                cookies = list(await context.cookies())  # type: ignore[arg-type]
                if cookies == last_cookies:
                    continue

                save_cookies(cookies)

                async with yamibo_client() as client:
                    if await check_login(client):
                        print("登录成功，Cookie 已保存到 cookies.json")
                        await browser.close()
                        return
                last_cookies = cookies

            except Exception:
                raise RuntimeError("浏览器被关闭，登录未完成")


if __name__ == "__main__":
    asyncio.run(do_login())
