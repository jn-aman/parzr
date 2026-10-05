// A single bounded, offline llama.cpp context. No server, downloads or telemetry.
#include "llama.h"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include <malloc/malloc.h>
#import <Foundation/Foundation.h>
#import <NaturalLanguage/NaturalLanguage.h>

namespace {
using Clock = std::chrono::steady_clock;
void shutdown();
struct Runtime {
    std::mutex mutex;
    std::condition_variable wake;
    std::atomic<uint64_t> epoch{0};
    llama_model *model = nullptr;
    llama_context *context = nullptr;
    std::string path;
    Clock::time_point last = Clock::now();
    Runtime() {
        llama_log_set([](ggml_log_level, const char *, void *) {}, nullptr);
        llama_backend_init();
        // Sleeping timer releases weights and KV state; no polling or idle inference.
        std::thread([this] {
            std::unique_lock lock(mutex);
            for (;;) {
                if (!model) wake.wait(lock, [this] { return model != nullptr; });
                else wake.wait_until(lock, last + std::chrono::seconds(30));
                if (model && Clock::now() - last >= std::chrono::seconds(30)) release();
            }
        }).detach();
    }
    void release() {
        if (context) llama_free(context);
        if (model) llama_model_free(model);
        context = nullptr; model = nullptr; path.clear();
        malloc_zone_pressure_relief(nullptr, 0);
    }
    bool load(const char *file) {
        if (model && path == file) return true;
        release();
        auto mp = llama_model_default_params();
        mp.load_mode = LLAMA_LOAD_MODE_MMAP;
        mp.n_gpu_layers = -1;
        mp.use_extra_bufts = false;
        model = llama_model_load_from_file(file, mp);
        if (!model) return false;
        auto cp = llama_context_default_params();
        cp.n_ctx = 4096; cp.n_batch = 512; cp.n_ubatch = 128;
        cp.n_seq_max = 1; cp.n_threads = 2; cp.n_threads_batch = 2;
        cp.no_perf = true;
        context = llama_init_from_model(model, cp);
        if (!context) { release(); return false; }
        path = file;
        // Register after llama/Metal's lazily initialized globals so their destruction
        // happens after model buffers are released. Re-registration after reload is safe.
        std::atexit(shutdown);
        return true;
    }
};
// Retained until process exit, so the sleeping timer never references a destroyed mutex.
Runtime &runtime() { static auto *value = new Runtime; return *value; }
void shutdown() {
    auto &r = runtime();
    r.epoch.fetch_add(1);
    std::lock_guard lock(r.mutex);
    r.release();
}
char *copy(const std::string &s) {
    auto *p = static_cast<char *>(std::malloc(s.size() + 1));
    if (p) std::memcpy(p, s.c_str(), s.size() + 1);
    return p;
}
struct Abort {
    Runtime &runtime;
    uint64_t epoch;
    Clock::time_point deadline;
    bool stopped() const { return runtime.epoch.load() != epoch || Clock::now() >= deadline; }
};
}
extern "C" void parzr_model_cancel() { runtime().epoch.fetch_add(1); }
extern "C" void parzr_model_string_free(char *value) { std::free(value); }
// The same OS language hints for the app, browser host and LSP. This does not load weights.
extern "C" char *parzr_model_token_hints(const char *input) {
    if (!input) return nullptr;
    @autoreleasepool {
        NSString *text = [[NSString alloc] initWithUTF8String:input];
        if (!text) return nullptr;
        NLTagger *tagger = [[NLTagger alloc] initWithTagSchemes:@[NLTagSchemeLexicalClass, NLTagSchemeLemma, NLTagSchemeNameType]];
        tagger.string = text;
        NSMutableArray *hints = [NSMutableArray array];
        [tagger enumerateTagsInRange:NSMakeRange(0, text.length) unit:NLTokenUnitWord scheme:NLTagSchemeLexicalClass options:NLTaggerOmitWhitespace | NLTaggerOmitPunctuation usingBlock:^(NLTag tag, NSRange range, BOOL *) {
            NSString *word = [text substringWithRange:range];
            NLTag name = [tagger tagAtIndex:range.location unit:NLTokenUnitWord scheme:NLTagSchemeNameType tokenRange:nil];
            NSString *lemma = [tagger tagAtIndex:range.location unit:NLTokenUnitWord scheme:NLTagSchemeLemma tokenRange:nil] ?: word.lowercaseString;
            BOOL named = ([name isEqualToString:NLTagPersonalName] || [name isEqualToString:NLTagPlaceName] || [name isEqualToString:NLTagOrganizationName]) && [word rangeOfCharacterFromSet:NSCharacterSet.uppercaseLetterCharacterSet].location != NSNotFound;
            [hints addObject:@{@"start_utf16":@(range.location), @"end_utf16":@(NSMaxRange(range)), @"pos":tag ?: @"Other", @"lemma":lemma, @"name":@(named)}];
        }];
        NSData *data = [NSJSONSerialization dataWithJSONObject:hints options:0 error:nil];
        if (!data) return nullptr;
        return copy(std::string(static_cast<const char *>(data.bytes), data.length));
    }
}
// Empty output is a failure, never interpreted as a clean passage.
extern "C" char *parzr_model_generate(const char *file, const char *prompt) {
    if (!file || !prompt) return nullptr;
    auto &r = runtime();
    const auto epoch = r.epoch.load();
    std::unique_lock lock(r.mutex);
    struct Idle {
        Runtime &r;
        ~Idle() { r.last = Clock::now(); r.wake.notify_one(); }
    } idle{r};
    if (r.epoch.load() != epoch) return nullptr;
    Abort abort{r, epoch, Clock::now() + std::chrono::seconds(20)};
    try {
        if (!r.load(file) || abort.stopped()) return nullptr;
        const auto *vocab = llama_model_get_vocab(r.model);
        std::vector<llama_token> tokens(4096);
        int count = llama_tokenize(vocab, prompt, int(std::strlen(prompt)), tokens.data(), int(tokens.size()), true, true);
        if (count <= 0 || count > 2048) return nullptr;
        llama_memory_clear(llama_get_memory(r.context), true);
        llama_set_abort_callback(r.context, [](void *p) { return static_cast<Abort *>(p)->stopped(); }, &abort);
        struct Clear {
            Runtime &r;
            ~Clear() {
                llama_set_abort_callback(r.context, nullptr, nullptr);
                llama_memory_clear(llama_get_memory(r.context), true);
                r.last = Clock::now();
                r.wake.notify_one();
            }
        } clear{r};
        for (int offset = 0; offset < count; offset += 512) {
            if (abort.stopped()) return nullptr;
            auto batch = llama_batch_get_one(tokens.data() + offset, std::min(512, count - offset));
            if (llama_decode(r.context, batch) != 0) return nullptr;
        }
        auto *sampler = llama_sampler_init_greedy();
        struct FreeSampler { llama_sampler *p; ~FreeSampler() { llama_sampler_free(p); } } free{sampler};
        std::string output;
        for (int i = 0; i < 2048 && count + i < 4096; ++i) {
            if (abort.stopped()) return nullptr;
            auto token = llama_sampler_sample(sampler, r.context, -1);
            if (llama_vocab_is_eog(vocab, token)) return copy(output);
            char piece[256];
            auto size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, false);
            if (size < 0 || size > int(sizeof(piece))) return nullptr;
            output.append(piece, size);
            if (output.size() > 65536) return nullptr;
            if (llama_decode(r.context, llama_batch_get_one(&token, 1)) != 0) return nullptr;
        }
    } catch (...) { return nullptr; }
    return nullptr;
}
