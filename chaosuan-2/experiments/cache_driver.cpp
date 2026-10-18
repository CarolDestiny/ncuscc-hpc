// Auxiliary profiler driver. Original kernels are included unchanged.
// Initialization and FP64 correctness reference are excluded from Cachegrind.
// Correctness is checked separately by the original benchmark programs.
#define main original_gemm_main
#include "../gemm.cpp"
#undef main
#define main original_stencil_main
#include "../stencil.cpp"
#undef main
#include <valgrind/cachegrind.h>
#include <cstdlib>
#include <cstring>
#include <unistd.h>

// Optional perf-stat ROI control. perf starts disabled; acknowledgements ensure
// initialization/warmup/reset are excluded. Only user-space events are collected.
void perf_control(const char* command) {
    const char* control = std::getenv("BENCH_PERF_CONTROL_FD");
    if (!control) return;
    const int fd = std::atoi(control);
    const int ack = std::atoi(std::getenv("BENCH_PERF_ACK_FD"));
    if (::write(fd,command,std::strlen(command)) != static_cast<ssize_t>(std::strlen(command)))
        throw std::runtime_error("perf control write failed");
    char ch=0;
    do { if (::read(ack,&ch,1)!=1) throw std::runtime_error("perf ack failed"); } while(ch!='\n');
}

int main(int argc, char** argv) {
    if (argc != 5) return 2;
    const std::string kind = argv[1], impl = argv[3];
    const int n = positive(argv[2], 4096), param = positive(argv[4], 256);
    const std::size_t count = static_cast<std::size_t>(n)*n;
    std::uint32_t seed = 2026;
    std::vector<float> a(count, 0), b(count, 0), c(count, 0);
    if (kind == "gemm") {
        for (auto& v : a) v = sample(seed);
        for (auto& v : b) v = sample(seed);
        std::vector<float> at(param*param), bt(param*param), ct(param*param);
        if (std::getenv("BENCH_PERF_CONTROL_FD")) {
            if (impl == "naive") gemm_naive(a,b,c,n);
            else gemm_blocked(a,b,c,n,param,at,bt,ct);
            std::fill(c.begin(),c.end(),0.0f);
        }
        perf_control("enable\n");
        CACHEGRIND_START_INSTRUMENTATION;
        if (impl == "naive") gemm_naive(a,b,c,n);
        else gemm_blocked(a,b,c,n,param,at,bt,ct);
        CACHEGRIND_STOP_INSTRUMENTATION;
        perf_control("disable\n");
        double sum = 0; for (float v : c) sum += v;
        std::cout << "profile_checksum=" << sum << '\n';
    } else if (kind == "stencil") {
        for (int r=1; r<n-1; ++r) for (int j=1; j<n-1; ++j)
            a[static_cast<std::size_t>(r)*n+j] = sample(seed);
        if (std::getenv("BENCH_PERF_CONTROL_FD")) {
            c=a;
            for (int step=0; step<param; ++step) {
                stencil_step(a.data(),b.data(),n,n,impl=="column"); a.swap(b);
            }
            a=c; std::fill(b.begin(),b.end(),0.0f);
        }
        perf_control("enable\n");
        CACHEGRIND_START_INSTRUMENTATION;
        for (int step=0; step<param; ++step) {
            stencil_step(a.data(), b.data(), n, n, impl == "column");
            a.swap(b);
        }
        CACHEGRIND_STOP_INSTRUMENTATION;
        perf_control("disable\n");
        double sum = 0; for (float v : a) sum += v;
        std::cout << "profile_checksum=" << sum << '\n';
    } else return 2;
}
