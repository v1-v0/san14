# san14

# RTK14 Recruitment Log Analyzer

A Python tool for analyzing **登庸 (recruitment)** events from _Romance of the Three Kingdoms XIV_ (三國志14) game logs. It parses recruitment attempts from an Excel log, generates cleaned data and statistics, and visualizes recruiter–target relationships as network graphs.

---

## ✨ Features

- **Log parsing** — Extracts successful, failed, cancelled, and prisoner-system recruitments from raw game log text.
- **OCR/typo correction** — Built-in dictionary fixes common character recognition errors (e.g. `簡庸 → 簡雍`, `越雲 → 趙雲`).
- **Statistics**
  - Recruiter performance: total attempts, successes, failures, and success rate.
  - Target difficulty: most-attempted targets across the campaign.
- **Network visualizations** (PNG):
  - ✅ Successful recruitments network
  - ❌ Failed recruitments network
  - ⚠️ Outstanding targets — failed targets that were _never_ recruited by anyone
- **CJK font auto-detection** — Automatically picks a Chinese-capable font for plot labels.

---

## 📦 Requirements

- Python 3.9+
- Packages:
  - `pandas`
  - `numpy`
  - `openpyxl` (for Excel I/O)
  - `networkx`
  - `matplotlib`

Install with:

```bash
pip install pandas numpy openpyxl networkx matplotlib
```

### Chinese font (required for proper label rendering)

The script searches for one of the following installed fonts:

- Microsoft JhengHei / YaHei, SimHei
- PingFang TC/SC, Heiti TC/SC
- Noto Sans CJK TC/SC/JP
- WenQuanYi Zen Hei
- Arial Unicode MS

**Linux users** can install Noto CJK fonts via:

```bash
sudo apt install fonts-noto-cjk
```

---

## 📁 Input Format

The script expects an Excel file (`.xlsx`) with at least these columns:

| Date     | Actions            |
| -------- | ------------------ |
| 200年1月 | 劉備登庸關羽成功   |
| 200年2月 | 曹操登庸關羽失敗   |
| 200年3月 | 中止登庸張遼       |
| 200年4月 | 成功登庸了俘虜張郃 |

- **`Date`** — Any date/turn label (kept as-is for reference).
- **`Actions`** — Raw log line. The parser matches these patterns:
  - `{recruiter}登庸{target}成功` → Success
  - `{recruiter}登庸{target}失敗` → Failed
  - `{recruiter}中止登庸{target}` → Cancelled
  - `成功登庸了俘虜{target}` → Prisoner system (recruiter recorded as `(俘虜系統)`)

If the `Actions` column is missing, the script falls back to the last column of the sheet.

---

## ⚙️ Configuration

Edit the constants at the top of `dev.py`:

```python
INPUT_FILE = "~/Downloads/san14_recruitment.xlsx"
OUTPUT_CLEANED = "recruitment_parsed.csv"
OUTPUT_STATS = "recruitment_stats.xlsx"
OUTPUT_GRAPH_SUCCESS = "~/Downloads/recruitment_network_success.png"
OUTPUT_GRAPH_FAILED  = "~/Downloads/recruitment_network_failure.png"
OUTPUT_GRAPH_OUTSTANDING = "~/Downloads/recruitment_network_outstanding.png"
```

### Extending OCR fixes

If your log contains other misrecognized characters, add them to the `NAME_FIXES` dictionary:

```python
NAME_FIXES = {
    "簡庸": "簡雍",
    "越雲": "趙雲",
    # add your own entries here
}
```

⚠️ Be cautious with ambiguous one-character keys — they may overcorrect unrelated text.

---

## 🚀 Usage

```bash
python dev.py
```

The script will:

1. Load and clean the Excel log
2. Parse all recruitment events
3. Save a cleaned CSV (`recruitment_parsed.csv`)
4. Generate an Excel report with three sheets:
   - `All_Events` — every parsed recruitment
   - `By_Recruiter` — performance per officer
   - `By_Target` — difficulty per target
5. Render three network PNGs (success / failure / outstanding)
6. Print top recruiters, most-attempted targets, and outstanding targets to the console

---

## 📊 Output Files

| File                                  | Description                                               |
| ------------------------------------- | --------------------------------------------------------- |
| `recruitment_parsed.csv`              | All parsed events (recruiter, target, result, type, date) |
| `recruitment_stats.xlsx`              | Multi-sheet statistics report                             |
| `recruitment_network_success.png`     | Green-edged graph of successful recruitments              |
| `recruitment_network_failure.png`     | Red-edged graph of failed attempts                        |
| `recruitment_network_outstanding.png` | Red graph of targets who escaped recruitment entirely     |

### Graph legend

- **Blue nodes** — recruiters / officers
- **Pink/red nodes** — outstanding targets (in the outstanding-network plot only)
- **Edge thickness** — proportional to number of attempts
- **Edge label** — shown only when the same pair attempted recruitment more than once

---

## 🗂 Project Structure

```
san14/
├── dev.py                       # main analyzer script
├── recruitment_parsed.csv       # generated
├── recruitment_stats.xlsx       # generated
└── README.md
```

---

## 🐛 Troubleshooting

**Chinese characters appear as boxes (`☐☐☐`)**
Install a CJK font (see Requirements). The console will print `[font] No CJK font found` if none is detected.

**`FileNotFoundError` on the input file**
Verify the `INPUT_FILE` path. The default is `~/Downloads/san14_recruitment.xlsx`.

**Regex misses some lines**
The patterns assume names are 2–4 characters. If your log contains longer names or extra formatting (e.g. brackets, dates inline), adjust `PAT_SUCCESS`, `PAT_FAIL`, `PAT_CANCEL`, and `PAT_PRISONER` in the source.

**Wrong recruiter or target after parsing**
Add an entry to `NAME_FIXES` to correct OCR drift before regex matching.

---

## 📜 License

MIT (or your preferred license — update this section accordingly).

---

## 🙏 Acknowledgements

Built for analyzing playthroughs of **Romance of the Three Kingdoms XIV** (KOEI TECMO). Not affiliated with or endorsed by the publisher.
