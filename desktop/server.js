// خادم محلي صغير يقدّم ملفات الواجهة من داخل البرنامج، عشان fetch للملفات (JSON والخط) يشتغل
const http = require('http');
const fs = require('fs');
const path = require('path');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.webmanifest': 'application/manifest+json',
};

function startServer(root) {
  const base = path.resolve(root);
  return new Promise((resolve, reject) => {
    const srv = http.createServer((req, res) => {
      let p;
      try {
        p = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      } catch {
        res.writeHead(400);
        return res.end();
      }
      if (p === '/') p = '/index.html';
      const file = path.resolve(base, '.' + p);
      if (!file.startsWith(base + path.sep)) {
        res.writeHead(403);
        return res.end();
      }
      fs.readFile(file, (err, data) => {
        if (err) {
          res.writeHead(404);
          return res.end('Not found');
        }
        res.writeHead(200, {
          'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream',
          'Cache-Control': 'no-cache',
        });
        res.end(data);
      });
    });
    srv.on('error', reject);
    // منفذ عشوائي على الجهاز نفسه فقط
    srv.listen(0, '127.0.0.1', () => resolve(srv));
  });
}

module.exports = { startServer };
