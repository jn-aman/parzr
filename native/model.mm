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
#include <Accelerate/Accelerate.h>
#import <Foundation/Foundation.h>
#import <NaturalLanguage/NaturalLanguage.h>
#import <AppKit/AppKit.h>
#import <CoreML/CoreML.h>
#include <dlfcn.h>

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
    // Typing checks keep the weights resident until this time (later than the usual 30 s after `last`).
    Clock::time_point keep = Clock::now();
    std::atomic<bool> resident{false};
    Clock::time_point until() const { return std::max(last + std::chrono::seconds(30), keep); }
    Runtime() {
        llama_log_set([](ggml_log_level, const char *, void *) {}, nullptr);
        llama_backend_init();
        // Sleeping timer releases weights and KV state; no polling or idle inference.
        std::thread([this] {
            std::unique_lock lock(mutex);
            for (;;) {
                if (!model) wake.wait(lock, [this] { return model != nullptr; });
                else wake.wait_until(lock, until());
                if (model && Clock::now() >= until()) release();
            }
        }).detach();
        // Under memory pressure an idle model goes at once, whatever keep-alive typing asked for; a call in
        // progress keeps it (the timer releases it later).
        auto *pressure = dispatch_source_create(DISPATCH_SOURCE_TYPE_MEMORYPRESSURE, 0, DISPATCH_MEMORYPRESSURE_WARN | DISPATCH_MEMORYPRESSURE_CRITICAL, dispatch_get_global_queue(QOS_CLASS_UTILITY, 0));
        dispatch_source_set_event_handler(pressure, ^{
            std::unique_lock lock(mutex, std::try_to_lock);
            if (lock.owns_lock() && model) { release(); keep = Clock::now(); }
        });
        dispatch_resume(pressure);
    }
    void release() {
        if (context) llama_free(context);
        if (model) llama_model_free(model);
        context = nullptr; model = nullptr; path.clear(); resident.store(false);
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
        // Four sequences share one 4096-token cache: sentence-swap variants are scored side by side (about 30 MB of
        // recurrent state and buffers per sequence); generation uses sequence 0 alone.
        cp.n_seq_max = 4; cp.kv_unified = true; cp.n_threads = 2; cp.n_threads_batch = 2;
        cp.no_perf = true;
        context = llama_init_from_model(model, cp);
        if (!context) { release(); return false; }
        path = file;
        resident.store(true);
        // Register after llama/Metal's lazily initialized globals so their destruction
        // happens after model buffers are released. Re-registration after reload is safe.
        std::atexit(shutdown);
        return true;
    }
};
// Retained until process exit, so the sleeping timer never references a destroyed mutex.
// Set once the runtime exists: its first construction initializes Metal, which can take seconds.
std::atomic<bool> constructed{false};
Runtime &runtime() {
    static auto *value = [] { auto *r = new Runtime; constructed.store(true); return r; }();
    return *value;
}
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

