# 🎨 SimpleImageEditor (Dark Blue Edition)

A raster-vector graphics editor built using `tkinter` (with `ttk` custom styling) and the `Pillow (PIL)` imaging engine. Designed with a modular grid, adaptive canvas scaling, multi-layer logic for object selection, and global hotkeys.

## 🛠 Dependencies & Deployment

Requires `Pillow` and `matplotlib` for filter processing and font parsing.

### Package Installation
```bash
pip install Pillow matplotlib
```
### Application Launch
```bash
python image_editor.py
```
## 🏗 Architectural Features & Algorithms

* Optimized Flood Fill: Uses an iterative BFS approach (via `collections.deque`) instead of recursive methods to prevent stack overflow errors during large-resolution processing.
* Non-destructive History (Undo/Redo): Caches state as immutable `PIL.Image.copy()` objects with a strict `MAX_HISTORY = 30` limit to prevent memory leaks.
* Isolated Selection Layer: When using `select_rect`, the area is programmatically cropped and projected as an independent object, with automatic merging upon tool switching or double-clicking.
* Dynamic Typography: Utilizes `matplotlib.font_manager` to scan OS directories for real-time font path mapping, avoiding hardcoded dependencies.

## ⌨️ Controls & Hotkeys

### System Operations
* Ctrl + N — New Canvas (800x600px)
* Ctrl + O — Import Image
* Ctrl + S — Save Canvas

### Tool Selection
* Ctrl + 1 — Pencil
* Ctrl + 2 — Line
* Ctrl + 3 — Rectangle
* Ctrl + 4 — Oval
* Ctrl + 5 — Flood Fill
* Ctrl + 6 — Selection
* Ctrl + 7 — Text
* Ctrl + 8 — Eyedropper
* Ctrl + 9 — Eraser

### Transformation & History
* Ctrl + Z — Undo
* Ctrl + Y — Redo
* Ctrl + Enter — Crop selection
* Double-click — Fix selection/Deslect
