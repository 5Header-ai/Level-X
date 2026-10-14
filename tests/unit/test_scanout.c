/* SPDX-License-Identifier: MIT */
#include "levelx_scanout.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #x); exit(1); \
} } while (0)

typedef struct {
    size_t live, allocations, frees;
    int fail_alloc, fail_read;
    size_t reads;
    uint64_t base;
    uint8_t page0[4096], page1[4096];
} Fixture;

static void *allocate(void *opaque, size_t size)
{
    Fixture *f = opaque;
    if (f->fail_alloc) return NULL;
    void *p = malloc(size);
    CHECK(p);
    f->allocations++;
    f->live++;
    memset(p, 0xCD, size);
    return p;
}

static void release(void *opaque, void *p)
{
    Fixture *f = opaque;
    CHECK(f->live > 0);
    f->live--;
    f->frees++;
    free(p);
}

/* Two discontiguous host pages model callback-owned IOVA translation. This
 * tests our transfer contract, not the real DART page-table walker. */
static int read_dma(void *opaque, uint64_t addr, void *dst, size_t size)
{
    Fixture *f = opaque;
    f->reads++;
    CHECK(size && size <= 4096u - (size_t)(addr & 4095u));
    if (f->fail_read && f->reads == (size_t)f->fail_read) {
        memset(dst, 0xEE, size); /* Partial write before fault must not publish. */
        return -1;
    }
    if (addr < f->base || addr - f->base >= 8192u ||
        size > 8192u - (size_t)(addr - f->base)) return -1;
    size_t off = (size_t)(addr - f->base);
    const uint8_t *p = off < 4096u ? f->page0 + off : f->page1 + off - 4096u;
    memcpy(dst, p, size);
    return 0;
}

static Fixture fixture(void)
{
    Fixture f = {0};
    f.base = 0x2000;
    memset(f.page0, 0x31, sizeof(f.page0));
    memset(f.page1, 0x72, sizeof(f.page1));
    return f;
}

static LXGAllocator allocator(Fixture *f)
{
    LXGAllocator a = {f, allocate, release};
    return a;
}

static LXGLayout valid_layout(void)
{
    LXGLayout l = {0x2000, 8, 4, 40, LXG_RAW32};
    return l;
}

static const LXGLimits limits = {UINT32_MAX, LXG_DEFAULT_MAX_BYTES};

static void test_validation(void)
{
    LXGLayout l = valid_layout();
    size_t n = 123;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_OK && n == 160);
    CHECK(lxg_validate(NULL, &limits, &n) == LXG_INVALID && n == 0);
    CHECK(lxg_validate(&l, NULL, &n) == LXG_INVALID);
    CHECK(lxg_validate(&l, &limits, NULL) == LXG_INVALID);
    LXGLimits zero = {0, 0};
    CHECK(lxg_validate(&l, &zero, &n) == LXG_INVALID);
    l.format = (LXGFormat)99;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_UNSUPPORTED);
    l = valid_layout(); l.width = 0;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l = valid_layout(); l.height = 0;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l = valid_layout(); l.width = LXG_MAX_DIMENSION + 1;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l = valid_layout(); l.height = UINT32_MAX;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l = valid_layout(); l.stride = 28;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l.stride = 33;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l.stride = 0xFFFFFFFCu;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS);
    l = valid_layout(); l.height = 16384; l.stride = 0x100000;
    CHECK(lxg_validate(&l, &limits, &n) == LXG_BOUNDS); /* 32-bit product wrap */
}

static void test_address_edges(void)
{
    LXGLayout l = {UINT32_MAX - 3u, 1, 1, 4, LXG_RAW32};
    LXGLimits lim = {UINT32_MAX, 4};
    size_t n;
    CHECK(lxg_validate(&l, &lim, &n) == LXG_OK && n == 4);
    l.iova++;
    CHECK(lxg_validate(&l, &lim, &n) == LXG_BOUNDS);
    l.iova = UINT64_MAX - 3u; lim.address_max = UINT64_MAX;
    CHECK(lxg_validate(&l, &lim, &n) == LXG_OK);
    l.iova++;
    CHECK(lxg_validate(&l, &lim, &n) == LXG_BOUNDS);
    l.iova = 0; lim.max_bytes = 3;
    CHECK(lxg_validate(&l, &lim, &n) == LXG_BOUNDS);
    l.iova = 100; lim.max_bytes = 4; lim.address_max = 99;
    CHECK(lxg_validate(&l, &lim, &n) == LXG_BOUNDS);
}

