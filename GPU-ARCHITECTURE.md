# Level X GPU Backend: карта и границы доказательств

Дата: 2026-10-14. Baseline: `cc4302a99167abec69b714cfd00c38caece7e7de`.
Это предварительное исследование исходников. Полный аппаратный протокол A13
не восстановлен; уровни приёмки 1–5 целиком пока не заявляются.

## Что подтверждено исходниками

`t8030_create_display()` в
[t8030.c](https://github.com/ChefKissInc/Inferno/blob/cc4302a99167abec69b714cfd00c38caece7e7de/hw/arm/apple-silicon/t8030.c#L2109)
создаёт DisplayPipe v4, получает SID из `arm-io/dart-disp0/mapper-disp0/reg`,
передаёт `apple_dart_iommu_mr()` и подключает MMIO/IRQ из DeviceTree.
Физический base = `armio_base + disp0.reg[0]`; размер окна = `disp0.reg[1]`.
Числовые AIC interrupt IDs и абсолютный base в этом коде не зашиты.
Без конкретного DT для 18A5351d их нельзя честно назвать.

[DisplayPipe v4](https://github.com/ChefKissInc/Inferno/blob/cc4302a99167abec69b714cfd00c38caece7e7de/hw/display/apple_displaypipe_v4.c)
читает готовые пиксели через `dma_memory_read`, создаёт Pixman image, выполняет
`PIXMAN_OP_SRC` и обновляет QemuConsole. Два GP, ограниченная поддержка layer0;
положения, полноценное смешивание и compressed buffers не реализованы полностью.
Сжатый кадр явно отбрасывается. Это scanout/compositing, не выполнение шейдеров.

`adp_v4_update_vram_mapping()` размещает конечный framebuffer в конце VRAM;
он также используется при boot/verbose display. Наша интеграция сохраняет его
и не добавляет framebuffer-устройство поверх существующего.

### Карта относительных MMIO существующей модели

| Offset | Реализованное поведение |
|---|---|
| `0x45818` | INT_STATUS, запись очищает указанные биты (W1C) |
| `0x4581c` | INT_ENABLE, маска IRQ |
| `0x46020` | CONTROL_VERSION возвращает `0x70045` |
| `0x4602c`, bit12 | Запрос обновления через QEMU BH |
| `0x4603c` | width << 16 \| height |
| `0x50000`, `0x58000` | GP0/GP1, размер блока `0x8000` |
| GP + `0x04` | RUN bit0, ENABLED bit31; бит18 назван USE_DMA |
| GP + `0x1c` | Pixel format; bit30 — compressed path, который отбрасывается |
| GP + `0x30`, `0x40` | Layer0 DATA_START / DATA_END; DATA_END хранится, но baseline не использует его для bounds |
| GP + `0x60` | Stride в байтах |
| GP + `0x70` | Source width/height packed 16/16 |
| GP + `0x80` | Destination width/height packed 16/16 |
| `0x60014`, `0x60018` | Blend layer config read/write; полноценного blend execution нет |
| `+0x200000` | В callback вычитается этот offset для shadow-обращений |

Это описание **эмулятора**, не независимо подтверждённая спецификация Apple.
Полный список деклараций REG32 и их строки генерируется в
`reports/baseline-audit.json`; наличие декларации не означает реализации регистра.

Есть 9 выходных IRQ, но `adp_v4_update_irqs()` управляет только IRQ0:
`(int_status & int_enable) != 0`. `gfx_update` устанавливает OUTPUT_READY bit10;
display BH — FRAME_PROCESSED bit20 даже если слой не отрисован.
Назначения остальных IRQ в upstream-комментариях предположительны.
FRAME_PROCESSED не является подтверждением Metal fence или успешной GPU-команды.
Патч не переопределяет эту семантику и не создаёт новые аппаратные IRQ.

### DART и память

[dart.c](https://github.com/ChefKissInc/Inferno/blob/cc4302a99167abec69b714cfd00c38caece7e7de/hw/arm/apple-silicon/dart.c)
создаёт IOMMUMemoryRegion для SID. В реализации: 16 streams, 38-bit VA region,
page-size из DT, ветви для 4/16 KiB; TTBR/PTE walk, permission bits и fault IRQ.
PARAMS `0x00/04`, TLB_OP `0x20`, ERROR_STATUS `0x40`, ERROR_ADDRESS `0x50/54`,
SID_CONFIG от `0x100`, TTBR от `0x200` по формуле из исходника.
Это не доказательство полноты DART: в коде есть TODO по bypass и закомментированная
миграция. Проверка реальной DART translation пока NOT RUN.

Новый модуль не дублирует page walker: принимает callback и работает с тем же
AddressSpace. Проверяется размер, арифметическое переполнение, 32-bit диапазон
DATA_START в адаптере и результат каждого DMA chunk. Физические host pointers
никогда не формируются из guest IOVA. Разбиение на 4 KiB — ограничение размера
transfer callback, не утверждение о реальной page size DART/GPU.

## Что требуется для Metal и чего пока нет

На уровне API Metal предоставляет device, resources, pipelines и command queues;
завершение command buffer устанавливает границу видимости результатов для CPU.
Это отражено в [документации Apple](https://developer.apple.com/library/archive/documentation/Miscellaneous/Conceptual/MetalProgrammingGuide/Mem-Obj/Mem-Obj.html).
IOSurface отвечает за совместное использование поверхностей; наличие IOSurface
или CoreAnimation/UI не устанавливает наличие рабочего AGX.

Рабочая гипотеза для исследования iOS 14: Metal/userspace AGX ↔ kernel
AGX/IOGPUFamily ↔ аппаратные очереди/память/синхронизация ↔ GPU. CoreAnimation
использует результаты графики и дисплейный путь. Точные user-client ABI,
firmware/interface revision, GPU VA layout и submission packets для A13 в
18A5351d в этой работе не установлены. Открытый XNU описывает IOKit DMA и
memory descriptors, но просмотренный source tree не предоставляет AGX/IOGPUFamily
драйверы, позволяющие вывести полный контракт.

[Asahi AGX notes](https://asahilinux.org/docs/hw/soc/agx/) описывают UAT,
firmware channels, work queues, microsequences и completion stamps в исследуемой
ими платформе Apple Silicon. Эти сведения полезны как перечень вопросов;
их UAT, адреса, поколения, firmware ABI и размеры нельзя автоматически переносить
на A13/iOS 14. **DART display mapping и GPU UAT — не взаимозаменяемые понятия.**

Для настоящего исполнения нужны подтверждённые: устройство/DT/MMIO/IRQ,
initialization и power/reset sequence, GPU mappings, packets/context ownership,
fence/fault/cancellation semantics, texture/tile/compression formats, shader ISA
или корректное преобразование программ, renderer и синхронизация с display.
Ни Vulkan, ни OpenGL сами этот промежуток не реализуют.

## Модульная архитектура

```text
Stock iOS driver
    │  AGX hardware protocol — UNKNOWN / BLOCKED
    ▼
A. Guest adapter (будущий; новые MMIO/IRQ пока не добавляются)
    ▼
B. Validated operations + resource lifetime + synchronization (будущий)
    ▼
C. Host executor: software first; Vulkan/OpenGL after protocol proof
    ▼
D. Existing DisplayPipe / DART / Pixman / QemuConsole
         └─ opt-in Level X checked scanout (реализован как source patch)
```

Текущий переносимый компонент C — `LXGSnapshot`: bounded allocation,
transactional DMA copy, reset/free, host-only rect fill. Нет Apple opcodes,
эмуляции очередей или ложного `MTLDevice`. Нативное диагностическое приложение
отдельно проверяет фактическую работу compute и render/readback.

| Host backend | Возможная роль | Решение сейчас |
|---|---|---|
| Software/Pixman | Прозрачный эталон пикселей, воспроизводимость, работает без GPU API | Сохранён baseline compositor; собственный raw32 fill протестирован |
| Vulkan | Потенциальные compute/graphics queues, barriers, host acceleration | Отложен до декодера; зависимости/Windows driver пока не нужны |
| OpenGL | Возможный более простой raster executor | Отложен; не решает compute/Apple shader и coherency protocol |
| apple-gfx/reims-vgpu | Apple paravirtual GPU на другой платформе | Не переносим как A13 device; иной guest driver |

Решение: двигаться от трасс и проверенных контрактов. Альтернатива — собственный
guest paravirtual driver и API translation — меняет гостевой стек и не удовлетворяет
требованию совместимости неизменённых iOS/AGX автоматически. До такого изменения
нужен отдельный архитектурный выбор команды, а не незаметная подмена устройства.

## Следующие доказательства

Нужны source-only Level X baseline, несекретная карта DT (reg/interrupts/SID),
OS build и идентификаторы драйверов, MMIO/DMA/fault traces с собственной диагностикой.
Сначала доказать один submission, memory mapping и completion без рисования;
потом реальную проверяемую операцию. Не копировать неизвестные mailbox ACK
из другой iOS-версии и не объявлять успех только по наличию UI.
