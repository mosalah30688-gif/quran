// تخزين مؤقت للواجهة ليعمل التطبيق بدون اتصال (بيانات السور تُخزن عند أول تحميل)
const CACHE = 'quran-shell-v3';
const SHELL = ['./', './index.html', './app.js', './manifest.json', './icon.png', './icon-192.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const isAPI = url.hostname.includes('alquran.cloud') || url.hostname.includes('islamic.network');
  if (isAPI) {
    // شبكة أولاً ثم تخزين مؤقت عند انقطاع الاتصال
    e.respondWith(
      fetch(req).then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }
  // الواجهة: الكاش أولاً
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
