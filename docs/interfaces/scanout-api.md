# Host API v1

`include/levelx_scanout.h` — полный контракт. C11, libc, никаких сторонних библиотек.
Zero-initialize `LXGSnapshot`; предоставьте allocator/free одной семьи и callback
DMA read. Callback обязан сообщать ошибку при неполном чтении. В QEMU он использует
уже настроенный DART AddressSpace, а не глобальную физическую память.

`lxg_validate` ограничивает width/height 16384, stride кратен 4 и не превышает
INT_MAX, размер не превосходит лимит, диапазон inclusive address_max не переполняется.
Adapter задаёт 64 MiB на слой и UINT32_MAX для существующего DATA_START.
Это защитные лимиты host, не заявленные аппаратные лимиты A13.

`lxg_snapshot_read` сначала строит отдельный snapshot и публикует его только после
всех успешных чтений. При ошибке прежний snapshot остаётся неизменным. Запрещено
предъявлять его как результат неудачной операции. Пик памяти равен старому размеру
плюс новому; для двух GP до трёх 64-MiB buffers суммарно при последовательной замене,
не считая framebuffer/Pixman. В QEMU при ошибке buf_len остаётся нулевым.

`lxg_snapshot_reset` идемпотентен и освобождает память через allocator, которым
она была получена. `lxg_fill_rect` работает только с host snapshot, проверяет
границы и сохраняет padding. Формат RAW32 хранит четыре непреобразованных байта.

Calls сериализуются владельцем. Нет потоков, fences, MMIO, GPU command queue,
DMA write, zero-copy mapping или callback после возврата. Guest RAM может меняться
между chunks: quiescence/fence — обязанность вызывающего аппаратного слоя.
Транзакционная публикация предотвращает частичный host-кадр при ошибке, но не
гарантирует аппаратную атомарность чтения одновременно изменяемой гостем памяти.

В adapter используется прежняя синхронная BH/display execution context. Флаг
`levelx-checked-scanout` не включён в VMState и должен совпадать на обоих концах
миграции; миграция и QEMU lifecycle остаются NOT RUN. Существующие VMState layout
и framebuffer не меняются.