// Plain-text language-model scores for one-word swaps in a short window (no chat template, so these are true LM log-probabilities).
// `spans` holds 2 * count UTF-8 byte offsets [start, end) into `text`; `candidates[i]` replaces span i. For every swap:
//   left[i] = log P(first changed token of the variant | left context) - log P(first changed token of the original | left context),
//             all from ONE forward pass over the original window;
//   full[i] = log P(variant) - log P(original) over the changed tokens and up to kRight tokens after them (left and right context),
//             computed only when left[i] >= screen, else NaN. A swap whose tokens do not line up stays NaN in both.
// Flags: 1 load the model if it is not resident (explicit checks); otherwise a cold model returns 1 at once and, with flag 2, starts
// loading in the background so a later check finds it warm. Flag 4 waits for a busy runtime; otherwise a busy runtime returns 2.
// Flag 8 keeps the model resident for kTypingKeep after this call (typing), instead of the usual 30 s.
// Flag 8 also limits the call to one variant decode (the swaps with the best left scores); when others passed the screen
// it returns 5, and they stay NaN.
// Returns 0 when every swap was scored, 4 when the budget ran out first (later swaps stay NaN), 5 when typing scored only
// the most promising swaps, 1 cold, 2 busy, 3 failure.
namespace {
// A variant decode stays within one 128-token micro-batch: one more costs about as much again.
constexpr int kRight = 6, kMaxTokens = 160, kMaxOutputs = 48, kGroupTokens = 128;
constexpr auto kTypingKeep = std::chrono::seconds(180);
std::atomic<bool> warming{false};
// One background load at a time; it holds the runtime lock while loading, so checks skip (busy) rather than wait.
void startWarm(const std::string &path) {
    if (warming.exchange(true)) return;
    std::thread([path] {
        auto &rt = runtime();
        {
            std::lock_guard guard(rt.mutex);
            try {
                // One small decode after loading prepares the GPU pipelines, so the first typing check fits its budget.
                if (rt.load(path.c_str())) {
                    llama_token tokens[8];
                    const char *probe = "\nThanks, see you soon.";
                    int n = llama_tokenize(llama_model_get_vocab(rt.model), probe, int(std::strlen(probe)), tokens, 8, false, false);
                    if (n > 0 && llama_decode(rt.context, llama_batch_get_one(tokens, n)) == 0) llama_synchronize(rt.context);
                    llama_memory_clear(llama_get_memory(rt.context), true);
                }
            } catch (...) {}
            rt.last = Clock::now();
            rt.keep = std::max(rt.keep, rt.last + kTypingKeep);
        }
        rt.wake.notify_one();
        warming.store(false);
    }).detach();
}
// Log-softmax normalizer of one row of logits.
// Vectorized (Accelerate): a 248k-entry row takes well under a millisecond.
double logNormalizer(const float *row, int n) {
    thread_local std::vector<float> scratch;
    scratch.resize(size_t(n));
    float top = 0, sum = 0, shift;
    vDSP_maxv(row, 1, &top, vDSP_Length(n));
    shift = -top;
    vDSP_vsadd(row, 1, &shift, scratch.data(), 1, vDSP_Length(n));
    vvexpf(scratch.data(), scratch.data(), &n);
    vDSP_sve(scratch.data(), 1, &sum, vDSP_Length(n));
    return double(top) + std::log(double(sum));
}
// Byte offset where each token starts in the tokenized string (plus the total); empty when the pieces do not rebuild it.
std::vector<size_t> tokenOffsets(const llama_vocab *vocab, const std::vector<llama_token> &tokens, const std::string &text) {
    std::vector<size_t> at;
    size_t offset = 0;
    char piece[256];
    for (auto t : tokens) {
        at.push_back(offset);
        int n = llama_token_to_piece(vocab, t, piece, sizeof(piece), 0, false);
        if (n < 0 || offset + n > text.size() || text.compare(offset, n, piece, n) != 0) return {};
        offset += n;
    }
    if (offset != text.size()) return {};
    at.push_back(offset);
    return at;
}
std::vector<llama_token> tokenizePlain(const llama_vocab *vocab, const std::string &text) {
    std::vector<llama_token> tokens(text.size() + 8);
    int n = llama_tokenize(vocab, text.c_str(), int(text.size()), tokens.data(), int(tokens.size()), false, false);
    if (n < 0) return {};
    tokens.resize(n);
    return tokens;
}
}
extern "C" int32_t parzr_model_swap_scores(const char *file, const char *text, uint32_t count, const uint32_t *spans,
                                           const char *const *candidates, double screen, uint32_t budget_ms, uint32_t flags,
                                           double *left, double *full) {
    const double nan = std::nan("");
    if (!file || !text || !left || !full || (count && (!spans || !candidates))) return 3;
    for (uint32_t i = 0; i < count; i++) left[i] = full[i] = nan;
    const std::string window = std::string("\n") + text;  // a line start: the first word is predicted too
    // A check that may not load never pays for initializing the runtime either: that happens in the background.
    if (!(flags & 1) && !constructed.load()) {
        if (flags & 2) startWarm(file);
        return 1;
    }
    auto &r = runtime();
    const auto epoch = r.epoch.load();
    const auto started = Clock::now();
    std::unique_lock lock(r.mutex, std::defer_lock);
    if (flags & 4) lock.lock();
    else if (!lock.try_lock()) return 2;
    if (!r.model || r.path != file) {
        if (!(flags & 1)) {
            if (flags & 2) startWarm(file);
            return 1;
        }
    }
    struct Idle {
        Runtime &r;
        bool typing;
        ~Idle() {
            r.last = Clock::now();
            if (typing) r.keep = std::max(r.keep, r.last + kTypingKeep);
            r.wake.notify_one();
        }
    } idle{r, (flags & 8) != 0};
    if (r.epoch.load() != epoch) return 3;
    Abort abort{r, epoch, started + std::chrono::milliseconds(std::max<uint32_t>(budget_ms, 1))};
    try {
        if (!r.load(file)) return 3;
        if (abort.stopped()) return 4;
        const auto *vocab = llama_model_get_vocab(r.model);
        const int vocabSize = llama_vocab_n_tokens(vocab);
        const auto original = tokenizePlain(vocab, window);
        const int n = int(original.size());
        if (n < 2 || n > kMaxTokens) return 3;
        const auto offsets = tokenOffsets(vocab, original, window);
        if (offsets.empty()) return 3;
        llama_set_abort_callback(r.context, [](void *p) { return static_cast<Abort *>(p)->stopped(); }, &abort);
        struct Clear {
            Runtime &r;
            ~Clear() {
                llama_set_abort_callback(r.context, nullptr, nullptr);
                llama_memory_clear(llama_get_memory(r.context), true);
            }
        } clear{r};
        // Each swap as token edits: the variant's tokens, the first changed index and the common suffix length.
        struct Swap { std::vector<llama_token> tokens; int first = -1, suffix = 0; };
        std::vector<Swap> swaps(count);
        int earliest = n;
        for (uint32_t i = 0; i < count; i++) {
            const size_t a = size_t(spans[2 * i]) + 1, b = size_t(spans[2 * i + 1]) + 1;
            if (!candidates[i] || a >= b || b > window.size()) continue;
            const std::string variant = window.substr(0, a) + candidates[i] + window.substr(b);
            auto tokens = tokenizePlain(vocab, variant);
            const int m = int(tokens.size());
            if (m < 2 || m > kMaxTokens) continue;
            int first = 0;
            while (first < std::min(n, m) && tokens[first] == original[first]) first++;
            int suffix = 0;
            while (suffix < std::min(n, m) - first && tokens[m - 1 - suffix] == original[n - 1 - suffix]) suffix++;
            // The change must stay inside the swapped word: the tokens before it are untouched.
            if (first == 0 || first >= std::min(n, m) || offsets[first] > a) continue;
            swaps[i] = {std::move(tokens), first, suffix};
            earliest = std::min(earliest, first);
        }
        if (earliest >= n) return 0;
        // ONE pass over the original window: per-position logits give every left score and the original's own log-probs.
        std::vector<double> base(n, 0.0);
        {
            const int from = earliest - 1;
            for (int chunk = from; chunk < n - 1; chunk += kMaxOutputs) {
                // Outputs are capped per decode to bound the logits buffer; a long window repeats the (cheap) prefix.
                const int end = std::min(n, chunk + kMaxOutputs + 1);
                llama_batch batch = llama_batch_init(end, 0, 1);
                struct FreeBatch { llama_batch &b; ~FreeBatch() { llama_batch_free(b); } } freeBatch{batch};
                for (int i = 0; i < end; i++) {
                    batch.token[i] = original[i]; batch.pos[i] = i; batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0;
                    batch.logits[i] = i >= chunk && i < end - 1;
                }
                batch.n_tokens = end;
                llama_memory_clear(llama_get_memory(r.context), true);
                if (abort.stopped()) return 4;
                if (llama_decode(r.context, batch) != 0) return abort.stopped() ? 4 : 3;
                for (int i = chunk; i < end - 1; i++) {
                    const float *row = llama_get_logits_ith(r.context, i);
                    if (!row) return 3;
                    // A left score is a difference of two logits (no normalizer). The original's log-prob of a token is
                    // needed only where a swap that passed the screen is compared (its change and the tokens after it).
                    bool needed = false;
                    for (uint32_t k = 0; k < count; k++) {
                        const auto &s = swaps[k];
                        if (s.first == i + 1) left[k] = double(row[s.tokens[s.first]]) - double(row[original[s.first]]);
                        needed = needed || (s.first > 0 && s.first <= i + 1 && i + 1 < n - s.suffix + std::min(kRight, s.suffix) && left[k] >= screen);
                        needed = needed || (s.first > 0 && s.suffix > 0 && i + 1 == n - s.suffix);
                    }
                    if (needed) base[i + 1] = double(row[original[i + 1]]) - logNormalizer(row, vocabSize);
                }
            }
        }
        // Full-context variant passes, most promising first, until the budget runs out.
        std::vector<uint32_t> order;
        for (uint32_t k = 0; k < count; k++) if (swaps[k].first > 0 && std::isfinite(left[k]) && left[k] >= screen) order.push_back(k);
        // Most promising first: a high left score, and a typed word that makes the next token improbable (a slip
        // shows in what follows it: "I think the already").
        auto priority = [&](uint32_t k) { return left[k] - (swaps[k].suffix > 0 ? base[n - swaps[k].suffix] : 0.0); };
        std::sort(order.begin(), order.end(), [&](uint32_t x, uint32_t y) { return priority(x) > priority(y); });
        // Variants run side by side as separate sequences (the recurrent layers cannot share a prefix), up to
        // kSeqs per decode and kMaxOutputs logits rows, and each stops kRight tokens after its change.
        const int seqs = int(llama_n_seq_max(r.context));
        size_t next = 0;
        while (next < order.size()) {
            if (abort.stopped()) return 4;
            std::vector<uint32_t> group;
            int tokensIn = 0, outputs = 0;
            for (; next < order.size() && int(group.size()) < seqs; next++) {
                const auto &s = swaps[order[next]];
                const int end = int(s.tokens.size()) - s.suffix + std::min(kRight, s.suffix);
                if (!group.empty() && (outputs + end - s.first + 1 > kMaxOutputs || tokensIn + end > kGroupTokens)) break;
                group.push_back(order[next]); tokensIn += end; outputs += end - s.first + 1;
            }
            llama_batch batch = llama_batch_init(tokensIn, 0, 1);
            struct FreeBatch { llama_batch &b; ~FreeBatch() { llama_batch_free(b); } } freeBatch{batch};
            std::vector<int> at;  // batch index of each group member's first token
            int b = 0;
            for (size_t j = 0; j < group.size(); j++) {
                const auto &s = swaps[group[j]];
                const int end = int(s.tokens.size()) - s.suffix + std::min(kRight, s.suffix);
                at.push_back(b);
                for (int i = 0; i < end; i++, b++) {
                    batch.token[b] = s.tokens[i]; batch.pos[b] = i; batch.n_seq_id[b] = 1; batch.seq_id[b][0] = int(j);
                    batch.logits[b] = i >= s.first - 1 && i < end - 1;
                }
            }
            batch.n_tokens = b;
            llama_memory_clear(llama_get_memory(r.context), true);
            if (llama_decode(r.context, batch) != 0) return abort.stopped() ? 4 : 3;
            for (size_t j = 0; j < group.size(); j++) {
                const auto k = group[j];
                const auto &s = swaps[k];
                const int keep = std::min(kRight, s.suffix);
                const int end = int(s.tokens.size()) - s.suffix + keep, originalEnd = n - s.suffix + keep;
                double gain = 0;
                for (int i = s.first - 1; i < end - 1; i++) {
                    const float *row = llama_get_logits_ith(r.context, at[j] + i);
                    if (!row) return 3;
                    gain += double(row[s.tokens[i + 1]]) - logNormalizer(row, vocabSize);
                }
                for (int t = s.first; t < originalEnd; t++) gain -= base[t];
                full[k] = gain;
            }
            if ((flags & 8) && next < order.size()) return 5;
        }
    } catch (...) { return 3; }
    return 0;
}
// Loads the model in the background (typing paths call this so a later check finds it warm). Never blocks.
extern "C" void parzr_model_warm(const char *file) { if (file) startWarm(file); }
// 1 when the model is resident (no lock taken, so the answer may already be stale).
extern "C" int32_t parzr_model_resident(void) { return runtime().resident.load() ? 1 : 0; }

