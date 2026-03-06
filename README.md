# FBP — Swift Tools

Swift-native automation tools: **fbp** CLI client.

## fbp — Swift CLI

Native macOS command-line client for FBP Backend (Python FastAPI).

**Requires:** FBP Backend running at `http://127.0.0.1:8000` (separate repo/deployment).

```bash
cd tools/fbp-cli
swift build
swift run fbp --help
make install   # install to /usr/local/bin/fbp
```

See [tools/fbp-cli/README.md](tools/fbp-cli/README.md) for full usage.

## Structure

```
FBP_Backend/
└── tools/fbp-cli/     # Swift CLI (SPM + ArgumentParser)
    ├── Sources/
    └── Package.swift
```

## History

- **NFASEFAZPB** Safari extension (Xcode/macOS app) was removed; Swift surface is **fbp-cli** only.
