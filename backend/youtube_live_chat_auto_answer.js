/**
 * AI-BS YouTube Live Giveaway Auto-Submitter (Configured for Brett Stehouwer)
 * Email: BrettStehouwer@gmail.com
 */

const USER_EMAIL = "BrettStehouwer@gmail.com";

window.submitAnswer = function(rawAnswer) {
    const formattedText = `${USER_EMAIL} ${rawAnswer.trim()}`;
    
    // Check if chat is inside iframe or top document
    const chatFrame = document.querySelector('iframe#chatframe');
    const doc = chatFrame ? chatFrame.contentDocument : document;

    // 1. Check for Active Q&A Modal / Drawer
    const qnaInput = doc.querySelector('yt-live-chat-qna-post-dialog-renderer textarea, yt-live-chat-qna-post-dialog-renderer #input');
    const qnaSubmit = doc.querySelector('yt-live-chat-qna-post-dialog-renderer #submit-button button, yt-live-chat-qna-post-dialog-renderer button[aria-label*="Submit"]');
    
    if (qnaInput && qnaSubmit) {
        qnaInput.focus();
        qnaInput.value = formattedText;
        qnaInput.dispatchEvent(new Event('input', { bubbles: true }));
        qnaSubmit.click();
        console.log(`%c[AI-BS Q&A SUBMITTED] ${formattedText}`, "color: #10b981; font-weight: bold;");
        return;
    }

    // 2. Check for Pinned Q&A Banner ("Ask Something" / Action Button)
    const qnaBannerBtn = doc.querySelector('yt-live-chat-qna-banner-renderer #action-button button, yt-live-chat-qna-banner-renderer yt-button-renderer button, yt-live-chat-pinned-message-renderer button');
    if (qnaBannerBtn) {
        qnaBannerBtn.click();
        setTimeout(() => window.submitAnswer(rawAnswer), 150);
        return;
    }

    // 3. Fallback to Primary Live Chat Box
    const chatInput = doc.querySelector('yt-live-chat-message-input-renderer div#input[contenteditable="true"], #chatinput #input');
    const sendBtn = doc.querySelector('yt-icon-button#send-button button, #send-button button');

    if (chatInput) {
        chatInput.focus();
        chatInput.textContent = formattedText;
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        setTimeout(() => {
            if (sendBtn) sendBtn.click();
            console.log(`%c[AI-BS CHAT SENT] ${formattedText}`, "color: #3b82f6; font-weight: bold;");
        }, 50);
    } else {
        console.warn("[AI-BS] Chat input field not found.");
    }
};

window.postPromo = function(customText) {
    const promoText = customText || "Stehouwer-Publishing.com";
    const chatFrame = document.querySelector('iframe#chatframe');
    const doc = chatFrame ? chatFrame.contentDocument : document;
    const chatInput = doc.querySelector('yt-live-chat-message-input-renderer div#input[contenteditable="true"], #chatinput #input');
    const sendBtn = doc.querySelector('yt-icon-button#send-button button, #send-button button');

    if (chatInput) {
        chatInput.focus();
        chatInput.textContent = promoText;
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
        setTimeout(() => {
            if (sendBtn) sendBtn.click();
            console.log(`%c[AI-BS PROMO SENT] ${promoText}`, "color: #38bdf8; font-weight: bold;");
        }, 50);
    } else {
        console.warn("[AI-BS] Chat input field not found.");
    }
};

console.log("%c[AI-BS CONFIGURED] Use submitAnswer('YOUR_ANSWER') or postPromo() to post live!", "color: #a855f7; font-size: 13px; font-weight: bold;");
