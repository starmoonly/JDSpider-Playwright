# JD Spider with Playwright

A Playwright-based crawler for JD.com search and product detail pages.

This project can:

- open JD.com with a local Microsoft Edge installation
- reuse saved login state to reduce repeated QR-code logins
- search products by keyword
- extract search result cards into `JSON`
- open product detail pages in controlled batches
- save per-product HTML, metadata, images, and comments

## Features

- `debug` mode: pause before each major step and wait for Enter
- `normal` mode: run continuously without interactive pauses
- configurable behavior through `crawler_config.json`
- automatic search-result extraction for newer JD card layouts
- per-product output folders under `product_details/`

## Requirements

- Windows
- Python 3.10+
- Microsoft Edge installed locally
- Conda or a normal Python environment

## Installation

### Option 1: Conda

```powershell
conda env create -f environment.yml
conda activate jd-playwright
```

### Option 2: pip

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Project Files

- `open_jingdong.py`: main crawler entry script
- `crawler_config.json`: runtime configuration
- `page_sources/`: saved search page HTML and `products.json`
- `product_details/`: per-product output folders
- `jd_storage_state.json`: saved Playwright login state

## Configuration

All major runtime parameters are stored in `crawler_config.json`.

Example:

```json
{
  "run_mode": "normal",
  "search": {
    "default_keyword": "Xi'an Dayanta"
  },
  "comments": {
    "max_pages": 3,
    "page_size": 10
  },
  "detail_scraping": {
    "batch_size": 2,
    "open_interval_seconds": 8,
    "page_settle_seconds": 4,
    "batch_pause_seconds": 6
  },
  "login": {
    "default_scan_wait_seconds": 15
  }
}
```

### Important Settings

- `run_mode`
  - `normal`: run automatically
  - `debug`: wait for Enter before each major step
- `search.default_keyword`: default search keyword when no CLI keyword is provided
- `comments.max_pages`: max number of comment pages per SKU
- `comments.page_size`: number of comments per page
- `detail_scraping.batch_size`: number of products handled in one batch
- `detail_scraping.open_interval_seconds`: gap between opening product pages in the same batch
- `detail_scraping.page_settle_seconds`: extra wait time after a product page loads
- `detail_scraping.batch_pause_seconds`: pause between batches
- `login.default_scan_wait_seconds`: auto wait time for QR login in `normal` mode when no valid login state exists

## Usage

### Normal Mode

Run automatically with the default keyword from `crawler_config.json`:

```powershell
python open_jingdong.py
```

Run automatically with a custom keyword:

```powershell
python open_jingdong.py "Xi'an Jiaotong University"
```

Force normal mode explicitly:

```powershell
python open_jingdong.py --normal "Xi'an Jiaotong University"
```

### Debug Mode

Pause before each major step:

```powershell
python open_jingdong.py --debug
python open_jingdong.py --debug "Xi'an Jiaotong University"
```

## Output Structure

### Search Results

The script saves search-level artifacts into `page_sources/`:

- `jingdong_page.html`
- `jingdong_page_viewable.html`
- `products.json`
- `first_product_detail.html`

### Product Details

Each product gets its own folder under `product_details/`:

```text
product_details/
  001_<sku>_<title>/
    detail.html
    product.json
    comments.json
    comments_error.txt
    error.txt
    images/
      01.jpg
      02.jpg
```

## Login State

The file `jd_storage_state.json` stores Playwright browser state such as cookies and local storage so the script can reuse an existing JD login session.

This file is sensitive and should never be committed or shared publicly.

If login state becomes invalid:

1. delete `jd_storage_state.json`
2. run the script again
3. scan the QR code to log in

## Notes

- The project currently uses local Edge via Playwright `channel="msedge"`.
- Search result DOM on JD changes over time. Extraction logic may need updates when JD changes card structure.
- Some products may fail to return comments. In those cases the script writes `comments_error.txt`.
- This project is best suited for personal research, testing, and internal data collection workflows.

## Security Checklist Before Publishing

Before making this repository public, make sure you do **not** publish:

- `jd_storage_state.json`
- real scraped output in `page_sources/`
- real scraped output in `product_details/`
- any private account data or session files

You may also want to extend `.gitignore` to ignore generated output directories entirely.

## Disclaimer

Use this project responsibly and in compliance with JD.com's terms of service, robots rules, and applicable laws. The repository is intended for educational, testing, and internal automation purposes.
