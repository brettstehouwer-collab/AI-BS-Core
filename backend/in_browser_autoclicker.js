/**
 * Cymatics Drop 100% In-Browser Auto-Clicker & Checkout Fallback
 * Paste this directly into Chrome DevTools Console (F12 > Console) on https://cymatics.fm/pages/cymatics-c86v
 * 
 * It runs INSIDE your active browser tab, bypasses Cloudflare/CAPTCHA,
 * and the millisecond ANY card unlocks, it clicks Add to Cart and routes to Checkout!
 */

(function() {
    console.log("%c[AI-BS In-Browser Sniper Armed & Active]", "color: #00f0ff; font-weight: bold; font-size: 14px;");
    
    let claimedCards = new Set();

    function sweepDOM() {
        // 1. Scan for any unlocked .dl-card__cta buttons
        const buttons = document.querySelectorAll('.dl-card__cta, .download-btn, button[data-variant-id]');
        buttons.forEach((btn, idx) => {
            const isHidden = btn.style.display === 'none' || btn.offsetParent === null;
            const isDisabled = btn.disabled;
            const card = btn.closest('.dl-card') || btn.parentElement;
            const cardNum = card ? (card.getAttribute('data-card-num') || idx) : idx;
            
            // If button is visible and enabled
            if (!isHidden && !isDisabled && !claimedCards.has(cardNum)) {
                claimedCards.add(cardNum);
                console.log("%c[🚨 UNLOCKED CARD DETECTED IN BROWSER! Auto-Clicking...]", "color: #10b981; font-weight: bold; font-size: 16px;");
                btn.click();
                
                // Audio beep alert in browser
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(880, ctx.currentTime);
                    osc.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.5);
                } catch(e) {}
                
                // Auto-click checkout drawer if opened
                setTimeout(() => {
                    const checkoutBtn = document.querySelector('.cym-cart__checkout, a[href*="checkout"], button[name="checkout"]');
                    if (checkoutBtn) {
                        console.log("%c[⚡ AUTO-CLICKING CHECKOUT BUTTON...]", "color: #f59e0b; font-weight: bold; font-size: 16px;");
                        checkoutBtn.click();
                    } else {
                        window.location.href = '/checkout';
                    }
                }, 400);
            }
        });

        // 2. Scan for unlocked cards that lost .dl-card--locked class
        const unlockedCards = document.querySelectorAll('.dl-card:not(.dl-card--locked)');
        unlockedCards.forEach((c, idx) => {
            const btn = c.querySelector('.dl-card__cta, button');
            if (btn && !claimedCards.has(idx)) {
                btn.style.display = 'inline-block';
                btn.removeAttribute('disabled');
            }
        });
    }

    // High frequency 100ms in-browser DOM observer
    setInterval(sweepDOM, 100);
    console.log("%c[✓ In-Browser Auto-Clicker Polling Every 100ms]", "color: #a855f7; font-size: 12px;");
})();
