# Ограничения и блокеры

1. Нет актуального source-only Level X baseline. Патчи подтверждены только по
   применимости к публичному SHA; это не гарантия Windows production compatibility.
2. Нет восстановленного AGX A13 submission/initialization/VM/fence протокола.
   Случайные MMIO ACK или фиктивный Metal success не добавлены. Это основной
   исследовательский блокер, а не недостающая библиотека Vulkan.
3. Компиляция/линковка всего aarch64-softmmu выполнена на Windows/MSYS2.
   Штатный configure останавливается на postconf symbolic links (WinError1314).
   Проверка использует frozen build graph и исключает неполный qemu-bundle;
   это не проверка install workflow, guest boot или production packaging.
4. В pinned Inferno отсутствует QTest. Его восстановление требует отдельной
   согласованной зависимости; mock callback не заменяет hardware integration test.
5. Нет iOS fixture, macOS/Xcode и физического iPhone. MetalProbe не скомпилирован
   и не запущен; тестовые JSON PASS не выдумывались.
6. Snapshot: raw32, до 64 MiB на слой, width/height ≤16384. Новая аллокация на кадр,
   возможны заметные затраты на copy. Проверена корректность, не производительность.
7. DATA_END не используется, потому что endpoint semantics не установлены;
   нет tiled/compressed decode. Stride/address bounds не заменяют корректный DART.
8. Нет guest queue, fence, async worker, shader compiler, GPU MMU или DMA write.
9. Транзакционная публикация host buffer не делает гостевую память атомарной.
   Caller обязан обеспечить синхронизацию; текущий adapter наследует BH context.
10. Существующие IRQ, миграция, VRAM bounds, display lifecycle и другие ограничения
    upstream не исправляются полностью. С флагом off сохраняется прежний путь,
    включая его недостатки. Нужна отдельная runtime-регрессия off/on.
11. Репозиторий владельца — 5Header-ai/Level-X. Git HTTPS write transport на
    локальном хосте аварийно завершился; перенос через connector API создаёт
    новые commit IDs, сохраняя content tree и логические этапы. Original history
    сохраняется в bundle. GitHub CI не заменяет отсутствующий guest-стенд.

Для продолжения нужны исходники и воспроизводимый тестовый fixture, не чужие
секреты или production-доступ. Критерии снятия блокеров: в acceptance checklist.
