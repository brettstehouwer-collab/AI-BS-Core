#include <windows.h>
#include <stdint.h>
#include <stdbool.h>

#define AIBS_SHM_MAGIC 0xA1B51996
#define AIBS_SHM_NAME L"Local\\AI_BS_IPC_SHM_RING"
#define AIBS_RING_SLOTS 64
#define AIBS_SLOT_PAYLOAD_SIZE 60
#define AIBS_SHM_TOTAL_SIZE 4224

#pragma pack(push, 1)

typedef struct {
    uint16_t topic_id;
    uint8_t flags;
    uint8_t seq;
    uint8_t payload[AIBS_SLOT_PAYLOAD_SIZE];
} RingSlotMultiTopic;

typedef struct {
    uint32_t magic;
    uint32_t version;
    volatile uint64_t head;
    volatile uint64_t tail;
    volatile uint64_t total_pushed;
    volatile uint64_t total_popped;
    uint8_t padding[24];
    RingSlotMultiTopic slots[AIBS_RING_SLOTS];
} ShmRingBufferMultiTopic;

#pragma pack(pop)

static HANDLE g_hMapFile = NULL;
static ShmRingBufferMultiTopic* g_pRing = NULL;
static uint8_t g_seqCounter = 0;

#ifdef __cplusplus
extern "C" {
#endif

__declspec(dllexport) int aibs_shm_init(const wchar_t* shm_name) {
    if (g_pRing != NULL) {
        return 0; // Already initialized
    }

    const wchar_t* target_name = (shm_name != NULL && shm_name[0] != L'\0') ? shm_name : AIBS_SHM_NAME;

    g_hMapFile = CreateFileMappingW(
        INVALID_HANDLE_VALUE,
        NULL,
        PAGE_READWRITE,
        0,
        AIBS_SHM_TOTAL_SIZE,
        target_name
    );

    if (g_hMapFile == NULL) {
        return -1;
    }

    g_pRing = (ShmRingBufferMultiTopic*)MapViewOfFile(
        g_hMapFile,
        FILE_MAP_ALL_ACCESS,
        0,
        0,
        AIBS_SHM_TOTAL_SIZE
    );

    if (g_pRing == NULL) {
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
        return -2;
    }

    // Interlocked check / init magic
    if (g_pRing->magic != AIBS_SHM_MAGIC) {
        g_pRing->magic = AIBS_SHM_MAGIC;
        g_pRing->version = 2;
        g_pRing->head = 0;
        g_pRing->tail = 0;
        g_pRing->total_pushed = 0;
        g_pRing->total_popped = 0;
    }

    return 0;
}

__declspec(dllexport) int aibs_shm_push(uint16_t topic_id, uint8_t flags, const uint8_t* data, uint32_t len) {
    if (g_pRing == NULL) {
        return -1;
    }

    uint64_t head = g_pRing->head;
    uint64_t tail = g_pRing->tail;

    // Check full
    if ((head - tail) >= AIBS_RING_SLOTS) {
        return -2; // Ring buffer full / backpressure
    }

    uint32_t slot_idx = (uint32_t)(head % AIBS_RING_SLOTS);
    RingSlotMultiTopic* slot = &g_pRing->slots[slot_idx];

    slot->topic_id = topic_id;
    slot->flags = flags;
    slot->seq = g_seqCounter++;

    uint32_t copy_len = (len < AIBS_SLOT_PAYLOAD_SIZE) ? len : AIBS_SLOT_PAYLOAD_SIZE;
    
    // Fast memory copy
    for (uint32_t i = 0; i < copy_len; ++i) {
        slot->payload[i] = data[i];
    }
    for (uint32_t i = copy_len; i < AIBS_SLOT_PAYLOAD_SIZE; ++i) {
        slot->payload[i] = 0;
    }

    MemoryBarrier();
    g_pRing->head = head + 1;
    InterlockedIncrement64((volatile LONG64*)&g_pRing->total_pushed);

    return 0;
}

__declspec(dllexport) int aibs_shm_pop(uint16_t* out_topic_id, uint8_t* out_flags, uint8_t* out_seq, uint8_t* out_data, uint32_t max_len, uint32_t* out_actual_len) {
    if (g_pRing == NULL) {
        return -1;
    }

    uint64_t head = g_pRing->head;
    uint64_t tail = g_pRing->tail;

    if (tail >= head) {
        return -2; // Ring buffer empty
    }

    uint32_t slot_idx = (uint32_t)(tail % AIBS_RING_SLOTS);
    RingSlotMultiTopic* slot = &g_pRing->slots[slot_idx];

    if (out_topic_id) *out_topic_id = slot->topic_id;
    if (out_flags) *out_flags = slot->flags;
    if (out_seq) *out_seq = slot->seq;

    uint32_t copy_len = (max_len < AIBS_SLOT_PAYLOAD_SIZE) ? max_len : AIBS_SLOT_PAYLOAD_SIZE;
    if (out_data) {
        for (uint32_t i = 0; i < copy_len; ++i) {
            out_data[i] = slot->payload[i];
        }
    }
    if (out_actual_len) {
        *out_actual_len = copy_len;
    }

    MemoryBarrier();
    g_pRing->tail = tail + 1;
    InterlockedIncrement64((volatile LONG64*)&g_pRing->total_popped);

    return 0;
}

__declspec(dllexport) void aibs_shm_get_stats(uint64_t* out_head, uint64_t* out_tail, uint64_t* out_pushed, uint64_t* out_popped) {
    if (g_pRing == NULL) {
        if (out_head) *out_head = 0;
        if (out_tail) *out_tail = 0;
        if (out_pushed) *out_pushed = 0;
        if (out_popped) *out_popped = 0;
        return;
    }
    if (out_head) *out_head = g_pRing->head;
    if (out_tail) *out_tail = g_pRing->tail;
    if (out_pushed) *out_pushed = g_pRing->total_pushed;
    if (out_popped) *out_popped = g_pRing->total_popped;
}

__declspec(dllexport) int aibs_shm_close(void) {
    if (g_pRing != NULL) {
        UnmapViewOfFile(g_pRing);
        g_pRing = NULL;
    }
    if (g_hMapFile != NULL) {
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
    }
    return 0;
}

#ifdef __cplusplus
}
#endif
