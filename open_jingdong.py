"""
Open browser and go to 京东 (JD.com) website.
- 打开页面后请用手机扫码登录，每一步操作前都会在终端暂停，你按回车后再继续。
- 支持在首页搜索框输入关键词并点击搜索；可读取当前页商品信息并保存为 JSON。
用法: python open_jingdong.py [关键词]
  例如: python open_jingdong.py 手机
  不传关键词则使用默认「王者荣耀」。
"""
import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# 脚本所在目录，用于保存文件（避免因运行目录不同而保存到别处）
SCRIPT_DIR = Path(__file__).resolve().parent
# 专门存放页面源码的文件夹
PAGE_SOURCES_DIR = SCRIPT_DIR / "page_sources"
# 登录状态文件（cookies + storage），携带后下次可免扫码
JD_STORAGE_STATE_PATH = SCRIPT_DIR / "jd_storage_state.json"


def get_valid_storage_state_path() -> str | None:
    """Return storage state path only when the file exists and contains valid JSON."""
    if not JD_STORAGE_STATE_PATH.exists():
        return None

    try:
        raw = JD_STORAGE_STATE_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        json.loads(raw)
        return str(JD_STORAGE_STATE_PATH)
    except Exception:
        return None


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


# 在页面内执行的 JS：从搜索结果/商品列表页提取商品信息（兼容旧版 gl-item 与新版结构）
EXTRACT_PRODUCTS_JS = """
() => {
  const products = [];
  const seen = new Set();
  function add(item) {
    const sku = (item.sku || '').trim();
    if (!sku || seen.has(sku)) return;
    seen.add(sku);
    products.push({
      sku,
      title: (item.title || '').trim() || '未知',
      price: (item.price || '').trim(),
      link: item.link || ('https://item.jd.com/' + sku + '.html'),
      shop: (item.shop || '').trim(),
      image: item.image || ''
    });
  }
  // 1) 新版卡片：直接抓带 data-sku 的商品容器
  document.querySelectorAll('[data-sku]').forEach(el => {
    const sku = el.getAttribute('data-sku') || '';
    const titleEl = el.querySelector('[title], [class*="title"], [class*="text"]');
    const priceWrap = el.querySelector('[class*="price"], [class*="Price"]');
    const shopEl = el.querySelector('[class*="shop"] [class*="name"], [class*="shopFloor"] [class*="name"], [class*="store"]');
    const imgEl = el.querySelector('img');
    const linkEl = el.querySelector('a[href*="item.jd.com"], a[href*="item.m.jd.com"]');
    const title = (
      (titleEl && (titleEl.getAttribute('title') || titleEl.textContent)) ||
      ''
    ).replace(/\\s+/g, ' ').trim();
    const priceText = priceWrap ? priceWrap.textContent.replace(/\\s+/g, '') : '';
    const priceMatch = priceText.match(/\\d+(?:\\.\\d+)?/);
    add({
      sku,
      title,
      price: priceMatch ? priceMatch[0] : '',
      link: linkEl ? linkEl.href.split('?')[0] : `https://item.jd.com/${sku}.html`,
      shop: shopEl ? shopEl.textContent : '',
      image: imgEl ? (imgEl.currentSrc || imgEl.src || imgEl.getAttribute('data-src') || '') : ''
    });
  });
  if (products.length > 0) return products;
  // 2) 旧版: .gl-item
  document.querySelectorAll('.gl-item').forEach(el => {
    const nameEl = el.querySelector('.p-name em, .p-name a');
    const priceEl = el.querySelector('.p-price i');
    const linkEl = el.querySelector('.p-img a, .p-name a');
    const href = linkEl ? linkEl.href : '';
    const m = href.match(/item\\.(m\\.)?jd\\.com\\/(\\d+)/);
    if (m) {
      add({
        sku: m[2],
        title: nameEl ? nameEl.innerText : '',
        price: priceEl ? priceEl.innerText : '',
        link: href
      });
    }
  });
  if (products.length > 0) return products;
  // 3) 兜底：任意带 item.jd.com / item.m.jd.com 的链接
  document.querySelectorAll('a[href*="item.jd.com"], a[href*="item.m.jd.com"]').forEach(a => {
    const href = (a.href || '').split('?')[0];
    const m = href.match(/item\\.(m\\.)?jd\\.com\\/(\\d+)/);
    if (!m) return;
    const sku = m[2];
    const card = a.closest('li, [class*="item"], [class*="product"], [class*="sku"], [class*="card"]') || a;
    let title = (a.textContent || '').trim();
    if (title.length > 100) title = title.slice(0, 100);
    const priceEl = card.querySelector('[class*="price"] i, [class*="price"] strong, [class*="Price"]');
    const price = priceEl ? priceEl.textContent.trim() : '';
    add({ sku, title, price, link: href });
  });
  return products;
}
"""