// GECToR (roberta-base, 5001 edit labels) on the Neural Engine: one static 80 token Core ML model, resident once prepared, never touching Qwen
// state. Own mutex. The first load compiles for the ANE (a few seconds, cached by the OS); later loads take well under a second.
namespace {
constexpr int kGecLength = 80, kGecLabels = 5001, kGecDetect = 2, kGecPad = 1;
struct Gec {
    std::mutex mutex;
    MLModel *model = nil;
    std::string directory;
    dispatch_source_t pressure = nullptr;
};
Gec &gec() { static auto *value = new Gec; return *value; }
void gecRelease(Gec &g) {
    g.model = nil; g.directory.clear();
    malloc_zone_pressure_relief(nullptr, 0);
}
// PARZR_GEC_DIR, else `gector` beside the Qwen model file (PARZR_MODEL_PATH), else beside this library (dist/model) or in the app's Resources/Model.
std::string gecDirectory(const char *given) {
    if (given && *given) return given;
    if (const char *env = std::getenv("PARZR_GEC_DIR"); env && *env) return env;
    NSFileManager *files = NSFileManager.defaultManager;
    NSMutableArray<NSString *> *candidates = [NSMutableArray array];
    if (const char *model = std::getenv("PARZR_MODEL_PATH"); model && *model) [candidates addObject:[[@(model) stringByDeletingLastPathComponent] stringByAppendingPathComponent:@"gector"]];
    Dl_info info;
    if (dladdr(reinterpret_cast<const void *>(&gecDirectory), &info) && info.dli_fname) {
        NSString *library = [@(info.dli_fname) stringByDeletingLastPathComponent];
        [candidates addObject:[library stringByAppendingPathComponent:@"gector"]];
        [candidates addObject:[library stringByAppendingPathComponent:@"../Resources/Model/gector"]];
    }
    for (NSString *path in candidates) if ([files fileExistsAtPath:[path stringByAppendingPathComponent:@"gector.mlmodelc"]]) return path.UTF8String;
    return candidates.count ? candidates.firstObject.UTF8String : "";
}
int32_t gecPrepare(Gec &g, const char *given) {
    const std::string directory = gecDirectory(given);
    if (g.model && g.directory == directory) return 0;
    if (directory.empty()) return 1;
    @autoreleasepool {
        NSURL *url = [NSURL fileURLWithPath:[@(directory.c_str()) stringByAppendingPathComponent:@"gector.mlmodelc"] isDirectory:YES];
        if (![url checkResourceIsReachableAndReturnError:nil]) return 2;
        auto *configuration = [MLModelConfiguration new];
        configuration.computeUnits = MLComputeUnitsCPUAndNeuralEngine;  // .all picks the GPU, which is slow here
        NSError *error = nil;
        MLModel *model = [MLModel modelWithContentsOfURL:url configuration:configuration error:&error];
        if (!model) return 3;
        g.model = model; g.directory = directory;
        if (!g.pressure) {
            g.pressure = dispatch_source_create(DISPATCH_SOURCE_TYPE_MEMORYPRESSURE, 0, DISPATCH_MEMORYPRESSURE_WARN | DISPATCH_MEMORYPRESSURE_CRITICAL, dispatch_get_global_queue(QOS_CLASS_UTILITY, 0));
            dispatch_source_set_event_handler(g.pressure, ^{ auto &now = gec(); std::lock_guard lock(now.mutex); gecRelease(now); });
            dispatch_resume(g.pressure);
        }
    }
    return 0;
}
}
extern "C" int32_t parzr_gec_prepare(const char *directory) {
    auto &g = gec();
    std::lock_guard lock(g.mutex);
    try { return gecPrepare(g, directory); } catch (...) { return 4; }
}
extern "C" void parzr_gec_release(void) {
    auto &g = gec();
    std::lock_guard lock(g.mutex);
    gecRelease(g);
}
// `ids` (count 1..80, <s> and </s> included by the caller) are padded to 80 with the pad id; the first `count` rows of the logits are written row-major as fp32.
extern "C" int32_t parzr_gec_forward(const int32_t *ids, int32_t count, float *labels, float *detect) {
    if (!ids || !labels || !detect || count < 1 || count > kGecLength) return 1;
    auto &g = gec();
    std::lock_guard lock(g.mutex);
    try {
        if (!g.model) { if (int32_t status = gecPrepare(g, nullptr)) return status; }
        @autoreleasepool {
            NSError *error = nil;
            auto *input = [[MLMultiArray alloc] initWithShape:@[@1, @(kGecLength)] dataType:MLMultiArrayDataTypeInt32 error:&error];
            if (!input) return 5;
            auto *slots = static_cast<int32_t *>(input.dataPointer);
            for (int i = 0; i < kGecLength; i++) slots[i] = i < count ? ids[i] : kGecPad;
            auto *features = [[MLDictionaryFeatureProvider alloc] initWithDictionary:@{@"input_ids": input} error:&error];
            id<MLFeatureProvider> result = features ? [g.model predictionFromFeatures:features error:&error] : nil;
            if (!result) return 6;
            // Outputs are fp16 (or fp32) and strided: read them through the strides, never as dense.
            auto copyRows = [&](NSString *name, int width, float *destination) {
                MLMultiArray *array = [result featureValueForName:name].multiArrayValue;
                if (!array || array.shape.count != 3 || array.shape[2].intValue != width || array.shape[1].intValue < count) return false;
                const long row = array.strides[1].longValue, column = array.strides[2].longValue;
                const bool half = array.dataType == MLMultiArrayDataTypeFloat16;
                if (!half && array.dataType != MLMultiArrayDataTypeFloat32) return false;
                [array getBytesWithHandler:^(const void *bytes, NSInteger) {
                    for (int t = 0; t < count; t++)
                        for (int c = 0; c < width; c++) {
                            const long at = t * row + c * column;
                            destination[size_t(t) * width + c] = half ? float(static_cast<const _Float16 *>(bytes)[at]) : static_cast<const float *>(bytes)[at];
                        }
                }];
                return true;
            };
            if (!copyRows(@"logits_labels", kGecLabels, labels) || !copyRows(@"logits_d", kGecDetect, detect)) return 7;
        }
    } catch (...) { return 4; }
    return 0;
}
