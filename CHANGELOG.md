# Changelog

## [0.16.0](https://github.com/Texarkanine/stockroom/compare/v0.15.0...v0.16.0) (2026-07-23)


### Features

* **dashboard:** show session token usage [[#83](https://github.com/Texarkanine/stockroom/issues/83)] ([#89](https://github.com/Texarkanine/stockroom/issues/89)) ([c475593](https://github.com/Texarkanine/stockroom/commit/c47559360a2be8e5b988b59e041c94dc37b27f75))
* **doctor:** suggest shim ensure-env when freeze exists [[#86](https://github.com/Texarkanine/stockroom/issues/86)] ([#88](https://github.com/Texarkanine/stockroom/issues/88)) ([bfe6f6c](https://github.com/Texarkanine/stockroom/commit/bfe6f6cdfd35871e6acbc07b27e459d59e68bc05))


### Bug Fixes

* **ingest:** merge all Cursor ai-tracking DBs for sessions.models ([#85](https://github.com/Texarkanine/stockroom/issues/85)) ([b5eb8bc](https://github.com/Texarkanine/stockroom/commit/b5eb8bc2e46de71239dc12068d5e8e03e700665b))

## [0.15.0](https://github.com/Texarkanine/stockroom/compare/v0.14.0...v0.15.0) (2026-07-21)


### Features

* **ingest:** Cursor CLI chats and sessions.entrypoint ([#80](https://github.com/Texarkanine/stockroom/issues/80)) ([8575e60](https://github.com/Texarkanine/stockroom/commit/8575e60da91a8e0be00af7362d08c3ab06f6685a))

## [0.14.0](https://github.com/Texarkanine/stockroom/compare/v0.13.0...v0.14.0) (2026-07-20)


### Features

* **query:** add sr-query cookbook for tokens, tools, and skills ([#76](https://github.com/Texarkanine/stockroom/issues/76)) ([45c3b8f](https://github.com/Texarkanine/stockroom/commit/45c3b8fa27e0b126127cd3d782e030f5d4abb8fc))
* **warehouse:** dual-grain session tokens and rollup VIEW ([#74](https://github.com/Texarkanine/stockroom/issues/74)) ([1d87a91](https://github.com/Texarkanine/stockroom/commit/1d87a91ac6a25f815be960160b65dafe544394f6))


### Bug Fixes

* **dashboard:** portable ownership check for macOS replace ([#78](https://github.com/Texarkanine/stockroom/issues/78)) ([677d96d](https://github.com/Texarkanine/stockroom/commit/677d96df42ab46f1a74d758ab2fcc06b0ae4d646))

## [0.13.0](https://github.com/Texarkanine/stockroom/compare/v0.12.0...v0.13.0) (2026-07-19)


### Features

* **docs:** add llms.txt to static site ([#72](https://github.com/Texarkanine/stockroom/issues/72)) ([5408435](https://github.com/Texarkanine/stockroom/commit/5408435f57066d923c31956e3a5b79fedb76981f))

## [0.12.0](https://github.com/Texarkanine/stockroom/compare/v0.11.0...v0.12.0) (2026-07-19)


### Features

* **dashboard:** dual-grain model analytics and usage over time ([#70](https://github.com/Texarkanine/stockroom/issues/70)) ([69b1ac8](https://github.com/Texarkanine/stockroom/commit/69b1ac8407456eef0bd9f10e4cb08d12efa9f0b8))

## [0.11.0](https://github.com/Texarkanine/stockroom/compare/v0.10.0...v0.11.0) (2026-07-17)


### Features

* **dashboard:** skill distribution sunburst and /api/skills ([#64](https://github.com/Texarkanine/stockroom/issues/64)) ([b1ccf38](https://github.com/Texarkanine/stockroom/commit/b1ccf3835bc4c08b4d579abc4d1d726b9722dc92))

## [0.10.0](https://github.com/Texarkanine/stockroom/compare/v0.9.0...v0.10.0) (2026-07-15)


### Features

* **embed:** cross-message batching and orphan cleanup [[#54](https://github.com/Texarkanine/stockroom/issues/54)] [[#56](https://github.com/Texarkanine/stockroom/issues/56)] ([#59](https://github.com/Texarkanine/stockroom/issues/59)) ([7097478](https://github.com/Texarkanine/stockroom/commit/7097478a562cdacc8850422fea2ea464bdc70a61))


### Bug Fixes

* **dashboard:** force-replace on make local-dashboard [[#48](https://github.com/Texarkanine/stockroom/issues/48)] ([#61](https://github.com/Texarkanine/stockroom/issues/61)) ([2166f75](https://github.com/Texarkanine/stockroom/commit/2166f751869895a999a048cd496e187cc2b2ef96))

## [0.9.0](https://github.com/Texarkanine/stockroom/compare/v0.8.0...v0.9.0) (2026-07-15)


### Features

* **docs:** apply Texarkanine paper/ember Material theme ([#58](https://github.com/Texarkanine/stockroom/issues/58)) ([9229643](https://github.com/Texarkanine/stockroom/commit/9229643c39c347eea5404b0527d7f33b8f17992b))
* **ingest:** surgically invalidate embeddings on session rewrite [[#43](https://github.com/Texarkanine/stockroom/issues/43)] ([#55](https://github.com/Texarkanine/stockroom/issues/55)) ([6469614](https://github.com/Texarkanine/stockroom/commit/646961498db41c7be450016388a4e65b21c7f0dd))

## [0.8.0](https://github.com/Texarkanine/stockroom/compare/v0.7.0...v0.8.0) (2026-07-15)


### Features

* **dashboard:** add sessions browse on local dashboard [[#49](https://github.com/Texarkanine/stockroom/issues/49)] ([#52](https://github.com/Texarkanine/stockroom/issues/52)) ([2e99532](https://github.com/Texarkanine/stockroom/commit/2e995322dbfce205e1c865adbd3aac604a0fcf5f))

## [0.7.0](https://github.com/Texarkanine/stockroom/compare/v0.6.0...v0.7.0) (2026-07-14)


### Features

* add sessions.workspace_key for cross-harness project rollup ([#50](https://github.com/Texarkanine/stockroom/issues/50)) ([e109869](https://github.com/Texarkanine/stockroom/commit/e109869eb94f33e2833628bbb9f0de36f82af67d))

## [0.6.0](https://github.com/Texarkanine/stockroom/compare/v0.5.0...v0.6.0) (2026-07-14)


### Features

* **docs:** Intial release-quality documentation site. ([#44](https://github.com/Texarkanine/stockroom/issues/44)) ([7696af4](https://github.com/Texarkanine/stockroom/commit/7696af48143bccf38eeb6eaaa67dfd1a116d69ef))

## [0.5.0](https://github.com/Texarkanine/stockroom/compare/v0.4.0...v0.5.0) (2026-07-11)


### Features

* **dashboard:** session inspection view with deep-links and export ([#40](https://github.com/Texarkanine/stockroom/issues/40)) ([5a16ccd](https://github.com/Texarkanine/stockroom/commit/5a16ccd6770b0a1d7141630a76a4579fc77997dc))

## [0.4.0](https://github.com/Texarkanine/stockroom/compare/v0.3.0...v0.4.0) (2026-07-11)


### ⚠ BREAKING CHANGES

* **dashboard:** change default port to 58008 ([#36](https://github.com/Texarkanine/stockroom/issues/36))

### Features

* **dashboard:** change default port to 58008 ([#36](https://github.com/Texarkanine/stockroom/issues/36)) ([2b41fe0](https://github.com/Texarkanine/stockroom/commit/2b41fe03a53eacf0b1da2b6292a2bf8de8323fce))

## [0.3.0](https://github.com/Texarkanine/stockroom/compare/v0.2.0...v0.3.0) (2026-07-11)


### Features

* **dashboard:** polish controls, ratios, labels, and help ([#31](https://github.com/Texarkanine/stockroom/issues/31)) ([065b479](https://github.com/Texarkanine/stockroom/commit/065b479d024d8bf6823af112ba9cf9f5ce4492e2))
* **query,semantic:** add --detail raw for exact message text ([#35](https://github.com/Texarkanine/stockroom/issues/35)) ([0feaa37](https://github.com/Texarkanine/stockroom/commit/0feaa371e02b849f7c481c847657fef60adb647a))


### Bug Fixes

* **dashboard:** store warehouse timestamps as UTC ([#34](https://github.com/Texarkanine/stockroom/issues/34)) ([e2f5039](https://github.com/Texarkanine/stockroom/commit/e2f50394a1018e80a3248e2bda3e3ea949f64afc))

## [0.2.0](https://github.com/Texarkanine/stockroom/compare/v0.1.5...v0.2.0) (2026-07-10)


### Features

* **ingest,embed:** add progress meter ([#1](https://github.com/Texarkanine/stockroom/issues/1)) ([#26](https://github.com/Texarkanine/stockroom/issues/26)) ([ee10ef2](https://github.com/Texarkanine/stockroom/commit/ee10ef280b7f1eb19bcb5b5035d79decde8eb2ec))

## [0.1.5](https://github.com/Texarkanine/stockroom/compare/v0.1.4...v0.1.5) (2026-07-10)


### Bug Fixes

* **format:** make format ([d30bb94](https://github.com/Texarkanine/stockroom/commit/d30bb941f2e9dbacd4b63a8a3c0f2c4a6e987305))
* **heal:** stdlib-only shim import after plugin move ([#27](https://github.com/Texarkanine/stockroom/issues/27)) ([098befa](https://github.com/Texarkanine/stockroom/commit/098befa934e5cdbcebdc850c1ed9825bc843dea8))

## [0.1.4](https://github.com/Texarkanine/stockroom/compare/v0.1.3...v0.1.4) (2026-07-10)


### Bug Fixes

* **hooks:** sessionStart + uv python find bootstrap ([#23](https://github.com/Texarkanine/stockroom/issues/23)) ([201b353](https://github.com/Texarkanine/stockroom/commit/201b35399ef675a8ed8c942964b33d098afda94f))

## [0.1.3](https://github.com/Texarkanine/stockroom/compare/v0.1.2...v0.1.3) (2026-07-10)


### Bug Fixes

* **dashboard:** replace stale owned listener after plugin move ([#20](https://github.com/Texarkanine/stockroom/issues/20)) ([094e8a0](https://github.com/Texarkanine/stockroom/commit/094e8a0fb6c0a4ea67588413dd5ea8403ae5bf26))
* **shim:** manage stockroom.__version__ via release-please ([#21](https://github.com/Texarkanine/stockroom/issues/21)) ([9c338d1](https://github.com/Texarkanine/stockroom/commit/9c338d186ca8ede97e921e251ae00f665c9a5a75))

## [0.1.2](https://github.com/Texarkanine/stockroom/compare/v0.1.1...v0.1.2) (2026-07-10)


### Bug Fixes

* **cursor:** make Cursor auto-dashboard hook load and run ([#12](https://github.com/Texarkanine/stockroom/issues/12)) ([#16](https://github.com/Texarkanine/stockroom/issues/16)) ([8d4709f](https://github.com/Texarkanine/stockroom/commit/8d4709fe749fc2f0bee65ed94d43c1f18df94f22))
* heal engine env and hashed torch freeze after plugin moves [[#17](https://github.com/Texarkanine/stockroom/issues/17)] ([#19](https://github.com/Texarkanine/stockroom/issues/19)) ([efd2e44](https://github.com/Texarkanine/stockroom/commit/efd2e44bb63f78f6f28b05c6625311689e1b44e3))

## [0.1.1](https://github.com/Texarkanine/stockroom/compare/v0.1.0...v0.1.1) (2026-07-10)


### Bug Fixes

* reconfigure release-please post 0.x release & add doggy header ([dbbbe83](https://github.com/Texarkanine/stockroom/commit/dbbbe83f4459119816e63a27802cba5a728ea9cd))

## 0.1.0 (2026-07-10)


### Features

* stockroom v0 - warehouse, search, dashboard, distribution ([3839f48](https://github.com/Texarkanine/stockroom/commit/3839f480b3dee7c17a65c300aa07383dae44dc3d))
