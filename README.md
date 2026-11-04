<h1><img src="docs/icon.png" width="40" align="top"> Maple Classic Exp Overlay</h1>

**A free EXP tracker for MapleStory Classic World.** A small window sits next to the game and shows how fast you're leveling and making mesos, and the [best maps for your class](https://mcwo.app).

**[Download it here](../../releases/latest)** · [How to install](#how-to-install)

> **This is a beta.** It works, but you might run into rough edges. I'm actively improving it, so check back for updates. If something doesn't work, please [tell me](../../issues)!

![The overlay next to MapleStory, while farming](docs/screenshot-game.jpg)

## What it shows

![The overlay up close, with its log open](docs/screenshot-main.png)

- **EXP per hour**, for your whole session and for the last 5 minutes, and how long until your next level
- **Mesos per hour**, read from your inventory, and **net mesos per hour** (minus what your potions cost)
- **A log of every map you farm**: EXP/hr and mesos/hr there, at which level and class, solo or in a party

You don't type anything in. It reads all of this from your game screen by itself.

## How to install

### On Windows (10 or 11)

1. Go to the **[download page](../../releases/latest)** and, under **Assets**, click the **Maple-Classic-Exp-Overlay-v….zip** file. (Not "Source code".)
2. **Right-click** the zip in your Downloads folder, choose **Extract All...**, then **Extract**. Double-clicking it isn't enough.
3. Open the new folder, then **Maple Classic Exp Overlay** inside it, and double-click **Maple Classic Exp Overlay.exe** (it may show as just **Maple Classic Exp Overlay**, with a gold chart icon).

**"Windows protected your PC"?** Click **More info**, then **Run anyway**. Windows shows this for any new program that isn't from a big company.

**Keep the whole folder together:** the program needs the files next to it. To put it on your desktop, right-click the .exe and choose **Send to > Desktop (create shortcut)** (on Windows 11, under **Show more options**).

### On macOS

It works with the game's own Mac version, or the Windows one through CrossOver, Whisky, Parallels or a game stream. **A test download: I don't own a Mac, so I haven't tested it myself** (GitHub's automatic tests run on a real Mac, but not with the game). A player has confirmed it works on an Apple Silicon Mac with Nexon's Mac launcher; Intel isn't confirmed yet. The Mac version comes from thanhphamvan's, fabriciorby's and cpaez33's work, and they tried it with the game. If you try it, please tell me how it goes.

