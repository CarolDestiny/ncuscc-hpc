#pragma once
#include "support.hpp"
#include <cstddef>

// Stable filter. Input/output must not overlap; output has room for count records.
// count == 0 permits null pointers. Query validity is the caller's responsibility.
std::size_t filter_records(const Record* input, std::size_t count,
                           Record* output, const Query& query);
