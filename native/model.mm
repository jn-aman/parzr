// A single bounded, offline llama.cpp context. No server, downloads or telemetry.
#include "llama.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
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
#import <AppKit/AppKit.h>

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

// The macOS spell checker knows proper names only Capitalized: "jatin" is flagged, "Jatin" is accepted, while a typo stays flagged either way.
// A lowercase word it rejects but accepts Capitalized is a name (the engine may then only re-case it). Same gate as the app's SystemLexicon.
// NSSpellChecker is not documented as thread-safe: one lock serializes every lookup. Per-word results are cached (about 2,000 words).
static BOOL parzrWordChar(unichar c) { return [NSCharacterSet.letterCharacterSet characterIsMember:c] || c == '-'; }
static BOOL parzrApostrophe(unichar c) { return c == '\'' || c == 0x2019; }
// The run of letters, hyphens and inner apostrophes around `range`.
static NSRange parzrWordRun(NSString *text, NSRange range) {
    NSUInteger start = range.location, end = NSMaxRange(range), n = text.length;
    for (;;) {
        if (start > 0 && parzrWordChar([text characterAtIndex:start - 1])) { start--; continue; }
        if (start > 1 && parzrApostrophe([text characterAtIndex:start - 1]) && parzrWordChar([text characterAtIndex:start - 2])) { start -= 2; continue; }
        break;
    }
    for (;;) {
        if (end < n && parzrWordChar([text characterAtIndex:end])) { end++; continue; }
        if (end + 1 < n && parzrApostrophe([text characterAtIndex:end]) && parzrWordChar([text characterAtIndex:end + 1])) { end += 2; continue; }
        break;
    }
    return NSMakeRange(start, end - start);
}
// Lowercase letters only (inner apostrophes and hyphens allowed), outer quotes and a possessive dropped; nil otherwise.
static NSString *parzrShaped(NSString *raw) {
    NSString *word = [raw stringByTrimmingCharactersInSet:[NSCharacterSet characterSetWithCharactersInString:@"'\u2019-"]];
    for (NSString *suffix in @[@"'s", @"\u2019s"]) if ([word hasSuffix:suffix]) word = [word substringToIndex:word.length - suffix.length];
    if (word.length < 2 || word.length > 128) return nil;
    BOOL letter = NO;
    for (NSUInteger i = 0; i < word.length; i++) {
        unichar c = [word characterAtIndex:i];
        if ([NSCharacterSet.lowercaseLetterCharacterSet characterIsMember:c]) letter = YES;
        else if (c != '-' && !parzrApostrophe(c)) return nil;
    }
    return letter ? word : nil;
}
static NSString *parzrCapitalized(NSString *word) {
    NSMutableArray *parts = [NSMutableArray array];
    for (NSString *part in [word componentsSeparatedByString:@"-"]) [parts addObject:part.length ? [[[part substringToIndex:1] uppercaseString] stringByAppendingString:[part substringFromIndex:1]] : part];
    return [parts componentsJoinedByString:@"-"];
}
// Per lowercase word of `text` (at most 1000 distinct): bit 1 the system lexicon treats it as a name, bit 2 the system spell checker rejects it.
// A word without bit 2 is accepted as spelled, so the engine never respells it.
static NSDictionary<NSString *, NSNumber *> *parzrLexiconInfo(NSString *text) {
    static std::mutex lock;
    static NSCache<NSString *, NSNumber *> *cache = [] { auto *c = [NSCache new]; c.countLimit = 2000; return c; }();
    NSMutableArray<NSString *> *tokens = [NSMutableArray array], *fresh = [NSMutableArray array];
    NSMutableSet<NSString *> *seen = [NSMutableSet set];
    NSMutableDictionary<NSString *, NSNumber *> *info = [NSMutableDictionary dictionary];
    NSUInteger at = 0, n = text.length;
    while (at < n && tokens.count < 1000) {
        if (!parzrWordChar([text characterAtIndex:at])) { at++; continue; }
        NSRange run = parzrWordRun(text, NSMakeRange(at, 1));
        at = NSMaxRange(run);
        NSString *word = parzrShaped([text substringWithRange:run]);
        if (word && [seen member:word] == nil) { [seen addObject:word]; [tokens addObject:word]; }
    }
    std::lock_guard<std::mutex> guard(lock);
    for (NSString *word in tokens) { if (![cache objectForKey:word]) [fresh addObject:word]; }
    if (fresh.count) {
        static NSInteger tag = [NSSpellChecker uniqueSpellDocumentTag];
        NSSpellChecker *checker = NSSpellChecker.sharedSpellChecker;
        NSMutableSet<NSString *> *flagged = [NSMutableSet set];
        NSUInteger found = 0;
        for (NSUInteger from = 0; from < n && found < 2000; found++) {
            NSRange r = [checker checkSpellingOfString:text startingAt:from language:@"en" wrap:NO inSpellDocumentWithTag:tag wordCount:nil];
            if (r.location == NSNotFound || r.length == 0) break;
            NSString *word = parzrShaped([text substringWithRange:r]);
            if (word) [flagged addObject:word];
            from = NSMaxRange(r);
        }
        for (NSString *word in fresh) {
            BOOL flaggedWord = [flagged containsObject:word], rejected = flaggedWord || found >= 2000; // past the scan cap nothing is known
            BOOL name = flaggedWord && [checker checkSpellingOfString:parzrCapitalized(word) startingAt:0 language:@"en" wrap:NO inSpellDocumentWithTag:tag wordCount:nil].location == NSNotFound;
            [cache setObject:@((name ? 1 : 0) | (rejected ? 2 : 0)) forKey:word];
        }
    }
    for (NSString *word in tokens) info[word] = [cache objectForKey:word];
    return info;
}
// The same OS language hints for the app, browser host and LSP. This does not load weights.
extern "C" char *parzr_model_token_hints(const char *input) {
    if (!input) return nullptr;
    @autoreleasepool {
        NSString *text = [[NSString alloc] initWithUTF8String:input];
        if (!text) return nullptr;
        NLTagger *tagger = [[NLTagger alloc] initWithTagSchemes:@[NLTagSchemeLexicalClass, NLTagSchemeLemma, NLTagSchemeNameType]];
        tagger.string = text;
        // Without an explicit language, short texts get no tags ("I met Aman Jain." yields no name).
        [tagger setLanguage:NLLanguageEnglish range:NSMakeRange(0, text.length)];
        NSMutableArray *hints = [NSMutableArray array];
        NSDictionary<NSString *, NSNumber *> *lexicon = parzrLexiconInfo(text);
        __block NSUInteger consumed = 0;
        [tagger enumerateTagsInRange:NSMakeRange(0, text.length) unit:NLTokenUnitWord scheme:NLTagSchemeLexicalClass options:NLTaggerOmitWhitespace | NLTaggerOmitPunctuation usingBlock:^(NLTag tag, NSRange range, BOOL *) {
            if (range.location < consumed) return;
            NSString *word = [text substringWithRange:range];
            NLTag name = [tagger tagAtIndex:range.location unit:NLTokenUnitWord scheme:NLTagSchemeNameType tokenRange:nil];
            NSString *lemma = [tagger tagAtIndex:range.location unit:NLTokenUnitWord scheme:NLTagSchemeLemma tokenRange:nil] ?: word.lowercaseString;
            BOOL named = ([name isEqualToString:NLTagPersonalName] || [name isEqualToString:NLTagPlaceName] || [name isEqualToString:NLTagOrganizationName]) && [word rangeOfCharacterFromSet:NSCharacterSet.uppercaseLetterCharacterSet].location != NSNotFound;
            NSUInteger end = NSMaxRange(range);
            // A lowercase word the system lexicon knows only Capitalized is a name; the hint covers the whole run ("jean-luc", "jatin's").
            if (!named && lexicon.count) {
                NSRange run = parzrWordRun(text, range);
                NSString *shaped = parzrShaped([text substringWithRange:run]);
                if (shaped && ([lexicon[shaped] intValue] & 1)) { named = YES; end = NSMaxRange(run); range = NSMakeRange(run.location, run.length); }
            }
            // The system spell checker accepts this word as spelled (absent from the table: unknown, so not known).
            NSString *plain = parzrShaped(word);
            NSNumber *mask = plain ? lexicon[plain] : nil;
            BOOL known = mask != nil && !([mask intValue] & 2);
            // The engine tokenizes "Aman's" as one word, so the name hint must cover the possessive too.
            if (named && end + 2 <= text.length && ([text characterAtIndex:end] == '\'' || [text characterAtIndex:end] == 0x2019) && [text characterAtIndex:end + 1] == 's' && (end + 2 == text.length || ![NSCharacterSet.letterCharacterSet characterIsMember:[text characterAtIndex:end + 2]])) end += 2;
            consumed = end;
            [hints addObject:@{@"start_utf16":@(range.location), @"end_utf16":@(end), @"pos":tag ?: @"Other", @"lemma":lemma, @"name":@(named), @"known":@(known)}];
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

// Log-odds log P(yes) - log P(no) that `text[start, end)` (UTF-8 byte range) is a person's name, from ONE forward pass over a short
// classification prompt (no generation). The text is cut to a window around the word. NaN on any failure, never a guess.
extern "C" double parzr_model_name_log_odds(const char *file, const char *text, unsigned start, unsigned end) {
    const double nan = std::nan("");
    if (!file || !text) return nan;
    const size_t length = std::strlen(text);
    if (start >= end || end > length || end - start > 64) return nan;
    auto &r = runtime();
    const auto epoch = r.epoch.load();
    std::unique_lock lock(r.mutex);
    struct Idle {
        Runtime &r;
        ~Idle() { r.last = Clock::now(); r.wake.notify_one(); }
    } idle{r};
    if (r.epoch.load() != epoch) return nan;
    Abort abort{r, epoch, Clock::now() + std::chrono::seconds(5)};
    try {
        // About 240 bytes either side of the word, moved to a character boundary and then past a partial word.
        size_t from = start > 240 ? start - 240 : 0, to = std::min(length, size_t(end) + 240);
        while (from < start && (text[from] & 0xC0) == 0x80) from++;
        while (to > end && to < length && (text[to] & 0xC0) == 0x80) to--;
        if (from > 0) while (from < start && text[from - 1] != ' ' && text[from - 1] != '\n') from++;
        if (to < length) while (to > end && text[to] != ' ' && text[to] != '\n') to--;
        const std::string word(text + start, end - start), window(text + from, to - from);
        // The text comes first and the question last: measured AUC 0.996 against 0.969 with the question first.
        const std::string prompt = "<|im_start|>user\nText: " + window + "\n\nIn this text, is '" + word + "' a person's name? Answer yes or no.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
        if (!r.load(file) || abort.stopped()) return nan;
        const auto *vocab = llama_model_get_vocab(r.model);
        std::vector<llama_token> tokens(1024);
        int count = llama_tokenize(vocab, prompt.c_str(), int(prompt.size()), tokens.data(), int(tokens.size()), true, true);
        if (count <= 0 || count > 512) return nan;
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
        if (llama_decode(r.context, llama_batch_get_one(tokens.data(), count)) != 0) return nan;
        const float *logits = llama_get_logits_ith(r.context, -1);
        if (!logits) return nan;
        // Each answer word is one token in this vocabulary; a spelling that is not is skipped. The shift only keeps exp() in range.
        auto mass = [&](std::initializer_list<const char *> words) {
            double sum = 0;
            for (auto *w : words) {
                llama_token t;
                if (llama_tokenize(vocab, w, int(std::strlen(w)), &t, 1, false, false) == 1) sum += std::exp(double(logits[t]) - 20.0);
            }
            return sum;
        };
        const double yes = mass({"Yes", "yes"}), no = mass({"No", "no"});
        if (!(yes > 0) || !(no > 0)) return nan;
        return std::log(yes) - std::log(no);
    } catch (...) { return nan; }
}