1. On the [download page](../../releases/latest), pick the file for your Mac (needs macOS 14 or newer). Apple menu > About This Mac: **Apple M1/M2/M3/M4** = `...-macOS-AppleSilicon.dmg`, **Intel** = `...-macOS-Intel.dmg`.
2. Open it and drag **Maple Classic Exp Overlay** onto Applications.
3. Open it once (macOS refuses it, because it isn't signed with an Apple developer account). Then **System Settings > Privacy & Security**, scroll down to "Maple Classic Exp Overlay was blocked", click **Open Anyway**, and confirm. If that button doesn't show up, run this in Terminal once, then open the app again: `xattr -dr com.apple.quarantine "/Applications/Maple Classic Exp Overlay.app"`
4. Allow it in **System Settings > Privacy & Security > Screen Recording** (it reads the game from the screen), then start it again. If macOS asks whether to let the app bypass the system's private window picker to access the screen, click **Allow** and start it again. macOS may ask again after an update. The game window is found by "MapleStory" in its title; if it isn't found, use **Select area**.

Hotkeys aren't available on macOS yet.

## How to use it

1. **Start MapleStory**, then the overlay. It finds the game window by itself.
2. **Don't cover** the minimap, the EXP bar, the mesos at the bottom of your inventory or the party list with the overlay. It tells you if it's in the way.
3. **Press Start** and play. It pauses by itself after 15 seconds without EXP or when you leave the map, and carries on at your next EXP. A new map starts new numbers (unless **No Reset** is on).
4. **For mesos,** open your inventory when you start and now and then. **For net mesos,** keep your potions on the quick-slot bar.

| Control | What it does |
|---|---|
| **Start / Pause** | Starts and stops tracking |
| **Reset** (round arrow) | Starts over from zero |
| **Log this run** | Turn it off to keep this run out of the log. It turns itself back on after the run. |
| **No Reset** | For farming across maps: changing maps doesn't start new numbers. These runs stay on your PC. |
| **Best maps** | Opens [mcwo.app](https://mcwo.app) for your level, party size and class |
| **...** (More) | **View capture** shows what it read; **Select area** if it can't find the EXP numbers |
| Log, compact and ⚙ icons | The log, a smaller window (Square, Wide or Bar), and Settings |

Hotkeys (Windows): **Shift+1** Start/Pause, **Shift+2** Reset, **Shift+3** Log this run, **Shift+4** Compact. Change them in ⚙.

**More:** the [full guide](docs/guide.md) has the log, compact shapes, hotkeys, every setting, net mesos and potions, the best-maps site and how accurate it is.

## Something not working?

**Click View capture first** (in **...**). It shows exactly what the overlay read.

| Problem | Try this |
|---|---|
| An error when you open the .exe | Extract the zip first (step 2). It can't run from inside the zip or away from its folder. |
| "MapleStory window not found" | Start the game first, and bring it back up if it's minimized. |
| "Can't find the EXP bar" | Make sure nothing covers the bottom of the game, the overlay included. A very small game window: make it bigger. |
| Mesos says "open inventory" | Open your inventory and make sure the mesos at its bottom aren't covered (in small windows the chat bar can). |
| The map name is wrong | Right-click the log line, **Rename map**. |
| Anything else | ⚙ > **Report a bug**: **Send to the developer** (no account needed, you see what's sent) or on GitHub. |

More fixes: [the full guide](docs/guide.md#something-not-working).

## Is it safe? Is it allowed?

- **Only download it from this repository's [Releases](../../releases).** Other people have copied the code (that's allowed, it's open source), but their copies aren't mine and I haven't checked them. Mine are built by GitHub, and you can [check that](docs/download.md).
- **It only looks at your screen**, like a screen recorder. It never touches the game's files or memory, and never presses keys or clicks for you.
- **Your log, notes, settings and potion data stay on your PC.** It only goes online to check for updates, and, only if you said yes, to share finished 15-minute runs with the best-maps site and send a daily health report (numbers only). The update check, sharing and health reports can each be turned off in ⚙. A bug report goes only when you send it. Nothing about who you are is sent. Details: [Privacy](docs/privacy.md).
- **Your antivirus might warn about it** by mistake. All of the code is public right here, so anyone can check what it does.
- **It isn't made by or affiliated with Nexon.** Like any third-party tool, you use it at your own risk.

## Updates

When a new version is out, the overlay tells you when it starts. Download the new version and use it instead of the old one: your log, notes and settings stay. What changed: [CHANGELOG.md](CHANGELOG.md).

### Code signing policy

Free code signing from [SignPath Foundation](https://signpath.org) is planned, so Windows stops warning about new downloads. Only builds made by the Build workflow from this repository are signed.

- Committers and reviewers: [beanguri](https://github.com/beanguri)
- Approvers: [beanguri](https://github.com/beanguri)
- Privacy policy: see [Privacy](docs/privacy.md). In short: your log and notes stay on your PC, and the overlay only sends anything to another system if you turn on sharing your finished 15-minute runs or the daily health report (both off until you say yes, and you can turn them off any time in Settings), if you click **Send to the developer** on a bug report, or to check GitHub for a newer version (can be turned off too).

## More

- [Full guide](docs/guide.md) · [Privacy](docs/privacy.md) · [Where the download comes from](docs/download.md) · [For developers](docs/developers.md) (run from source, build, tests, forking)
- Credits: the [EXP table](https://meowdb.com/msclassic/guides/exp-table-level-1-to-100) (used to work out your level) and the [list of map names](https://meowdb.com/msclassic/maps/all) (`assets/maps.txt`) are from meowdb, a fan-made MapleStory Classic database (thank you). Map names are read with [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache 2.0 license), included in the download. The typeface is [Manrope](https://github.com/googlefonts/manrope) (SIL Open Font License, `assets/fonts/OFL.txt`).
- License: [MIT](LICENSE): free to use, change and share.
**Credits:** the list of the game's map names (`assets/maps.txt`) comes from [meowdb.com](https://meowdb.com/msclassic/maps/all), a fan-made MapleStory Classic database (thank you). The typeface is [Manrope](https://github.com/googlefonts/manrope) (SIL Open Font License, included as `assets/fonts/OFL.txt`).

## Updates

This is a beta, and I'm still adding features and fixing things.

**New name:** since v0.9.3 it's called Maple Classic Exp Overlay. It used to be Maple EXP/hr. Your log and settings carry over.

**When a new version is out,** the overlay tells you when you start it, and shows what's new. Click **Get the update** to open the download page, or **Not now** / **Skip this version** if you'd rather wait.

**To update:** download the newest zip from the [download page](../../releases/latest) and use it instead of the old folder. Your log, notes and settings stay, because they're saved separately (⚙ → **Open data folder** shows where).

**To remove it:** delete its folder. To also delete your log and settings, delete the folder that **Open data folder** opens.

See [CHANGELOG.md](CHANGELOG.md) for what changed in each version.

---

<details>
<summary><b>For developers</b></summary>

**Run from source.** You need Python 3.10 or newer, and [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for map names.

```
py -3 -m pip install -r requirements.txt
run.bat
```

**On macOS** (from source only, with the game running through CrossOver, Whisky, Parallels or a game stream): macOS support was written by thanhphamvan, who tried it on a real Mac with the game. I don't own a Mac, so I can't test it myself: GitHub's automatic tests run on a real Mac, but not with the game. If you try it, please tell me how it goes.

**How to run it on a Mac:** `brew install tesseract`, then `python3 -m pip install -r requirements.txt` and `python3 maple_exp.py`. The first time, allow your Terminal (or Python) in **System Settings > Privacy & Security > Screen Recording**, then start it again. The window is found by "MapleStory" in its title; if it isn't, use **Select area**. Hotkeys aren't available on macOS yet.

**On Linux** (from source, with the game running through Steam/Proton, Lutris or Wine): install Tesseract (`sudo apt install tesseract-ocr`, `sudo pacman -S tesseract`, or your distribution's package), then

```
python3 -m pip install -r requirements.txt
python3 maple_exp.py
```

The window is found by "MapleStory" in its title or window class (Wine, Proton and Lutris name the program after the game's `.exe`, which is how it's told apart from a browser tab). Following the game reads the game's **own window**, so this app can sit on top of the EXP bar, and it works in a Wayland session too. **Select area** is a picture of the whole screen, which a Wayland session doesn't allow: log in with X11 (Xorg) to use that. Hotkeys work while MapleStory or the overlay is in front.

Everything that differs between Windows, macOS and Linux (finding the game window, screen scaling, hotkeys, the one-copy-at-a-time lock) is in `platforms/`: one `Platform` interface in `base.py`, one implementation per OS, and `create_platform()` picks the one for the OS it's on.

**Build the download** (puts `Maple-Classic-Exp-Overlay-v<version>.zip` in `release/`, and a copy to use right away in the project folder: `Maple Classic Exp Overlay.exe` with its `_internal` folder):

```
py -3 -m pip install -r requirements.txt pyinstaller
py -3 build.py
```

**Testing never shares anything:** with `MAPLE_EXP_DATA` set (it moves the data folder, which is how the tests keep away from your real log), the overlay refuses to send runs to the real site, so made-up test runs can't end up there. (Set `MAPLE_EXP_ALLOW_SHARE=1` only to test against a local copy of the server.)

**Run the tests:**

```
py -3 tests/test_logic.py
py -3 tests/test_screen.py
py -3 tests/test_ui.py     # opens the real window for a few seconds (the notes box)
```

The report-a-bug checks in `test_ui.py` are turned off when `MAPLE_EXP_TEST_REPORT` isn't set; set it to `1` to run them.

To build with exactly the packages the releases use: `py -3 -m pip install --require-hashes -r requirements-build.txt`.

GitHub runs the logic tests on every push ([Tests workflow](.github/workflows/tests.yml)). The [Build workflow](.github/workflows/build.yml) builds the download on GitHub (Actions tab, **Build**, **Run workflow**), runs all the tests first, and signs the .exe once code signing is set up. Pushing a version tag also attests the zip and drafts the release with it; releases are only ever made that way.

**The stats site** is in `server/`: a Cloudflare Pages site with a D1 database (free tier). The page is `server/public/`, the API is `server/src/index.js`. `npm --prefix server install`, then `npm --prefix server run dev` runs it locally, `py -3 server/test_server.py http://localhost:8787` tests it, and `npm --prefix server run deploy` puts it online.

**How it reads the screen:**
- It finds the `MapleStory.exe` window, then the EXP numbers (like `12,345 [12.34%]`) in the status bar.
- Each digit is resized to a standard size and compared against saved examples of the game's font in `assets/`.
- A reading only counts if the EXP and % agree with how much EXP that level needs, so misreads are ignored.
- Mesos are read the same way. The mesos box is found by its outline, which also works while the inventory is see-through.
- The potion counts, your level (the orange **LV** badge) and the EXP number are read with the game's own font, drawn from `assets/fonts_v2/`; the party size by the exact shape of the party list's HP bars (`assets/party_shapes.json`). The older EXP reader and party count stay as a backup. Mesos are still read the older way; a newer mesos reader runs in a test mode that only compares and never changes a number you see; the daily health report counts how often the readers agree.
- The party size is the number of HP bars in the party list.
- Map names are read with Tesseract.
- Settings, the log and `errors.log` are saved in `%APPDATA%\MapleEXP` (`~/Library/Application Support/MapleEXP` on macOS; from its old name, Maple EXP/hr, so updates keep them).

</details>

## Forking or changing this code

[MIT](LICENSE) lets you change and share this code. One request: **a changed copy must not send anything to mcwo.app.** The site takes shared runs, daily health reports and bug reports only from official releases, so it turns down versions it doesn't know. Numbers from a changed copy would only add noise to the Best maps and the health numbers.

To turn sending off, or point it at your own server, in `maple_exp.py`:

- `STATS_SITE` is the website's address. Change it to your own server.
- `post_runs`, `post_health` and `post_report` are the three functions that send to it. Make them do nothing (or raise) to stop sending.
- `check_for_update` asks GitHub for the newest release of this project. Point `GITHUB_REPO` at your own, or make it do nothing.

The checks are only about the version number: a copy that keeps a real release's version number can't be told apart, so please don't do that.

## Credits

- The Classic World EXP table is from [meowdb](https://meowdb.com/msclassic/guides/exp-table-level-1-to-100). It's used to work out your level.
- Map names are read with [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache 2.0 license), which is included in the download.

## License

[MIT](LICENSE): free to use, change and share.
