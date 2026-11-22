const express = require('express');
const { createHash, timingSafeEqual } = require('node:crypto');

// External fetching and persistence are held pending an approved local implementation.
function localAdmin(req, res, next) {
    res.set('Cache-Control', 'private, no-store');
    const token = process.env.AI_BS_LOCAL_ADMIN_TOKEN;
    if (!token || !token.trim()) {
        return res.status(503).json({ error: 'Local administrator access is not configured', code: 'ADMIN_UNCONFIGURED' });
    }
    const authorization = req.headers.authorization;
    const supplied = typeof authorization === 'string' ? authorization : '';
    const digest = value => createHash('sha256').update(value).digest();
    if (!timingSafeEqual(digest(supplied), digest(`Bearer ${token}`))) {
        return res.status(401).json({ error: 'Administrator authentication required' });
    }
    next();
}

function held(req, res) {
    res.set('Cache-Control', 'private, no-store');
    return res.status(503).json({ code: 'SERVICE_HELD', error: 'External fetching and persistence are held pending an approved local implementation' });
}

function createApp() {
    const app = express();
    // Authenticate before any body processing. Held actions never need a JSON parser.
    app.use(localAdmin);
    app.post('/api/fetch', held);
    app.post('/api/utils/fb-group-id', held);
    return app;
}

function startServer() {
    return createApp().listen(3001, '127.0.0.1');
}

module.exports = { createApp, startServer, localAdmin };
if (require.main === module) startServer();
