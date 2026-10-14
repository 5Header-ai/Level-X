# Приёмка

- [x] Точный публичный baseline SHA и VERSION.
- [x] Отдельный репозиторий и ветка feature/levelx-gpu.
- [x] Архитектура с разделением фактов и гипотез.
- [x] Переносимый C-код, unit/ASan tests и логи.
- [x] Минимальные patches, source identity и rollback проверены.
- [x] Notices и происхождение кода зафиксированы.
- [x] Исходники собственного MetalProbe.
- [x] Компиляция/линковка public baseline + 2 patches на Windows/UCRT64.
- [x] CLI registration: T8030, default-off property, trace events.
- [x] Реестр готовых технологий и тесты интеграции штатного trace reader.
- [ ] Актуальный source-only Level X baseline и локальные исправления сверены.
- [ ] Штатный configure/install workflow и сборка на целевом Level X окружении.
- [ ] QTest или согласованный реальный device harness: MMIO, DART, IRQ.
- [ ] Off path соответствует pristine при загрузке/кадрах/IRQ.
- [ ] On path корректен при malformed frame и DMA faults.
- [ ] Reset/pending BH/shutdown/migration без утечек и stale references.
- [ ] Полная карта A13 AGX init/queue/VM/fence протокола подтверждена.
- [ ] Нативный probe собран, подписан и запущен на physical/VM.
- [ ] Compute и render/readback реальные PASS в VM.
- [ ] Performance, repetitions и extended scenarios.
- [ ] Review/merge основной командой.

Нельзя повышать уровень только по C unit PASS или наличию SpringBoard.
