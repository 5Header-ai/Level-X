# Baseline — предварительный, 14 октября 2026

## Зафиксированный источник

- Upstream: https://github.com/ChefKissInc/Inferno
- Commit: `cc4302a99167abec69b714cfd00c38caece7e7de` (проверен `git rev-parse HEAD`).
- VERSION: `ChefKissInferno-1.0.0rc1_QEMU-10.2.2_10.1.3_hybrid`.
- Это гибридная ветка Inferno, **не чистый QEMU 10.2.2** и не приватный Level X.
- Целевая машина: `t8030`, AArch64 system emulation, TCG, `aarch64-softmmu`.
- `CONFIG_APPLE_SOC` зависит от TCG/ARM/AARCH64; выбирает `APPLE_DART`.
- Upstream CI собирает aarch64-softmmu и x86_64-softmmu на Linux/macOS;
  это не свидетельство сборки под Windows. Здесь доступен MSVC для автономного C-кода.
- Запуск iOS, исходники локальных Windows-исправлений и физический iPhone не предоставлены.
  Версия iOS `14.0 beta 5 / 18A5351d` и ProductType `iPhone12,1` — целевые данные задания,
  а не результат выполненного запуска.
- В этом SHA отсутствуют root `tests/`, qtest source/accelerator и `-qtest`
  option. Нельзя использовать стандартный QEMU QTest recipe без восстановления
  инфраструктуры. Проверка отражена в `reports/baseline-audit.json`.

## Существующие интерфейсы и зависимости

| Файл | Назначение |
|---|---|
| `hw/arm/apple-silicon/t8030.c` | Создаёт disp0 и dart-disp0; MMIO base, IRQ и SID берёт из DeviceTree |
| `hw/display/apple_displaypipe_v4.c` | MMIO DisplayTarget5, DMA-чтение слоёв, Pixman, QemuConsole, framebuffer, IRQ |
| `include/hw/display/apple_displaypipe_v4.h` | `adp_v4_from_node`, `adp_v4_update_vram_mapping`, `adp_v4_get_fb_off` |
| `hw/arm/apple-silicon/dart.c` | QEMU IOMMUMemoryRegion, SID, translation, page-table walk, fault IRQ |
| `include/hw/arm/apple-silicon/dart.h` | `apple_dart_iommu_mr`, `apple_dart_instance_iommu_mr` |
| `hw/display/apple_scaler.c` | Отдельная модель scaler; не AGX |
| `hw/display/apple_displaypipe_v2.c` | Другой DisplayPipe; не точка интеграции T8030 |
| `hw/display/meson.build` | Подключение DisplayPipe при CONFIG_APPLE_SOC |
| `hw/arm/apple-silicon/meson.build`, `hw/arm/Kconfig` | Сборка SoC, DART, зависимости |
| `include/system/dma.h`, `system/memory.c` | DMA API и механизм address spaces |

DisplayPipe v4 требует Pixman и libpng, использует GLib/QOM/BH/timer/VMState.
DMA уже направляется через DART address space. Публичной модели AGX/A13 GPU,
декодера его команд и исполнителя шейдеров в просмотренном T8030 пути не найдено.

## Планируемая область изменений (зафиксирована до реализации)

1. Новый переносимый C-модуль проверки layout и транзакционного чтения scanout.
2. Отдельный opt-in адаптер внутри `apple_displaypipe_v4.c`, отключённый по умолчанию.
3. Одна локальная правка `hw/display/meson.build` для подключения нового файла.
4. Тесты, диагностическое iOS-приложение и документация вне основного движка.

Не планируются изменения CPU, DART, USB, сети, SEP, NVRAM, restore, хранилища,
подписей, аппаратной аттестации или production. Новые AGX MMIO и IRQ не выдумываются.
Неизвестный аппаратный протокол остаётся отдельным исследовательским блокером.

## Сторонние патчи

Ни один сторонний патч пока не признан переносимым без проверки.
`MakrSas/Inferno` ориентирован на запуск внутри iPhone-приложения;
`reims-vgpu` в orchard-ios относится к apple-vm/macOS, а не к A13/iOS AGX.
Сравнение pinned исходников и область применимости зафиксированы в
`docs/hardware/source-audit.md`. Дальнейшие reuse-кандидаты и условия адаптации:
`REUSABLE-TECHNOLOGIES.md`; импорт backend пока не выбран.

Перед переносом на Level X нужны точный commit, source-only локальные изменения,
конфигурация сборки и сравнение этих интерфейсов. Применение патча к указанному
upstream не подтверждает совместимость с актуальным Level X.
