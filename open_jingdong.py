"""
Open browser and go to 京东 (JD.com) website.
- 打开页面后请用手机扫码登录，每一步操作前都会在终端暂停，你按回车后再继续。
- 支持在首页搜索框输入关键词并点击搜索。
用法: python open_jingdong.py [关键词]
  例如: python open_jingdong.py 手机
  不传关键词则使用默认「王者荣耀」。
"""
import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# 脚本所在目录，用于保存文件（避免因运行目录不同而保存到别处）
SCRIPT_DIR = Path(__file__).resolve().parent
# 专门存放页面源码的文件夹
PAGE_SOURCES_DIR = SCRIPT_DIR / "page_sources"


def make_html_viewable(html: str, base_url: str = "https://www.jingdong.com/") -> str:
    """生成可用浏览器直接打开、不卡死的 HTML。
    - 协议相对地址 //xxx 改为 https://xxx，避免在 file:// 下加载失败
    - 插入 <base href="...">，使相对路径正确
    - 移除所有 <script>，避免统计/上报等脚本在本地运行导致卡死
    """
    # 协议相对 URL 转为 https（属性里常见的 "// 和 '//）
    html = re.sub(r'(["\'])(//)', r'\1https://', html)
    # 在 <head> 后插入 base，便于相对路径解析
    html = re.sub(r"<head(\s[^>]*)?>", r'<head\1><base href="' + base_url + '">', html, count=1, flags=re.I)
    if not re.search(r"<base\s", html, re.I):
        html = html.replace("<head>", "<head><base href=\"" + base_url + "\">", 1)
    # 移除所有 script 标签，避免在 file:// 下执行导致卡死
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.I)
    return html


async def open_jingdong(keyword: str | None = None):
    async with async_playwright() as p:
        # Launch system Edge browser (use headless=False to see the browser)
        # --start-maximized: 启动时窗口最大化
        # viewport=None: 视口随窗口大小变化，避免最大化后右侧/下方出现空白
        browser = await p.chromium.launch(
            channel="msedge",
            headless=False,
            args=["--start-maximized"],
        )
        context = await browser.new_context(viewport=None)  # 视口跟随窗口，不固定尺寸
        page = await context.new_page()

        # Go to 京东 (JD.com)
        await page.goto("https://www.jingdong.com/")

        # 京东有持续请求，networkidle 可能永不触发；改用 domcontentloaded 并稍等
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # Step 1: 等待你使用手机扫码登录，完成后在终端按回车再继续
        input("请用手机扫码登录，完成后在终端按回车继续... ")

        # 若弹窗仍存在则关闭，避免挡住后续操作
        try:
            close_btn = page.locator("#login2025-dialog-close")
            if await close_btn.is_visible():
                await close_btn.click(timeout=2000)
                await asyncio.sleep(0.5)
        except Exception:
            pass

        # Step 2: 按回车后再执行搜索
        if keyword and keyword.strip():
            input(f"按回车后将搜索关键词「{keyword.strip()}」... ")
            search_input = page.locator("#key")
            await search_input.wait_for(state="visible", timeout=10000)
            await search_input.fill(keyword.strip())
            await page.locator("button.button:has-text('搜索')").click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            print(f"已搜索: {keyword.strip()}")

        # Step 3: 按回车后再保存页面源码
        input("按回车后保存当前页面源码... ")
        html = await page.content()
        PAGE_SOURCES_DIR.mkdir(exist_ok=True)
        raw_file = PAGE_SOURCES_DIR / "jingdong_page.html"
        raw_file.write_text(html, encoding="utf-8")
        print(f"原始源码已保存: {raw_file}")
        viewable_html = make_html_viewable(html)
        viewable_file = PAGE_SOURCES_DIR / "jingdong_page_viewable.html"
        viewable_file.write_text(viewable_html, encoding="utf-8")
        print(f"可浏览版已保存: {viewable_file}")

        # Step 4: 按回车后关闭浏览器
        input("按回车关闭浏览器... ")
        await browser.close()


# 默认搜索关键词（不传命令行参数时直接使用）
DEFAULT_KEYWORD = "王者荣耀"

if __name__ == "__main__":
    # 未传命令行参数则用「王者荣耀」；传了则用传入的关键词，如: python open_jingdong.py 手机
    kw = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else DEFAULT_KEYWORD
    asyncio.run(open_jingdong(keyword=kw))
