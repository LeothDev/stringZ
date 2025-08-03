# StringZ 🎮

**Translation QA Tool for Game Localization (ZGAME)**

StringZ automates tedious manual work in translation quality assurance, improving efficiency and consistency for game localization teams. Built specifically for handling game-specific formatting, variables, and large translation datasets.

---

## 🚀 Quick Start (Windows Users)

### Option 1: Simple Setup (Recommended for Teams)
1. **Download** the StringZ package (ZIP file)
2. **Extract** to any folder
3. **Double-click** `run.bat`
4. **Wait** for browser to open automatically
5. **Upload** your Excel file and start processing!

### Option 2: Manual Setup
```bash
# Install Python 3.8+ from https://python.org
# Make sure to check the "Add Python to PATH" section!

pip install -r requirements.txt
python app.py
```

---

## 🎯 Key Features

### 🔄 Smart Deduplication
- **Eliminates duplicate review work** - no more checking the same string multiple times
- **Tracks occurrence counts** - see how many duplicates each string pair (EN-TargetLang) has
- **Configurable strategies** - keep first, best (Recommended to leave the defaulted)

### 🧠 AI-Powered Similarity Grouping
> A better approach could be implemented by using powerful ML models, but they're memory hungry
> thus I opted for a simpler, but effective solution: Term Frequency-Inverse Document Frequency
- **Groups related strings together** using TF-IDF semantic analysis
- **Faster consistency checking** - similar strings appear consecutively (More frequently)
- **Configurable thresholds** - adjust sensitivity to your needs
- **Hybrid algorithm** - combines substring and semantic matching

### ⚠️ Game-Specific Validation
**Automatically detects common game localization errors:**
- **Color tags**: `<color="#hex">text</color>` validation
- **Game variables**: `{skm1}`, `{skm2}`, ability references `[123]`
- **Token mismatches**: Missing brackets, variables, formatting
- **Punctuation inconsistencies** between source and target
- **Malformed markup** with detailed error descriptions

> **⚠️ Important**: This tool complements Smartcat/CAT tools - it's not perfect!
> Some issues could be missed, false-positive could be introduced.
> Always review flagged issues manually and make use of the Visualizer!

### 📊 Interactive Visualizer
- **Standalone HTML file** - works offline, NDA-compliant
- **Pass/Fail review states** - track your LQA progress
- **Personal notes system** - add comments for yourself
- **Raw/Formatted toggle** - debug formatting issues easily
- **Professional dark theme** - easy on the eyes during long review sessions
- **Easy Copy feature** - just click on a text and copy directly the raw text to your clipboard!

---

## 📋 Supported File Formats

### Input Requirements
Your Excel file must contain these columns:
- **String ID**: `strId`, `ID`, `KEY_NAME`, or similar
- **English source**: `EN`, `English`, or `Source`
- **Target language**: Any other column name (e.g., `German`, `Spanish`, `中文`), will be automatically detected

### Supported File Types
- `.xlsx`
- `.xls` (Legacy Excel)

## 🛠️ Workflow

### 1. Upload & Column Detection
- Upload your translation file
- StringZ automatically detects ID, source, and target columns
- Choose your target language from detected columns
- "Load" button will work with the language you select; changing the language after loading the previous won't work.

### 2. Configure Processing
- **Remove Duplicates**: ✅ Recommended for LQA efficiency
- **Sort by Similarity**: ✅ Groups related strings for consistency
- **Advanced Settings**: Fine-tune similarity thresholds (The default parameters work best)

### 3. Review Results
- **📊 Results Tab**: Download processed files
- **🔍 Review Tab**: Browse grouped strings for consistency
- **⚠️ LQA Validation Tab**: Critical issues/warnings detection
- **🔍 String Comparison Tab**: Compare two strings for equality (Currently working on a way to highlight differences.)

### 4. Export Options
- **📊 Interactive Visualizer**: HTML file for offline LQA
- **📈 Processed Spreadsheet**: Clean Excel with deduplication, occurrences and strings sorted by similarity
- **Future**: High-priority strings (Strings with more than 5 duplicates)

