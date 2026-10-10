#ifndef BACKSCRIPT_RUNTIME_H
#define BACKSCRIPT_RUNTIME_H

#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

typedef enum { BS_NULL, BS_NUMBER, BS_BOOL, BS_STRING, BS_ARRAY, BS_OBJECT } BSKind;
typedef struct BSValue BSValue;
typedef struct { size_t length, capacity; BSValue *items; } BSArray;
typedef struct { size_t length, capacity; char **keys; BSValue *values; } BSObject;
struct BSValue {
    BSKind kind;
    double number;
    int boolean;
    char *string;
    BSArray *array;
    BSObject *object;
};

typedef struct BSAllocation { void *pointer; struct BSAllocation *next; } BSAllocation;
static BSAllocation *bs_allocations;

static inline _Noreturn void bs_error(const char *message) {
    fprintf(stderr, "BackScript runtime error: %s\n", message);
    exit(1);
}
static inline void bs_cleanup(void) {
    while (bs_allocations) {
        BSAllocation *next = bs_allocations->next;
        free(bs_allocations->pointer);
        free(bs_allocations);
        bs_allocations = next;
    }
}
static inline void bs_init(void) {
    if (atexit(bs_cleanup) != 0) bs_error("cannot initialize memory cleanup");
}
static inline void *bs_allocate(size_t count, size_t width) {
    if (width && count > SIZE_MAX / width) bs_error("allocation size overflow");
    void *pointer = calloc(count ? count : 1, width);
    BSAllocation *entry = malloc(sizeof(*entry));
    if (!pointer || !entry) {
        free(pointer);
        free(entry);
        bs_error("out of memory");
    }
    entry->pointer = pointer;
    entry->next = bs_allocations;
    bs_allocations = entry;
    return pointer;
}
static inline void *bs_resize(void *pointer, size_t count, size_t width) {
    if (!pointer) return bs_allocate(count, width);
    if (width && count > SIZE_MAX / width) bs_error("allocation size overflow");
    BSAllocation *entry = bs_allocations;
    while (entry && entry->pointer != pointer) entry = entry->next;
    if (!entry) bs_error("invalid runtime allocation");
    void *resized = realloc(pointer, count * width);
    if (!resized) bs_error("out of memory");
    entry->pointer = resized;
    return resized;
}
static inline size_t bs_capacity(size_t current, size_t required) {
    size_t capacity = current ? current : 4;
    while (capacity < required) {
        if (capacity > SIZE_MAX / 2) bs_error("collection size overflow");
        capacity *= 2;
    }
    return capacity;
}
static inline BSValue bs_null(void) { BSValue value = {0}; return value; }
static inline BSValue bs_number(double number) {
    BSValue value = bs_null(); value.kind = BS_NUMBER; value.number = number; return value;
}
static inline BSValue bs_bool(int boolean) {
    BSValue value = bs_null(); value.kind = BS_BOOL; value.boolean = !!boolean; return value;
}
static inline BSValue bs_string_n(const char *text, size_t length) {
    if (length == SIZE_MAX) bs_error("string size overflow");
    BSValue value = bs_null(); value.kind = BS_STRING;
    value.string = bs_allocate(length + 1, 1);
    memcpy(value.string, text, length);
    return value;
}
static inline BSValue bs_string(const char *text) { return bs_string_n(text, strlen(text)); }
static inline const char *bs_text(BSValue value) {
    if (value.kind != BS_STRING) bs_error("expected string");
    return value.string;
}
static inline double bs_num(BSValue value) {
    if (value.kind != BS_NUMBER) bs_error("expected number");
    return value.number;
}
static inline void bs_finite(double number) {
    if (!isfinite(number)) bs_error("expected finite number");
}
static inline double bs_range_next(double cursor, double step) {
    double next = cursor + step;
    if (!isfinite(next) || next == cursor) bs_error("range cannot advance with this step");
    return next;
}
static inline size_t bs_index(BSValue value, size_t limit, int allow_end) {
    double number = bs_num(value);
    if (!isfinite(number) || number < 0 || floor(number) != number ||
        (allow_end ? number > (double)limit : number >= (double)limit))
        bs_error("index out of range or not an integer");
    return (size_t)number;
}
static inline BSArray *bs_array(BSValue value) {
    if (value.kind != BS_ARRAY) bs_error("expected array");
    return value.array;
}
static inline BSObject *bs_object(BSValue value) {
    if (value.kind != BS_OBJECT) bs_error("expected object");
    return value.object;
}
static inline BSValue bs_array_from(size_t count, const BSValue *items) {
    BSValue value = bs_null(); value.kind = BS_ARRAY;
    value.array = bs_allocate(1, sizeof(BSArray));
    value.array->length = count;
    value.array->capacity = count;
    value.array->items = bs_allocate(count, sizeof(BSValue));
    if (count) memcpy(value.array->items, items, count * sizeof(BSValue));
    return value;
}
static inline int bs_truthy(BSValue value) {
    switch (value.kind) {
        case BS_BOOL: return value.boolean;
        case BS_NUMBER: return value.number != 0;
        case BS_STRING: return value.string[0] != '\0';
        case BS_ARRAY: return value.array->length != 0;
        case BS_OBJECT: return value.object->length != 0;
        case BS_NULL: return 0;
    }
    return 0;
}
static inline BSValue bs_equal(BSValue left, BSValue right) {
    if (left.kind != right.kind) return bs_bool(0);
    switch (left.kind) {
        case BS_NULL: return bs_bool(1);
        case BS_NUMBER: return bs_bool(left.number == right.number);
        case BS_BOOL: return bs_bool(left.boolean == right.boolean);
        case BS_STRING: return bs_bool(strcmp(left.string ? left.string : "", right.string ? right.string : "") == 0);
        case BS_ARRAY: return bs_bool(left.array == right.array);
        case BS_OBJECT: return bs_bool(left.object == right.object);
    }
    return bs_bool(0);
}
static inline BSValue bs_not_equal(BSValue left, BSValue right) {
    return bs_bool(!bs_equal(left, right).boolean);
}
static inline BSValue bs_not(BSValue value) { return bs_bool(!bs_truthy(value)); }
static inline BSValue bs_and(BSValue left, BSValue right) { return bs_bool(bs_truthy(left) && bs_truthy(right)); }
static inline BSValue bs_or(BSValue left, BSValue right) { return bs_bool(bs_truthy(left) || bs_truthy(right)); }
static inline BSValue bs_string_convert(BSValue value) {
    char buffer[64];
    switch (value.kind) {
        case BS_STRING: return value;
        case BS_NUMBER: snprintf(buffer, sizeof(buffer), "%.15g", value.number); return bs_string(buffer);
        case BS_BOOL: return bs_string(value.boolean ? "true" : "false");
        case BS_NULL: return bs_string("null");
        default: bs_error("string conversion expects a scalar");
    }
    return bs_null();
}
static inline BSValue bs_add(BSValue left, BSValue right) {
    if (left.kind != BS_STRING && right.kind != BS_STRING)
        return bs_number(bs_num(left) + bs_num(right));
    const char *a = bs_text(bs_string_convert(left)), *b = bs_text(bs_string_convert(right));
    size_t n = strlen(a), m = strlen(b);
    if (m >= SIZE_MAX - n) bs_error("string size overflow");
    char *text = bs_allocate(n + m + 1, 1);
    memcpy(text, a, n); memcpy(text + n, b, m);
    BSValue value = bs_null(); value.kind = BS_STRING; value.string = text; return value;
}
static inline BSValue bs_subtract(BSValue a, BSValue b) { return bs_number(bs_num(a) - bs_num(b)); }
static inline BSValue bs_multiply(BSValue a, BSValue b) { return bs_number(bs_num(a) * bs_num(b)); }
static inline BSValue bs_divide(BSValue a, BSValue b) {
    double denominator = bs_num(b);
    if (denominator == 0) bs_error("division by zero");
    return bs_number(bs_num(a) / denominator);
}
static inline BSValue bs_mod(BSValue a, BSValue b) {
    double denominator = bs_num(b);
    if (denominator == 0) bs_error("modulo by zero");
    return bs_number(fmod(bs_num(a), denominator));
}
#define BS_COMPARE(name, operator) \
    static inline BSValue bs_##name(BSValue a, BSValue b) { return bs_bool(bs_num(a) operator bs_num(b)); }
