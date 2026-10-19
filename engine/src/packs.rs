//! Model packs: the pinned list of downloadable model files (`engine/models.json`, compiled in) and
//! where a verified pack lives on this Mac. The app downloads a pack into
//! `~/Library/Application Support/Parzr/Models/<pack>/<version>/`, staging it beside that folder and
//! renaming the folder into place only after every file matched its SHA-256. A folder alone is
//! never trusted: the app (and scripts/model-pack.py) writes a marker, `.verified.json`, naming
//! every file's pinned hash and its identity on disk (size, inode, modification time) once its
//! SHA-256 checked out, and the engine uses a pack only while every file still has that identity.
//! A file replaced or rewritten since then makes the pack unavailable until the app verifies it
//! again.
//!
//! The marker alone is not trusted either: anyone who can write the folder can write a marker. So
//! the engine hashes each pack file itself, once per process, against the SHA-256 compiled into
//! this build, and remembers the verdict with the file's identity (including its change time,
//! which no ordinary write or `utimes` can set back). A model load waits for its own files'
//! verdicts; the availability checks every typing check makes never wait (see `available`). The
//! hashing starts on a background thread the first time the engine looks at its packs, smallest
//! files first, so the grammar and slip models are cleared long before the writing model is.
//! The engine never downloads anything.
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, HashMap},
    path::{Path, PathBuf},
    sync::{
        Condvar, Mutex, MutexGuard, OnceLock,
        atomic::{AtomicBool, Ordering},
    },
};

/// The verification marker in a version folder (hidden, so it is never one of the pack's files).
pub const MARKER: &str = ".verified.json";

/// The manifest as compiled into this build. The app reads it through `parzr_model_manifest`.
pub const MANIFEST_JSON: &str = include_str!("../models.json");

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema: u32,
    pub packs: Vec<Pack>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Pack {
    pub id: String,
    pub version: String,
    pub title: String,
    pub purpose: String,
    pub license: String,
    /// What the engine looks up in this pack: a role (`writing_model`, `grammar_model`) and the
    /// path of its file or folder inside the pack.
    pub provides: BTreeMap<String, String>,
    pub files: Vec<File>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct File {
    pub path: String,
    pub url: String,
    pub bytes: u64,
    pub sha256: String,
    pub name: String,
    pub version: String,
    pub license: String,
    pub purpose: String,
}

pub fn manifest() -> &'static Manifest {
    static MANIFEST: OnceLock<Manifest> = OnceLock::new();
    MANIFEST.get_or_init(|| {
        serde_json::from_str(MANIFEST_JSON).expect("engine/models.json is checked by its tests")
    })
}

/// `PARZR_MODELS_DIR` (tests, development; ignored without the `dev-overrides` feature), else
/// `~/Library/Application Support/Parzr/Models`.
pub fn root() -> Option<PathBuf> {
    if let Some(dir) = crate::overrides::var("PARZR_MODELS_DIR") {
        return Some(PathBuf::from(dir));
    }
    let home = std::env::var_os("HOME").filter(|h| !h.is_empty())?;
    Some(PathBuf::from(home).join("Library/Application Support/Parzr/Models"))
}

/// Set by the app while it re-hashes the installed packs at launch: until it lets go, no pack is
/// used in this process, so a file is never loaded before this run checked it.
static HOLD: AtomicBool = AtomicBool::new(false);
pub fn hold(on: bool) {
    HOLD.store(on, Ordering::SeqCst);
    if !on {
        verify_in_background();
    }
}

