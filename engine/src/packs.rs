//! Model packs: the pinned list of downloadable model files (`engine/models.json`, compiled in) and
//! where a verified pack lives on this Mac. The app downloads a pack into
//! `~/Library/Application Support/Parzr/Models/<pack>/<version>/`, staging it beside that folder and
//! renaming the folder into place only after every file matched its SHA-256. A folder alone is
//! never trusted: the app (and scripts/model-pack.py) writes a marker, `.verified.json`, naming
//! every file's pinned hash and its identity on disk (size, inode, modification time) once its
//! SHA-256 checked out, and the engine uses a pack only while every file still has that identity.
//! A file replaced or rewritten since then makes the pack unavailable until the app verifies it
//! again. The engine only reads: it never downloads or hashes anything.
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    path::{Path, PathBuf},
    sync::{
        OnceLock,
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
}

/// The installed file or folder that plays `role`, when its pack's verified version is on disk.
pub fn installed(role: &str) -> Option<PathBuf> {
    if HOLD.load(Ordering::SeqCst) {
        return None;
    }
    installed_in(manifest(), &root()?, role)
}
fn installed_in(manifest: &Manifest, root: &Path, role: &str) -> Option<PathBuf> {
    manifest.packs.iter().find_map(|pack| {
        let relative = pack.provides.get(role)?;
        let folder = root.join(&pack.id).join(&pack.version);
        let path = folder.join(relative);
        (path.exists() && verified(pack, &folder)).then_some(path)
    })
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
    /// A small pack whose files the test writes for real (the pinned ones are hundreds of MB).
    fn small() -> Manifest {
        let file = |path: &str, bytes: u64| File {
            path: path.into(),
            url: format!("https://github.com/jn-aman/parzr/releases/download/t/{path}"),
            bytes,
            sha256: "ab".repeat(32),
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
        std::fs::write(current.join(model), b"y").unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        mark(pack, &current);
        assert!(installed_in(m, &root, "writing_model").is_some());
        // Rewritten in place: a new modification time.
        std::thread::sleep(std::time::Duration::from_millis(20));
        std::fs::write(current.join("gector/labels.txt"), b"xyz").unwrap();
        assert!(installed_in(m, &root, "grammar_model").is_none());
        mark(pack, &current);
        // A symbolic link in place of a file is never a verified file.
        std::fs::remove_file(current.join(model)).unwrap();
        std::os::unix::fs::symlink(current.join("gector/labels.txt"), current.join(model)).unwrap();
        assert!(installed_in(m, &root, "writing_model").is_none());
        std::fs::remove_file(current.join(model)).unwrap();
        std::fs::write(current.join(model), b"x").unwrap();
        mark(pack, &current);
        // A marker for another pack, another version or other hashes vouches for nothing.
        let marker = std::fs::read_to_string(current.join(MARKER)).unwrap();
        let (ab, cd) = ("ab".repeat(32), "cd".repeat(32));
        for (from, to) in [
            ("\"version\":\"1\"", "\"version\":\"2\""),
            ("\"pack\":\"essential\"", "\"pack\":\"other\""),
            (ab.as_str(), cd.as_str()),
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
}
