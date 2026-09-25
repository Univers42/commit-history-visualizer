---
globs: ["**/*.rs"]
description: Rust refactoring rules
---

# Rust Refactoring

## Idioms

- Max 40 lines per function
- No file exceeds 300 lines
- Errors are `Result`; no `unwrap`/`expect` in library paths
- No `unwrap` in tests unless the panic *is* the assertion
- No `unsafe` without a documented invariant on the next line
- Prefer `&T` / `&mut T` over clones; clone is a decision, not a default
- Module paths are `snake_case`; types are `PascalCase`; enums are not stringly typed

## Hexagonal architecture

- Domain (`camera`, `scene`, `edit`, `history`) has zero `web-sys` / `wasm-bindgen` imports
- WASM and Canvas2D live behind a `Painter` / host adapter
- Ports (traits) in the domain; adapters implement them

## After refactoring

- `cargo fmt --all --check` — zero drift
- `cargo clippy --all-targets --all-features -- -D warnings` — zero issues
- `cargo test` — zero failures
- No unexplained `#[allow(...)]` (every suppression links an issue)

## Rust-specific ladder extensions

- Rung 2: `std` (`HashMap`, `Vec`, `fmt`) before any crate
- Rung 3: `serde`/`serde_json` for `.osidraw`; `wasm-bindgen`/`web-sys` only under `cfg(target_arch = "wasm32")`
- Rung 4: a std trait fits (`Iterator`, `From`)? Use it — don't define your own
- No getter if the field can be `pub`
- `Default` when the zero value is usable

## Rust performance guardrails

- Pre-size `Vec` when the length is known (`Vec::with_capacity`)
- Scene lookups are `HashMap` (O(1)); ordered z-list is a cached `Vec`
- Do not clone the scene per frame; the painter reads a borrow
- WASM: keep the scene inside Rust; cross the JS boundary with ids, JSON, and style patches — not per-element objects every paint
- `format!` in a hot loop? `Write` into a reused `String`
