const https = require('https');
https.get('https://nexaris-750648121075.europe-west1.run.app/api/v1/download/apk', (res) => {
  console.log('Status Code:', res.statusCode);
  console.log('Headers:', res.headers);
  res.on('data', (d) => {
    console.log('First chunk length:', d.length);
    console.log('First 4 bytes:', d.toString('hex', 0, 4));
    process.exit(0);
  });
}).on('error', (e) => {
  console.error(e);
});
