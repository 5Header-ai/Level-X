# Готовые технологии для Level X

Проверка: 14 октября 2026. Область: A13/T8030, iOS 14 build 18A5351d,
Inferno `cc4302a99167abec69b714cfd00c38caece7e7de`, Windows/TCG.
Просмотр исходника не означает успешного исполнения. Ни один сторонний GPU
backend ниже не запускался на нашем госте. В исследованной выборке совместимая
готовая модель A13 AGX не найдена; это не утверждение об отсутствии её вообще.

Точные файлы и SHA256: [source-lock](docs/hardware/source-lock.json),
[reuse-search](docs/hardware/reuse-search.json). История основных fork:
[history-audit](docs/hardware/history-audit.json). Новые runtime зависимости
ради исследовательских кандидатов в Inferno не добавлялись.

## Использовать сейчас — существующий display path (A)

**[ChefKissInc/Inferno](https://github.com/ChefKissInc/Inferno)**,
`cc4302a99167abec69b714cfd00c38caece7e7de`.
Используем существующие DisplayPipe, DART AddressSpace, `dma_memory_read`, QOM,
BH, IRQ и Pixman. Прочитаны `apple_displaypipe_v4.c`, `dart.c`, `t8030.c`,
headers/build files. T8030 wiring подтверждён исходниками; запуск именно
18A5351d здесь NOT RUN. Зависимости GLib/Pixman/PNG/QEMU; лицензии per-file,
DisplayPipe AGPL-3.0-or-later, авторские notices сохранены.
Решение **использовать и адаптировать**: два небольших патча добавляют opt-in
bounds/snapshot и trace, сохраняя прежний default. Файлы, тесты и перенос:
[INTEGRATION](INTEGRATION.md). DART не переписывается и не называется AGX UAT.

**[Pixman](https://gitlab.freedesktop.org/pixman/pixman)**,
исследованный SHA `f227dcbe57e8fcfb5174ffd7eb55a69b6692d512`.
Просмотрены `pixman/pixman-bits-image.c`, `COPYING`: raw pixel image/compositing,
проверки stride/alignment и собственной allocation. MIT-style notices нескольких
авторов. Применим к host pixels независимо от версии iOS. При переданном `bits`
Pixman заимствует pointer и не знает фактический размер внешнего DMA buffer.
Решение **использовать уже подключённый Pixman**, без обновления на этот SHA;
не писать новый compositor. Поэтому небольшой собственный bounds/snapshot
остаётся необходимым. Его C/ASan tests выполнены; Pixman+guest regression NOT RUN.
Новых скопированных Pixman файлов нет.

**[LZFSE](https://github.com/lzfse/lzfse)**,
`e634ca58b4821d9f3d560cdc6df5dec02ffc93fd`.
Существующая upstream-зависимость boot code, не GPU decoder. BSD-3-Clause,
Apple Inc.; C99, libc, Make/GCC. Пакет UCRT64 не найден; поэтому **использован
оригинальный исходник без изменений** и собран в отдельном workspace MSYS2
prefix. Компиляция и установка библиотеки PASS, iOS decompression NOT RUN.
В GPU source package код не копируется. Для повторения нужен этот SHA,
`make`, затем `make install INSTALL_PREFIX=<build-prefix>`; нужен native
MinGW library и header при конфигурации Inferno.

**QEMU tracing**, тот же Inferno SHA; upstream сравнение:
[qemu/qemu](https://github.com/qemu/qemu), tag v10.2.2,
`f8ed81651e61d9c2166df6121ce2af0f44f06b3e`.
Решение **использовать штатные tracetool и trace backends**. Новые события приняты
tracetool. Для binary simple traces использовать штатный `scripts/simpletrace.py`
из той же сборки с её `trace-events-all`, не писать ещё один binary decoder.
Реализован небольшой `tools/analyze_trace.py` на его Analyzer2 API; пять synthetic
fixture integration tests PASS, raw guest trace NOT RUN. Подключение описано
в [trace-analysis](docs/experiments/trace-analysis.md).
У simpletrace GPL-2.0; он не копируется в MIT-модуль. Python нужен только tooling.
QTest из другого QEMU не добавляется одной случайной копией: pinned Inferno
удалил harness/accelerator. Восстановление требует отдельного согласованного патча.

## Fork и аппаратные исследования (B/C)

**[MakrSas/Inferno](https://github.com/MakrSas/Inferno)**,
`b76fa575831d94a80db169ffb3c76d9094a648bd`.
Изучены DisplayPipe/DART/T8030 и история, включая PCC handshake. iOS embedding
и отличающиеся гостевые версии/host assumptions; зависимости QEMU/Apple embedding.
Лицензии наследуются per-file от Inferno/QEMU. **Изучить позже** отдельные display
исправления; whole-fork replacement отклонён. Falling-edge handshake не переносится
без воспроизводимого trace на 18A5351d. Прочитанные изменения не тестировались
здесь, скопированных файлов нет; будущая адаптация отдельным patch + off/on regression.

**[den0620/QEMUAppleSilicon](https://github.com/den0620/QEMUAppleSilicon)**,
`80d84158cb42889f8f3b07bb98c6e449f8e588c0`.
Ранние Apple SoC/DART/DisplayPipe модели и T8030 wiring, QEMU dependencies,
смешанные исходные GPL/LGPL/per-file notices. **Изучить позже** как сравнительный
источник регистров: файлы отличаются от baseline; совпадение функций не доказывает
совместимость поведения. Самостоятельного подтверждения GPU/Metal нет. Перенос
возможен только минимальными hunks после теста регистров/DMA/reset, сейчас 0 файлов.

**[Apple XNU](https://github.com/apple-oss-distributions/xnu)**,
`bb611c8fecc755a0d8e56e2fa51513527c5b7a0e` (7195.50.7.100.1).
IOKit/IODMACommand и kernel memory interfaces полезны для терминов, lifecycle
и требований к DMA. Этот tag не тождествен build 18A5351d; полного AGX driver
в просмотренных исходниках нет. Apple build/kernel dependencies, APSL и другие
per-file licenses. **Использовать как документацию**, не переносить kernel source
в QEMU. Проверены определения и ссылки, runtime NOT RUN, файлов адаптации нет.

**[AsahiLinux/m1n1](https://github.com/AsahiLinux/m1n1)**,
`94395adce7e6f7bf781a072edb8e6e042b71f9d7`.
Прочитаны `proxyclient/m1n1/hw/{agx,uat}.py`, `agx/{__init__,render}.py`,
`fw/agx/{cmdqueue,initdata}.py`: UAT, firmware queues, stamps, resource lifetime.
Проверенные ветви относятся к M-series/G13/G14, chip IDs 8103/8112; поддержку
T8030/iOS14 они не доказывают. Нужны proxyclient, Python/construct, m1n1 и совместимое
железо/firmware. AGX файлы GPL-2.0-or-later; проект начинался с MIT и менял лицензию,
поэтому нельзя присваивать MIT всему текущему дереву. **Адаптировать идеи после
проверки A13 ABI (C)**. Сейчас reference only, 0 скопированных файлов. Следующий
тест — сопоставить захваченные layout/queue records с поколением/версией; затем
изолированный decoder fixture, а не запуск G13 firmware на A13.
Материалы: [Asahi AGX](https://asahilinux.org/docs/hw/soc/agx/).

**[Mesa/Asahi](https://gitlab.freedesktop.org/mesa/mesa)**,
`8b07f64a383f19c7002a4e97f422bbd01e9d4f54`.
Прочитаны `src/asahi/lib/{decode.c,agx_bo.h,agx_device.h}`, `docs/license.rst`.
Есть AGX command decoding, memory object interfaces, Linux DRM/Asahi device path;
decoder зависит от generated `agx_pack`, ISA disassembler и Mesa util, device path
от libdrm/asahi_drm/vdrm. Просмотренные headers/decoder MIT (Alyssa Rosenzweig,
Connor Abbott, Collabora и соответствующие file notices); у дерева лицензии разные.
**Изучить позже / адаптировать decoder при совпадении формата**. Применение на
M-series Linux не подтверждает A13 iOS driver ABI. Ни Mesa runtime, ни decoder здесь
не собирались; 0 скопированных файлов. Будущий перенос: ограниченный decoder +
generated schema, notices, known/invalid packet tests; не замена всего QEMU.
Официально: [Asahi driver](https://docs.mesa3d.org/drivers/asahi.html).

## Paravirtual GPU и host backend (B/C)

**[MakrSas/orchard-ios](https://github.com/MakrSas/orchard-ios)**,
`fab0f9f0d60acfdc2488181385ac53b7b4ea23c6`.
vmapple/macOS guest, iOS host embedding, AppleParavirtGPU/reims integration.
Зависимости платформенного wrapper и Metal/Apple frameworks, лицензии разных
компонентов требуют отдельных notices. **Изучить позже** host integration, **отклонить
как готовую T8030 модель**: stock iOS14 AGX не говорит AppleParavirtGPU. Источники
изучены, собственный запуск NOT RUN. В будущей адаптации сначала отдельный backend
API и доказанный guest protocol bridge; сейчас скопированных файлов нет.

**QEMU apple-gfx**, SHA v10.2.2 указан выше. Прочитаны `hw/display/apple-gfx*`:
реализация Apple paravirtual graphics и DMA callbacks, macOS host framework
ParavirtualizedGraphics/Metal, vmapple/PCI guest path. Условия соответствующих
QEMU file headers. **Использовать как reference для lifecycle**, **отклонить прямой
перенос на Windows/T8030**. Не содержит готового AGX decoder. Здесь NOT RUN,
файлов адаптации нет; потребуется другой backend и отдельные host/guest tests.

**[steelbrain/reims-vgpu](https://github.com/steelbrain/reims-vgpu)**,
`86d492197228df29514a87c3de62b2ce59f2188f`.
Прочитаны C ABI, core page-table/mapping code и `memory_compose.rs`, manifests,
docs. AppleParavirtGPU через vmapple MMIO или PCI 106b:eeee, Rust Metal/Vulkan
backends, framebuffer writeback; guest APV page entries — u32 guest page numbers,
это не доказанная AGX UAT. README сообщает macOS13–26 на M3Max, macOS26 на
Linux/x86+RTX5080: это **результаты авторов, не наша проверка**. Rust1.98.1,
ash0.38, SDL3, metal2vulkan pinned ниже; GPL-2.0-or-later OR LGPL-3.0-or-later,
зависимости имеют собственные условия. **Изучить позже как backend (B)**;
прямая замена A13 отклонена. Взятых файлов 0. Для адаптации нужны narrow C ABI,
доказанный bridge, memory ownership/reset tests и Linux/Windows validation.

**[steelbrain/metal2vulkan](https://github.com/steelbrain/metal2vulkan)**,
`ecb80e019d54b8eb1585974fb2a6cc37bac359cc` (rev зависимости reims).
Просмотрены manifests, LICENSE, translator/runtime `lib.rs`. AIR→SPIR-V translator
и отдельный Metal-shaped Vulkan runtime, budgets/cancel API; не эмуляция AGX ISA
или аппаратных очередей. Rust1.98+, ash/Vulkan, внутренние AIR/runtime crates.
GPL-2.0-or-later OR LGPL-3.0-or-later, автор Anees Iqbal; зависимые лицензии проверять
отдельно. **Изучить позже / адаптировать**, если вход shader IR подтверждён. Не
разрабатывать такой translator с нуля до проверки этого кандидата. Здесь source
inspection only, compile/corpus/Vulkan tests NOT RUN. Переносимых файлов сейчас 0;
будущий первый тест — наш разрешённый compute shader с точным CPU oracle.

**[medfa12/apple-silicon-anyos-project](https://github.com/medfa12/apple-silicon-anyos-project)**,
`59fd73aac4ae386939bc69dc58dffbce1b2167b2`.
Исследовательский macOS26/vmapple на non-Apple ARM KVM, Metal→Vulkan/lavapipe;
просмотрены README и несколько vendor/metal2vulkan исходников. Ubuntu24.04,
KVM arm64, Rust, Vulkan loader/lavapipe. Root GPLv2 текст не определяет лицензии
всего vendor дерева; component audit не завершён. **Изучить позже (C)** для
software host fallback, **отклонить whole-QEMU replacement**. Результаты автора
здесь не воспроизведены, поддержка A13 отсутствует в изученных материалах.
Ничего не заимствовано; перенос только отдельного проверенного компонента.

**Corellium, публичные материалы**: [официальный FAQ](https://support.corellium.com/troubleshooting-faqs/general-faqs).
SHA неприменим (веб-документ, просмотр 2026-10-14). FAQ указывает ограничение Metal;
исходного совместимого backend в изученных публичных материалах нет.
**Отклонить как источник готового кода**, сохранить как сравнение заявленных
возможностей. Исходников/лицензии для заимствования не получено, runtime NOT RUN.

## Issues, открытые PR и история

- Inferno [#274](https://github.com/ChefKissInc/Inferno/issues/274): AGX/SGX остаётся
  открытой задачей в просмотренном состоянии. [#243](https://github.com/ChefKissInc/Inferno/issues/243)
  dynamic SID и [#207](https://github.com/ChefKissInc/Inferno/issues/207) s8000 DART
  не следует выдавать за готовые T8030 GPU patches.
- Inferno [PR3](https://github.com/ChefKissInc/Inferno/pull/3), head
  `c69fd074e392f0453ca1889c0bb096a2b3aac03f`, merged; исторический display fix
  затрагивает старый apple_h12p/T8030/ARM PTW. **Не применять повторно** к новой
  модели без comparison. DisplayPipe history и точные commits сохранены отдельно.
- reims [PR121](https://github.com/steelbrain/reims-vgpu/pull/121), head
  `fc93e58b06ca4864415085ff5c9c941ee0d0a89e`, open: fallback при отказе Vulkan
  host-memory import, тесты отказов. Автор сообщает RADV/macOS13, не нашу
  конфигурацию. **Изучить позже** для fallback/ownership tests; текущий reims
  переразбил crates, PR относится к другой base. Нельзя слепо cherry-pick.
- reims [PR117](https://github.com/steelbrain/reims-vgpu/pull/117), head
  `969352c791d98d96662757f61162965c8f334c92`, open: освобождение stranded work
  публикует completion даже для невыполненной операции. **Отклонить эту семантику
  для Level X**: она не удовлетворяет требованию не имитировать успешное выполнение.
  Идею явного terminal error и cleanup сохраняем, точный гостевой error ABI ещё нужен.
- reims [#71](https://github.com/steelbrain/reims-vgpu/issues/71),
  [#32](https://github.com/steelbrain/reims-vgpu/issues/32),
  [#90](https://github.com/steelbrain/reims-vgpu/issues/90): reports memory-release
  panic, WSL/Dozen crash, framebuffer corruption. Поддержка Vulkan сама по себе
  не является результатом приёмки Windows/TCG/iOS14.

## Как продолжать поиск и интеграцию

Термины проверок: AGX/SGX, AppleGPU/IOGPU, T8030/A13, AppleDisplayPipe/displaypipe,
DART/dynamic SID, UAT/TTBR, AppleParavirtGPU/AppleParavirtPageTable, PCC/doorbell,
guest RAM import, framebuffer writeback, Metal AIR/SPIR-V. Поиск ограничен
релевантными исходниками/историей; это не полный аудит всех fork или открытых PR.
Повторять при неизвестном ABI, новом blocker или перед дорогой реализацией.

Каждый новый импорт: URL + полный SHA + per-file authors/license + список файлов
адаптационный diff + тест + инструкция переноса. При несовпадении ABI сначала
fixture/эксперимент, затем интеграция. Все текущие сторонние кандидаты вне baseline
остаются ссылками; обещаний работоспособности и скрытого vendoring нет.
