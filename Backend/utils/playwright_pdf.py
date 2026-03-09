from playwright.async_api import async_playwright
import os
import tempfile
import json
import logging

logger = logging.getLogger("api")

async def generate_dashboard_pdf_playwright(report_data: dict, dashboard_url: str) -> bytes:
    """
    Launch headless Chromium, inject the report data, navigate to the React dashboard,
    wait for it to render, and capture a perfect native A4 PDF.
    
    Args:
        report_data: The JSON dictionary containing the report to inject into localStorage.
        dashboard_url: The internal container URL for the frontend (e.g., http://frontend:5000/content-review-dashboard)
        
    Returns:
        The raw PDF bytes.
    """
    logger.info(f"Starting Playwright PDF generation for: {dashboard_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(
            viewport={'width': 1200, 'height': 800}
        )
        
        # Determine the correct local storage key based on the URL path
        storage_key = "latest_content_review_report"
        if "header" in dashboard_url.lower():
            storage_key = "latest_header_report"
            
        # We need to set the local storage BEFORE navigating, so we need to initialize the domain first
        # We navigate to a blank page on the same domain to set the localStorage
        domain = "/".join(dashboard_url.split("/")[:3]) # e.g. http://frontend:5000
        
        page = await context.new_page()
        logger.info(f"Navigating to domain {domain} to set localStorage")
        
        try:
            # Go to the root domain just to establish the origin
            await page.goto(f"{domain}/", wait_until="commit")
            
            # Inject the report data into localStorage so the React component finds it on mount
            await page.evaluate(
                "({key, value}) => localStorage.setItem(key, value)", 
                {"key": storage_key, "value": json.dumps(report_data)}
            )
            
            logger.info("LocalStorage injected. Loading full dashboard.")
            # Now navigate to the actual dashboard URL
            await page.goto(dashboard_url, wait_until="networkidle")
            
            # Additional small wait to ensure React animations / framer-motion complete
            await page.wait_for_timeout(1500)
            
            # Hide the Print/Email buttons specifically for the PDF
            await page.evaluate('''() => {
                const actionButtons = document.querySelector('.flex.flex-col.sm\\\\:flex-row.gap-3');
                if (actionButtons) actionButtons.style.display = 'none';
            }''')
            
            # Generate perfect A4 PDF natively from Chromium engine
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "40px", "bottom": "40px", "left": "20px", "right": "20px"}
            )
            
            logger.info("PDF captured successfully via Playwright.")
            await browser.close()
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Playwright PDF Error: {str(e)}")
            await browser.close()
            raise
