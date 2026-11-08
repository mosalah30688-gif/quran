// غلاف سراج وبيانات القراءة الأساسية مخزّنة مسبقًا ليعمل المصحف دون اتصال.
const CACHE = 'siraj-shell-v30';
const SHELL = [
  './', './index.html', './smart-context.js', './smart-services.js', './tajweed-learning.js',
  './tajweed-curriculum-loader.js', './prayer-times.js', './prayer-data.js', './prayer-ui.js', './app.js',
  './manifest.json', './icon.png', './icon-192.png',
  './quran-hafs.json', './quran-madani-lines.json', './quran-tajweed.json', './tajweed-learning-catalog.json', './tajweed-scope-registry.json',
  './surahs.json', './tafsir-catalog.json', './quran-reciters.json',
  './quran-search.json', './quran-meanings.json', './quran-riwayat.json', './adhkar.json',
  './fonts/AmiriQuran-arabic.woff2', './fonts/Amiri-Regular.ttf',
  './fonts/AmiriQuran-Regular.ttf', './fonts/NotoNaskhArabic-Variable.ttf',
  './fonts/ScheherazadeNew-Regular.ttf',
];

function curriculumArtifacts(registry) {
  if (!registry || registry.fallbackPolicy !== 'FORBIDDEN_BETWEEN_SCOPES'
      || !Array.isArray(registry.settings)) return [];
  const safe = /^tajweed-curricula\/[a-z0-9][a-z0-9._-]*\.json$/;
  const artifacts = [];
  registry.settings.forEach((entry) => {
    (Array.isArray(entry.curricula) ? entry.curricula : []).forEach((pointer) => {
      if (pointer && safe.test(pointer.artifact) && !artifacts.includes(pointer.artifact)) {
        artifacts.push(pointer.artifact);
      }
    });
  });
  return artifacts.map((artifact) => './' + artifact);
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(SHELL);
    const registryResponse = await cache.match('./tajweed-scope-registry.json');
    if (registryResponse) {
      const registry = await registryResponse.json();
      const curricula = curriculumArtifacts(registry);
      if (curricula.length) await cache.addAll(curricula);
    }
    await self.skipWaiting();
  })());
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
  event.respondWith(caches.match(request).then((hit) => hit || fetch(request).then((response) => {
    if (response.ok && url.origin === self.location.origin) {
      const copy = response.clone();
      caches.open(CACHE).then((cache) => cache.put(request, copy));
    }
    return response;
  })));
});
