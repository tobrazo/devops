from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from tabulate import tabulate
import sys

URL = "https://axelarscan.io/validators/evm-polls"

def fetch_page_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_timeout(6000)
        content = page.content()
        browser.close()
        return content

def parse_votes(html, validator_name):
    soup = BeautifulSoup(html, "html.parser")
    validator_link = soup.find("a", string=validator_name)
    if not validator_link:
        print(f"[ERROR] Validator '{validator_name}' not found")
        return {}

    row = validator_link.find_parent("tr")
    if not row:
        print("[ERROR] Parent row not found")
        return {}

    cells = row.find_all("td")
    if len(cells) < 5:
        print("[ERROR] Unexpected number of cells")
        return {}

    evm_cell = cells[-1]
    images = evm_cell.find_all("img")
    text_spans = evm_cell.find_all("span", class_="text-sm")

    stats = {}
    for img, yes_span, no_span in zip(images, text_spans[::2], text_spans[1::2]):
        chain = img.get("src", "").split("/")[-1].split(".")[0].capitalize()
        yes = yes_span.text.strip()
        no = no_span.text.strip().replace("/", "").strip()
        stats[chain] = {"Yes": yes, "No": no}
    return stats

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 evmpolls_scraper.py <validator_name>")
        sys.exit(1)

    validator_name = sys.argv[1]
    html = fetch_page_html()
    stats = parse_votes(html, validator_name)

    if not stats:
        print("No voting data found.")
        return

    table = [[chain, data["Yes"], data["No"]] for chain, data in sorted(stats.items())]
    print(f"\n=== Voting Stats for '{validator_name}' (Yes / No) ===\n")
    print(tabulate(table, headers=["Chain", "Yes", "No"], tablefmt="grid"))

if __name__ == "__main__":
    main()