/* SPDX-License-Identifier: MIT */
#ifndef LEVELX_SCANOUT_H
#define LEVELX_SCANOUT_H

#include <stddef.h>
#include <stdint.h>

#define LXG_ABI_VERSION 1u
#define LXG_DEFAULT_MAX_BYTES (64u * 1024u * 1024u)
#define LXG_MAX_DIMENSION 16384u

/* Host-side API only. These values are NOT Apple register/opcode values. */
typedef enum {
    LXG_OK = 0,
    LXG_INVALID,
    LXG_UNSUPPORTED,
    LXG_BOUNDS,
    LXG_NO_MEMORY,
    LXG_DMA_ERROR
} LXGStatus;

typedef enum {
    LXG_RAW32 = 1 /* Four opaque bytes/pixel; no conversion or compression. */
} LXGFormat;

typedef struct {
    uint64_t iova;
    uint32_t width, height, stride;
    LXGFormat format;
} LXGLayout;

typedef struct {
    uint64_t address_max; /* Inclusive maximum DMA address, supplied by adapter. */
    size_t max_bytes;     /* Maximum per-frame allocation, nonzero. */
} LXGLimits;

typedef struct {
    void *opaque;
    void *(*alloc)(void *opaque, size_t size);
    void (*release)(void *opaque, void *ptr);
} LXGAllocator;

/* Return zero only if all requested bytes were read. No retained pointers. */
typedef int (*LXGRead)(void *opaque, uint64_t iova, void *dst, size_t size);

/* Zero-initialize. Treat fields as read-only; serialize calls externally.
 * No worker threads, guest queues, implicit identity mappings or IRQs. */
typedef struct {
    uint8_t *data;
    size_t size;
    LXGLayout layout;
    LXGAllocator allocator;
} LXGSnapshot;

LXGStatus lxg_validate(const LXGLayout *layout, const LXGLimits *limits,
                       size_t *required);

/* Transactional replacement: on failure the previous snapshot is unchanged.
 * Caller must not present it as the failed frame. Peak storage is the previous
 * snapshot size plus the new cap (at most 2*cap when limits are unchanged).
 * Callback chunks stop at 4 KiB boundaries (transfer granularity, NOT a DART
 * page-size assertion); the callback owns translation and access checks.
 * The guest must be quiescent or provide synchronization before this call. */
LXGStatus lxg_snapshot_read(LXGSnapshot *snapshot, const LXGLayout *layout,
                            const LXGLimits *limits,
                            const LXGAllocator *allocator,
                            LXGRead read, void *opaque);

/* Idempotent reset/destroy. All borrowed data pointers become invalid. */
void lxg_snapshot_reset(LXGSnapshot *snapshot);

/* Minimal software operation, for host-owned snapshots only. Writes the four
 * supplied bytes literally; preserves row padding and all other pixels.
 * This is NOT a guest command, Metal operation, or shader implementation. */
LXGStatus lxg_fill_rect(LXGSnapshot *snapshot, uint32_t x, uint32_t y,
                        uint32_t width, uint32_t height, const uint8_t pixel[4]);

const char *lxg_status_string(LXGStatus status);
#endif
