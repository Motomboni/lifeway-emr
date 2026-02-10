# WeasyPrint on Windows (MSYS2 + GTK)

This guide installs WeasyPrint’s system dependencies (Pango, Cairo, etc.) on Windows using MSYS2, so your **existing Windows Python** (e.g. in `.venv`) can generate PDFs.

**Requirements:** 64-bit Windows, 64-bit Python (3.10+). Your Python and GTK must both be 64-bit.

---

## Step 1: Install MSYS2

1. Download the **x86_64** installer: [https://www.msys2.org/](https://www.msys2.org/)
2. Run the installer and use the default path: `C:\msys64`
3. When the installer finishes, it may open an MSYS2 shell. Close it; we’ll use it in the next step.

---

## Step 2: Install GTK and dependencies in MSYS2

1. Open **Start Menu** → **MSYS2 UCRT64** (or **MSYS2** → **UCRT64**).
2. In the UCRT64 terminal, run:

```bash
pacman -Syu
```

If it says to close the window and run again, do that, then run `pacman -Syu` once more.

3. Install GTK and related libraries (Pango, Cairo, GDK-PixBuf are pulled in automatically):

```bash
pacman -S mingw-w64-ucrt-x86_64-gtk3
```

Or for GTK4:

```bash
pacman -S mingw-w64-ucrt-x86_64-gtk4
```

4. Confirm with `Y` when prompted.

---

## Step 3: Add MSYS2 UCRT64 to your Windows PATH

Your Windows Python must see the MSYS2 DLLs. Add the UCRT64 `bin` folder to the **system** or **user** PATH.

**Option A – PowerShell (current user, permanent):**

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\msys64\ucrt64\bin", "User")
```

**Option B – System Properties (GUI):**

1. Press **Win + R**, type `sysdm.cpl`, Enter.
2. **Advanced** tab → **Environment Variables**.
3. Under **User variables** or **System variables**, select **Path** → **Edit** → **New**.
4. Add: `C:\msys64\ucrt64\bin`
5. OK out of all dialogs.

**Important:** Put `C:\msys64\ucrt64\bin` **before** any other path that might contain conflicting DLLs (e.g. old GTK or ImageMagick).

---

## Step 4: Restart your terminal

Close and reopen PowerShell (or Cursor/IDE) so the new PATH is picked up.

---

## Step 5: Install WeasyPrint in your project

From your project backend folder, using your existing venv:

```powershell
cd "C:\Users\Damian Motomboni\Desktop\Modern EMR\backend"
.\.venv\Scripts\Activate.ps1
pip install weasyprint
```

---

## Step 6: Verify

```powershell
python -c "from weasyprint import HTML; print('WeasyPrint OK')"
```

If you see `WeasyPrint OK`, backend PDF generation (receipts/invoices) will use WeasyPrint. If you see an error about missing DLLs, check:

- Python is **64-bit**: `python -c "import sys; print(sys.maxsize > 2**32)"` → `True`
- PATH contains `C:\msys64\ucrt64\bin` and you restarted the terminal after adding it.

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `DLL load failed` or “could not import external libraries” | Ensure `C:\msys64\ucrt64\bin` is in PATH and you’re using 64-bit Python. Restart terminal. |
| Wrong architecture | Use 64-bit Python with UCRT64 (not 32-bit Python or MINGW32). |
| PATH not updated | Restart PowerShell/IDE after changing PATH. |
| Still failing | Try GTK3 instead of GTK4 (or vice versa): `pacman -S mingw-w64-ucrt-x86_64-gtk3` and ensure `ucrt64\bin` is in PATH. |

---

## Optional: Check Pango in MSYS2

Inside **MSYS2 UCRT64**:

```bash
pango-view --version
```

If that works, the libraries are installed; the remaining step is making them visible to Windows Python via PATH.
