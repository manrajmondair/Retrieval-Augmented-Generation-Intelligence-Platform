const http = require('http');
const httpProxy = require('http-proxy');
const fs = require('fs');
const path = require('path');

// Create a proxy server that adds the API key header
const proxy = httpProxy.createProxyServer({});

const server = http.createServer((req, res) => {
  // Add CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-api-key');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Serve the premium UI for the root path
  if (req.url === '/' || req.url === '/index.html') {
    const htmlPath = path.join(__dirname, 'premium-ui.html');
    
    fs.readFile(htmlPath, 'utf8', (err, data) => {
      if (err) {
        // Fallback to proxying if file doesn't exist
        req.headers['x-api-key'] = 'changeme';
        proxy.web(req, res, {
          target: 'http://localhost:8000',
          changeOrigin: true
        });
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(data);
    });
    return;
  }

  // Add the API key header for all other requests
  req.headers['x-api-key'] = 'changeme';
  
  // Proxy to the backend
  proxy.web(req, res, {
    target: 'http://localhost:8000',
    changeOrigin: true
  });
});

server.listen(3000, () => {
  console.log('Premium RAG UI running on http://localhost:3000');
  console.log('Backend API proxied with automatic authentication');
});