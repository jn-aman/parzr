// C interface of Parzr's Rust writing engine (engine/src/lib.rs), as linked into the iOS app and
// keyboard. The iOS build is rules-only (cargo --no-default-features): no native model runtime,
// so tone modes return the rule fixes plus a warning, and the app writes tone rewrites with Apple
// Foundation Models instead.
#ifndef PARZR_ENGINE_H
#define PARZR_ENGINE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/// Runs one engine request (JSON, see EngineRequest in mac/Sources/ParzrCore/Models.swift) and
/// returns a JSON RewriteResult or {"error": "..."}. Free the result with parzr_string_free.
char *parzr_rewrite_json(const char *input);

/// Checks a rewrite written outside the engine (Apple Foundation Models) with the engine's tone
/// meaning guard. Input: {"mode","source","output","source_tokens"?,"output_tokens"?}. Output:
/// {"ok":bool,"output":string,"reason"?:string} or {"error":string}. Free with parzr_string_free.
char *parzr_tone_guard_json(const char *input);

/// Frees a string returned by the engine. NULL is ignored.
void parzr_string_free(char *ptr);

/// Cancels an in-flight model call. A no-op in the rules-only build.
void parzr_cancel_rewrite(void);

/// 1 when `word` is a reviewed misspelling (teh, recieved, alot), else 0.
int32_t parzr_is_known_misspelling(const char *word);

/// The pinned model manifest compiled into the engine, as JSON. Free with parzr_string_free.
char *parzr_model_manifest(void);

#ifdef __cplusplus
}
#endif

#endif
