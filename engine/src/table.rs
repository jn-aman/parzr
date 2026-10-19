//! Read-only hash tables that `build.rs` writes at compile time and the engine reads in place
//! from the binary (the spelling lexicon, its deletion index, word frequencies and word pairs).
//! Nothing is parsed or copied at run time: a lookup touches a few pages of the executable,
//! which stay clean and shared, so the tables cost almost no process memory.
//!
//! Layout, little endian, every field a u32:
//! `magic, slots, entries, value_size, extras, arena` then `slots × u32`, `entries × (key_offset,
//! key_len, value…)`, `extras × u32`, and the key bytes. A slot is 0 when empty, else the entry
//! index + 1 in its low 24 bits and the top 8 bits of the key's hash in its high 8 (most probes
//! for absent keys, the common case in the deletion index, stop there without reading a key).
//! Linear probing. `build.rs` includes this file to share `hash`, `slot` and the constants.

pub(crate) const MAGIC: u32 = u32::from_le_bytes(*b"PZT2");
/// The file holding all four tables: `BUNDLE_MAGIC, count` then `count × (offset, len)` as u64,
/// then the tables, each starting on an 8-byte boundary.
pub(crate) const BUNDLE_MAGIC: u32 = u32::from_le_bytes(*b"PZTS");
/// The tables in a bundle, in order: lexicon, deletes, frequency, word pairs.
pub(crate) const BUNDLE_TABLES: usize = 4;

/// Writes a bundle (build.rs).
#[allow(dead_code)]
pub(crate) fn bundle(tables: &[&[u8]]) -> Vec<u8> {
    let header = 8 + tables.len() * 16;
    let mut out = Vec::new();
    out.extend(BUNDLE_MAGIC.to_le_bytes());
    out.extend((tables.len() as u32).to_le_bytes());
    let mut at = header.next_multiple_of(8);
    for table in tables {
        out.extend((at as u64).to_le_bytes());
        out.extend((table.len() as u64).to_le_bytes());
        at = (at + table.len()).next_multiple_of(8);
    }
    for table in tables {
        out.resize(out.len().next_multiple_of(8), 0);
        out.extend_from_slice(table);
    }
    out
}

/// The tables of a bundle, or why it is not one.
#[allow(dead_code)]
pub(crate) fn unbundle(data: &'static [u8]) -> Result<[&'static [u8]; BUNDLE_TABLES], String> {
    let word = |at: usize| -> Option<u64> {
        Some(u64::from_le_bytes(data.get(at..at + 8)?.try_into().ok()?))
    };
    let magic = data
        .get(..4)
        .map(|m| u32::from_le_bytes(m.try_into().unwrap()));
    let count = data
        .get(4..8)
        .map(|c| u32::from_le_bytes(c.try_into().unwrap()));
    if magic != Some(BUNDLE_MAGIC) || count != Some(BUNDLE_TABLES as u32) {
        return Err("not a Parzr table bundle".into());
    }
    let mut tables = [&data[..0]; BUNDLE_TABLES];
    for (i, table) in tables.iter_mut().enumerate() {
        let (at, len) = (word(8 + i * 16), word(16 + i * 16));
        let (Some(at), Some(len)) = (at, len) else {
            return Err("truncated table bundle".into());
        };
        *table = data
            .get(at as usize..(at + len) as usize)
            .ok_or("truncated table bundle")?;
    }
    Ok(tables)
}
pub(crate) const HEADER: usize = 6 * 4;
/// Entries a table may hold (24-bit indices). Used by build.rs.
#[allow(dead_code)]
pub(crate) const MAX_ENTRIES: usize = (1 << 24) - 1;

