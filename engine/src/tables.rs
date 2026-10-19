//! Where the compiled tables (`build.rs`, `table.rs`) come from.
//!
//! By default they are embedded in the binary. With the `external-tables` feature (the Mac app
//! bundle, whose four engine binaries would otherwise each carry a copy) they are one read-only
//! file, `Contents/Resources/parzr-tables.dat`, mapped into memory. The engine accepts only the
//! exact file it was built with (length and hash compiled in) and otherwise answers every request
//! with an error naming the problem; it never runs on other tables.
use crate::table::{BUNDLE_TABLES, unbundle};
use std::sync::OnceLock;

#[allow(dead_code)]
mod meta {
    include!(concat!(env!("OUT_DIR"), "/tables_meta.rs"));
}

/// The file name of the tables in the Mac app's Resources.
pub const FILE_NAME: &str = "parzr-tables.dat";

pub(crate) struct Tables {
    pub(crate) lexicon: &'static [u8],
    pub(crate) deletes: &'static [u8],
    pub(crate) frequency: &'static [u8],
    pub(crate) bigrams: &'static [u8],
}

fn split(data: &'static [u8]) -> Result<Tables, String> {
    let [lexicon, deletes, frequency, bigrams]: [&'static [u8]; BUNDLE_TABLES] = unbundle(data)?;
    Ok(Tables {
        lexicon,
        deletes,
        frequency,
        bigrams,
    })
}

fn loaded() -> &'static Result<Tables, String> {
    static TABLES: OnceLock<Result<Tables, String>> = OnceLock::new();
    TABLES.get_or_init(load)
}

/// The tables. Callers past `ready()` (every request checks it first) never see the panic.
pub(crate) fn get() -> &'static Tables {
    match loaded() {
        Ok(tables) => tables,
        Err(error) => panic!("{error}"),
    }
}

/// Ok when the tables are there; else the message to show (the data file is missing or is not
/// the one this engine was built with).
pub fn ready() -> Result<(), String> {
    loaded().as_ref().map(|_| ()).map_err(Clone::clone)
}

#[cfg(not(feature = "external-tables"))]
fn load() -> Result<Tables, String> {
    split(include_bytes!(concat!(
        env!("OUT_DIR"),
        "/parzr-tables.dat"
    )))
}

#[cfg(feature = "external-tables")]
fn load() -> Result<Tables, String> {
    let candidates = external::candidates();
    let Some(path) = candidates.iter().find(|p| p.is_file()) else {
        return Err(format!(
            "The writing engine's data file ({FILE_NAME}) is missing. Reinstall Parzr. Looked in: {}",
            candidates
                .iter()
                .map(|p| p.display().to_string())
                .collect::<Vec<_>>()
                .join(", ")
        ));
    };
    let damaged = |why: &str| {
        format!(
            "The writing engine's data file {} {why}. Reinstall Parzr.",
            path.display()
        )
    };
    let data = external::map(path).map_err(|e| damaged(&format!("could not be read ({e})")))?;
    if data.len() != meta::TABLES_LEN || crate::table::hash(data) != meta::TABLES_HASH {
        return Err(damaged("does not belong to this version of the engine"));
    }
    split(data).map_err(|e| damaged(&e))
}

#[cfg(feature = "external-tables")]
mod external {
    use super::FILE_NAME;
    use std::{
        ffi::{CStr, c_char, c_int, c_void},
        fs::File,
        os::fd::AsRawFd,
        path::{Path, PathBuf},
    };

    #[repr(C)]
    struct DlInfo {
        fname: *const c_char,
        fbase: *mut c_void,
        sname: *const c_char,
        saddr: *mut c_void,
    }
    unsafe extern "C" {
        fn mmap(
            addr: *mut c_void,
            len: usize,
            prot: c_int,
            flags: c_int,
            fd: c_int,
            offset: i64,
        ) -> *mut c_void;
        fn dladdr(addr: *const c_void, info: *mut DlInfo) -> c_int;
    }
    const PROT_READ: c_int = 1;
    const MAP_PRIVATE: c_int = 2;

    /// The file this code was loaded from: the dylib inside the app, or an executable.
    fn image() -> Option<PathBuf> {
        let mut info = DlInfo {
            fname: std::ptr::null(),
            fbase: std::ptr::null_mut(),
            sname: std::ptr::null(),
            saddr: std::ptr::null_mut(),
        };
        // SAFETY: dladdr only reads the address and fills `info`; the name it returns lives as
        // long as the image stays loaded, and it is copied at once.
        let here: fn() -> Option<PathBuf> = image;
        let found = unsafe { dladdr(here as *const c_void, &mut info) };
        if found == 0 || info.fname.is_null() {
            return std::env::current_exe().ok();
        }
        // SAFETY: dladdr returned a NUL-terminated path.
        let name = unsafe { CStr::from_ptr(info.fname) }.to_str().ok()?;
        Some(PathBuf::from(name))
    }

    /// PARZR_TABLES_PATH, then `../Resources/` beside the image's folder (Contents/MacOS and
    /// Contents/Frameworks both sit beside Contents/Resources), then the image's own folder.
    pub(super) fn candidates() -> Vec<PathBuf> {
        let mut out = vec![];
        if let Some(path) = std::env::var_os("PARZR_TABLES_PATH").filter(|p| !p.is_empty()) {
            out.push(PathBuf::from(path));
        }
        if let Some(image) = image() {
            let image = std::fs::canonicalize(&image).unwrap_or(image);
            if let Some(folder) = image.parent() {
                out.push(folder.join("../Resources").join(FILE_NAME));
                out.push(folder.join(FILE_NAME));
            }
        }
        out
    }

    /// Maps the file read-only for the life of the process.
    pub(super) fn map(path: &Path) -> std::io::Result<&'static [u8]> {
        let file = File::open(path)?;
        let len = file.metadata()?.len() as usize;
        if len == 0 {
            return Ok(&[]);
        }
        // SAFETY: a private read-only mapping of a file opened for reading; it is never unmapped,
        // so the slice is valid for the rest of the process. The file is part of the signed app
        // bundle and is not modified while Parzr runs.
        let ptr = unsafe {
            mmap(
                std::ptr::null_mut(),
                len,
                PROT_READ,
                MAP_PRIVATE,
                file.as_raw_fd(),
                0,
            )
        };
        if ptr as isize == -1 || ptr.is_null() {
            return Err(std::io::Error::last_os_error());
        }
        // SAFETY: the mapping covers `len` readable bytes and lives for the process.
        Ok(unsafe { std::slice::from_raw_parts(ptr as *const u8, len) })
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn the_tables_load_and_match_their_pinned_length() {
        super::ready().unwrap();
        let t = super::get();
        assert!(!t.lexicon.is_empty() && !t.deletes.is_empty());
        assert!(!t.frequency.is_empty() && !t.bigrams.is_empty());
        assert!(super::meta::TABLES_LEN > t.lexicon.len() + t.deletes.len());
    }
}
