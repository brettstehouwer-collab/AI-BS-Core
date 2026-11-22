"""Public concept rendering check using a real Chromium WebGL context.

Run with --url pointing at the hosted /bs-game/index.html page. This does not
sign into or bypass the protected AI-BS workspace and never touches game saves.
"""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright


def verify(url: str, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--enable-unsafe-swiftshader'])
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
            page.on('pageerror', lambda error: errors.append(str(error)))
            response = page.goto(url, wait_until='networkidle', timeout=45000)
            if not response or response.status != 200:
                raise AssertionError(f'Playground response was {response.status if response else "missing"}')
            canvas = page.locator('#canvas-container canvas')
            canvas.wait_for(state='visible', timeout=20000)
            if page.locator('#concept-fallback').is_visible():
                raise AssertionError(page.locator('#concept-fallback').inner_text())
            context = canvas.evaluate("element => Boolean(element.getContext('webgl2') || element.getContext('webgl'))")
            if not context:
                raise AssertionError('No active WebGL context')
            page.wait_for_timeout(450)
            yaw_before = page.evaluate('camera.rotation.y')
            page.mouse.move(850, 550)
            page.mouse.down(button='right')
            page.mouse.move(970, 575, steps=8)
            page.mouse.up(button='right')
            page.wait_for_timeout(150)
            yaw_after = page.evaluate('camera.rotation.y')
            if abs(yaw_after - yaw_before) <= 0.1:
                raise AssertionError('Right-drag did not turn the view')
            # Return using real mouse input before aiming at the repairable core.
            page.mouse.move(970, 575)
            page.mouse.down(button='right')
            page.mouse.move(850, 550, steps=8)
            page.mouse.up(button='right')
            point = page.evaluate('''() => {
                const point = coreNode.position.clone().project(camera);
                return { x: (point.x + 1) * innerWidth / 2, y: (1 - point.y) * innerHeight / 2 };
            }''')
            page.mouse.move(point['x'], point['y'])
            page.wait_for_timeout(150)
            if 'Core Node 01' not in page.locator('#interaction-prompt').inner_text():
                raise AssertionError('Pointing at the visible core did not show its interaction hint')
            page.mouse.click(point['x'], point['y'])
            if 'restored' not in page.locator('#txt-objective').inner_text().lower():
                raise AssertionError('Clicking the visible core did not complete its repair')
            if 'holds' not in page.locator('#adam-text').inner_text():
                raise AssertionError('Adam did not acknowledge the actual completed repair')
            if page.evaluate('gpuRestorationLight.intensity') <= 0:
                raise AssertionError('Core repair did not illuminate the GPU landmark')
            page.keyboard.press('e')
            if 'already restored' not in page.locator('#adam-text').inner_text():
                raise AssertionError('E did not interact with the pointed-at core')
            rendered_triangles = page.evaluate('renderer.info.render.triangles')
            if rendered_triangles <= 0:
                raise AssertionError('WebGL submitted no scene triangles')
            before = Image.open(io.BytesIO(canvas.screenshot())).convert('RGB')
            if sum(ImageStat.Stat(before).stddev) <= 3:
                raise AssertionError('Rendered scene appears blank')
            before_position = page.evaluate('playerPos.z')
            page.keyboard.down('w')
            page.wait_for_timeout(800)
            page.keyboard.up('w')
            page.wait_for_timeout(250)
            after_position = page.evaluate('playerPos.z')
            if after_position >= before_position:
                raise AssertionError('W input did not move the concept player forward')
            after = Image.open(io.BytesIO(canvas.screenshot())).convert('RGB')
            difference = sum(ImageStat.Stat(ImageChops.difference(before, after)).mean)
            if difference <= 0.1:
                raise AssertionError('Movement did not change the rendered scene')

            page.get_by_role('button', name='Coolant Vessels & Buggies').click()
            modal_position = page.evaluate('playerPos.z')
            page.keyboard.down('w')
            page.wait_for_timeout(150)
            page.keyboard.up('w')
            if page.evaluate('playerPos.z') != modal_position:
                raise AssertionError('Movement continued while a catalog modal was open')
            page.locator('#modal-body .modal-card').filter(has_text='Coolant Skimmer').click()
            if 'Skimmer' not in page.locator('#txt-vehicle').inner_text():
                raise AssertionError('Vehicle selection did not update the loadout')
            page.get_by_role('button', name='V240 Garage Diagnostics').click()
            page.get_by_role('button', name='Unpinch Thermal Line & Upgrade Micro-Impeller').click()
            if 'Optimized' not in page.locator('#garage-flow').inner_text():
                raise AssertionError('Garage concept interaction did not update the diagnostic display')
            page.get_by_role('button', name='Close / Apply').click()
            if errors:
                raise AssertionError('Browser script errors: ' + '; '.join(errors))
            page.screenshot(path=str(output / 'playground-live.png'), full_page=True)
            result = {
                'status': 'passed', 'url': url,
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'webgl_context': True, 'movement_pixel_difference': difference,
                'rendered_triangles': rendered_triangles,
                'player_z_before': before_position, 'player_z_after': after_position,
                'right_drag_yaw_before': yaw_before, 'right_drag_yaw_after': yaw_after,
                'checks': ['HTTP 200', 'WebGL scene rendered nonblank', 'Right-drag free look changed camera',
                           'Visible core raycast click repaired system and lit GPU', 'W movement changed scene',
                           'E interaction acknowledged existing repair', 'Catalog modal paused movement',
                           'Vehicle catalog selection', 'Garage tuning interaction', 'No page script errors'],
                'limits': 'Chromium may use a software WebGL adapter; this does not verify the native DX12 renderer.',
            }
            (output / 'playground-live.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            return result
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] / 'engine/out/site-verification')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.url, args.output), indent=2))
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