/// The installed file or folder that plays `role`, for loading it: its pack's verified version is
/// on disk and every file of the role hashed to its pinned SHA-256 in this process. Waits for
/// those verdicts (the first time, while the files are hashed); call it only to load a model.
pub fn installed(role: &str) -> Option<PathBuf> {
    if HOLD.load(Ordering::SeqCst) {
        return None;
    }
    verify_in_background();
    installed_in(manifest(), &root()?, role)
}
/// Whether `role` looks installed, without waiting: its pack's marker vouches for the files on
/// disk and no file of the role has failed its hash in this process (a file still being hashed
/// counts as installed; loading it through `installed` then waits for the verdict). For the cheap
/// checks a typing check makes, which must never wait for a model file to be hashed.
pub fn available(role: &str) -> Option<PathBuf> {
    if HOLD.load(Ordering::SeqCst) {
        return None;
    }
    verify_in_background();
    available_in(manifest(), &root()?, role)
}
fn installed_in(manifest: &Manifest, root: &Path, role: &str) -> Option<PathBuf> {
    let (pack, folder, path) = located(manifest, root, role)?;
    role_files(pack, role)
        .all(|f| content_verified(&folder.join(&f.path), &f.sha256))
        .then_some(path)
}
fn available_in(manifest: &Manifest, root: &Path, role: &str) -> Option<PathBuf> {
    let (pack, folder, path) = located(manifest, root, role)?;
    role_files(pack, role)
        .all(|f| known_verdict(&folder.join(&f.path), &f.sha256) != Some(false))
        .then_some(path)
}
/// The pack providing `role`, its version folder and the role's path, when the folder's marker
/// vouches for every file on disk.
fn located<'a>(
    manifest: &'a Manifest,
    root: &Path,
    role: &str,
) -> Option<(&'a Pack, PathBuf, PathBuf)> {
    manifest.packs.iter().find_map(|pack| {
        let relative = pack.provides.get(role)?;
        let folder = root.join(&pack.id).join(&pack.version);
        let path = folder.join(relative);
        (path.exists() && verified(pack, &folder)).then_some((pack, folder, path))
    })
}
/// The files a role loads: its file, or every file in its folder.
fn role_files<'a>(pack: &'a Pack, role: &str) -> impl Iterator<Item = &'a File> {
    let relative = pack.provides.get(role).map(String::as_str).unwrap_or("");
    pack.files.iter().filter(move |f| {
        f.path == relative
            || f.path
                .strip_prefix(relative)
                .is_some_and(|rest| rest.starts_with('/'))
    })
}

/// Starts hashing every installed pack's files on a background thread, once per process (not
/// while the app holds the packs). Smallest first: the grammar and slip models' files are done
/// in a fraction of a second, the writing model's file last. A model load that comes first
/// hashes its own files, or waits for the one being hashed.
pub fn verify_in_background() {
    static STARTED: OnceLock<()> = OnceLock::new();
    if HOLD.load(Ordering::SeqCst) || STARTED.get().is_some() {
        return;
    }
    STARTED.get_or_init(|| {
        let Some(root) = root() else { return };
        // A thread that cannot start leaves each load to hash its own files.
        let _ = std::thread::Builder::new()
            .name("parzr-pack-verify".into())
            .spawn(move || verify_all(manifest(), &root));
    });
}
fn verify_all(manifest: &Manifest, root: &Path) {
    let mut files: Vec<(PathBuf, &str, u64)> = manifest
        .packs
        .iter()
        .filter_map(|pack| {
            let folder = root.join(&pack.id).join(&pack.version);
            verified(pack, &folder).then(|| {
                pack.files
                    .iter()
                    .map(move |f| (folder.join(&f.path), f.sha256.as_str(), f.bytes))
            })
        })
        .flatten()
        .collect();
    files.sort_by_key(|f| f.2);
    for (path, sha256, _) in files {
        content_verified(&path, sha256);
    }
}

/// A regular file's size, inode, modification and change times: what a verdict was given for.
/// The change time moves on every write, rename or `utimes`, and an ordinary process cannot set
/// it back, so a file with the same stamp has not been touched since it was hashed.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Stamp {
    bytes: u64,
    inode: u64,
    mtime_ns: i128,
    ctime_ns: i128,
}
fn stamp_of(meta: &std::fs::Metadata) -> Option<Stamp> {
    use std::os::unix::fs::MetadataExt;
    meta.file_type().is_file().then(|| Stamp {
        bytes: meta.size(),
        inode: meta.ino(),
        mtime_ns: i128::from(meta.mtime()) * 1_000_000_000 + i128::from(meta.mtime_nsec()),
        ctime_ns: i128::from(meta.ctime()) * 1_000_000_000 + i128::from(meta.ctime_nsec()),
    })
}
fn stamp(path: &Path) -> Option<Stamp> {
    stamp_of(&std::fs::symlink_metadata(path).ok()?)
}

