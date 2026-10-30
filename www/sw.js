// غلاف سراج وبيانات القراءة الأساسية مخزّنة مسبقًا ليعمل المصحف دون اتصال.
const CACHE = 'siraj-shell-v7';
const SHELL = [
  './', './index.html', './app.js', './manifest.json', './icon.png', './icon-192.png',
  './quran-hafs.json', './quran-tajweed.json', './surahs.json', './tafsir-catalog.json',
  './quran-search.json', './quran-meanings.json', './quran-riwayat.json', './adhkar.json',
  './fonts/AmiriQuran-arabic.woff2', './fonts/Amiri-Regular.ttf',
  './fonts/AmiriQuran-Regular.ttf', './fonts/NotoNaskhArabic-Variable.ttf',
  './fonts/ScheherazadeNew-Regular.ttf',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  const isAPI = url.hostname.includes('alquran.cloud') || url.hostname.includes('islamic.network');
  if (isAPI) {
    // الشبكة أولًا للترجمات والمصادر الحية، ثم النسخة السابقة عند انقطاع الاتصال.
    event.respondWith(
      fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      }).catch(() => caches.match(request))
    );
    return;
  }
  event.respondWith(caches.match(request).then((hit) => hit || fetch(request)));
});
