# Матрица совместимости

| Возможность | Реализовано | Непосредственно проверено |
|---|---|---|
| C layout/address validation | Да | MSVC + ASan + GCC PASS |
| Bounded DMA callback snapshot | Да | Синтетические разнесённые страницы/fault PASS |
| Alloc/free/reset/re-init | Да, standalone | 1000 циклов PASS |
| Software raw32 rect fill | Да, host-only | Все пиксели и padding PASS |
| Feature flag off | В source adapter, default false | CLI property default off PASS; guest NOT RUN |
| Inferno integration patches | Да | Чистое применение, исходники и откат PASS |
| Trace MMIO/DMA | Да, source patch | Генерация заголовка штатным tracetool PASS |
| Компиляция и линковка Inferno EXE | Да, Windows UCRT64 | PASS, 1949 build steps; source diff чистый |
| Штатный configure/install tree | Зависит от symlink permissions | FAIL postconf; использован compile-only workaround |
| CLI model/property/trace registration | Да | 4 проверки PASS; это не device realization |
| Анализ binary traces | Штатный simpletrace + metadata aggregator | 5 synthetic integration tests PASS |
| QTest MMIO/IRQ | Спецификация | BLOCKED — QTest отсутствует в baseline |
| Реальный DART translation/fault IRQ | Используется существующий код | NOT RUN; callback mock не DART |
| Guest command queues/fences | Нет | BLOCKED — нет подтверждённого A13 контракта |
| AGX initialization/firmware | Нет | BLOCKED — требуется исследование |
| Vulkan/OpenGL renderer | Нет | Не запускался |
| Compressed/tiled Apple textures | Нет | Не поддерживаются |
| UIKit/SpringBoard regression | Не изменяем guest стек | NOT RUN |
| Metal device/compute/render | Исходники diagnostic app | NOT RUN; функциональность не заявляется |
| Physical iPhone 11 comparison | План и одинаковый probe | NOT RUN |
| Migration, BH shutdown, repeated VM reset | Наследуется baseline | NOT RUN |
| Коммерческие приложения | Не тестировались | Не заявляется |

Нет поддерживаемого списка Metal features: пока нет ни одного выполненного
guest-теста. Host rect fill не повышает уровень Metal совместимости.
