import asyncio
import os
from playwright.async_api import async_playwright
import PIL.JpegImagePlugin
import PIL.PngImagePlugin
from PIL import Image

async def convert_application_html_to_pdf():
    html_file = r"C:\AI-BS\docs\Application.html"
    output_pdf = r"C:\AI-BS\docs\Application.pdf"

    if not os.path.exists(html_file):
        print(f"Error: {html_file} does not exist.")
        return False

    file_url = "file:///" + os.path.abspath(html_file).replace("\\", "/")
    print(f"Loading: {file_url}")

    async with async_playwright() as p:
        # Launch with 2.0 device scale factor for 300 DPI high-definition rendering
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1600, "height": 2200},
            device_scale_factor=2.0
        )
        page = await context.new_page()
        await page.goto(file_url, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # Remove top toolbar, banners, and CCPA overlays
        await page.evaluate("""() => {
            const toolbar = document.querySelector('[data-testid="signer-toolbar"]');
            if (toolbar) toolbar.remove();
            const ccpa = document.getElementById('ccpa-iframe');
            if (ccpa) ccpa.remove();
            
            // Clean textarea borders for pristine appearance
            document.querySelectorAll('textarea').forEach(ta => {
                ta.style.border = 'none';
                ta.style.outline = 'none';
                ta.style.background = 'transparent';
                ta.style.boxShadow = 'none';
            });
        }""")

        # Find all page containers
        page_elements = await page.query_selector_all('[id^="page-"]')
        print(f"Detected {len(page_elements)} document page containers.")

        image_files = []
        temp_dir = os.path.join(os.path.dirname(output_pdf), "temp_pdf_pages")
        os.makedirs(temp_dir, exist_ok=True)

        for idx, page_el in enumerate(page_elements):
            page_id = await page_el.get_attribute("id")
            temp_img_path = os.path.join(temp_dir, f"page_{idx}_{page_id}.png")
            print(f"  Rendering high-definition screenshot of {page_id}...")
            
            # Scroll into view and screenshot the exact element
            await page_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(200)
            await page_el.screenshot(path=temp_img_path)
            image_files.append(temp_img_path)

        await browser.close()

    # Assemble all high-definition page images into a multi-page PDF using Pillow
    if image_files:
        pil_images = []
        for img_path in image_files:
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            pil_images.append(img)

        print(f"Assembling {len(pil_images)} pages into {output_pdf}...")
        first_img = pil_images[0]
        first_img.save(
            output_pdf,
            save_all=True,
            append_images=pil_images[1:],
            resolution=300.0,
            quality=95
        )

        # Cleanup temp screenshots
        for img_path in image_files:
            try:
                os.remove(img_path)
            except Exception:
                pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass

    if os.path.exists(output_pdf):
        size_mb = round(os.path.getsize(output_pdf) / (1024 * 1024), 2)
        print(f"[SUCCESS] Multi-Page High-Res PDF Generated: {output_pdf} ({size_mb} MB)")
        return True
    else:
        print("[ERROR] PDF generation failed.")
        return False

if __name__ == "__main__":
    asyncio.run(convert_application_html_to_pdf())

