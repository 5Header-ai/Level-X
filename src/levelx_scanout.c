/* SPDX-License-Identifier: MIT */
#include "levelx_scanout.h"
#include <limits.h>
#include <string.h>

LXGStatus lxg_validate(const LXGLayout *layout, const LXGLimits *limits,
                       size_t *required)
{
    uint64_t bytes;
    if (required) {
        *required = 0;
    }
    if (!layout || !limits || !required || !limits->max_bytes) {
        return LXG_INVALID;
    }
    if (layout->format != LXG_RAW32) {
        return LXG_UNSUPPORTED;
    }
    if (!layout->width || !layout->height ||
        layout->width > LXG_MAX_DIMENSION ||
        layout->height > LXG_MAX_DIMENSION) {
        return LXG_BOUNDS;
    }
    /* Pixman consumes signed-int dimensions and a four-byte-aligned stride. */
    if ((layout->stride & 3u) || layout->stride > INT_MAX ||
        (uint64_t)layout->stride < (uint64_t)layout->width * 4u) {
        return LXG_BOUNDS;
    }
    bytes = (uint64_t)layout->stride * layout->height;
    if (bytes > SIZE_MAX || bytes > limits->max_bytes ||
        layout->iova > limits->address_max ||
        bytes - 1u > limits->address_max - layout->iova) {
        return LXG_BOUNDS;
    }
    *required = (size_t)bytes;
    return LXG_OK;
}

void lxg_snapshot_reset(LXGSnapshot *snapshot)
{
    if (!snapshot) {
        return;
    }
    if (snapshot->data) {
        snapshot->allocator.release(snapshot->allocator.opaque, snapshot->data);
    }
    memset(snapshot, 0, sizeof(*snapshot));
}

LXGStatus lxg_snapshot_read(LXGSnapshot *snapshot, const LXGLayout *layout,
                            const LXGLimits *limits,
                            const LXGAllocator *allocator,
                            LXGRead read, void *opaque)
{
    LXGSnapshot next = {0};
    LXGStatus status;
    size_t offset = 0;
    if (!snapshot || !allocator || !allocator->alloc ||
        !allocator->release || !read) {
        return LXG_INVALID;
    }
    status = lxg_validate(layout, limits, &next.size);
    if (status != LXG_OK) {
        return status;
    }
    next.layout = *layout;
    next.allocator = *allocator;
    next.data = allocator->alloc(allocator->opaque, next.size);
    if (!next.data) {
        return LXG_NO_MEMORY;
    }
    while (offset < next.size) {
        uint64_t addr = next.layout.iova + offset;
        size_t chunk = 4096u - (size_t)(addr & 4095u);
        if (chunk > next.size - offset) {
            chunk = next.size - offset;
        }
        if (read(opaque, addr, next.data + offset, chunk) != 0) {
            lxg_snapshot_reset(&next);
            return LXG_DMA_ERROR;
        }
        offset += chunk;
    }
    lxg_snapshot_reset(snapshot);
    *snapshot = next;
    return LXG_OK;
}

LXGStatus lxg_fill_rect(LXGSnapshot *snapshot, uint32_t x, uint32_t y,
                        uint32_t width, uint32_t height, const uint8_t pixel[4])
{
    size_t required;
    LXGLimits limits = {UINT64_MAX, SIZE_MAX};
    uint8_t value[4];
    if (!snapshot || !snapshot->data || !pixel) {
        return LXG_INVALID;
    }
    if (lxg_validate(&snapshot->layout, &limits, &required) != LXG_OK ||
        required != snapshot->size || x > snapshot->layout.width ||
        y > snapshot->layout.height || width > snapshot->layout.width - x ||
        height > snapshot->layout.height - y) {
        return LXG_BOUNDS;
    }
    /* pixel may alias the destination. Capture it before the first write. */
    memcpy(value, pixel, sizeof(value));
    for (uint32_t row = 0; row < height; ++row) {
        uint8_t *dst = snapshot->data + (size_t)(y + row) * snapshot->layout.stride
                       + (size_t)x * 4u;
        for (uint32_t col = 0; col < width; ++col) {
            memcpy(dst + (size_t)col * 4u, value, sizeof(value));
        }
    }
    return LXG_OK;
}

const char *lxg_status_string(LXGStatus status)
{
    switch (status) {
    case LXG_OK: return "ok";
    case LXG_INVALID: return "invalid argument";
    case LXG_UNSUPPORTED: return "unsupported format";
    case LXG_BOUNDS: return "layout/address outside limits";
    case LXG_NO_MEMORY: return "allocation failed";
    case LXG_DMA_ERROR: return "DMA read failed";
    default: return "unknown status";
    }
}
