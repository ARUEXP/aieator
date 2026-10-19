# Aieator — Standalone Motion Graphics & Video Editor

## What is Aieator
A CPU-rendered After Effects alternative made mainly for **anime edits and car edits**, built for AE users — it keeps the AE-style workflow (layers, keyframes, graph editor, effects) but delivers what AE lacks: a modern UI, ease, and simplicity. C++17 (single-file generated C++), Dear ImGui 1.91, Windows GDI typography, stb_image, **Media Foundation video decode + H.264 MP4 export**. Standalone ~3.0MB exe (no FFmpeg DLLs). Includes 42 FX, keyframes, 3 themes, 18 easing presets + bezier, multi-track timeline.

**Target hardware floor: i3-4005U + 4GB DDR3 single-channel.** The app must run on any system at least that capable — chosen as the floor because AE itself still runs on such machines, so we must too. Primary dev/reference machine: i5-7300U / 8GB / HD620 (HP ProBook 650 G3); performance numbers below come from it.

---

## Project Structure

```
aieator/
├── gen.py              # THE SOURCE OF TRUTH (~4591 lines, 621KB) — edit this, NOT main.cpp
├── icons_build.py      # Icon pipeline: Iconoir SVGs in icons/ → white RGBA baked into gen.py (run before gen.py)
├── main.cpp            # Generated (written by gen.py, ~621KB)
├── aieator.exe         # Built binary (~3.0MB with icons + MF)
├── app.ico             # Generated exe icon (from logo.png, multi-size 16→256)
├── aie_icon.ico        # Generated .aie file icon (from "aie file icon.png")
├── app_res.rc / .res   # Windows resource (2 ICONs: 1=exe, 2=.aie)
├── logo.png            # Source for exe icon
├── "aie file icon.png" # Source for .aie file icon
├── imgui.ini           # ImGui window layout persistence
├── CONTEXT.md          # This file
├── capture_tests.py    # Visual regression (home + studio + 3 themes)
├── test_project.aie    # Default project (test harness uses it)
├── test_video.mp4      # AMV sample for video decode test
├── fonts/              # Typography library scanned at startup (Space Grotesk drives the UI)
├── icons/              # Iconoir set (regular/ + solid/) — source of truth for the 25 embedded icon textures
├── screenshots/        # Visual regression outputs (capture_tests.py)
├── ui references/      # Design reference images (graph presets, liquid glass mockups)
└── thirdparty/
    ├── imgui/ 1.91.0 (with Win32 + OpenGL3 backends)
    ├── stb_image.h
    └── stb_image_write.h
```

---

## Build System

### Development Workflow

```powershell
# 1. Edit gen.py (NOT main.cpp)
# 1b. Icons only when swapping Iconoir files: python icons_build.py (bakes icons/ into gen.py)
# 2. Generate main.cpp
python gen.py

# 3. Compile icons resource (after updating logo.png / aie file icon.png)
#    (generate ICOs via Pillow, then:)
windres app_res.rc -O coff -o app_res.res

# 4. Compile exe (MF libs required for video decode/encode)
g++ -O3 -std=c++17 main.cpp app_res.res thirdparty/imgui/imgui.cpp thirdparty/imgui/imgui_draw.cpp thirdparty/imgui/imgui_widgets.cpp thirdparty/imgui/imgui_tables.cpp thirdparty/imgui/backends/imgui_impl_win32.cpp thirdparty/imgui/backends/imgui_impl_opengl3.cpp -o aieator.exe -mwindows -Ithirdparty -Ithirdparty/imgui -Ithirdparty/imgui/backends -lopengl32 -lgdi32 -luser32 -lkernel32 -lcomdlg32 -lshell32 -ldwmapi -lole32 -loleaut32 -luuid -lmfplat -lmfreadwrite -lmfuuid -lwinmm

# 5. Register .aie file association (per-user, no admin, done once)
# exe icon = logo.png (resource 1), file icon = aie file icon.png (resource 2 as index 1)
# HKCU\Software\Classes\.aie -> AieatorProject; HKCU\...\DefaultIcon -> "C:\...\aieator.exe,1"

# 6. Smoke test
Stop-Process -Name aieator -Force -ErrorAction SilentlyContinue
$p = Start-Process .\aieator.exe -PassThru; Start-Sleep -Seconds 4; if ($p.HasExited) { "CRASHED" } else { "RUNNING"; Stop-Process -Name aieator -Force }

# 7. Visual regression
python capture_tests.py
```

### Toolchain
- MinGW-w64 g++ 16.1.0, C++17, `-O3 -mwindows`, OpenGL 1.1 compat, GDI, COM (IFileDialog), Media Foundation (mfplat/mfreadwrite/mfuuid)
- Python required for `gen.py` and `capture_tests.py` only at build/test

---

## Architecture & UI Layout

