# Level X iPhone GPU Engine — 0.1.0 preliminary

Отдельный репозиторий исследований и переносимых компонентов графики для
Inferno/T8030. **Полноценный A13 GPU и Metal пока не реализованы.**

Сделано: pinned source audit, карта DisplayPipe/DART, переносимый C-модуль
проверки памяти и DMA scanout, минимальная software-операция, автоматические
тесты, два opt-in патча Inferno, исходники собственного iOS Metal Probe,
база готовых технологий и анализатор на штатном QEMU simpletrace.

Проверено на Windows x64/MSVC: 9 групп C-тестов, AddressSanitizer, 1960 граничных
комбинаций, 1000 повторных lifecycle-циклов; применение и откат обоих патчей на
точном baseline, совпадение перенесённого C-кода с протестированным. Также прошли
9 групп на GCC и 5 проверок trace reader. **Inferno aarch64-softmmu с двумя патчами
скомпилирован и слинкован на Windows; 4 CLI registration checks PASS.**
Штатный configure/install workflow требует исправной symbolic-link среды;
использованный compile-only обход описан в [build report](docs/experiments/windows-build.md).
**Реализация устройства в VM, MMIO/DART/IRQ, iOS и Metal: NOT RUN.**

```sh
python tools/test.py --report reports/local-unit.json
python tools/test.py --sanitize --report reports/local-asan.json
```

Windows: установленный Visual Studio C++ Build Tools + Windows SDK (скрипт
находит их через vswhere). Linux/macOS: `cc`, Python 3.10+, libc;
команды для этих платформ подготовлены, здесь не выполнялись.

Начните с [отчёта о готовности](reports/STATUS.md),
[архитектуры](GPU-ARCHITECTURE.md) и [интеграции](INTEGRATION.md).
Контракт C API: [scanout-api](docs/interfaces/scanout-api.md).
Гостевой тест: [MetalProbe](tests/integration/ios/README.md).
Готовые решения и решения об адаптации: [REUSABLE-TECHNOLOGIES](REUSABLE-TECHNOLOGIES.md).
Проверка целостности: `python tools/verify_manifest.py`.
GitHub Actions workflow подготовлен; фактическое исполнение CI проверяется отдельно.

## Передача

Рабочая ветка: `feature/levelx-gpu`; `main` содержит стартовую страницу проекта.
История полная для **этого независимого репозитория**. Это не fork
с полной историей QEMU. Патчи в `patches/inferno/` построены относительно точного
upstream SHA, поэтому историю upstream переносить искусственно не требуется.
Рядом с репозиторием экспортируются source ZIP и Git bundle с полной его историей.
Архив исходников не содержит build outputs, Apple firmware, дисков и ключей.

Приватный baseline Level X пока не предоставлен. Автоматического merge в основной
движок не выполнялось. Репозиторий: [5Header-ai/Level-X](https://github.com/5Header-ai/Level-X).
Из-за сбоя локального Git HTTPS transport публикация выполняется через GitHub API:
логические этапы сохраняются отдельными commits, original tree SHA проверяется.
Original local commits сохраняются в ветке `archive/local-development` в Git bundle; remote commits имеют
новые IDs и trailer `Original-local-commit`. Основная команда принимает изменения
через review; merge в production не выполняется.

Лицензии: [LICENSES.md](LICENSES.md). Никакой связи или одобрения со стороны
Apple, QEMU или ChefKiss не заявляется.
