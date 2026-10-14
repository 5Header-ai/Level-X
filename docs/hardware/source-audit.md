# Аудит связанных исходников

Все Git refs зафиксированы 2026-10-14. `source-lock.json` содержит URL через
repository + SHA, перечень прочитанных файлов и SHA-256; API tree не был truncated.
Это целевой обзор графики, не аудит всех файлов каждого проекта.

| Проект / ref | Что изучено | Вывод о переносимости |
|---|---|---|
| [ChefKissInc/Inferno](https://github.com/ChefKissInc/Inferno/tree/cc4302a99167abec69b714cfd00c38caece7e7de) `cc4302a…` | T8030, DisplayPipe v4/v2, DART, scaler, QEMU DMA, build/license | Единственная база патчей; не Level X private baseline |
| [MakrSas/Inferno](https://github.com/MakrSas/Inferno/tree/b76fa575831d94a80db169ffb3c76d9094a648bd) `b76fa575…` | iOS embedding README, DisplayPipe v4, последние commits | Ветка содержит PCC mailbox workaround для другого контекста; не доказана применимость к iOS14 beta5 |
| [den0620/QEMUAppleSilicon](https://github.com/den0620/QEMUAppleSilicon/tree/80d84158cb42889f8f3b07bb98c6e449f8e588c0) `80d84158…` | T8030, DART, DisplayPipe v4/v2, история | Сходные устройства, но три проверенных файла отличаются от baseline; blind cherry-pick не допускается |
| [MakrSas/orchard-ios](https://github.com/MakrSas/orchard-ios/tree/fab0f9f0d60acfdc2488181385ac53b7b4ea23c6) `fab0f9f0…` | reims MMIO/PCI shim, C ABI, README, patch series, recent history | AppleParavirtGPU/vmapple, не AGX A13; части host Metal требуют Darwin |
| [QEMU v10.2.2](https://github.com/qemu/qemu/tree/f8ed81651e61d9c2166df6121ce2af0f44f06b3e) `f8ed8165…` | apple-gfx, DMA/memory, release history | PVG framework на macOS, не готовый Windows backend для stock iOS AGX |
| [XNU 7195.50.7.100.1](https://github.com/apple-oss-distributions/xnu/tree/bb611c8fecc755a0d8e56e2fa51513527c5b7a0e) `bb611c8f…` | IODMACommand / IOMemoryDescriptor, tree, release import history | Общие DMA abstractions; не точный kernel source 18A5351d и не AGX driver source |

`history-audit.json` фиксирует недавние изменения DisplayPipe baseline и сравнения
файлов. Существенны `08f1b5d97a86` (кеш Pixman image) и `5641521b9e57`
(int_status): новый adapter освобождает заимствующий image до замены buffer.
В MakrSas на pinned HEAD `b76fa575…` поправлена falling-edge PCC doorbell,
а `b0b55605…` добавляет временный handshake. Эти commits дают направление
исследования, но не верифицированный A13 GPU контракт.
В orchard `1bbc5eb8…` отменяет deferred surface writeback; даже на его платформе
нельзя предполагать корректность отложенной синхронизации без тестов.

**Заимствовано кода: 0 строк из этих сторонних fork/backend.** Patch context
Inferno и изменения AGPL-файла сохраняют upstream лицензию. MIT C-модуль написан
заново. Shader probe также собственный.