### Single-File Monolith
`gen.py` raw string `SRC` holds the entire C++ source. Sections inside:
1. **Headers & Win32/GL** — windows.h, dwmapi, shobjidl, mfapi/mfidl/mfreadwrite, GL, stb, DpiAwareness
2. **FX / Kinetic Text Enums** — `FX_*` (42), `TextAnimParams`, `IconType` (25 embedded icons)
3. **Data Model** — `ImageData`, `VideoData` (MF, NV12-decode), `TimelineItem` (ItemType MEDIA/TEXT, track/startTime/duration/speed, `imageIdx` + `videoIdx`, Camera/ColorGrade/TextOverlay, `std::vector<FXParams> fx`, keyframes, transType/Dur)
4. **Globals & Easing** — `g_Images`, `g_Videos` (MF), `g_Clips alias g_Items`, `g_PreviewScale=0.5` + `g_ProjectPath`, 18 easing presets + bezier, `g_MagnetSnap`, `g_ShowGrid3x3`, font DPI scale, themes
5. **FX Algorithms** — 42 effects, LUT tables, separable blurs, downsampled glow
6. **Sampler + GDI TTF + RenderPipeline** — `Sample()` bilinear, `DrawTextToBuffer()` GDI, `ApplyFXPipeline()`, `RenderTimelineItem()` (video via `VideoGetFrame` + NV12→RGBA), `CompositeLayer()`, `RenderPreview()` (per-track loop, Smart Depth)
7. **Media Foundation Video Engine** — `LoadVideo` (find video stream 0..7, request NV12 decode, duration/fps), `VideoGetFrame` (seek via SetCurrentPosition, decode NV12→RGBA BT.709), `FreeVideos`, `EncodeMP4` (SinkWriter H.264, bitrate clamp, stride BGRA flip)
8. **File I/O** — `ImportAssets` (extension routing: video→MF, else stb_image), `SaveProject`/`LoadProject` format version 3 + `VIDEOS`/`VID`/`videoIdx` column (tolerant 7/8-col ITEM read), resize `g_PrevBuf` in preview loop
9. **Themes** — `ApplyTheme` (Light/Dark Glass #050608 spec, AMOLED)
10. **Timeline + Titlebar + Win32/Entry** — `DrawTimeline`, `DrawCustomTitleBar`, `CreateGL`, `WinMain` (Home/Studio, toolbar, panels, screenshot `--screenshot`/`--theme`, titlebar DPI-aware, keyboard shortcuts, shutdown with `FreeImages`/`FreeVideos`/`FreeIcons`/`MFShutdown`)

### Design System
- **AMOLED + minimalism + brutalism** — app bg pure `#000000`, slabs `#0a0a0a`, raw 1px white-22% edges, sharp 2px corners, bone-white text, single volt accent `(0.66,0.90,0.06)` reserved for active states (slider grab, tab, selection, playhead/markers)
- **Radii** — 2 everywhere (Window, Child, Frame, Popup, Scrollbar, Grab, Tab)
- **Spacing** — 8px system: `ItemSpacing 8,6`, `WindowPadding 10,10`, `FramePadding 10,5`; text buttons auto-size from `FramePadding` (no fixed widths)
- **Typography** — Space Grotesk (Medium UI / SemiBold headings / Bold titles, bundled in `fonts/`); GDI rasterizes TextOverlay with fontIdx/variant
- **Icons** — 25 embedded 28x28 RGBA icon textures; Iconoir source pool in `icons/` (1383 regular + 288 solid)
- **Layout** — Home: titlebar + project creator (aspect/resolution/fps, 7 aspects incl 4:3/3:4) + recent projects + templates (no hero strip); Studio: left MediaBin + EffectControls, center Composition Viewer (exact-fit `g_PrevTex`, NEAREST on zoom-upscale), right Character & Typography + Graph Editor (18 easing cards + key strip), bottom multi-track Timeline (ruler + markers + work-area bar + playhead), top toolbar + menu bar

---

## Data Model

```cpp
enum ItemType { ITEM_MEDIA = 0, ITEM_TEXT = 1 };
struct VideoData{
    std::string path; int w,h; double duration; float fps;
    IMFSourceReader* reader; DWORD streamIdx; GUID nativeSubtype;
    std::vector<unsigned char> frame; double cacheTime; // NV12→RGBA cache
};
struct TimelineItem{
    ItemType type = ITEM_MEDIA;
    int track = 0;            float startTime = 0.0f; float duration = 2.5f; float speed = 1.0f;
    bool visible = true; bool expanded = false; bool motionBlur = false; int shutterAngle = 180; float opacity = 1.0f;
    int imageIdx = -1; int videoIdx = -1;
    char textContent[256] = "Modern Title"; int fontIdx = 0; float fontSize = 72.0f;
    float textColor[3] = {1,1,1}; float textAlpha = 1.0f; TextAnimParams anim;
    Camera cam; bool kenBurns = false; std::vector<Key2D> kPos; std::vector<Key1D> kScale, kRot, kOp;
    // AE-exact: independent per-prop key lists; diamonds add/remove at playhead (filled = key here)
    // inspector shows playhead values, edits key when list non-empty; timeline: ◆ keys all, diamonds (click/drag/right-click), twirl rows, U jumps, magnet scrub-snap; per-layer motion blur
    ColorGrade color; std::vector<FXParams> fx; int transType = TRANS_NONE; float transDur = 0.3f;
};
typedef TimelineItem Clip;
```

Preview at global time `t`: each track's active item → `lt = (t-st)/max(0.1,speed)`, `cam = EvaluateClipTransform(item,lt)`, `VideoGetFrame(vd, clamp((t-st)*speed,0,dur))` before `RenderTimelineItem`; Smart Depth blur inter-track.

---

## FX System — 42 Effects

`FX_*` enum 0..41 (`FX_COUNT=42`), names in UI include "None" + 41 labels. Each `FXParams{ int type; bool enabled; float p[8]; }`. Glow uses downsampled blur (4→blur→up), Gaussian separable, LUT for grade, NV12 path uses YCbCr→RGB BT.709.

---

## Video & Export Pipeline

### Decode (native, zero DLLs)
- Windows Media Foundation only via `IMFSourceReader`; stream 0 may be audio → probes 0..7 for `MFMediaType_Video`.
- Requests `NV12` decoder output (fallback `RGB32`); reads `MF_MT_FRAME_SIZE` + `MF_MT_FRAME_RATE` from **current** media type; `MF_PD_DURATION` via `MF_SOURCE_READER_MEDIASOURCE`.
- Per-frame `VideoGetFrame` — seek when backward or >0.6s ahead (`SetCurrentPosition(GUID_NULL, VT_I8(100ns))`), reads samples until `pts ≥ target`, converts `NV12→RGBA` (studio-swing BT.709) or `BGRA→RGBA` + bottom-up flip for RGB path, caches at ~half-frame tolerance. 720p ≈ few ms.

### Export
- `Export / Render` dialog offers **MP4 (H.264)** or **PNG** single frame (file dialog filter, extension-based routing). `EncodeMP4` via `IMFSinkWriter` (`MFVideoFormat_H264` out, `RGB32` in, auto color-conv), bitrate `clamp(2..20 Mbps, w*h*fps*0.12)`, sequential `RenderPreview` → bottom-up BGRA flip per frame → `WriteSample`/`Finalize`. A 30s 1080p30 ≈ ~900 frames; blocks UI.

---

## File I/O & Project Format

- **Import** — `IFileOpenDialog` multi-select; ext routing: `.mp4/.mov/.avi/.mkv/.webm/.wmv` → `LoadVideo` (`duration` from MF), others → `stbi_load` → per-track append (`nextStart` on track 0), one `PushUndo()` batch.
- **Format** `AIEATOR 3` (tolerant reader for 7 or 8 col ITEM): `RES`, `FPS`, `IMAGES n` + `IMG <path>` lines, `VIDEOS n` + `VID <path>` lines, `CLIPS n` then per `ITEM` → `MEDIA`, `CAM`/`KF`, `COL`, `TXT`+`TTX`, `TRN`, `FX`/`FXE`.
- **Save/Load** — `g_ProjectPath` tracks current file; `Ctrl+S` saves to current path or opens `SaveProjectDialog` if empty; `Open Project` and CLI args set `g_ProjectPath`. `CreateNewProjectAction` resets clips/undo/redo. Shutdown calls `FreeImages`, `FreeVideos`, `FreeIcons`, `MFShutdown`.
- **Undo** — `PushUndo()` wired into `SplitClipAtPlayhead`, `DeleteSelectedClip`, `AddNewTextLayer`, and import batch; `Ctrl+Z` (undo) / `Ctrl+Y` (redo) via `DoUndo`/`DoRedo` (capacity 50).

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space / K | Toggle play/pause |
| J / L | Step backward / forward (5 frames) |
| Home / End | Go to start / end of timeline |
| Delete / Backspace | Delete selected clip |
| R | Split clip at playhead |
| F9 | Stamp Easy Ease on selected layer |
| M / Shift+M | Add / delete marker at playhead |
| , / . | Prev / next marker |
| I / O / X | Work-area in / out / clear |
| Left / Right | Step 1 frame |
| Up / Down | Select prev / next clip |
| Shift+Del | Ripple delete (close gap) |
| Ctrl+C / Ctrl+V | Copy / paste selected keyframe |
| Ctrl+Space | FX console (search + stamp effects) |
| G | Toggle 3x3 grid |
| A | Mute preview audio |
| U / Shift+U | Jump to next / previous keyframe on selected layer |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+S | Save project |

---

## Render & Preview Pipeline

- `RenderPreview(t,W,H,buf)` — checkerboard bg, per-track max, collect active layer, evaluate cam, warm video cache, zero `s_LayerBuf`, `RenderTimelineItem` (+ FX), focal depth auto blur, `CompositeLayer` (pre-multiplied alpha). Paused preview renders at exact display size (1:1 texel:pixel, re-renders on size change); playback uses 1/2 or 1/4; `UploadPrev(nearestMag)` uses NEAREST magnification on zoomed-upscale views.
- `UploadPrev()` — GL upload of `g_PrevBuf` → `g_PrevTex`; called from main loop's dirty-driven preview block (`g_PreviewScale` 1/2 default; quality combo hooks `g_Dirty`).
- `DrawTextToBuffer` GDI, `Sample` bilinear.

---

## UI/UX Notes & Remaining Work

### Done this pass (bug-fix + UI pass)
- **Motion Tile FX (43rd effect)**: AE-style duplicate-tile recompose (Tile Size / Pan Offset / Output Zoom / Mirror Edges) — added to enum, `ApplyFXPipeline`, param UI, and the FX popup menu.
- **Add Effect UX**: full-width "Add Effect" button removed → small plus icon in the EFFECT CONTROLS header (opens the same Add FX popup).
- **Motion blur darkening fix**: the old accumulation formula `acc += (tap-acc)*w` was a running weighted blend that diluted the reference frame to ~(1/N)^N over N iterations — causing severe darkening. Replaced with additive sum into a float buffer + single normalize pass; brightness now preserved.
- **Custom bezier editor bounds**: CP handles clamped to [0,1] (was -0.5..1.5) so curves and control points stay inside the graph grid.
- **Easing graph cards**: Back In/Out presets overshot y>1 and drew above the card box — preset card curves now auto-fit their y-range so every curve stays inside its card (shape preserved; rows without overshoot are unchanged).
- **Motion blur smoothness**: temporal taps raised to 4/6/8/10 by shutter angle (was flat 2/4) with triangle weights (middle taps weigh most) — far smoother smear. Consecutive identical `ltk` taps dedupe via counts so video clips near frame boundaries stay cheap.
- Motion-blur smear: `s_MbTap` was never cleared before the tap loop and the text blit blends (doesn't overwrite) — stale pixels smeared behind motion-blurred text; now memset per clip render.
- Perf: media grade math (brightness/contrast/sat) now skipped entirely when identity; GDI text raster cached in `s_TextCache` keyed on (text, size, font, width) — avoids re-running DIB+`DrawTextA` every frame and every motion-blur tap (typewriter opts out; cap 8, cleared on new/open/shutdown).
- Text rotation now actually rotates: glyph blit transforms around the glyph center via `cam->rot` (was axis-aligned — rotation did nothing); media path already rotated.
- Glow impl intensity clamp fixed to match UI range (0..3).
- Transform inspector uses integer widgets: Position in project px, Scale in %, Opacity in %.
- Dropped the Typography "Animation" combo (overlaps keyframe motion; `TextAnimParams` still loads/saves).
- Added Reset Layer row (clears transform, keys, FX, motion blur, selection).
- Timeline marquee box-select: drag on empty lane → translucent LB rect → selects intersecting clips into `g_SelMulti` (primary = topmost); Delete removes the whole batch in one undo. Single-clip clicks clear the batch.
- Media Bin per-row × delete buttons (undo, fixes selection like Delete).
- Undo/redo: fixed redo stack corruption (PushUndo in DoRedo cleared the state being restored), added redo cap 50, SelClip clamped after undo/redo. PushUndo no longer snapshots empty state on no-op split/delete.
- Split (R/razor) now carries keyframes into both halves (previously all keyframes silently vanished).
- Import: single PushUndo AFTER the batch (was pushed before with empty state → import was not undoable); .mp3/.wav accepted by dialog are now skipped with reason instead of becoming dead "Media" clips; 3-char ext (".mv") false-positive fixed.
- Render: layer Opacity slider now affects text layers; track visibility eye actually hides the layer; Vignette uses params as labeled (radius/softness); Shake uses magnitude param as "px"; RGB Split uses px; Wave Warp freq/amp unswapped (UI sliders match effect).
- Home screen: Recent Projects now lists real scanned .aie files (was hardcoded "test_project"); resolution segmented control no longer shows 1440p/4K labels that silently create 1080p projects.
- Studio: titlebar timecode no longer divides by 0 fps (custom fps could crash); 3x3 grid toggle now draws the grid; PNG export renders the full-res composition (was a window screenshot); timeline footer shows total duration, not the zoom window.
- **Motion blur darkening fix (v2, root cause)**: taps render at slightly different camera positions, so edge pixels are covered by only some taps — dividing by total weight darkened them while alpha was forced to 255. Now tracks per-pixel accumulated weight (`wts[]`) and normalizes RGB by it; untouched pixels stay transparent.
- **Add FX (+) icon fix**: `OpenPopup` fired in the header (main window) but `BeginPopup` lives in `##eff_controls_child` — ImGui popups are window-scoped so it never opened. Flag bridge (`s_OpenAddFX` set in header, opened inside the child).
- **Shortcuts modal fix**: same window-scope bug — `OpenPopup("ShortcutsModal")` fired inside `HelpMenuPopup`, `BeginPopupModal` in the outer scope. Same flag-bridge fix (`s_OpenShortcuts`); Help → Keyboard Shortcuts now opens.
- **TRANSFORM & PROPERTIES header**: removed the "Add Text" button (text layers come from toolbar/Ctrl+T).
- **Timeline unlimited layers + scroll**: `maxTracks = max(usedTop+2, 5)` with no upper cap; `g_TrackVisible` is now a `std::vector<bool>` grown via `EnsureTrackSize()` at every track-assignment site; fixed 30px lane height with wheel + draggable-bar vertical scroll (`g_TimelineScrollY`, clip-rect culled, off-screen lanes/clips skip draw + hit-test); few lanes still stretch to fill. Auto-placement cap raised 32→256.
- **Track lock → motion blur**: lock icon/`g_TrackLocked`/`DrawLockIcon` deleted (drag-to-locked-track block removed); "MB" text toggle in each track header flips `motionBlur` on all clips of that track (lime = on, tooltip shows state); Mot.Blur checkbox removed from properties (shutter combo stays, shown only when MB is on); context menu "Toggle Track Lock" → "Toggle Motion Blur" on the selected clip.
- **Perf pass (`--bench N` harness + 5 fixes, all output-preserving)**: `aieator.exe <proj>.aie --bench N` renders N evenly-spaced `RenderPreview` frames headless (preview-scale + fullres, writes `bench.txt`). Text+Glow 88→23ms preview (540→84ms fullres); 720p video 31→21ms preview (144→96ms fullres render-only). Fixes: Glow V-pass runs once on the 1/4 image + nearest-upsample (identical values; also fixed latent OOB when width%4!=0); axis-aligned warp fast path for `rot==0` (bit-identical maps, ~1.6x); decode format COM query cached per video; integer BT.709 NV12 (pairwise CbCr, ±1 LSB); intermediate forward frames not converted; MB `sum`/`wts` persistent + per-tap `s_MbTap` clear (fixes inter-tap ghosting); 32-bit bg fill. Pixel-verified on real anime frames via headless PNG dump. ±15% run variance — don't chase smaller deltas.
- **Channel-cross bug family (4 FX wrote blended red into green/blue)**: Vignette, Grid Lines, Drop Shadow and Ghost all computed G/B from the already-overwritten R channel (red-tinted or over-whitened output). Fixed with per-pixel channel snapshots. Found by regex sweep; no other instances.
- **Glow kernel asymmetry**: kernel was copy-pasted from Gaussian as `(i-r)/r` but spans the small-image radius `br` — sampled only the gaussian's left tail, smearing halos off-center. Now `(i-br)/br` (symmetric). Changes existing glow output (from wrong to correct).
- **MB ignored layer opacity**: accumulation normalized tap alpha away and forced 255 — motion-blurred clips rendered fully opaque regardless of the Opacity slider/keys. Now reapplies current-frame `EvaluateClipOpacity*opacity` after normalize.
- **EncodeMP4 leak**: `IMFSample` leaked when `MFCreateMemoryBuffer` failed. Split the error paths.
- Dead-code removal: unused `gotFrames`/`lastSec` in `VideoGetFrame`, stale "Lock Icons" comment.
- **Warning sweep (`-Wall -Wextra`, our code now clean)**: split 4 misleading-indentation one-liner double-ifs (all false positives, zero behavior change); removed dead locals (`bokehGain`, `anyMedia`, `textCol`/`textDim`, `textTertiary`x2, `colCanvas`, `colWhite` in menu bar, `applyBtnY`, flicker-dump `i0`/`dummy`); dropped ignored `ReadSample` HRESULT (failure already surfaces as null sample); `(int)` casts on 5 ImGui size compares; `%08X`→`%08lX` for DWORD. Skipped as benign: `{0}`-idiom noise, `GUID{0}`, `GetProcAddress` casts, entry-point unused params.
- **Stress tests (temp projects, deleted after)**: odd-size comp (1281x721, glow+warp+MB paths) benched clean — the old glow code read 1 column OOB per row here; 12-track project confirmed unlimited lanes + visible scrollbar + correct clip/track mapping and top-track-wins compositing.
- **ITEM persistence fix**: `motionBlur`, `shutterAngle` and `opacity` were never saved — silently reset on reload. Now trailing ITEM cols 9-11 (`mb shutter opacity`); tolerant reader keeps old 8-col files on defaults, old binaries ignore the extras.
- **`--export <file.mp4>` flag**: headless `EncodeMP4` so the export path is regression-testable. First verified export: rotated+MB+0.7-opacity video under a glow title → valid 720p30 H.264, frame reads correct (rotation, MB brightness, opacity blend, compositing all confirmed in one frame).
- **Correctness + smoothness pass (3-audit sweep + effectcraft comparison, fixes verified by rebuild + bench + hostile-file tests)**:
    - Undo is now actually undoable: clip drag/trim pushed the snapshot AFTER mutating (Ctrl+Z restored the dragged state and wiped redo) — now pushed before the first write; same post-mutation bug fixed in Import (snapshot taken before the batch) and in split-guard (no-op split no longer pushes junk). New Project (menu + Ctrl+N) and Open now clear `g_Undo/g_Redo/g_SelMulti` (Ctrl+Z after New/Open used to resurrect the old project, Delete hit stale multi-select). "Deselect All" clears the batch too. Release-time drag push removed (it re-broke the fix).
    - Data-loss chain closed: Home "Create Project" kept the old `g_ProjectPath`, so autosave/Ctrl+S overwrote the PREVIOUS project with an empty one — `CreateNewProjectAction` now clears the path. `SaveProject` writes tmp + rename (a crash mid-write can't truncate the only copy). Load is hardened: RES clamped 16..8192 (100000x100000 malloc'd 10GB → null write), FPS NaN/0/negative → 30, track clamped 0..255 (10^9 lane scan per frame = hang), missing media pushes placeholders so later clips don't shift onto the WRONG image/video, `EnsurePrevBuffer` null-guards malloc failure. Hostile-file bench (RES 100000, FPS 0, track 10^9) exits 0.
    - Timeline uses window-time everywhere now: box/hit/marquee/trim/snap used raw `duration` while the renderer plays `duration*speed` — at Speed≠1 clips were un-grabbable and keys piled at the box edge. Trim math converts win↔media by `/speed`. New `TimelineItem.srcOff`: trim-left/split slip the footage instead of restarting it at the head (video seek was also `(t-st)*speed` = speed² off — now media-time `lt`; split carries `srcOff` into the right half). ITEM gets trailing col 12 (`srcOff`); old files default 0, old binaries ignore it.
    - FX time base: `ApplyFXPipeline` takes clip-local time — Shake (was `rand()` per repaint: different jitter every mouse move, dead Speed slider) and film grain (one frozen pattern from dead `p[1]`) are now deterministic per-frame hashes, Wave Warp animates (had no phase term), text RGB-glitch likewise.
    - FX param wiring: Drop Shadow read OffsetY as red / Blur as green / Alpha as blue with real alpha from unset `p[4]` = 0 (complete no-op from UI) + negative offsets over-read the heap — now `(ox,oy,alpha)` black shadow with bounds guard, Blur slider removed (never implemented), Outline clamped + white (generic Amount slider overflowed the uchar cast). Smart Depth mode read `p[6]` while the UI writes `p[3]` (selector dead, auto-blur too) — both read `p[3]` now. LUT saturation rebuilt (old math tinted everything red at any saturation — curve LUT + per-pixel lum). Vignette `v` clamped ≥0 (negative → UB bright ring). Fisheye `amt` clamped ≥-0.98 (1/0 exponent collapsed the frame). RGB Split Angle now offsets along the angle vector. EncodeMP4 uses float FPS for frame count + render times (29.97 drifted ~1s/30s). `VideoGetFrame` always unlocks a locked buffer; odd-width NV12 clamps the chroma read; `LoadVideo` validates the duration variant type.
    - Perf: Gaussian Blur was O(w·h·r) + per-frame kernel alloc (the #1 scrub stall) — now O(1)/px sliding box passes over premultiplied RGBA (also fixes the dark halo + razor alpha edge); Directional/Zoom/Motion-blur FX subsample taps above 16 (~3x). Text+Gauss50: 49.7ms preview / 136.7ms fullres; main project unchanged within run variance (34.6/121.6 vs 40.8/135.2 baseline — ±15% harness noise).
    - UI honesty + input: 1440p/4K/21:9 now create real projects (were silent 1080p/16:9; new `QUAL_1440P/QUAL_4K`, `ASPECT_21_9`, template fixed); F9 stamps Easy Ease on the selected layer (label said F9, nothing was bound); "Move to Track Above" cap 6→255; Motion Tile shows its real name/params in the inspector (`<43` bound excluded it); `--menu=file` test flag is one-shot (menu reopened every frame); shortcuts + clip-drag start ignore input while a popup/modal is open (clicks bled through to the timeline, Ctrl+N wiped the project behind the shortcuts list); DPI `ScaleAllSizes` moved after `ApplyTheme` (it resets the style); bezier handles latch only on the press frame (sweep-past grabbed them); bin-row delete keeps selection/multi-select indices correct.
    - GDI: text raster deleted the DC last — `DeleteObject` fails on selected-in objects, leaking a DIB + font per uncached raster (typewriter/RGB-glitch leak every frame) — DC is deleted first now.
- **Keyframes, markers, audio + efficiency pass (nothing skipped)**:
    - HOLD keys: `Key1D/Key2D.hold` (AE square key, frozen until next key) in `InterpKeys1D` + position loop, square drawing on lane + graph strip, inspector Hold checkbox, `Ctrl+C/V` single-key copy/paste at playhead, persisted as trailing K cols (old readers ignore).
    - IN-side ease: per-key `inEaseType/inBezCP`, segment curve composed effectcraft-style (`P1 = k1.out, P2 = (1-k2.inX, 1-k2.inY)` — either side linear leaves the other exact, so old projects render bit-identical). Inspector Key row edits Hold + Out/In combos (Custom adopts `g_BezCP`); preset cards/F9/custom-graph now stamp ONLY the selected key, whole layer when none selected; card highlight follows the selected key; custom editor loads the selected key's curve once per selection; new key strip under the grid shows the layer's real keys on a time axis (click = select).
    - Glow Threshold (soft knee, default 0.7) + Operation combo (On Top / Behind / Glow Only).
    - Markers (`M` add, `Shift+M` delete, drag on ruler, right-click delete, `,`/`.` navigate, magnet + clip-snap targets) + work area (`I/O` set, `X` clear, ruler bar, preview loops it, MP4 export renders exactly it — verified 3.000s). Persisted as `MARKERS`/`WORK` trailer; new/open project resets them. Markers are outside undo (navigation, not content).
    - Audio engine: second SourceReader decodes PCM @44.1k stereo on video import (180s cap ≈31MB), audio-only files (mp3/wav/ogg/flac/m4a) import as video-less clips (silent render, audible mix, waveform), `waveOut` feeder with instant stop on pause/scrub/mute + auto-resync on seeks and work-loop jumps, global mute (`A` + toolbar speaker), hidden tracks silent, 128-col waveforms on video clips, AAC mux in MP4 export with video-only fallback (verified: 5s export probes `audio=1 duration=5.015`; text-only export probes `audio=0`), failed exports delete the partial file + CLI exits nonzero, `--probe-audio <file>` verifier (always writes `probe.txt`, also reports video duration).
    - Efficiency keys: arrows (1-frame step, clip select), `G` grid, ripple delete, Edit-menu marker/work items, shortcuts modal documents everything. CLI exit codes via `g_ExitCode`.
    - Compromises kept: per-track audio SOLO dropped (no header room; mute + eye cover it); export audio uses timeline mix (no per-clip gain yet); roving keys + spatial motion paths still out (data-model breaks, effectcraft-scale jobs); audio decode is capped at 180s per file.
- **Theme/font/preview/FX-console/animation pass**:
    - Space Grotesk UI (Medium / SemiBold headings / Bold titles, already bundled — was silently falling back to Departure Mono since `fonts/Google_Sans/` never existed).
    - Home hero strip deleted (configurator + recents own the hub); 4:3 + 3:4 aspects added (7-up segmented, dimensions already handled).
    - Theme is now AMOLED + minimalism + brutalism: 2px radii, raw 1px white-22% edges (incl. window frames), pitch black, bone white, one volt accent on active states only; text buttons auto-size from padding (Close `120×0` → `0,0`).
    - Preview crispness/perf: paused renders at exact display size (was fixed 1/2 upscale = blurry) with re-render on resize, NEAREST magnification on 100%/200% zoom-upscale, playback keeps 1/2–1/4; verified brighter/crisp in screenshots.
    - `Ctrl+Space` FX console (FX-Console style): prefix-ranked fuzzy search over all 43 FX, Up/Down + Enter/click stamps with `InitFXDefaults`, stays open for multi-stamp, Esc closes; plain Space no longer toggles play while Ctrl is held.
    - Micro-animation kit (`AnimNowSec/EaseOutCubic/PopupEnterAlpha/DrawViewFade`): 150ms ease-in on all 7 menus/popups + console (fade + rise), 180ms black dip on home↔studio switches (skipped in `--screenshot` mode — captures fire on frame 3).

### Done in previous passes
- Video import plays sampled footage (MF NV12 decode).
- Preview viewport renders (dirty-driven, 1/2 quality default).
- MP4 export via `EncodeMP4` + PNG single-frame export (file dialog with both filters).
- Undo wired (`Ctrl+Z`/`Ctrl+Y`), Save wired (`Ctrl+S`), Delete wired (`Delete` key), Split wired (`R` key + razor button).
- Timeline toolbar razor icon → `SplitClipAtPlayhead()`.
- Viewer grid icon → toggle `g_ShowGrid3x3`; magnet icon → toggle `g_MagnetSnap`.
- 18 easing presets rendered as 4-column bezier curve visualization cards (parametric `BezierX`/`BezierY` sampling, grid dots, lime selection highlight).
- 25 Iconoir icons embedded via `DrawIconTex` helper (transport, undo/redo, grid, magnet, media, FX, cut, text, folder); source SVGs in `icons/`, baked by `icons_build.py`.
- Space Grotesk UI (Medium / SemiBold headings / Bold titles, bundled in `fonts/`).
- Exe/file icons embedded (Windres resource `app.ico` + `aie_icon.ico`).
- Shutdown cleanup: `FreeImages`, `FreeVideos`, `FreeIcons`, `MFShutdown` (verified graceful exit code 0).
- Dead code cleanup: removed ~35 one-shot build scripts, ~10 unused draw helpers, junk artifacts.

### Known compromises (`ponytail:`)
- NV12 YCbCr uses BT.709 limited-range fixed; no auto detection of transfer func.
- Video export blocks UI (synchronous loop); background thread if throughput matters.
- 1671 Iconoir SVGs available in `icons/` but only 25 embedded as runtime icon textures.
- Timeline audio icons (mute, headphones, equalizer) are decorative — no audio engine.
- Magnet snap applies to timeline clip drags (frame + playhead + adjacent-clip snapping); ruler scrub, playhead jumps and keyframe drags snap to frame.
- Graph editor custom bezier mode (`DrawBezierFlowCurveEditor`) writes to clip keys via `ApplyEaseAll` ("Apply Custom Graph to Layer"); per-key targeting (not clip-wide) is the remaining gap.
- **Intel iGPU red-tile flicker (investigated 2026-09):** tiny 8x4 tile-aligned red boxes flash for 1 frame at random positions. Confirmed NOT app draw data (ImGui vertices/atlas clean, artifact re-render of same data is always clean). Cause: Intel driver mis-reconstructs streamed GPU tiles. Mitigations shipped: `glFinish()` before UI render + double-render UI pass in both render paths (~7x fewer hits, zero crashes). Full fix attempt: persistent-mapped ring buffer in vendored backend (reduced to 0 hits / 2,100 frames) but this driver segfaults in ICD at process exit with mapped storage alive, even when ring is deliberately leaked — so the ring is kept in `imgui_impl_opengl3.cpp` behind `UsePersistRing` (default OFF; needs `glBufferStorage`/fences present + opt-in). Resume path: enable ring + replace `wglDeleteContext`-at-exit with `ExitProcess`-style teardown, or test newer Intel drivers.

### Validation
- `python capture_tests.py` captures Home + Studio + 3 themes.
- Graceful close verified (WM_CLOSE → exit code 0).

---

## Performance (floor: i3-4005U, 4GB DDR3 single-channel)

Usability target is the floor machine; numbers below are from the dev machine (i5-7300U), measured via `aieator.exe <project>.aie --bench N` (writes `bench.txt`, ±15% run variance):
- Text + Deep Glow, 960x540 preview: 88ms → 23ms/frame (~45fps scrub); 1080p fullres: 540ms → 84ms.
- 720p30 H.264 video, 1:1 frames: 31ms → 21ms/frame preview (~47fps scrub); fullres render-only 144ms → 96ms (~10fps before encode).
- Text-only: 4ms preview / 11ms fullres. Grade math already skipped on identity; text raster cached.

What the 2026-09 perf pass changed (all output-preserving, pixel-verified on real frames):
- Glow: vertical blur pass ran a 25-tap kernel per FULL-res pixel — now runs once on the 1/4 image + nearest-upsample (linear/shift-invariant ⇒ identical values, ~1/16th the gathers). Also fixed a latent 1-column OOB read when width % 4 != 0.
- Warp: axis-aligned fast path for `cam.rot == 0` (separable precomputed maps with the same recurrence ⇒ bit-identical; rotation keeps the general path). ~1.5-1.65x on all media renders. Grade block factored into `GradePixel` (inline, shared).
- Decode: `GetCurrentMediaType` COM query cached per video (never changes for a file reader); NV12→RGBA converted to integer BT.709 (x256, one CbCr load per pixel pair, ±1 LSB); intermediate forward-decode frames are no longer converted (timelapse/scrub only — sequential playback still converts every shown frame).
- Motion blur: `sum`/`wts` accumulators persist across frames (grow-once + memset, no per-frame multi-MB alloc); `s_MbTap` now cleared per TAP (media/text paths leave uncovered pixels untouched — old code leaked tap u-1's pixels into tap u = ghosting).
- `RenderPreview` background: single 32-bit fill (was memset + redundant loop).

Memory budget rules that keep it inside 4GB:
- Per video: exactly one cached RGBA frame (~3.5MB@720p, ~8MB@1080p), re-decoded on demand — never full-file buffering.
- Preview buffer scales with `g_PreviewScale` (quality combo 1.0 / 0.5 / 0.25); 0.25 is the low-RAM escape hatch.
- Undo/redo stores full `g_Clips` vector snapshots, capped at 50 entries per stack — watch this on very long projects.
- Everything else (FX scratch buffers, GDI text buffers, NV12 decode) is transient per-frame allocation.

---

## Third-Party Dependencies

`Dear ImGui 1.91`, `stb_image`, `stb_image_write`, Win32 (GDI/COM/DWM), OpenGL, Media Foundation (`mfplat`, `mfreadwrite`, `mfuuid`), WinMM (`winmm`, preview audio only). No FFmpeg/extra DLLs - by design.
