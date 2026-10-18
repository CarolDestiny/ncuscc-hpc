#include "filter.hpp"
#include <iostream>
#include <random>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
const Record guard{UINT64_MAX, 0x12345678u, UINT32_MAX, 0xabcdef01u, 0x76543210u};
void check(const std::vector<Record>& rows, const Query& q) {
    auto input = rows;
    auto expected = reference_filter(rows, q);
    std::vector<Record> output(rows.size() + 2, guard);
    const auto count = filter_records(input.data(), input.size(), output.data(), q);
    require(count == expected.size(), "wrong count");
    for (std::size_t i = 0; i < count; ++i)
        require(equal_record(output[i], expected[i]), "wrong field/order");
    for (std::size_t i = 0; i < input.size(); ++i)
        require(equal_record(input[i], rows[i]), "input changed");
    require(equal_record(output[rows.size()], guard), "output overflow");
    require(equal_record(output[rows.size() + 1], guard), "output overflow");
}
}
int main() try {
    require(filter_records(nullptr, 0, nullptr, Query{}) == 0, "null/empty");
    const std::size_t sizes[]{0,1,2,31,32,33,63,64,65,127,128,129,
                              255,256,257,4095,4096,4097,65537};
    std::mt19937_64 rng(0xc0ffee);
    std::size_t cases = 1;
    for (auto n : sizes) {
        for (unsigned mode = 0; mode < 6; ++mode) {
            std::vector<Record> rows(n);
            for (std::size_t i = 0; i < n; ++i) {
                auto& r = rows[i];
                r = {1000 + i % 1000, static_cast<std::uint32_t>(rng()),
                     100, static_cast<std::uint32_t>(rng()), UINT32_MAX};
                if (mode == 1 || (mode == 2 && i % 2) || (mode == 3 && i % 67))
                    r.flags = 2;
                if (mode == 4) {
                    const std::uint64_t timestamps[]{0,999,1000,1999,2000,UINT64_MAX-1,UINT64_MAX};
                    r.timestamp = timestamps[i % 7];
                    r.latency_us = static_cast<std::uint32_t>(rng());
                    r.flags = static_cast<std::uint32_t>(rng());
                }
                if (mode == 5) r = {1500,7,100,UINT32_MAX,3};
            }
            for (Query q : {Query{}, Query{0,UINT64_MAX,0,0},
                            Query{1000,1000,0,0},
                            Query{UINT64_MAX-1,UINT64_MAX,UINT32_MAX,UINT32_MAX}}) {
                check(rows,q);
                ++cases;
            }
        }
    }
    for (unsigned trial = 0; trial < 600; ++trial) {
        std::vector<Record> rows(rng() % 2049);
        for (auto& r : rows)
            r = {rng(), static_cast<std::uint32_t>(rng()),
                 static_cast<std::uint32_t>(rng()), static_cast<std::uint32_t>(rng()),
                 static_cast<std::uint32_t>(rng())};
        std::uint64_t a = rng(), b = rng();
        if (a > b) std::swap(a,b);
        check(rows, Query{a,b,static_cast<std::uint32_t>(rng()),
                          trial % 3 == 0 ? 0u : static_cast<std::uint32_t>(rng() & 15)});
        ++cases;
    }
    std::cout << "API regression: " << cases << " cases PASS\n";
} catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
}
