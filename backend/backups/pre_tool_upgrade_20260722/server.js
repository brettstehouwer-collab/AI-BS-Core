const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

const app = express();
app.use(cors());
app.use(express.json());

const SAVED_DATA_DIR = path.join(__dirname, '..', 'saved_data');

// Ensure saved_data directory exists
if (!fs.existsSync(SAVED_DATA_DIR)){
    fs.mkdirSync(SAVED_DATA_DIR, { recursive: true });
}

app.post('/api/fetch', async (req, res) => {
    const { taskType, targetId, apiKey } = req.body;
    
    if (!taskType || !targetId || !apiKey) {
        return res.status(400).json({ error: 'Missing required parameters: taskType, targetId, or apiKey' });
    }

    let endpointUrl = '';
    let rapidApiHost = '';
    let fetchMethod = 'GET';
    let fetchBody = null;

    // Logic to construct the URL based on taskType
    if (taskType === 'facebook_group_videos') {
        endpointUrl = `https://facebook-scraper3.p.rapidapi.com/group/videos?group_id=${targetId}`;
        rapidApiHost = 'facebook-scraper3.p.rapidapi.com';
    } else if (taskType === 'facebook_user_search') {
        endpointUrl = `https://facebook-scraper3.p.rapidapi.com/search/users?query=${targetId}`;
        rapidApiHost = 'facebook-scraper3.p.rapidapi.com';
    } else if (taskType === 'tiktok_oldest_posts') {
        endpointUrl = `https://tiktok-api23.p.rapidapi.com/api/user/oldest-posts?secUid=${targetId}&count=30&cursor=0`;
        rapidApiHost = 'tiktok-api23.p.rapidapi.com';
    } else if (taskType === 'instagram_followings') {
        endpointUrl = `https://instagram120.p.rapidapi.com/api/instagram/followings`;
        rapidApiHost = 'instagram120.p.rapidapi.com';
        fetchMethod = 'POST';
        fetchBody = JSON.stringify({ username: targetId });
    } else if (taskType === 'google_search') {
        endpointUrl = `https://google-search74.p.rapidapi.com/?query=${targetId}&limit=10&related_keywords=true`;
        rapidApiHost = 'google-search74.p.rapidapi.com';
    } else if (taskType === 'subdomain_finder') {
        endpointUrl = `https://subdomain-finder3.p.rapidapi.com/v1/subdomain-finder/?domain=${targetId}`;
        rapidApiHost = 'subdomain-finder3.p.rapidapi.com';
    } else if (taskType === 'skip_tracing_email') {
        endpointUrl = `https://skip-tracing-working-api.p.rapidapi.com/search/byemail?email=${targetId}&phone=1`;
        rapidApiHost = 'skip-tracing-working-api.p.rapidapi.com';
    } else if (taskType === 'yahoo_finance') {
        endpointUrl = `https://yahoo-finance15.p.rapidapi.com/api/v1/markets/stock/quotes?ticker=${targetId}`;
        rapidApiHost = 'yahoo-finance15.p.rapidapi.com';
    } else if (taskType === 'crypto_market_data') {
        endpointUrl = `https://api.crypto.com/v2/public/get-ticker?instrument_name=${targetId}`;
        rapidApiHost = ''; // No RapidAPI host needed
    } else {
        return res.status(400).json({ error: 'Unknown taskType' });
    }

    try {
        console.log(`Fetching from ${endpointUrl}`);
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (rapidApiHost) {
            headers['x-rapidapi-host'] = rapidApiHost;
            headers['x-rapidapi-key'] = apiKey;
        } else if (apiKey && apiKey.trim() !== '' && apiKey !== 'undefined') {
            // If it's a generic API that needs auth in header, we could add it here
            // But for crypto_market_data public endpoints, we don't need the key
            // headers['Authorization'] = `Bearer ${apiKey}`;
        }

        const fetchOptions = {
            method: fetchMethod,
            headers: headers
        };

        if (fetchBody) {
            fetchOptions.body = fetchBody;
        }

        const response = await fetch(endpointUrl, fetchOptions);
        
        const data = await response.json();

        // Save data to local folder
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `${taskType}_${targetId}_${timestamp}.json`;
        const filePath = path.join(SAVED_DATA_DIR, filename);
        
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
        console.log(`Saved successfully to ${filePath}`);

        // Return data to frontend
        res.json({
            success: true,
            savedPath: filePath,
            data: data
        });

    } catch (error) {
        console.error('Fetch error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/utils/fb-group-id', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'Missing URL' });
    try {
        const response = await fetch(url, {
            headers: {
                // Send a generic user-agent so Facebook doesn't immediately block the request
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        });
        const text = await response.text();
        const match = text.match(/"groupID":"(\d+)"/) || text.match(/content="fb:\/\/group\/(\d+)"/);
        
        if (match && match[1]) {
            res.json({ success: true, groupId: match[1] });
        } else {
            res.json({ success: false, error: 'Could not find group ID. Make sure it is a full public group URL.' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`Universal Proxy Server running on http://localhost:${PORT}`);
});
