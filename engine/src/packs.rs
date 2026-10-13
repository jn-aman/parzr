//! Model packs: the pinned list of downloadable model files (`engine/models.json`, compiled in) and
//! where a verified pack lives on this Mac. The app downloads a pack into
//! `~/Library/Application Support/Parzr/Models/<pack>/<version>/`, staging it beside that folder and
//! renaming the folder into place only after every file matched its SHA-256, so a version folder
//! that exists is complete. The engine only reads: it never downloads anything.
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, path::PathBuf, sync::OnceLock};

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

/// `PARZR_MODELS_DIR` (tests, development), else `~/Library/Application Support/Parzr/Models`.
pub fn root() -> Option<PathBuf> {
    if let Some(dir) = std::env::var_os("PARZR_MODELS_DIR").filter(|d| !d.is_empty()) {
        return Some(PathBuf::from(dir));
    }
    let home = std::env::var_os("HOME").filter(|h| !h.is_empty())?;
    Some(PathBuf::from(home).join("Library/Application Support/Parzr/Models"))
}

/// The installed file or folder that plays `role`, when its pack's verified version is on disk.
pub fn installed(role: &str) -> Option<PathBuf> {
    installed_in(manifest(), &root()?, role)
}
fn installed_in(manifest: &Manifest, root: &std::path::Path, role: &str) -> Option<PathBuf> {
    manifest.packs.iter().find_map(|pack| {
        let relative = pack.provides.get(role)?;
        let path = root.join(&pack.id).join(&pack.version).join(relative);
        path.exists().then_some(path)
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
        // The engine's two models come from a pack.
        for role in ["writing_model", "grammar_model"] {
            assert!(m.packs.iter().any(|p| p.provides.contains_key(role)));
        }
    }
    #[test]
    fn only_a_verified_version_folder_counts() {
        let root = std::env::temp_dir().join(format!("parzr-packs-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let m = manifest();
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
        std::fs::create_dir_all(&current).unwrap();
        std::fs::write(current.join(model), b"x").unwrap();
        assert_eq!(
            installed_in(m, &root, "writing_model"),
            Some(current.join(model))
        );
        assert!(installed_in(m, &root, "no_such_role").is_none());
        std::fs::remove_dir_all(&root).unwrap();
    }
}
