<div align="center">

# 🔎 EVM Polls Scraper

**Scrape a validator's EVM-poll voting stats from Axelarscan and print them as a table.**

![Python](https://img.shields.io/badge/Python-3.7+-3776AB?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-headless-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-HTML%20parse-3FB950?style=flat-square)

</div>

---

A small Python CLI that uses [Playwright](https://playwright.dev/) to render [axelarscan.io/validators/evm-polls](https://axelarscan.io/validators/evm-polls) (the page is JS-heavy, so a headless browser is needed), then [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) to parse the target validator's row. It extracts the **Yes / No** vote counts per EVM chain and prints them with [tabulate](https://pypi.org/project/tabulate/).

---

## ⚙️ Requirements

- **Python 3.7+**
- Dependencies pinned in [`requirements.txt`](requirements.txt): `playwright`, `beautifulsoup4`, `tabulate`

---

## 🚀 Installation

```bash
pip install -r requirements.txt
python3 -m playwright install   # download the Chromium browser Playwright drives
```

---

## ▶️ Usage

```bash
python3 evmpolls_scraper.py <validator_name>
# example:
python3 evmpolls_scraper.py Cosmostation
```

Pass the validator's display name exactly as it appears on Axelarscan. The script launches headless Chromium, waits ~6s for the table to hydrate, finds the matching row, and tabulates its per-chain votes.

---

## 📋 Example output

```text
=== Voting Stats for 'Cosmostation' (Yes / No) ===

+---------+------+-----+
| Chain   | Yes  | No  |
+---------+------+-----+
| Axelar  |  123 |  0  |
| ...     | ...  | ... |
+---------+------+-----+
```

---

> [!TIP]
> The scraper reads Axelarscan's live DOM. If the validator name isn't found or cells look off, the page markup likely changed — bump the `wait_for_timeout` in `fetch_page_html()` or re-check the row/cell selectors in `parse_votes()`.

> [!NOTE]
> This tool only reads a **public** block explorer — no keys or credentials required.

---

## 📄 License

MIT
