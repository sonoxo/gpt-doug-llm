import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.mjs',
  fullyParallel: false,
  timeout: 45000,
  retries: 0,
  reporter: [['list'],['json',{outputFile:'artifacts/browser-results.json'}]],
  use: {baseURL:'http://127.0.0.1:8765',headless:true,trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer: {
    command:'python3 -m http.server 8765 --bind 127.0.0.1 --directory docs',
    url:'http://127.0.0.1:8765/darkweb/index.html',
    reuseExistingServer:false,
    timeout:30000
  }
});
