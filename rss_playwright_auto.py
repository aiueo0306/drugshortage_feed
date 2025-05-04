from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("DSJP｜医療用医薬品供給状況データベース")
    fg.link(href="https://drugshortage.jp/updatehistory.php")
    fg.description("DrugShortage.jpの更新履歴")
    fg.language("ja")

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        entry.guid(item['link'], permalink=False)
        entry.pubDate(datetime.now(timezone.utc))  # ← タイムゾーン付きで修正済み

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)

with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)  # GUIなしで実行
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto("https://drugshortage.jp/updatehistory.php", timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。Cloudflareにブロックされた可能性があります。")
        browser.close()
        exit()

    print("✅ Cloudflare通過後、規約同意をセット中...")
    page.evaluate("localStorage.setItem('policyAgreement', 'true');")
    page.reload()
    page.wait_for_load_state("load", timeout=30000)

    print("▶ 医薬品情報を抽出しています...")
    containers = page.locator("body > div > div > div > div > div > div > div > div > div")
    items = []

    count = containers.count()
    print(f"📦 発見した項目数: {count}")

    for i in range(count):
        container = containers.nth(i)
        try:
            title = container.locator("div:nth-child(2) a").inner_text().strip()
            link = container.locator("div:nth-child(2) a").get_attribute("href")
            description = container.locator("div:nth-child(1) div:nth-child(1)").inner_text().strip()
            if link and not link.startswith("http"):
                link = f"https://drugshortage.jp/{link}"
            items.append({"title": title, "link": link, "description": description})
        except:
            continue

    if not items:
        print("⚠ 抽出できた情報がありません。HTML構造変更の可能性があります。")

    today = datetime.now().strftime("%Y%m%d")
    rss_path = f"rss_output/drugshortage.xml"
    generate_rss(items, rss_path)

    print(f"\n✅ RSSフィード生成完了！\n📄 保存先: {rss_path}")
    browser.close()