enum Check {
    /// Another thread is hashing the file: wait for it.
    Hashing,
    Done {
        sha256: String,
        stamp: Stamp,
        ok: bool,
    },
}
/// Each file's verdict in this process, keyed by its path.
static CHECKS: Mutex<Option<HashMap<PathBuf, Check>>> = Mutex::new(None);
static CHECKED: Condvar = Condvar::new();
fn checks() -> MutexGuard<'static, Option<HashMap<PathBuf, Check>>> {
    CHECKS.lock().unwrap_or_else(|e| e.into_inner())
}

/// This process's verdict on `path` when it has one for the file as it is now, without waiting.
fn known_verdict(path: &Path, sha256: &str) -> Option<bool> {
    let now = stamp(path)?;
    match checks().as_ref()?.get(path)? {
        Check::Done {
            sha256: pinned,
            stamp,
            ok,
        } if pinned == sha256 && *stamp == now => Some(*ok),
        _ => None,
    }
}

/// True when `path` is a regular file whose contents hash to `sha256`: decided once per process
/// for the file as it is (a file changed since gets hashed again), waiting while another thread
/// hashes it.
fn content_verified(path: &Path, sha256: &str) -> bool {
    loop {
        let Some(now) = stamp(path) else {
            return false;
        };
        let mut guard = checks();
        let map = guard.get_or_insert_with(HashMap::new);
        match map.get(path) {
            Some(Check::Hashing) => {
                drop(CHECKED.wait(guard).unwrap_or_else(|e| e.into_inner()));
                continue;
            }
            Some(Check::Done {
                sha256: pinned,
                stamp,
                ok,
            }) if pinned == sha256 && *stamp == now => {
                return *ok;
            }
            _ => {
                map.insert(path.to_path_buf(), Check::Hashing);
            }
        }
        drop(guard);
        // Clears the mark if hashing unwinds, so a waiter hashes the file itself.
        struct Unmark<'a>(&'a Path);
        impl Drop for Unmark<'_> {
            fn drop(&mut self) {
                if let Some(map) = checks().as_mut() {
                    map.remove(self.0);
                }
                CHECKED.notify_all();
            }
        }
        let unmark = Unmark(path);
        let ok = hash_matches(path, now, sha256);
        std::mem::forget(unmark);
        if let Some(map) = checks().as_mut() {
            map.insert(
                path.to_path_buf(),
                Check::Done {
                    sha256: sha256.to_string(),
                    stamp: now,
                    ok,
                },
            );
        }
        CHECKED.notify_all();
        return ok;
    }
}
/// Hashes the file at `path` when it is still the one stamped `expected` (before and after), and
/// compares the digest with the pinned one.
fn hash_matches(path: &Path, expected: Stamp, sha256: &str) -> bool {
    let Ok(mut file) = std::fs::File::open(path) else {
        return false;
    };
    // The file opened is the file stamped: not one swapped in between the two.
    if file.metadata().ok().as_ref().and_then(stamp_of) != Some(expected) {
        return false;
    }
    let digest = sha256_hex(&mut file);
    digest.as_deref() == Some(sha256) && stamp(path) == Some(expected)
}

