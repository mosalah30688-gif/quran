<div align="center">
  <img src="icon.png" width="132" alt="Siraj icon">
  <h1>Siraj — Quran Kareem</h1>
  <p><strong>A cross-platform Arabic Quran application for reading, recitation, reflection, memorization, and consistent daily practice.</strong></p>
  <p><a href="README.md">Home</a> · <a href="README.ar.md">العربية</a> · <a href="https://github.com/mosalah30688-gif/quran/releases">Releases</a></p>
</div>

---

## Contents

- [About Siraj](#about-siraj)
- [Releases and downloads](#releases-and-downloads)
- [Features](#features)
- [Privacy and offline operation](#privacy-and-offline-operation)
- [Update and supply-chain integrity](#update-and-supply-chain-integrity)
- [Platform requirements and installation](#platform-requirements-and-installation)
- [File verification](#file-verification)
- [Technical architecture](#technical-architecture)
- [Running from source](#running-from-source)
- [Testing and audit](#testing-and-audit)
- [Content sources and rights](#content-sources-and-rights)
- [Contributing and security](#contributing-and-security)
- [License](#license)
- [Developer and contact](#developer-and-contact)

## About Siraj

**Siraj** is an Arabic Quran application for Android, Windows, and Linux. It brings together Quran reading, recitations, exegesis, search, word meanings, tajweed, memorization, wird, khatmah, adhkar, bookmarks, and statistics in one responsive, RTL-first experience.

The project follows five operating principles:

- **The text comes first:** a calm reading surface, an on-demand index, and direct navigation to the required location.
- **Every source is identified:** external data and assets are tied to provenance records, versions, and hashes.
- **Privacy by default:** no account is required, and core reading state remains on the user’s device.
- **Verification before release:** stable releases must pass tests, signing, hashes, and the release gate.
- **No inflated claims:** automated structural and provenance checks are not described as human scholarly certification.

> The displayed product name is **Siraj — Quran Kareem**. `com.quran.mushaf` is a historical Android package identifier retained to preserve upgrades from earlier versions.

## Releases and downloads

| Platform | Stable | Distribution | Release page |
|---|---:|---|---|
| Android | `1.4.4` (`versionCode 144`) | Signed full APK | [siraj-android-v1.4.4](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-android-v1.4.4) |
| Windows | `4.1.4` | Signed patch over Portable `4.1.1` | [Full baseline 4.1.1](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-windows-v4.1.1) · [Patch 4.1.4](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-windows-patch-v4.1.4) |
| Linux | `4.1.3` | Signed patch over AppImage `4.1.1` | [Full baseline 4.1.1](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-linux-test-v4.1.1) · [Patch 4.1.3](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-linux-patch-v4.1.3) |

Each platform has an independent version and stable channel. Published GitHub Releases are immutable: corrections are issued under a new version rather than replacing historical assets.

### Current file digests

| File | Size | SHA-256 |
|---|---:|---|
| `Siraj-Android-1.4.4.apk` | 7,447,716 bytes | `e155cf8a8ca2968f4e4a07167b8f54387eb1d38e5731c1325545da28d669e2f4` |
| `Siraj-Quran-4.1.4-windows.sirajpatch` | 2,816,294 bytes | `7fd386ba6eaadc2e3e6d3a44230e3596c953bc91763fb497aa01d80d6c1e8170` |
| `Siraj-Quran-4.1.3-linux.sirajpatch` | 2,403,198 bytes | `795ccbdd120cdc2090de56387e111943d7101ce73f7d240e1fb07eeb52b9196a` |

Release evidence:

- [`audit/ANDROID_RELEASE_1.4.4.json`](audit/ANDROID_RELEASE_1.4.4.json)
- [`audit/WINDOWS_PATCH_RELEASE_4.1.4.json`](audit/WINDOWS_PATCH_RELEASE_4.1.4.json)
- [`audit/LINUX_PATCH_RELEASE_4.1.3.json`](audit/LINUX_PATCH_RELEASE_4.1.3.json)

## Features

### 1. Quran reading

- The complete Quran: **6,236 ayat** across **114 surahs**.
- Page-by-page navigation using the **604-page** Madinah Mushaf page mapping.
- Surah, juz, and ayah index with direct navigation and last-position restoration.
- Hafs in Uthmani script and simplified orthography, with tajweed explanations in a separate tab that never recolors or alters the Mushaf text.
- Additional riwayat, including Warsh, Qalun, and Al-Duri alongside Hafs.
- A wide Hafs reading layout with centered surah title and basmalah, continuous text, and ornamental ayah markers.
- Presentation-layer basmalah handling so it appears once without changing source data, numbering, recitation mapping, or tafsir mapping.
- Text selection, copying, referenced ayah copy, and platform-supported sharing.
- Persistent bookmarks, multiple highlight colors, and quick return to saved locations.
- Deliberate page navigation that avoids accidental horizontal turns during vertical wheel or touchpad scrolling.

### 2. Recitation and audio

- **17 Hafs reciters** backed by recorded source and availability checks.
- Dedicated recitation sets for supported additional riwayat.
- Play an entire surah or begin at a selected ayah.
- Previous, next, pause, resume, stop, and a visible audio timeline.
- Repeat one ayah or a selected range for memorization and review.
- Download recitations into application storage; pause, resume, or remove a reciter’s files.
- Offline listening for previously downloaded audio.
- Clear reciter, riwayah, and provider attribution without claiming ownership of recordings.

### 3. Exegesis, search, and meanings

- **78 provenance- and rights-reviewed tafsir choices**:
  - 73 selected classical works from official Quranpedia dumps.
  - 5 documented AlQuran Cloud editions.
- Exclusion of modern or rights-uncertain works where permission could not be established.
- Local Quran search with direct navigation from a result to its ayah.
- Ayah-linked word meanings.
- Multiple Quran-meaning translations.
- Selectable tafsir with persistent preference.
- Windows and Linux full packages include the locked local tafsir database.
- Android offers the large tafsir database as an optional download outside the APK and verifies size, SHA-256, and SQLite structure before activation.
- Missing coverage in a partial work is shown as source coverage, not misreported as a network error.

### 4. Memorization and review

- A memorization mode that hides and reveals text for self-testing.
- Ayah-by-ayah review with audio repetition.
- Locally recorded memorized ranges and progress.
- Recitation playback from the same memorization position.
- Flexible tools rather than one mandatory learning plan.

### 5. Wird and khatmah

- Flexible daily reading without a mandatory target.
- Page, session, and reading-habit tracking.
- Khatmah planning and progress tracking.
- Streak and consistency statistics designed to encourage continuity without turning worship into competition.
- Optional in-app reminders and Android system notifications when enabled.

### 6. Adhkar and daily tools

- Categorized adhkar.
- A dedicated counter for each item.
- Source references retained where provided by the data source.
- Local state persistence.
- Quick movement between adhkar, Quran reading, and progress tools.

### 7. Typography, appearance, and accessibility

Four bundled or approved Arabic typefaces:

- Amiri Quran
- Amiri
- Noto Naskh Arabic
- Scheherazade New

Additional experience features:

- Quran and tafsir font family and size controls.
- Light and dark themes.
- Complete Arabic RTL interface.
- Clear touch targets and responsive phone, tablet, portrait, and landscape layouts.
- Compact desktop navigation and an index that opens only when needed.
- Windows keyboard navigation using Page Up, Page Down, and arrow keys.
- Focus restoration and Escape/outside-click menu dismissal where applicable.
- Reduced-motion support in interfaces that expose it.

### 8. Siraj identity

- The current application icon appears above the Amiri “سراج” wordmark.
- Android places “About” as the final Settings item, not in bottom navigation.
- Windows and Linux place “About” immediately below Settings.
- A consistent About page: “سراج”, “مصحف قرآن كريم”, five concise features, developer name, and contact links.
- Changelogs are not embedded in About; update prompts show user-facing features only.

## Privacy and offline operation

- Siraj does not require an account.
- Reading position, bookmarks, highlights, progress plans, and settings are stored locally.
- Core Quran text, indexes, and search operate from local assets.
- Windows and Linux tafsir operate locally after the full package is installed; Android can install an optional verified local database.
- The Project does not maintain a centralized listening history.
- Streaming or downloading a recitation connects the user’s device to the provider, which may receive IP address and request metadata under its own policy.
- Updates are not silently installed: the application verifies them and presents the action according to platform capabilities.

## Update and supply-chain integrity

### Android

- Full signed Release APK.
- Signer continuity and increasing `versionCode` are checked.
- Size and SHA-256 are verified before installation is offered.
- Required local assets are verified inside the packaged APK.

### Windows and Linux

- Independent **Ed25519-signed** update channel per platform.
- Product, version, size, and SHA-256 verification before application.
- `.sirajpatch` packages include a signed manifest and a digest for every payload file.
- Patch installation is simulated against the full `4.1.1` baseline during release verification.
- User data remains outside the replacement scope, with rollback behavior for failed updates.

### Release evidence

- CycloneDX SBOM for desktop candidates.
- GitHub build provenance/attestations for candidate assets.
- Exact asset-set verification before promoting a Draft.
- GitHub Immutable Releases; superseded versions remain available rather than being overwritten.
- Private signing keys remain in GitHub Secrets and are never committed.

> Windows executables are intentionally not Authenticode-signed at present, so SmartScreen may appear. Update-path authenticity is enforced through Ed25519, SHA-256, size checks, and immutable Releases.

## Platform requirements and installation

### Android

- Android 5.1 (API 22) or later.
- Download the APK from the [official release](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-android-v1.4.4).
- Optionally verify the digest, then allow installation from the source used for the download.
- Upgrades retain the historical package ID and the same signing certificate.

> Google Play preparation is deferred. The approved distribution is currently the direct GitHub APK.

### Windows

- Windows 10 version 1809 or later, or Windows 11, x64.
- Download the [full Portable 4.1.1 baseline](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-windows-v4.1.1), extract the complete ZIP, and run `Siraj.exe`.
- No installer or administrator privilege is required.
- Portable data is stored in `UserData` beside the executable; application settings are not written to the Registry.
- Update in-app to `4.1.4`, or apply the official patch through the update interface.

### Linux

- A modern x86_64 Linux desktop.
- Download the [full AppImage 4.1.1 baseline](https://github.com/mosalah30688-gif/quran/releases/tag/siraj-linux-test-v4.1.1).
- Grant execute permission once:

```bash
chmod +x Siraj-Quran-4.1.1-linux-x86_64.AppImage
./Siraj-Quran-4.1.1-linux-x86_64.AppImage
```

- The application then uses the signed stable patch channel through `4.1.3`.
- The Project does not distribute a DEB, RPM, or privileged installer.

## File verification

### Linux and macOS

```bash
sha256sum -c SHA256SUMS.txt
```

### Windows PowerShell

```powershell
Get-FileHash .\Siraj-Android-1.4.4.apk -Algorithm SHA256
```

Compare the result with the Release page or the relevant audit record. Do not install a similarly named file from an unofficial mirror.

## Technical architecture

| Area | Technology | Location |
|---|---|---|
| Android | Capacitor 6, HTML/CSS/JavaScript UI, native Java plugins | `index.html`, `app.js`, `android/` |
| Windows | Python 3.13 and PySide6, Portable package | `windows_app/` |
| Linux | Python 3.13 and PySide6, AppImage | `mushaf_app/` |
| Data | Local JSON and a locked SQLite tafsir database | data directories and `audit/` |
| Updates | Full APK/manifest and Ed25519 desktop channels/patches | `update/`, `scripts/` |
| Release | GitHub Actions, SBOM, attestations, Release Gate | `.github/workflows/`, `audit/RELEASE_GATE.json` |

Platform versions are independent because their build and distribution cycles differ; version-number differences do not imply different core Quran text.

## Running from source

> Source visibility does not grant reuse rights. These commands are for the Owner and authorized contributors under [`LICENSE`](LICENSE) and [`CLA.md`](CLA.md).

### Android

Requirements: Node.js 20, npm, JDK 17, and a suitable Android SDK.

```bash
npm ci
npm run build:www
npm run android:sync
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r windows_app\requirements.txt
.venv\Scripts\python windows_app\main.py
```

### Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r mushaf_app/requirements.txt
python scripts/fetch_offline_tafsir_data.py
python mushaf_app/main.py
```

## Testing and audit

Core shared checks:

```bash
node --check app.js
python scripts/verify_android_bundle.py
python scripts/verify_audio_sources.py
python scripts/verify_asset_provenance.py
python scripts/verify_data_provenance.py
python -m py_compile windows_app/main.py mushaf_app/main.py
```

Unit tests:

```bash
python -m unittest discover -s windows_app/tests -p 'test_*.py' -v
python -m unittest discover -s mushaf_app/tests -p 'test_*.py' -v
```

UI suites:

- `windows_app/tests/ui_test.py`
- `mushaf_app/tests/ui_test.py`
- Android responsive browser checks in the validation path.

Workflows additionally verify the locked tafsir database, audio sources, dependency licenses, package execution, SBOM, and corresponding source for LGPL/GPL components.

## Content sources and rights

Siraj uses documented material from sources including:

- AlQuran Cloud and Islamic Network;
- Quranpedia;
- MP3Quran;
- Amiri, Noto, and Scheherazade fonts under SIL OFL 1.1; and
- Capacitor, Python, Qt, and their dependencies under their own licenses.

Primary records:

- [`audit/DATA_PROVENANCE.md`](audit/DATA_PROVENANCE.md): data provenance, hashes, and generators.
- [`audit/THIRD_PARTY_REVIEW.md`](audit/THIRD_PARTY_REVIEW.md): rights and third-party component review.
- [`audit/SCHOLARLY_REVIEW.md`](audit/SCHOLARLY_REVIEW.md): human scholarly-review status.
- [`audit/ICON_PROVENANCE.md`](audit/ICON_PROVENANCE.md): Siraj icon provenance.
- [`NOTICE.md`](NOTICE.md): boundary between Siraj-owned and third-party material.

Packaging does not transfer ownership of Quran text, exegesis, translations, recordings, fonts, or other external material to the Project. Public availability alone is not treated as sufficient evidence of relicensing rights.

## Contributing and security

- Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.
- Every code contribution requires explicit acceptance of [`CLA.md`](CLA.md).
- Never submit a secret, signing key, PAT, or user data.
- Report unpatched vulnerabilities privately under [`SECURITY.md`](SECURITY.md), not in a public Issue.
- Bug reports and proposals are welcome, but review does not guarantee acceptance or a release date.

## License

Siraj is now **proprietary, not open source**:

- [`LICENSE`](LICENSE) permits later Official Binaries that carry it to be downloaded and run unmodified for personal, non-commercial use.
- Copying or modifying new original material, redistribution, commercial use, and organizational deployment require written permission.
- A complete Arabic translation is available in [`LICENSE.ar.md`](LICENSE.ar.md).
- Original material published at or before commit `4fda3631611b2eef8a630621719f9c9beef7390f` was historically offered under MIT. That grant remains valid for the copies it covered; its text is preserved in [`LICENSES/MIT-HISTORICAL.txt`](LICENSES/MIT-HISTORICAL.txt).
- Third-party materials are not automatically covered by either the proprietary license or the historical MIT grant; their own terms control.
- The Siraj name, icon, and identity are not licensed for reuse.
- [`audit/LICENSE_TRANSITION_2026-10-31.md`](audit/LICENSE_TRANSITION_2026-10-31.md) records the transition decision, boundary, and repository controls.

Commercial use, organizational deployment, redistribution, or integration into another product requires clear written permission from the Owner.

## Developer and contact

- **Developer:** [محمد صلاح عبد الخالق](https://elkatebmohamadsalah.blogspot.com/p/c.html)
- **Contact:** [Official contact page](https://elkatebmohamadsalah.blogspot.com/p/blog-page_827.html)
- **Source and issues:** [mosalah30688-gif/quran](https://github.com/mosalah30688-gif/quran)

## Important disclaimer

Siraj applies technical controls to source provenance, hashes, structure, and edition separation. Those controls do not replace qualified human review of Quran text, riwayat, tajweed, meanings, or adhkar. The human scholarly-review status is published transparently in [`audit/SCHOLARLY_REVIEW.md`](audit/SCHOLARLY_REVIEW.md).

---

<div align="center">
  <strong>Siraj — focused reading, structured listening, and practical tools for consistency.</strong>
</div>