async def wait_for_products_loaded(page, timeout_seconds: int = 30, min_count: int = 1):
    """等待商品数据真正出现在页面上，再继续后续转存。"""
    selector = '[data-sku], a[href*="item.jd.com"], a[href*="item.m.jd.com"], .gl-item'
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_products = []

    while asyncio.get_running_loop().time() < deadline:
        try:
            await page.wait_for_selector(selector, timeout=3000)
        except Exception:
            pass

        try:
            products = await page.evaluate(EXTRACT_PRODUCTS_JS)
            if isinstance(products, list):
                last_products = products
                if len(products) >= min_count:
                    return products
        except Exception:
            pass

        await page.evaluate("window.scrollBy(0, Math.max(window.innerHeight, 800))")
        await asyncio.sleep(1.2)

    await page.evaluate("window.scrollTo(0, 0)")
    return last_products


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
        # 若存在有效的已保存登录状态则加载，下次打开可免扫码
        storage_state = get_valid_storage_state_path()
        if storage_state:
            print("已加载本地登录状态，若已失效请删除 jd_storage_state.json 后重新扫码登录。")
        elif JD_STORAGE_STATE_PATH.exists():
            print("检测到 jd_storage_state.json 为空或已损坏，本次将忽略它并继续运行。")
        context = await browser.new_context(
            viewport=None,
            storage_state=storage_state,
        )
        page = await context.new_page()

        # Go to 京东 (JD.com)
        await page.goto("https://www.jingdong.com/")

        # 京东有持续请求，networkidle 可能永不触发；改用 domcontentloaded 并稍等
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # Step 1: 若无登录状态或需重新登录，请扫码后按回车；若已登录可直接按回车
        input("请用手机扫码登录（若已登录可直接按回车），完成后在终端按回车继续... ")
        # 保存当前登录状态，下次启动将自动携带 cookie 免扫码
        await context.storage_state(path=str(JD_STORAGE_STATE_PATH))
        print("已保存登录状态到 jd_storage_state.json，下次运行将自动携带。")

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
            products = await wait_for_products_loaded(page, timeout_seconds=30)
            print(f"已搜索: {keyword.strip()}，当前检测到 {len(products)} 条商品数据")

        # Step 3: 按回车后再保存页面源码并提取商品信息为 JSON
        input("按回车后保存当前页面源码并提取商品信息为 JSON... ")
        # 转存前再次确认商品数据已到达页面；如果还没到，继续等待一段时间
        products = await wait_for_products_loaded(page, timeout_seconds=20)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        html = await page.content()
        PAGE_SOURCES_DIR.mkdir(exist_ok=True)
        raw_file = PAGE_SOURCES_DIR / "jingdong_page.html"
        raw_file.write_text(html, encoding="utf-8")
        print(f"原始源码已保存: {raw_file}")
        viewable_html = make_html_viewable(html)
        viewable_file = PAGE_SOURCES_DIR / "jingdong_page_viewable.html"
        viewable_file.write_text(viewable_html, encoding="utf-8")
        print(f"可浏览版已保存: {viewable_file}")

        # 从当前页面 DOM 提取商品列表并保存为 JSON
        try:
            if not isinstance(products, list):
                products = []
            out = {"source": "search", "keyword": (keyword or "").strip(), "count": len(products), "products": products}
            json_file = PAGE_SOURCES_DIR / "products.json"
            json_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"商品信息已保存: {json_file}（共 {len(products)} 条）")
        except Exception as e:
            print(f"提取商品信息失败: {e}")

        # Step 4: 按回车后关闭浏览器
        input("按回车关闭浏览器... ")
        await browser.close()


# 默认搜索关键词（不传命令行参数时直接使用）
DEFAULT_KEYWORD = "西安大雁塔"

if __name__ == "__main__":
    # 未传命令行参数则用「王者荣耀」；传了则用传入的关键词，如: python open_jingdong.py 手机
    kw = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else DEFAULT_KEYWORD
    asyncio.run(open_jingdong(keyword=kw))