static void test_dma_transaction(void)
{
    Fixture f = fixture();
    LXGAllocator a = allocator(&f);
    LXGSnapshot s = {0};
    LXGLayout l = {0x2FFC, 2, 1, 8, LXG_RAW32};
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_OK);
    CHECK(s.size == 8 && f.reads == 2 && f.live == 1);
    CHECK(s.data[0] == 0x31 && s.data[3] == 0x31 && s.data[4] == 0x72);
    uint8_t *old = s.data;
    f.reads = 0; f.fail_read = 2;
    memset(f.page0, 0x99, sizeof(f.page0));
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_DMA_ERROR);
    CHECK(s.data == old && s.data[0] == 0x31 && f.live == 1);
    f.fail_read = 0; f.fail_alloc = 1; f.reads = 0;
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_NO_MEMORY);
    CHECK(s.data == old && f.live == 1 && f.reads == 0);
    f.fail_alloc = 0;
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_OK);
    CHECK(s.data[0] == 0x99 && f.live == 1);
    lxg_snapshot_reset(&s);
    lxg_snapshot_reset(&s);
    lxg_snapshot_reset(NULL);
    CHECK(!s.data && !s.size && !f.live && f.allocations == f.frees);
}

static void test_rejection_without_side_effects(void)
{
    Fixture f = fixture();
    LXGAllocator a = allocator(&f);
    LXGSnapshot s = {0};
    LXGLayout l = valid_layout();
    CHECK(lxg_snapshot_read(NULL, &l, &limits, &a, read_dma, &f) == LXG_INVALID);
    CHECK(lxg_snapshot_read(&s, &l, &limits, NULL, read_dma, &f) == LXG_INVALID);
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, NULL, &f) == LXG_INVALID);
    a.release = NULL;
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_INVALID);
    a = allocator(&f); l.width = UINT32_MAX;
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_BOUNDS);
    l = valid_layout(); l.format = (LXGFormat)0;
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_UNSUPPORTED);
    CHECK(f.allocations == 0 && f.reads == 0 && !s.data);
    l = valid_layout(); l.iova = 0x9000;
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_DMA_ERROR);
    CHECK(!s.data && !f.live);
}

static void test_reset_and_repeat(void)
{
    Fixture f = fixture();
    LXGAllocator a = allocator(&f);
    LXGSnapshot s = {0};
    LXGLayout l = valid_layout();
    for (unsigned i = 0; i < 1000; ++i) {
        l.height = 1u + i % 8u;
        CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_OK);
        CHECK(s.size == l.height * l.stride && f.live == 1);
        if (i % 3u == 0) lxg_snapshot_reset(&s);
    }
    lxg_snapshot_reset(&s);
    CHECK(f.live == 0 && f.allocations == 1000 && f.frees == 1000);
}

static void test_allocator_ownership(void)
{
    Fixture f = fixture(), g = fixture();
    LXGAllocator a = allocator(&f), b = allocator(&g);
    LXGLayout l = valid_layout();
    LXGSnapshot s = {0};
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_OK);
    CHECK(lxg_snapshot_read(&s, &l, &limits, &b, read_dma, &g) == LXG_OK);
    CHECK(f.live == 0 && g.live == 1);
    lxg_snapshot_reset(&s);
    CHECK(g.live == 0);
}

