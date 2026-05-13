const https = require('https');
https.get('https://nexaris-750648121075.europe-west1.run.app/health', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => console.log('GET /health:', res.statusCode, data));
}).on('error', err => console.log('Error GET /health:', err.message));