/// The SHA-256 of what is left to read in `file`, as lowercase hex. CommonCrypto (in libSystem,
/// hardware-accelerated on Apple silicon): no new dependency for the engine.
#[cfg(target_vendor = "apple")]
fn sha256_hex(file: &mut impl std::io::Read) -> Option<String> {
    use std::ffi::c_void;
    /// CC_SHA256_CTX: two counters, eight hash words and a sixteen-word block, all 32-bit.
    #[repr(C)]
    struct Context([u32; 26]);
    #[link(name = "System")]
    unsafe extern "C" {
        fn CC_SHA256_Init(c: *mut Context) -> i32;
        fn CC_SHA256_Update(c: *mut Context, data: *const c_void, len: u32) -> i32;
        fn CC_SHA256_Final(md: *mut u8, c: *mut Context) -> i32;
    }
    const CHUNK: usize = 4 << 20;
    let mut context = Context([0; 26]);
    // SAFETY: `context` is a CC_SHA256_CTX-sized, -aligned buffer that lives for these calls.
    if unsafe { CC_SHA256_Init(&mut context) } != 1 {
        return None;
    }
    let mut buffer = vec![0u8; CHUNK];
    loop {
        let read = match file.read(&mut buffer) {
            Ok(0) => break,
            Ok(n) => n,
            Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(_) => return None,
        };
        // SAFETY: the first `read` bytes of `buffer` are initialised; `read` <= CHUNK fits a u32.
        if unsafe { CC_SHA256_Update(&mut context, buffer.as_ptr().cast(), read as u32) } != 1 {
            return None;
        }
    }
    let mut digest = [0u8; 32];
    // SAFETY: `digest` holds the 32 bytes CC_SHA256_Final writes.
    if unsafe { CC_SHA256_Final(digest.as_mut_ptr(), &mut context) } != 1 {
        return None;
    }
    Some(digest.iter().map(|b| format!("{b:02x}")).collect())
}
/// Model packs are an Apple-platform feature (the model runtimes are too): elsewhere no pack
/// file is ever verified, so none is used. The PARZR_* development overrides still work.
#[cfg(not(target_vendor = "apple"))]
fn sha256_hex(_file: &mut impl std::io::Read) -> Option<String> {
    None
}

#[derive(Deserialize)]
struct Marker {
    schema: u32,
    pack: String,
    version: String,
    files: Vec<Marked>,
}
#[derive(Deserialize)]
struct Marked {
    path: String,
    sha256: String,
    bytes: u64,
    inode: u64,
    mtime_ns: i64,
}

/// A regular file's size, inode and modification time in nanoseconds; None for anything else
/// (a symbolic link, a folder, a missing file).
fn identity(path: &Path) -> Option<(u64, u64, i64)> {
    use std::os::unix::fs::MetadataExt;
    let meta = std::fs::symlink_metadata(path).ok()?;
    if !meta.file_type().is_file() {
        return None;
    }
    let nanos = meta
        .mtime()
        .checked_mul(1_000_000_000)?
        .checked_add(meta.mtime_nsec())?;
    Some((meta.size(), meta.ino(), nanos))
}

