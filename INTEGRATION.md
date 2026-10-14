# Передача и интеграция без участия автора

Версия `0.1.0-preliminary`. Полный GPU model отсутствует. Это исходники и патчи
checked scanout + diagnostic trace для существующего DisplayPipe.

## Baseline и изменения

Upstream: `https://github.com/ChefKissInc/Inferno.git`.
Base: `cc4302a99167abec69b714cfd00c38caece7e7de`.
QEMU VERSION: `ChefKissInferno-1.0.0rc1_QEMU-10.2.2_10.1.3_hybrid`.

Изменены:

- `hw/display/apple_displaypipe_v4.c`: opt-in property, DMA adapter, trace hooks.
- `hw/display/meson.build`: один дополнительный C-файл под CONFIG_APPLE_SOC.
- `hw/display/trace-events`: три отключённых по умолчанию trace events.

Добавлены в Inferno:

- `hw/display/levelx_scanout.c` — точная копия `src/levelx_scanout.c` с обязательным
  первым include `qemu/osdep.h`.
- `hw/display/levelx_scanout.h` — точная копия `include/levelx_scanout.h`.

Нет изменений DART/CPU/USB/сети/SEP/NVRAM/storage/restore/signing.
Новых QEMU targets и внешних runtime-библиотек нет. Автономный модуль использует
C11/libc; адаптер — существующие GLib, Pixman, DMA/QOM/BH. Libpng остаётся
upstream-зависимостью DisplayPipe. Флаг добавляет один bool вне VMState.

## Порядок применения

В отдельной чистой копии, не в production:

```sh
git clone https://github.com/ChefKissInc/Inferno.git levelx-inferno-review
cd levelx-inferno-review
git switch -c feature/levelx-gpu cc4302a99167abec69b714cfd00c38caece7e7de
git am /path/to/levelx-iphone-gpu-engine/patches/inferno/0001-*.patch
git rev-parse HEAD
git am /path/to/levelx-iphone-gpu-engine/patches/inferno/0002-*.patch
git rev-parse HEAD
```

Сохраните два напечатанных commit ID как PATCH1/PATCH2. Git am может получить
иные commit SHA из-за committer metadata; содержимое проверяется по patch hash.
Исходные patch commits: `c45f2f5d5fbdc2e707ebdf227177fd9baa4cd3f9`,
`9278a7d8e5d42a4d52d154ec25bf0368516347e0`.

Автоматическая проверка из этого репозитория:

```sh
python tools/audit_baseline.py /path/to/Inferno --output reports/local-baseline.json
python tests/integration/verify_transfer.py /path/to/Inferno --report reports/local-transfer.json
```

Вторая команда создаёт временный clone, применяет патчи, проверяет область
изменений, byte identity переносимого кода и обратное применение, затем удаляет
только временную копию. Рабочий Inferno не меняет. Это не проверка компиляции QEMU.

Для нового Level X baseline сначала сравните все перечисленные интерфейсы и
файлы. При конфликте не используйте автоматический `--3way` как доказательство
совместимости: перенесите минимальные hunks, пересоберите и повторите регрессии.

## Сборка

Автономный C-модуль реально проверен: `python tools/test.py`, затем `--sanitize`,
а также `--cc gcc` внутри UCRT64.

Для Inferno нужен рабочий upstream build environment: GNU/Clang toolchain,
Python, Meson/Ninja/pkg-config, GLib, Pixman, PNG, libtasn1 и включённые зависимости
ветки (в частности lzfse/nettle/gnutls при указанных ниже опциях). Используйте
проверенный рецепт сборки вашего Windows baseline. MSVC сам по себе не заменяет
GNU-окружение всего Inferno. Для проверки развернута отдельная MSYS2 root внутри
workspace. Точный рецепт и ограничение postconf symbolic links:
[Windows build](docs/experiments/windows-build.md). Системные настройки не менялись.

Пример исходной Linux/macOS конфигурации для проверки — **NOT RUN здесь**:

```sh
git submodule update --init --recursive
mkdir build-levelx
cd build-levelx
../configure --target-list=aarch64-softmmu --enable-pixman --enable-png \
  --enable-lzfse --enable-nettle --enable-gnutls --disable-guest-agent
ninja
```

Перед распространением производной сборки учтите branding notice upstream:
пакет наших патчей не содержит artwork и бинарников; recipe не решает отдельный
вопрос удаления защищённого branding из распространяемой производной сборки.
См. `LICENSES.md`.

## Запуск и переключение

К существующей тестовой команде `qemu-system-aarch64 -M t8030 ...` добавьте:

```text
-global apple-display-pipe-v4.levelx-checked-scanout=on
```

По умолчанию `off`; для явного отката поведения используйте то же свойство `=off`
и перезапустите VM. Не переключайте его через QMP во время исполнения.
Патчи не предоставляют загрузочные iOS-файлы и не меняют вашу команду их загрузки.

Опциональная диагностика:

```text
-trace enable=levelx_adp_mmio_read
-trace enable=levelx_adp_mmio_write
-trace enable=levelx_adp_scanout
-d guest_errors
```

Trace events доступны после патча 2; они логируют метаданные, не содержимое buffers.
Синтаксис событий проверен штатным `scripts/tracetool.py` baseline.
Не трактуйте FRAME_PROCESSED как Metal completion: прежняя IRQ-семантика сохранена.
Для binary traces добавлен анализатор на штатном QEMU simpletrace:
[trace-analysis](docs/experiments/trace-analysis.md). Его synthetic tests не являются
записью с гостя.

## Регрессии и ограничения

Обязательные проверки перечислены в `integration/integration-test-plan.md` и
`integration/acceptance-checklist.md`. В частности: off vs pristine pixels/IRQ,
on vs off, malformed DMA, reset/BH, shutdown, migration и повторные старты.
**Ни одна guest-регрессия здесь не запускалась.**

В checked path: 64 MiB на слой, RAW32, прежнее распознавание ARGB/BGRA, без
decompression. На каждый кадр выделяется snapshot; это цена надёжной публикации,
не оптимизированный renderer. DATA_END semantics пока неизвестны, пределы
обеспечиваются layout/address cap и DART. Ограничения framebuffer/VMState самого
upstream не устранены. GPU queues/fences/shaders отсутствуют.

## Откат

Сначала перезапустить с флагом off. Для удаления кода — в интеграционной ветке
`git revert PATCH2 PATCH1`, подставив сохранённые реальные SHA после git am.
Не делать reset --hard поверх изменений команды. При конфликте остановиться
и разобрать diff. Полное обратное применение обеих исходных patches к чистой
копии проверено; изменения после интеграции могут потребовать ручного ревью.

Восстановление независимого репозитория из поставки:

```sh
git clone levelx-iphone-gpu-engine.bundle levelx-iphone-gpu-engine
cd levelx-iphone-gpu-engine
git switch feature/levelx-gpu
```

Bundle содержит всю нашу историю, main и feature/levelx-gpu; отдельный upstream
Inferno clone получается по указанному URL/SHA. Основная команда выполняет merge
только после своей сборки, тестов и ревью.
