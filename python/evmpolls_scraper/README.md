# 🔎 EVM Polls Scraper

This Python script uses [Playwright](https://playwright.dev/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) to extract EVM poll voting statistics for any validator from [Axelarscan.io](https://axelarscan.io/validators/evm-polls).

It fetches data like "Yes" and "No" votes for each chain and prints the results as a table.

---

## ⚙️ Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

---

## 🚀 Installation

```bash
pip install -r requirements.txt
python3 -m playwright install
```

---

## ▶️ Usage

```bash
python3 evmpolls_scraper.py Cosmostation
```

Replace `Cosmostation` with the name of any validator you want to analyze.

---

## 📋 Output Example

```
=== Voting Stats for 'Cosmostation' (Yes / No) ===

+---------+------+-----+
| Chain   | Yes  | No  |
+---------+------+-----+
| Axelar  |  123 |  0  |
| ...     | ...  | ... |
+---------+------+-----+
```

---

## 📄 License

MIT