/// The marker vouches for this pack's pinned files and every file is still the one it vouched for.
fn verified(pack: &Pack, folder: &Path) -> bool {
    let Ok(text) = std::fs::read(folder.join(MARKER)) else {
        return false;
    };
    let Ok(marker) = serde_json::from_slice::<Marker>(&text) else {
        return false;
    };
    if marker.schema != 1 || marker.pack != pack.id || marker.version != pack.version {
        return false;
    }
    pack.files.iter().all(|file| {
        marker.files.iter().any(|m| {
            m.path == file.path
                && m.sha256 == file.sha256
                && m.bytes == file.bytes
                && identity(&folder.join(&file.path)) == Some((m.bytes, m.inode, m.mtime_ns))
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn the_pinned_manifest_is_complete_and_safe() {
        let m = manifest();
        assert_eq!(m.schema, 1);
        assert!(!m.packs.is_empty());
        let mut ids = std::collections::HashSet::new();
        for pack in &m.packs {
            assert!(ids.insert(&pack.id), "pack ids are unique");
            for part in [&pack.id, &pack.version] {
                assert!(!part.is_empty() && !part.starts_with('.'));
                assert!(
                    part.chars()
                        .all(|c| c.is_ascii_alphanumeric() || "-_.".contains(c))
                );
            }
            let mut paths = std::collections::HashSet::new();
            for file in &pack.files {
                assert!(paths.insert(&file.path), "{} is listed twice", file.path);
                // Relative, inside the pack: no absolute paths, no parent references, no hidden names.
                assert!(!file.path.starts_with('/') && !file.path.contains('\\'));
                assert!(
                    file.path
                        .split('/')
                        .all(|p| !p.is_empty() && !p.starts_with('.')),
                    "{}",
                    file.path
                );
                assert!(
                    file.url
                        .starts_with("https://github.com/jn-aman/parzr/releases/download/")
                );
                assert_eq!(file.sha256.len(), 64);
                assert!(
                    file.sha256
                        .chars()
                        .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
                );
                assert!(file.bytes > 0);
                for text in [&file.name, &file.version, &file.license, &file.purpose] {
                    assert!(!text.is_empty());
                }
            }
            for relative in pack.provides.values() {
                assert!(
                    pack.files
                        .iter()
                        .any(|f| f.path == *relative || f.path.starts_with(&format!("{relative}/"))),
                    "{relative} is not in the pack"
                );
            }
        }
        // The engine's models come from a pack: the writing and grammar models, and the slip checker
        // (an optional pack of its own, so it downloads, updates and is removed separately).
        for role in ["writing_model", "grammar_model", "slip_model"] {
            assert!(m.packs.iter().any(|p| p.provides.contains_key(role)));
        }
    }
    const SHA_X: &str = "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881";
    const SHA_ABC: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    /// A small pack whose files the test writes for real (the pinned ones are hundreds of MB):
    /// writer.gguf holds "x" and gector/labels.txt "abc".
    fn small() -> Manifest {
        let file = |path: &str, bytes: u64| File {
            path: path.into(),
            url: format!("https://github.com/jn-aman/parzr/releases/download/t/{path}"),
            bytes,
            sha256: if bytes == 1 { SHA_X } else { SHA_ABC }.into(),
            name: path.into(),
            version: "1".into(),
            license: "MIT".into(),
            purpose: "test".into(),
        };
        Manifest {
            schema: 1,
            packs: vec![Pack {
                id: "essential".into(),
                version: "1".into(),
                title: "t".into(),
                purpose: "t".into(),
                license: "MIT".into(),
                provides: BTreeMap::from([
                    ("writing_model".into(), "writer.gguf".into()),
                    ("grammar_model".into(), "gector".into()),
                ]),
                files: vec![file("writer.gguf", 1), file("gector/labels.txt", 3)],
            }],
        }
    }
    /// What the app writes once every file matched its SHA-256.
    fn mark(pack: &Pack, folder: &Path) {
        let files: Vec<_> = pack
            .files
            .iter()
            .map(|f| {
                let (bytes, inode, mtime_ns) = identity(&folder.join(&f.path)).unwrap();
                serde_json::json!({"path": f.path, "sha256": f.sha256, "bytes": bytes, "inode": inode, "mtime_ns": mtime_ns})
            })
            .collect();
        let marker = serde_json::json!({"schema": 1, "pack": pack.id, "version": pack.version, "files": files});
        std::fs::write(folder.join(MARKER), marker.to_string()).unwrap();
    }
    #[test]
    fn only_a_verified_version_folder_counts() {
        let root = std::env::temp_dir().join(format!("parzr-packs-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let m = &small();
        let pack = &m.packs[0];
        let model = &pack.provides["writing_model"];
        assert!(installed_in(m, &root, "writing_model").is_none());
        // A staging folder is not an installed pack.
        let staging = root
            .join(&pack.id)
            .join(format!(".download-{}", pack.version));
        std::fs::create_dir_all(&staging).unwrap();
        std::fs::write(staging.join(model), b"x").unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        // An older version is not this build's pack either.
        let old = root.join(&pack.id).join("0");
        std::fs::create_dir_all(&old).unwrap();
        std::fs::write(old.join(model), b"x").unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        let current = root.join(&pack.id).join(&pack.version);
        std::fs::create_dir_all(current.join("gector")).unwrap();
        std::fs::write(current.join(model), b"x").unwrap();
        std::fs::write(current.join("gector/labels.txt"), b"abc").unwrap();
        // A bare folder, even with every file at its pinned size, is not installed: nothing has
        // vouched for its contents.
        assert!(installed_in(m, &root, "writing_model").is_none());
        mark(pack, &current);
        assert_eq!(
            installed_in(m, &root, "writing_model"),
            Some(current.join(model))
        );
        assert_eq!(
            installed_in(m, &root, "grammar_model"),
            Some(current.join("gector"))
        );
        assert!(installed_in(m, &root, "no_such_role").is_none());
        // A file replaced after verification (another inode) is no longer the verified one.
        std::fs::remove_file(current.join(model)).unwrap();
        std::fs::write(current.join(model), b"x").unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        mark(pack, &current);
        assert!(installed_in(m, &root, "writing_model").is_some());
        // Rewritten in place: a new modification time.
        std::thread::sleep(std::time::Duration::from_millis(20));
        std::fs::write(current.join("gector/labels.txt"), b"xyz").unwrap();
        assert!(installed_in(m, &root, "grammar_model").is_none());
        // Even with a marker naming its new identity: "xyz" is not the pinned "abc".
        mark(pack, &current);
        assert!(installed_in(m, &root, "grammar_model").is_none());
        assert!(
            available_in(m, &root, "grammar_model").is_none(),
            "a failed hash is known without waiting"
        );
        std::fs::write(current.join("gector/labels.txt"), b"abc").unwrap();
        mark(pack, &current);
        assert!(installed_in(m, &root, "grammar_model").is_some());
        // A symbolic link in place of a file is never a verified file.
        std::fs::remove_file(current.join(model)).unwrap();
        std::os::unix::fs::symlink(current.join("gector/labels.txt"), current.join(model)).unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        std::fs::remove_file(current.join(model)).unwrap();
        std::fs::write(current.join(model), b"x").unwrap();
        mark(pack, &current);
        // A marker for another pack, another version or other hashes vouches for nothing.
        let marker = std::fs::read_to_string(current.join(MARKER)).unwrap();
        let cd = "cd".repeat(32);
        for (from, to) in [
            ("\"version\":\"1\"", "\"version\":\"2\""),
            ("\"pack\":\"essential\"", "\"pack\":\"other\""),
            (SHA_X, cd.as_str()),
        ] {
            assert!(marker.contains(from), "{from}");
            std::fs::write(current.join(MARKER), marker.replacen(from, to, 1)).unwrap();
            assert!(installed_in(m, &root, "writing_model").is_none(), "{to}");
        }
        std::fs::write(current.join(MARKER), b"not json").unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        std::fs::write(current.join(MARKER), &marker).unwrap();
        assert!(installed_in(m, &root, "writing_model").is_some());
        std::fs::remove_dir_all(&root).unwrap();
    }

    /// OBS-1: someone who can write the Models folder replaces a file with different contents of
    /// the same size and writes a marker naming the new file's identity and the pinned hash. The
    /// marker check alone accepted that; the engine's own hash refuses it.
    #[test]
    fn a_forged_marker_over_other_contents_is_refused() {
        let root = std::env::temp_dir().join(format!("parzr-packs-forged-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let m = &small();
        let pack = &m.packs[0];
        let current = root.join(&pack.id).join(&pack.version);
        std::fs::create_dir_all(current.join("gector")).unwrap();
        std::fs::write(current.join("writer.gguf"), b"x").unwrap();
        std::fs::write(current.join("gector/labels.txt"), b"abc").unwrap();
        mark(pack, &current);
        assert!(installed_in(m, &root, "writing_model").is_some());
        // Same size, other contents, and a marker that vouches for exactly this file.
        std::fs::remove_file(current.join("writer.gguf")).unwrap();
        std::fs::write(current.join("writer.gguf"), b"Y").unwrap();
        mark(pack, &current);
        assert!(
            verified(pack, &current),
            "the marker alone still vouches for it"
        );
        assert!(
            installed_in(m, &root, "writing_model").is_none(),
            "the contents do not hash to the pin"
        );
        assert!(available_in(m, &root, "writing_model").is_none());
        // The grammar model's files are untouched and still load.
        assert!(installed_in(m, &root, "grammar_model").is_some());
        // Rewritten in place with the same size and its modification time set back: the change
        // time still moves, so the file is hashed again rather than trusted from before.
        std::fs::remove_file(current.join("writer.gguf")).unwrap();
        std::fs::write(current.join("writer.gguf"), b"x").unwrap();
        mark(pack, &current);
        assert!(installed_in(m, &root, "writing_model").is_some());
        let path = current.join("writer.gguf");
        let before = std::fs::metadata(&path).unwrap().modified().unwrap();
        std::thread::sleep(std::time::Duration::from_millis(20));
        std::fs::write(&path, b"Y").unwrap();
        std::fs::File::options()
            .write(true)
            .open(&path)
            .unwrap()
            .set_modified(before)
            .unwrap();
        assert!(
            verified(pack, &current),
            "same size, inode and modification time"
        );
        assert!(installed_in(m, &root, "writing_model").is_none());
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn a_file_is_hashed_once_and_concurrent_loads_wait_for_one_verdict() {
        let root = std::env::temp_dir().join(format!("parzr-packs-once-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&root).unwrap();
        let path = root.join("big.bin");
        // 64 MB: long enough to hash that the other threads find it in progress.
        std::fs::write(&path, vec![7u8; 64 << 20]).unwrap();
        let mut file = std::fs::File::open(&path).unwrap();
        let pinned = sha256_hex(&mut file).unwrap();
        assert_eq!(
            known_verdict(&path, &pinned),
            None,
            "nothing known before the first hash"
        );
        let verdicts: Vec<bool> = std::thread::scope(|s| {
            let handles: Vec<_> = (0..4)
                .map(|_| s.spawn(|| content_verified(&path, &pinned)))
                .collect();
            handles.into_iter().map(|h| h.join().unwrap()).collect()
        });
        assert_eq!(verdicts, [true; 4]);
        assert_eq!(known_verdict(&path, &pinned), Some(true));
        assert_eq!(
            known_verdict(&path, &"0".repeat(64)),
            None,
            "a verdict is for its pinned hash"
        );
        assert!(!content_verified(&path, &"0".repeat(64)));
        assert!(!content_verified(&root.join("missing"), &pinned));
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn sha256_matches_the_standard_vectors() {
        let hex = |bytes: &[u8]| sha256_hex(&mut std::io::Cursor::new(bytes.to_vec())).unwrap();
        assert_eq!(
            hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        assert_eq!(hex(b"abc"), SHA_ABC);
        assert_eq!(hex(b"x"), SHA_X);
        assert_eq!(
            hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
        );
        // Across the 4 MiB read chunks: one million 'a's.
        assert_eq!(
            hex(&vec![b'a'; 1_000_000]),
            "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"
        );
        let big = vec![0x5au8; (4 << 20) + 3];
        assert_eq!(hex(&big).len(), 64);
    }

    /// What the per-process re-hash costs on this Mac, for the packs installed here:
    /// `cargo test --release --lib -- --ignored --nocapture packs::tests::verification_cost`.
    #[test]
    #[ignore = "reads the installed model packs (hundreds of MB)"]
    fn verification_cost() {
        let root = root().expect("HOME or PARZR_MODELS_DIR");
        for pack in &manifest().packs {
            let folder = root.join(&pack.id).join(&pack.version);
            if !verified(pack, &folder) {
                eprintln!("{}: not installed here", pack.id);
                continue;
            }
            let started = std::time::Instant::now();
            let mut bytes = 0;
            for f in &pack.files {
                let path = folder.join(&f.path);
                let mut file = std::fs::File::open(&path).unwrap();
                assert_eq!(
                    sha256_hex(&mut file).as_deref(),
                    Some(f.sha256.as_str()),
                    "{}",
                    f.path
                );
                bytes += f.bytes;
            }
            let took = started.elapsed();
            eprintln!(
                "{} {}: {} files, {:.1} MB in {:.3} s ({:.2} GB/s)",
                pack.id,
                pack.version,
                pack.files.len(),
                bytes as f64 / 1e6,
                took.as_secs_f64(),
                bytes as f64 / 1e9 / took.as_secs_f64()
            );
        }
        // The engine's path end to end: each role's verdict, with the background thread started.
        let started = std::time::Instant::now();
        verify_in_background();
        for role in ["grammar_model", "slip_model", "writing_model"] {
            let available = std::time::Instant::now();
            let quick = available_in(manifest(), &root, role).is_some();
            let quick_took = available.elapsed();
            let found = installed(role).is_some();
            eprintln!(
                "{role}: available()={quick} in {:.1} ms (never waits); installed()={found} at {:.3} s after start",
                quick_took.as_secs_f64() * 1e3,
                started.elapsed().as_secs_f64()
            );
        }
    }
}