BS_COMPARE(greater, >)
BS_COMPARE(less, <)
BS_COMPARE(greater_equal, >=)
BS_COMPARE(less_equal, <=)
#undef BS_COMPARE
#define BS_MATH_UNARY(name, operation) \
    static inline BSValue bs_##name(BSValue value) { return bs_number(operation(bs_num(value))); }
BS_MATH_UNARY(abs, fabs)
BS_MATH_UNARY(floor, floor)
BS_MATH_UNARY(ceil, ceil)
BS_MATH_UNARY(round, round)
#undef BS_MATH_UNARY
static inline BSValue bs_sqrt(BSValue value) {
    double number = bs_num(value);
    if (number < 0) bs_error("sqrt expects a nonnegative number");
    return bs_number(sqrt(number));
}
static inline BSValue bs_min(BSValue a, BSValue b) { return bs_number(fmin(bs_num(a), bs_num(b))); }
static inline BSValue bs_max(BSValue a, BSValue b) { return bs_number(fmax(bs_num(a), bs_num(b))); }
static inline BSValue bs_power(BSValue a, BSValue b) {
    double result = pow(bs_num(a), bs_num(b));
    if (!isfinite(result)) bs_error("power result is outside the finite numeric domain");
    return bs_number(result);
}
static inline BSValue bs_get(BSValue value, BSValue index) {
    BSArray *array = bs_array(value); return array->items[bs_index(index, array->length, 0)];
}
static inline BSValue bs_setat(BSValue value, BSValue index, BSValue item) {
    BSArray *array = bs_array(value); array->items[bs_index(index, array->length, 0)] = item; return value;
}
static inline BSValue bs_push(BSValue value, BSValue item) {
    BSArray *array = bs_array(value);
    if (array->length == SIZE_MAX) bs_error("array size overflow");
    if (array->length == array->capacity) {
        array->capacity = bs_capacity(array->capacity, array->length + 1);
        array->items = bs_resize(array->items, array->capacity, sizeof(BSValue));
    }
    array->items[array->length++] = item;
    return value;
}
static inline BSValue bs_pop(BSValue value) {
    BSArray *array = bs_array(value);
    if (!array->length) bs_error("pop from empty array");
    return array->items[--array->length];
}
static inline BSValue bs_length(BSValue value) {
    if (value.kind == BS_STRING) return bs_number((double)strlen(value.string));
    if (value.kind == BS_ARRAY) return bs_number((double)value.array->length);
    if (value.kind == BS_OBJECT) return bs_number((double)value.object->length);
    bs_error("length expects string, array, or object"); return bs_null();
}
static inline size_t bs_key_index(BSObject *object, const char *key) {
    for (size_t i = 0; i < object->length; i++)
        if (strcmp(object->keys[i], key) == 0) return i;
    return object->length;
}
static inline BSValue bs_set_property(BSValue value, BSValue key_value, BSValue item) {
    BSObject *object = bs_object(value);
    const char *key = bs_text(key_value);
    size_t index = bs_key_index(object, key);
    if (index == object->length) {
        if (object->length == SIZE_MAX) bs_error("object size overflow");
        if (object->length == object->capacity) {
            object->capacity = bs_capacity(object->capacity, index + 1);
            object->keys = bs_resize(object->keys, object->capacity, sizeof(char *));
            object->values = bs_resize(object->values, object->capacity, sizeof(BSValue));
        }
        object->keys[index] = key_value.string;
        object->length++;
    }
    object->values[index] = item; return value;
}
static inline BSValue bs_object_from(size_t count, const BSValue *items) {
    BSValue value = bs_null(); value.kind = BS_OBJECT;
    value.object = bs_allocate(1, sizeof(BSObject));
    for (size_t i = 0; i < count; i++) bs_set_property(value, items[i * 2], items[i * 2 + 1]);
    return value;
}
static inline BSValue bs_property(BSValue value, BSValue key) {
    BSObject *object = bs_object(value); size_t index = bs_key_index(object, bs_text(key));
    if (index == object->length) bs_error("object property does not exist");
    return object->values[index];
}
static inline BSValue bs_has_property(BSValue value, BSValue key) {
    BSObject *object = bs_object(value);
    return bs_bool(bs_key_index(object, bs_text(key)) != object->length);
}
static inline BSValue bs_keys_length(BSValue value) { return bs_number((double)bs_object(value)->length); }
static inline BSValue bs_substring(BSValue value, BSValue start_value, BSValue count_value) {
    const char *text = bs_text(value); size_t length = strlen(text);
    size_t start = bs_index(start_value, length, 1);
    size_t count = bs_index(count_value, length - start, 1);
    return bs_string_n(text + start, count);
}
static inline BSValue bs_contains(BSValue value, BSValue query) {
    return bs_bool(strstr(bs_text(value), bs_text(query)) != NULL);
}
static inline BSValue bs_starts_with(BSValue value, BSValue query) {
    const char *text = bs_text(value), *prefix = bs_text(query);
    return bs_bool(strncmp(text, prefix, strlen(prefix)) == 0);
}
static inline BSValue bs_ends_with(BSValue value, BSValue query) {
    const char *text = bs_text(value), *suffix = bs_text(query);
    size_t n = strlen(text), m = strlen(suffix);
    return bs_bool(n >= m && strcmp(text + n - m, suffix) == 0);
}
static inline BSValue bs_change_case(BSValue value, int upper) {
    BSValue result = bs_string(bs_text(value));
    for (size_t i = 0; result.string[i]; i++) {
        unsigned char byte = (unsigned char)result.string[i];
        result.string[i] = (char)(upper ? toupper(byte) : tolower(byte));
    }
    return result;
}
static inline BSValue bs_uppercase(BSValue value) { return bs_change_case(value, 1); }
static inline BSValue bs_lowercase(BSValue value) { return bs_change_case(value, 0); }
static inline BSValue bs_trim(BSValue value) {
    const char *text = bs_text(value); size_t start = 0, end = strlen(text);
    while (start < end && isspace((unsigned char)text[start])) start++;
    while (end > start && isspace((unsigned char)text[end - 1])) end--;
    return bs_string_n(text + start, end - start);
}
static inline _Noreturn void bs_file_error(const char *operation, const char *path) {
    fprintf(stderr, "BackScript runtime error: %s '%s': %s\n", operation, path, strerror(errno));
    exit(1);
}
static inline BSValue bs_read_file(BSValue path_value) {
    const char *path = bs_text(path_value);
    FILE *file = fopen(path, "rb");
    if (!file) bs_file_error("cannot read", path);
    size_t length = 0, capacity = 4096;
    char *buffer = malloc(capacity);
    if (!buffer) { fclose(file); bs_error("out of memory"); }
    for (;;) {
        if (length == capacity) {
            if (capacity > SIZE_MAX / 2) { free(buffer); fclose(file); bs_error("file too large"); }
            capacity *= 2;
            char *grown = realloc(buffer, capacity);
            if (!grown) { free(buffer); fclose(file); bs_error("out of memory"); }
            buffer = grown;
        }
        size_t count = fread(buffer + length, 1, capacity - length, file);
        length += count;
        if (ferror(file)) { free(buffer); fclose(file); bs_file_error("cannot read", path); }
        if (feof(file)) break;
    }
    if (fclose(file) != 0) { free(buffer); bs_file_error("cannot close", path); }
    if (memchr(buffer, 0, length)) { free(buffer); bs_error("text files cannot contain NUL bytes"); }
    BSValue result = bs_string_n(buffer, length); free(buffer); return result;
}
static inline void bs_write_mode(BSValue content, BSValue path_value, const char *mode) {
    const char *path = bs_text(path_value), *text = bs_text(content);
    FILE *file = fopen(path, mode);
    if (!file) bs_file_error("cannot write", path);
    size_t length = strlen(text);
    if (fwrite(text, 1, length, file) != length) { fclose(file); bs_file_error("cannot write", path); }
    if (fclose(file) != 0) bs_file_error("cannot close", path);
}
static inline void bs_write_file(BSValue content, BSValue path) { bs_write_mode(content, path, "wb"); }
static inline void bs_append_file(BSValue content, BSValue path) { bs_write_mode(content, path, "ab"); }
static inline BSValue bs_file_exists(BSValue path_value) {
    const char *path = bs_text(path_value); struct stat info;
    if (stat(path, &info) == 0) return bs_bool(S_ISREG(info.st_mode));
    if (errno == ENOENT || errno == ENOTDIR) return bs_bool(0);
    bs_file_error("cannot inspect", path); return bs_null();
}
static inline void bs_print_depth(BSValue value, unsigned depth) {
    if (depth > 32) { fputs("...", stdout); return; }
    switch (value.kind) {
        case BS_NULL: fputs("null", stdout); break;
        case BS_NUMBER: printf("%.15g", value.number); break;
        case BS_BOOL: fputs(value.boolean ? "true" : "false", stdout); break;
        case BS_STRING: fputs(value.string, stdout); break;
        case BS_ARRAY:
            putchar('[');
            for (size_t i = 0; i < value.array->length; i++) {
                if (i) fputs(", ", stdout);
                bs_print_depth(value.array->items[i], depth + 1);
            }
            putchar(']'); break;
        case BS_OBJECT:
            putchar('{');
            for (size_t i = 0; i < value.object->length; i++) {
                if (i) fputs(", ", stdout);
                printf("%s: ", value.object->keys[i]);
                bs_print_depth(value.object->values[i], depth + 1);
            }
            putchar('}'); break;
    }
}
static inline void bs_println(BSValue value) { bs_print_depth(value, 0); putchar('\n'); }

#endif
