# K-State Baseball — Arm Care Command Center (Streamlit)

The Command Center and the Throw Log are now one app. The sidebar has **Team**, **Pitchers** and **Position Players**.
Touch a player to open his file. It has four sections:

| Section | What's in it |
|---|---|
| **Daily Throwing Log** *(pitchers only)* | The full Throw Log app: Throw Log, Dashboard (ACWR), Day Type Templates and Next Outing Planner, plus Avg Top Velo and an attachable throwing-log workbook |
| **Performance Metrics** | ForceDecks CMJ results for each test day, with rank vs. the team, change since the last test, and a trend chart |
| **Performance Assessment** | Body map, flags, ROM (dominant vs. non-dominant), grip & pinch, screens and the assessment note. Every field can be edited |
| **Correctives** | The exercise program with video links, a program file (PDF, image or video), notes, the exercise library, and *Start new program* (archives the old one to history) |

**Team** shows all 36 tiles, the staff throwing overview (ACWR zone, spike, next outing, editable velo), force-plate rankings, and the by-region assessment table with grading criteria.

**Everything saves automatically**: there are no Save buttons.

## Run it in VS Code

1. Open this folder in VS Code (**File ▸ Open Folder…**).
2. Open `run.py` and click **▶ Run Python File** (top right).
   The first run installs Streamlit and the other packages, then the app opens at http://localhost:8501.
3. To stop it, click in the VS Code terminal and press **Ctrl+C**.

You can also open **`Command_Center.ipynb`** and run its cells in order, or run `pip install -r requirements.txt` and then `streamlit run app.py` in a terminal.

## Data

Everything is saved in `data/command_center.db`, a SQLite file. To back it up, copy that file, or use **Sidebar ▸ Import / backup ▸ Prepare Excel backup**. That backup has one sheet each for the roster, throw log, assessment, correctives, force plate and exercise library.

The first run builds that database from two sources:

- `data/seed_command_center.json` holds everything from the Arm Care Command Center: 36 athletes, their assessments, 35 photos (in `data/photos/`), corrective programs, Griffin Lewis's program PDF (in `data/files/`), 333 ForceDecks tests and 139 exercises in the library.
- `data/ACWR Throwing Plan Fall 2026.xlsx` holds the throw-log data: jersey numbers, year and B/T for the 21-man staff, Adam Arther's velo, his 30 logged sessions and his next-outing target.

If you delete `command_center.db`, the app rebuilds it from those two files.
**Sidebar ▸ Import / backup** also takes a new ACWR workbook or a new ForceDecks CMJ export (.csv).

> **Streamlit Community Cloud:** the SQLite file lives on the app's server disk. Streamlit Cloud wipes that disk when the app reboots or redeploys, and the app then rebuilds from the seed files. Download an Excel backup regularly. For data that has to survive reboots, point `THROW_DB` at a persistent disk, or move storage to a hosted database.

## Model

All the throwing-workload constants are in `model.py`. That file is unchanged from the Throw Log app, and its values come from the workbook's Reference tab.
The assessment thresholds (GIRD, ER/flexion deficits, elbow asymmetry, hip extension, screens) are in `assess.py` and match the Command Center exactly.

Assessment fields were extracted from scanned intake forms. Treat any flag as "go verify the original form," not as a diagnosis.
For internal K-State Baseball sports medicine staff use only.
