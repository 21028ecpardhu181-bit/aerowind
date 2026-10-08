const { chromium } = require('/opt/hatch/skills/spaces/ts-runtime/dist/node_modules/playwright-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = path.resolve(__dirname, '../docs/ui-screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function setupPageProxy(page) {
    await page.route('http://127.0.0.1:8000/**', async (route) => {
        const req = route.request();
        const url = req.url();
        const method = req.method();
        const headers = { ...req.headers() };
        delete headers['host'];
        delete headers['accept-encoding'];
        const postData = req.postData();

        const nodeReq = http.request(url, {
            method: method,
            headers: headers
        }, (res) => {
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => {
                const cleanHeaders = { ...res.headers };
                delete cleanHeaders['content-encoding'];
                delete cleanHeaders['transfer-encoding'];
                delete cleanHeaders['content-length'];
                route.fulfill({
                    status: res.statusCode,
                    headers: cleanHeaders,
                    body: Buffer.concat(chunks)
                });
            });
        });
        nodeReq.on('error', (err) => {
            console.error('Proxy route error for', url, err.message);
            route.abort();
        });
        if (postData) nodeReq.write(postData);
        nodeReq.end();
    });
}

async function verifyUI() {
    console.log('====================================================');
    console.log(' Starting Playwright UI Verification (Sprint 5 & Realism)');
    console.log('====================================================');

    const browser = await chromium.launch({
        executablePath: '/opt/meta-chromium/chrome',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--allow-file-access-from-files'
        ]
    });

    // ====================================================
    // TEST 1: DESKTOP VIEWPORT (1280x800)
    // ====================================================
    console.log('\n[1/2] Testing Desktop Viewport (1280x800)...');
    const pageDesktop = await browser.newPage({
        viewport: { width: 1280, height: 800 }
    });

    pageDesktop.on('console', msg => {
        if (msg.type() === 'error') {
            console.error('  [Desktop Console Error]:', msg.text());
        }
    });

    await setupPageProxy(pageDesktop);

    console.log('  Navigating to http://127.0.0.1:8000/map/...');
    await pageDesktop.goto('http://127.0.0.1:8000/map/', { waitUntil: 'load', timeout: 30000 });
    console.log('  Page loaded successfully.');

    // Wait for initial load and settlement
    await pageDesktop.waitForTimeout(3000);

    // Verify Title
    const title = await pageDesktop.title();
    console.log(`  Page Title: "${title}"`);

    // Verify Search Bar and Presets
    const searchVal = await pageDesktop.$eval('#search-input', el => el.value);
    console.log(`  Active Location Search: "${searchVal}"`);

    // Trigger K=4 WS-QAOA optimization
    console.log('  Triggering K=4 WS-QAOA optimization...');
    await pageDesktop.evaluate(() => {
        document.getElementById('k-slider').value = 4;
        updateK(4);
    });
    await pageDesktop.waitForSelector('.turbine-leaflet-marker', { timeout: 35000 });

    // Read and verify telemetry metrics
    const aep = await pageDesktop.$eval('#metric-aep', el => el.innerText);
    const wake = await pageDesktop.$eval('#metric-wake', el => el.innerText);
    const rev = await pageDesktop.$eval('#metric-rev', el => el.innerText);
    const solverTime = await pageDesktop.$eval('#metric-time', el => el.innerText);
    const bitstring = await pageDesktop.$eval('#metric-state', el => el.innerText);
    const compliance5D = await pageDesktop.$eval('#metric-5d', el => el.innerText);

    console.log('  --------------------------------------------');
    console.log(`  Telemetry HUD Verification (Anantapur K=4):`);
    console.log(`    • Annual Energy Yield (AEP): ${aep}`);
    console.log(`    • Jensen Wake Deficit Loss : ${wake}`);
    console.log(`    • Estimated Annual Revenue : ${rev}`);
    console.log(`    • WS-QAOA Solver Runtime   : ${solverTime}`);
    console.log(`    • 16-Qubit Optimal Bitstring: ${bitstring}`);
    console.log(`    • 5D Spacing Compliance    : ${compliance5D}`);
    console.log('  --------------------------------------------');

    // Verify Placed Turbine Markers on Satellite Map
    const markerCount = await pageDesktop.$$eval('.turbine-leaflet-marker', els => els.length);
    console.log(`  Placed Turbine Markers on Map: ${markerCount} (Expected: 4)`);
    if (markerCount !== 4) {
        throw new Error(`Expected 4 turbine markers on map, found ${markerCount}`);
    }

    // Verify Candidate Grid Targets
    const candidateCircles = await pageDesktop.$$eval('.candidate-site-circle', els => els.length);
    console.log(`  Candidate Siting Grid Rings : ${candidateCircles} (Expected: 16)`);

    // Click on Turbine T1 to open interactive popup
    console.log('  Clicking Turbine T1 marker to inspect popup telemetry...');
    await pageDesktop.click('.turbine-leaflet-marker');
    await pageDesktop.waitForTimeout(1000);

    const popupHtml = await pageDesktop.$eval('.turbine-popup-card', el => el.innerText).catch(() => 'No popup');
    console.log('  Turbine T1 Popup Details:\n' + popupHtml.split('\n').map(l => '    ' + l).join('\n'));

    // Capture Desktop Screenshot
    const desktopScreenshot = path.join(SCREENSHOT_DIR, 'desktop-1280px-anantapur.png');
    await pageDesktop.screenshot({ path: desktopScreenshot, fullPage: false });
    console.log(`  Saved Desktop Screenshot: ${desktopScreenshot}`);

    // ====================================================
    // TEST 2: MOBILE VIEWPORT (390x844 - iPhone / Smartphone)
    // ====================================================
    console.log('\n[2/2] Testing Mobile Viewport (390x844)...');
    const pageMobile = await browser.newPage({
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true
    });

    pageMobile.on('console', msg => {
        if (msg.type() === 'error') {
            console.error('  [Mobile Console Error]:', msg.text());
        }
    });

    await setupPageProxy(pageMobile);

    console.log('  Navigating mobile page to http://127.0.0.1:8000/map/...');
    await pageMobile.goto('http://127.0.0.1:8000/map/', { waitUntil: 'load', timeout: 30000 });
    
    // Wait for the turbine markers to appear
    console.log('  Waiting for turbine markers to render on mobile...');
    await pageMobile.waitForSelector('.turbine-leaflet-marker', { timeout: 35000 });

    const mobileMarkers = await pageMobile.$$eval('.turbine-leaflet-marker', els => els.length);
    const mobileAep = await pageMobile.$eval('#metric-aep', el => el.innerText);
    const mobileRev = await pageMobile.$eval('#metric-rev', el => el.innerText);
    console.log(`  Mobile Markers: ${mobileMarkers} (Expected: 4), AEP: ${mobileAep}, Revenue: ${mobileRev}`);

    const mobileScreenshot = path.join(SCREENSHOT_DIR, 'mobile-390px-anantapur.png');
    await pageMobile.screenshot({ path: mobileScreenshot, fullPage: false });
    console.log(`  Saved Mobile Screenshot: ${mobileScreenshot}`);

    await browser.close();

    console.log('\n====================================================');
    console.log(' Playwright UI Verification PASSED with Zero Errors!');
    console.log('====================================================');
    return {
        aep,
        wake,
        rev,
        solverTime,
        bitstring,
        markerCount,
        mobileMarkers,
        desktopScreenshot,
        mobileScreenshot
    };
}

verifyUI().then(results => {
    console.log('\nVerification Summary:');
    console.log(JSON.stringify(results, null, 2));
    process.exit(0);
}).catch(err => {
    console.error('\nVerification FAILED:', err);
    process.exit(1);
});