/// Multiply-rotate over 8-byte words with a final mix; the build and the reader must agree.
pub(crate) fn hash(bytes: &[u8]) -> u64 {
    let mut h: u64 = bytes.len() as u64;
    for chunk in bytes.chunks(8) {
        let mut word = [0; 8];
        word[..chunk.len()].copy_from_slice(chunk);
        h = (h.rotate_left(5) ^ u64::from_le_bytes(word)).wrapping_mul(0xf135_7aea_2e62_a9c5);
    }
    h = (h ^ (h >> 29)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    h ^ (h >> 32)
}
/// The slot word for entry `index` of a key with hash `h`. Used by build.rs.
#[allow(dead_code)]
pub(crate) fn slot(h: u64, index: usize) -> u32 {
    ((h >> 56) as u32) << 24 | (index as u32 + 1)
}

#[derive(Clone, Copy)]
pub(crate) struct Table {
    data: &'static [u8],
    mask: usize,
    entries: usize,
    entry_size: usize,
    slots_at: usize,
    entries_at: usize,
    extras_at: usize,
    arena_at: usize,
}

impl Table {
    pub(crate) fn new(data: &'static [u8]) -> Table {
        let word =
            |i: usize| u32::from_le_bytes(data[i * 4..i * 4 + 4].try_into().unwrap()) as usize;
        assert_eq!(
            word(0) as u32,
            MAGIC,
            "engine table built by another version"
        );
        let (slots, entries, value_size, extras) = (word(1), word(2), word(3), word(4));
        assert!(slots.is_power_of_two());
        let entry_size = 8 + value_size;
        let slots_at = HEADER;
        let entries_at = slots_at + slots * 4;
        let extras_at = entries_at + entries * entry_size;
        let arena_at = extras_at + extras * 4;
        assert_eq!(arena_at + word(5), data.len(), "truncated engine table");
        Table {
            data,
            mask: slots - 1,
            entries,
            entry_size,
            slots_at,
            entries_at,
            extras_at,
            arena_at,
        }
    }
    /// The number of entries.
    #[cfg(test)]
    pub(crate) fn len(&self) -> usize {
        self.entries
    }
    fn u32_at(&self, at: usize) -> usize {
        u32::from_le_bytes(self.data[at..at + 4].try_into().unwrap()) as usize
    }
    fn key_bytes(&self, entry: usize) -> &'static [u8] {
        let at = self.entries_at + entry * self.entry_size;
        let (offset, len) = (self.u32_at(at), self.u32_at(at + 4));
        &self.data[self.arena_at + offset..self.arena_at + offset + len]
    }
    /// The entry holding `key`.
    pub(crate) fn find(&self, key: &str) -> Option<usize> {
        if self.entries == 0 {
            return None;
        }
        let h = hash(key.as_bytes());
        let tag = (h >> 56) as usize;
        let mut slot = h as usize & self.mask;
        loop {
            let word = self.u32_at(self.slots_at + slot * 4);
            if word == 0 {
                return None;
            }
            let entry = (word & 0xff_ffff) - 1;
            if word >> 24 == tag && self.key_bytes(entry) == key.as_bytes() {
                return Some(entry);
            }
            slot = (slot + 1) & self.mask;
        }
    }
    pub(crate) fn key(&self, entry: usize) -> &'static str {
        std::str::from_utf8(self.key_bytes(entry)).expect("UTF-8 table key")
    }
    pub(crate) fn value(&self, entry: usize) -> &'static [u8] {
        let at = self.entries_at + entry * self.entry_size + 8;
        &self.data[at..self.entries_at + (entry + 1) * self.entry_size]
    }
    pub(crate) fn value_u32(&self, entry: usize, field: usize) -> u32 {
        let value = self.value(entry);
        u32::from_le_bytes(value[field * 4..field * 4 + 4].try_into().unwrap())
    }
    pub(crate) fn extra(&self, index: usize) -> u32 {
        self.u32_at(self.extras_at + index * 4) as u32
    }
    /// A string stored in the arena by the build (not a key), at `offset` with `len` bytes.
    pub(crate) fn arena_str(&self, offset: usize, len: usize) -> &'static str {
        std::str::from_utf8(&self.data[self.arena_at + offset..self.arena_at + offset + len])
            .expect("UTF-8 table string")
    }
}
