#!/usr/bin/env python3
"""
UI automation script for Investing.com historical data download.

This uses Playwright to open the page, set the date range, and click Download.
You may need to log in manually (Investing.com can require auth / captcha).

Example:
  python3 scripts/fetch_prices_investing_ui.py \
    --url "https://www.investing.com/equities/amazon-com-inc-historical-data" \
    --start 2024-01-04 --end 2026-02-05 --ticker AMZN
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def _fmt_date(date_str: str) -> str:
    # input: YYYY-MM-DD -> output: MM/DD/YYYY
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%m/%d/%Y")


def _range_str(start: str, end: str) -> str:
    return f"{_fmt_date(start)} - {_fmt_date(end)}"


def _guess_name(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", slug)
    return slug or "investing_data"


def _maybe_accept_cookies(page) -> None:
    candidates = [
        "Accept",
        "I Accept",
        "I agree",
        "Agree",
        "Got it",
        "OK",
    ]
    for label in candidates:
        try:
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                return
        except Exception:
            continue


def _find_date_input(page):
    selectors = [
        "input#picker",
        "input[name='datePicker']",
        "input[name*='date' i]",
        "input[data-test*='date' i]",
        "input[placeholder*='-']",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            return loc.first
    return None


def _set_input_value(locator, range_text: str) -> bool:
    try:
        locator.click(timeout=2000)
    except Exception:
        pass
    try:
        locator.fill(range_text, timeout=2000)
        locator.press("Enter", timeout=1000)
        return True
    except Exception:
        pass
    try:
        locator.evaluate(
            "(el, value) => { el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }",
            range_text,
        )
        return True
    except Exception:
        return False


def _try_set_date_range(page, range_text: str) -> bool:
    # Try to find an input that looks like the date range field.
    locator = _find_date_input(page)
    if locator is not None:
        if _set_input_value(locator, range_text):
            return True
    # Fallback: probe all inputs for a date-range-like value.
    js = """
    (rangeText) => {
      const inputs = Array.from(document.querySelectorAll('input'));
      const target = inputs.find(i =>
        i.value && i.value.includes(' - ') &&
        /\\d{2}\\/\\d{2}\\/\\d{4}/.test(i.value)
      ) || inputs.find(i =>
        i.placeholder && i.placeholder.includes(' - ')
      );
      if (!target) return false;
      target.focus();
      target.value = rangeText;
      target.dispatchEvent(new Event('input', { bubbles: true }));
      target.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }
    """
    try:
        return bool(page.evaluate(js, range_text))
    except Exception:
        return False


def _try_apply(page) -> None:
    for label in ["Apply", "OK", "Submit", "Done"]:
        try:
            btn = page.get_by_role("button", name=re.compile(label, re.I))
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                return
        except Exception:
            continue


def _try_select_daily(page) -> None:
    # If a dropdown exists and "Daily" is not selected, try to select it.
    try:
        daily = page.get_by_text("Daily", exact=False)
        if daily.count() > 0:
            daily.first.click(timeout=2000)
            return
    except Exception:
        pass


def _find_download(page):
    # Try a few selectors for the Download button or link.
    selectors = [
        "a:has-text(\"Download\")",
        "button:has-text(\"Download\")",
        "a:has-text(\"Download Data\")",
        "button:has-text(\"Download Data\")",
        "[aria-label*=\"Download\" i]",
    ]
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            return loc.first
    # fallback: text node
    try:
        return page.get_by_text("Download", exact=False).first
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Investing.com historical data URL")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--ticker", default="", help="Ticker symbol for output filename")
    parser.add_argument("--output-dir", default="data/price_cache/investing", help="Download output directory")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--manual", action="store_true", help="Pause for manual login/selection")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    range_text = _range_str(args.start, args.end)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")
        _maybe_accept_cookies(page)

        if args.manual:
            print("Manual mode: complete login/selection in the browser, then press Enter here.")
            input()

        _try_select_daily(page)
        if _try_set_date_range(page, range_text):
            _try_apply(page)

        download_btn = _find_download(page)
        if not download_btn:
            print("Download button not found. Try --manual to click it yourself.")
            return 2

        try:
            with page.expect_download(timeout=20000) as dl_info:
                download_btn.click()
            download = dl_info.value
        except PlaywrightTimeout:
            print("Download did not start. Try --manual and click Download yourself.")
            return 3

        # Save file
        suggested = download.suggested_filename
        name = args.ticker.upper() if args.ticker else _guess_name(args.url)
        out_path = output_dir / f"{name}.csv"
        # If Yahoo/Investing uses CSV name, keep it too
        if suggested and suggested.lower().endswith(".csv"):
            out_path = output_dir / suggested
        download.save_as(out_path)
        print(f"Saved: {out_path}")

        context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
