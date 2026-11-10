#ifndef FURBOMEK_WINDOW_FRAME_H
#define FURBOMEK_WINDOW_FRAME_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { HeaderSize = 28 };

static unsigned int shift_for(uint32_t mask) {
    unsigned int shift = 0;
    while (mask != 0 && (mask & 1u) == 0) { mask >>= 1; ++shift; }
    return shift;
}

static unsigned char channel(uint32_t pixel, uint32_t mask) {
    if (mask == 0) return 0;
    unsigned int shift = shift_for(mask);
    return (unsigned char)(((pixel & mask) >> shift) * 255u / (mask >> shift));
}

static void put_u32(unsigned char *buffer, uint32_t value) {
    buffer[0] = (unsigned char)(value >> 24); buffer[1] = (unsigned char)(value >> 16); buffer[2] = (unsigned char)(value >> 8); buffer[3] = (unsigned char)value;
}

static void put_u64(unsigned char *buffer, uint64_t value) {
    for (int index = 7; index >= 0; --index) { buffer[index] = (unsigned char)value; value >>= 8; }
}

static void error_frame(const char *message) {
    unsigned char header[HeaderSize] = {'X', 'E', 'R', 'R', 0, 1, 0, 0};
    size_t length = strlen(message);
    if (length > 65535) length = 65535;
    put_u32(header + 8, (uint32_t)length);
    fwrite(header, sizeof(header), 1, stdout); fwrite(message, length, 1, stdout); fflush(stdout);
}
#endif
