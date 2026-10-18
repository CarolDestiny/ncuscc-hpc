#include "filter.hpp"
#include <cstring>
#include <type_traits>

namespace {
// Evaluate all predicates with integer boolean operations. This avoids the
// unpredictable early-exit branches of the serial loop on mixed-hit inputs.
inline bool matches(const Record& r, const Query& q) {
    return (q.begin <= r.timestamp) & (r.timestamp < q.end) &
           (r.latency_us >= q.min_latency_us) &
           ((r.flags & q.required_flags) == q.required_flags);
}
}

std::size_t filter_records(const Record* input, std::size_t count,
                           Record* output, const Query& query) {
    static_assert(std::is_trivially_copyable<Record>::value,
                  "Contiguous copies require trivially copyable records");
    if (count == 0 || query.begin == query.end) return 0;
    std::size_t matched = 0;
    std::size_t base = 0;
    while (count - base >= 64) {
        std::uint64_t mask = 0;
        for (unsigned bit = 0; bit < 64; ++bit)
            mask |= std::uint64_t(matches(input[base + bit], query)) << bit;
        if (mask == UINT64_MAX) {
            // A whole selected block is already contiguous and in stable order.
            std::memcpy(output + matched, input + base, 64 * sizeof(Record));
            matched += 64;
        } else {
            // ctz is only called for nonzero masks; increasing bits preserve order.
            while (mask != 0) {
                const unsigned bit = static_cast<unsigned>(__builtin_ctzll(mask));
                output[matched++] = input[base + bit];
                mask &= mask - 1;
            }
        }
        base += 64;
    }
    // At most 63 records, with no vector loads or stores beyond the arrays.
    for (; base < count; ++base) {
        if (matches(input[base], query)) output[matched++] = input[base];
    }
    return matched;
}