static void test_fill_scene(void)
{
    Fixture f = fixture();
    LXGAllocator a = allocator(&f);
    LXGSnapshot s = {0};
    LXGLayout l = valid_layout();
    const uint8_t pixel[4] = {0x11, 0x22, 0x33, 0xFF};
    CHECK(lxg_snapshot_read(&s, &l, &limits, &a, read_dma, &f) == LXG_OK);
    CHECK(lxg_fill_rect(&s, 2, 1, 4, 2, pixel) == LXG_OK);
    /* Verify every pixel and every padding byte against independent coordinates. */
    for (unsigned y = 0; y < 4; ++y) {
        for (unsigned byte = 0; byte < 40; ++byte) {
            unsigned x = byte / 4u;
            uint8_t expected = (y >= 1 && y <= 2 && x >= 2 && x <= 5)
                               ? pixel[byte % 4u] : 0x31;
            CHECK(s.data[y * 40u + byte] == expected);
        }
    }
    uint8_t saved[160]; memcpy(saved, s.data, sizeof(saved));
    CHECK(lxg_fill_rect(&s, UINT32_MAX, 0, 1, 1, pixel) == LXG_BOUNDS);
    CHECK(lxg_fill_rect(&s, 7, 0, 2, 1, pixel) == LXG_BOUNDS);
    CHECK(lxg_fill_rect(&s, 0, 0, UINT32_MAX, 1, pixel) == LXG_BOUNDS);
    CHECK(lxg_fill_rect(&s, 8, 4, 0, 0, pixel) == LXG_OK);
    CHECK(memcmp(saved, s.data, sizeof(saved)) == 0);
    CHECK(lxg_fill_rect(&s, 0, 0, 1, 1, NULL) == LXG_INVALID);
    CHECK(lxg_fill_rect(&s, 0, 0, 2, 1, s.data + 48) == LXG_OK);
    CHECK(memcmp(s.data, pixel, 4) == 0 && memcmp(s.data + 4, pixel, 4) == 0);
    s.size--;
    CHECK(lxg_fill_rect(&s, 0, 0, 1, 1, pixel) == LXG_BOUNDS);
    lxg_snapshot_reset(&s);
    CHECK(lxg_fill_rect(&s, 0, 0, 1, 1, pixel) == LXG_INVALID);
}

static void test_boundary_matrix(void)
{
    const uint32_t widths[] = {0,1,2,828,16384,16385,UINT32_MAX};
    const uint32_t heights[] = {0,1,2,1792,16384,16385,UINT32_MAX};
    const uint32_t strides[] = {0,1,4,8,3312,65536,0x7FFFFFFC,0xFFFFFFFC};
    const uint64_t addresses[] = {0,0x2000,UINT32_MAX-3u,UINT32_MAX,UINT64_MAX};
    for (size_t w = 0; w < sizeof(widths)/sizeof(*widths); ++w)
    for (size_t h = 0; h < sizeof(heights)/sizeof(*heights); ++h)
    for (size_t p = 0; p < sizeof(strides)/sizeof(*strides); ++p)
    for (size_t a = 0; a < sizeof(addresses)/sizeof(*addresses); ++a) {
        LXGLayout l = {addresses[a],widths[w],heights[h],strides[p],LXG_RAW32};
        size_t n = 0;
        LXGStatus st = lxg_validate(&l, &limits, &n);
        if (st == LXG_OK) {
            CHECK(n && n <= limits.max_bytes);
            CHECK(l.width && l.height && l.width <= 16384 && l.height <= 16384);
            CHECK(l.stride % 4 == 0 && l.stride / 4 >= l.width);
            CHECK(n / l.height == l.stride);
            CHECK(l.iova <= UINT32_MAX && (uint64_t)n <= (UINT64_C(1)<<32)-l.iova);
        } else CHECK(n == 0);
    }
}

int main(void)
{
    test_validation(); puts("PASS validation");
    test_address_edges(); puts("PASS address_edges");
    test_dma_transaction(); puts("PASS dma_transaction");
    test_rejection_without_side_effects(); puts("PASS rejection_without_side_effects");
    test_reset_and_repeat(); puts("PASS reset_and_repeat_1000");
    test_allocator_ownership(); puts("PASS allocator_ownership");
    test_fill_scene(); puts("PASS software_fill_scene");
    test_boundary_matrix(); puts("PASS boundary_matrix_1960");
    CHECK(strcmp(lxg_status_string(LXG_DMA_ERROR), "DMA read failed") == 0);
    CHECK(strcmp(lxg_status_string((LXGStatus)999), "unknown status") == 0);
    puts("PASS status_strings");
    return 0;
}
