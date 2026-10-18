#include "filter.hpp"

std::size_t filter_records(const Record* input, std::size_t count,
                           Record* output, const Query& query) {
    std::size_t matched = 0;
    for (std::size_t i = 0; i < count; ++i) {
        const Record& r = input[i];
        if (query.begin <= r.timestamp && r.timestamp < query.end &&
            r.latency_us >= query.min_latency_us &&
            (r.flags & query.required_flags) == query.required_flags) {
            output[matched++] = r;
        }
    }
    return matched;
}