--- 

## 🎮 Game Localization Focus

### What Makes StringZ Game-Specific?
StringZ understands game content, based on some instances I found myself encountering while proofreading:

**Supported Game Elements:**
```
Color damage tags: <color="#eadca2">500 damage</color>
Skill variables: Deal {skm1} damage to {skm2} enemies
Ability references: Use ability [123] to cast [456]
UI formatting: Stats\\nDamage: 50%\\nSpeed: +25%
Punctuation: If source ends with a period, the target should too
```

**Common Issues Detected:**
> **IMPORTANT** Some of the Validator features don't work with asian languages.
> As of now the tool was tested only on German and Italian.
> It makes heavy use of regex, so careful attention is mandatory even after validation!
- Missing color tags in translations
- Inconsistent punctuation in UI text
- Malformed markup that breaks games

### Why This Matters
- **Prevents runtime crashes** from malformed tags
- **Maintains game functionality** with proper variables
- **Ensures UI consistency** across languages
- **Saves debugging time** by catching errors early

---

## ⚙️ Technical Details

### Architecture (Modular Flask App)
```
StringZ/
  app/
  ├── routes/           # Web endpoints
  ├── services/         # Business logic
  ├── static/           # CSS, JS
  └── templates/        # HTML templates (Visualizer)
  src/stringZ/
  ├── core/             # Deduplication, correlation algorithms
  ├── export/           # HTML visualizer generation
  ├── models            # Data structures
  ├── validation/       # Game-specific validation rules
  ├── ui                # Deprecated - Old Streamlit
  └── utils             # Extra functions to process data/
  app.py                # Main application entry point
  config.py             # Configs of the Flask server
  run.bat               # Windows launcher
```

### Processing Pipeline
1. **Excel Import** → Detect columns, validate structure
2. **Deduplication** → Remove identical source+target pairs
3. **AI Clustering** → Group similar strings using TF-IDF
4. **Validation** → Check game-specific formatting rules
5. **Export** → Generate visualizer and processed spreadsheet

## 🔧 Configuration Options

### Similarity Algorithms
- **Hybrid** ⭐ (Recommended): Best of substring + semantic
- **Semantic**: AI-powered contextual similarity
- **Substring**: Fast pattern-based matching

### Advanced Parameters
- **Similarity Threshold**: 0.5-0.9 (how similar to group)
- **Max Cluster Size**: 5-30 (strings per group)
- **Min Substring Length**: 3-15 (minimum match length)

---

## 🚨 Troubleshooting

### Common Issues
**"Python not found"**
- Install Python from https://python.org
- ⚠️ **Important**: Check "Add Python to PATH" during installation

**"No columns detected"**
- Ensure your Excel has `strId`/`ID`, `EN`/`English`, and target language columns
- Check column names match expected patterns

**"Validation shows false positives"**
- This is normal - no validator is perfect
- Always manually review flagged issues
- Use alongside the Visualizer and Smartcat

**Browser doesn't open automatically**
- Manually visit: http://127.0.0.1:5000
- Check if antivirus is blocking the connection

## 🤝 Feedback & Support

StringZ is actively developed for ZGAME localization workflows. 

**Report issues or suggestions:**
- Internal feedback: [Leoth - Feishu](https://www.feishu.cn/invitation/page/add_contact/?token=e89qd085-9025-4428-a40a-bed0f04239c5&amp;unique_id=_KLbHUPuq7nBhKtRj_PQDw==)
- Feature requests welcome
- Bug reports help improve accuracy

## 📄 License

MIT License - Internal tool for ZGAME LQA Members

---

**🎮 Built by an LQA Tester, for LQA Testers**
*Automate the tedious stuff, focus on the translation quality*

### Recent Updates
- ✅ **Flask Web Interface** - Modern web-based UI
- ✅ **Modular Architecture** - Easier maintenance and features
- ✅ **Improved Validation** - Better game-specific error detection
- ✅ **Team Distribution** - Easy setup with run.bat for Windows
- 🔄 **In Progress**: Enhanced export options, batch processing
