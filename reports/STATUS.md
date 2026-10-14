# Фактический результат — 14 октября 2026

Готов первый переносимый этап. **Весь план не завершён: A13 GPU/Metal отсутствует.**
Поставка предназначена для source review и дальнейшего исследования.

| Фаза | Реализовано | Проверено | Не проверено / заблокировано | Дальнейшее исследование |
|---|---|---|---|---|
| A — аудит | Baseline, source lock, DisplayPipe/DART map, архитектура | SHA/исходники/история, генерация карты | Актуальный private baseline | Точные A13 AGX interfaces |
| B — hardware | Opt-in adapter к существующему display, traces | Patches, compile/link, CLI registration PASS | Реальные MMIO/IRQ; QTest отсутствует | AGX MMIO/IRQ/initialization |
| C — memory | Bounded layout, callback DMA, lifecycle | C unit и ASan PASS | Реальная DART и concurrent guest writes | GPU VM, coherency/fences |
| D — execution | Host-only raw32 rect fill | Pixel/padding oracle PASS | GPU shaders/queues/Vulkan/OpenGL отсутствуют | Подтверждённый decoder/renderer |
| E — display | Source integration с default off | Scope/byte identity/rollback PASS | Guest display regression NOT RUN | Reset/shutdown/migration, frame comparison |
| F — Metal | Собственное iOS diagnostic приложение | Только source подготовка, plist syntax | Xcode build/device/Metal NOT RUN | Hardware/VM comparison |

## Уровни приёмки

- Level 1 Research Complete: **PARTIAL**. Карта существующего display воспроизводима,
  но обязательные A13 AGX interfaces, absolute DT addresses и ABI не установлены.
- Level 2 GPU Model Prototype: **NOT MET**. Есть протестированный компонент scanout,
  но нет модели A13 GPU и интеграционного запуска гостя. EXE компилируется.
- Level 3 Guest Compatibility: **NOT RUN**.
- Level 4 Metal Functionality: **NOT RUN**.
- Level 5 Extended Compatibility: **NOT RUN**.

## Выполненные проверки

- MSVC x64 19.44.35229, C11, `/W4 /WX /Od /Zi /RTC1`: 9 групп PASS.
- Тот же код с `/fsanitize=address`: 9 групп PASS, диагностики ASan нет.
- 1960 boundary combinations; 1000 allocate/read/reset/re-init cycles.
- Ошибки allocation и DMA после частичной записи; сохранность предыдущего
  snapshot, отсутствие публикации частичных данных, корректные free callbacks.
- Software fill: проверка всех pixels, padding, out-of-range и aliasing.
- 2 git-format patches: apply/check/am в чистом временном clone точного baseline;
  переносимый код совпадает побайтно; whitelist изменённых файлов; rollback PASS.
- Новые trace events приняты штатным `scripts/tracetool.py --format=h --backends=log`.
- GCC16.2.0/UCRT64: те же 9 групп C tests PASS, `-Werror`.
- Inferno aarch64-softmmu: 1949 build steps, compile и link PASS; два патча,
  без дополнительных изменений tracked upstream sources.
- Нормальный configure/install postconf FAIL (symlink privileges); frozen
  generated graph использован для compile-only проверки. Неполный generated
  qemu-bundle переименован для запуска. См. windows-build.json и recipe.
- 4 CLI проверки version/T8030/property default off/trace registration PASS.
- 5 synthetic integration tests штатного QEMU simpletrace PASS.
- GitHub Windows CI: MSVC/ASan, patch transfer/rollback и trace reader PASS.
  Запуск 38621511411, tested head `7eb0c430978b7046a205d731093d37c5ca0c30bb`;
  подробности в `github-ci.json`. Последующий commit фиксирует только результаты.
- Source ZIP и Git bundle экспортированы; bundle verify, восстановление feature
  HEAD и git fsck PASS. Точный экспортируемый HEAD и SHA-256 находятся рядом с
  архивами в `levelx-release.json` (вне репозитория, чтобы не ссылаться на себя).

Логи: `unit-msvc.json`, `unit-msvc-asan.json`, `transfer.json`, `baseline-audit.json`.
Дополнительно: `unit-gcc.json`, `windows-build.json`, `qemu-registration.json`,
`trace-reader.json`, configure log и excerpt compile log с hash оригинала.
Данные относятся к этому набору исходников, а не к приватной сборке владельца.

## Следующий необходимый этап

Получить source-only Level X baseline, согласовать QTest/альтернативный device
harness, повторить штатную сборку/упаковку в окружении команды, выполнить off/on регрессии и
MetalProbe. Дальше — восстановление AGX по подтверждённым наблюдениям. Этот
блокер нельзя устранить подстановкой готового reims/Vulkan backend.
