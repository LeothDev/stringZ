# StringZ 🎮

**Professional Translation QA Tool for ZGAME**

StringZ is a comprehensive translation quality assurance platform designed specifically for game localization workflows. It automates duplicate detection, intelligently groups similar strings using AI, and provides robust validation for game-specific formatting requirements.

## 🎯 Key Features

### 🔄 Smart Deduplication
- **Automatic duplicate detection** with occurrence counting
- **Multiple deduplication strategies** (keep first, keep best, keep with occurrences)
- **Intelligent grouping** of identical source+target combinations
- **Translation completion tracking** and metrics

### 🧠 AI-Powered Similarity Sorting
- **Hybrid correlation engine** combining substring and semantic analysis
- **Contextual grouping** of similar strings for consistency checking
- **Configurable similarity thresholds** and clustering parameters
- **Optimized for LQA workflows** - similar strings appear together

### ⚠️ Game-Specific Validation
- **Color tag validation** (`<color="#hex">text</color>`)
- **Game variable checking** (`{skm1}`, `{skm2}`, ability references `[123]`)
- **Token mismatch detection** (brackets, variables, formatting)
- **Punctuation consistency** validation
- **Malformed markup detection** with detailed error reporting

### 📊 Interactive Visualizer
- **Standalone HTML output** for offline LQA review
- **Raw/Formatted data toggle** for debugging
- **Pass/Fail review states** with persistent localStorage
- **Personal notes system** for team collaboration
- **Dark/Light mode** with professional styling
- **Progress tracking** and completion metrics

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Streamlit
- pandas, openpyxl, scikit-learn, numpy

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/stringZ.git
cd stringZ

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run streamlit_app.py
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up

# Or build manually
docker build -t stringz .
docker run -p 8501:8501 stringz
```

Access the application at `http://localhost:8501`

## 📋 Usage Workflow

### 1. **Upload Translation File**
- Upload Excel files (`.xlsx`, `.xls`) with required columns:
  - `strId` - Unique string identifier
  - `EN` - English source text
  - `[Target Language]` - Translation column (e.g., `German`, `Spanish`)

### 2. **Configure Processing**
- **Deduplication**: Remove duplicate entries automatically
- **Similarity Sorting**: Group related strings using AI
- **Advanced Settings**: Fine-tune thresholds and clustering parameters

### 3. **Review Results**
- **📊 Results Tab**: Download processed spreadsheets and interactive visualizer
- **🔍 Review Tab**: Consistency checking with similarity-grouped strings
- **⚠️ Validation Tab**: Automated error detection and issue reporting

### 4. **Export Options**
- **Interactive Visualizer**: Standalone HTML for LQA teams
- **Processed Spreadsheet**: Clean Excel file ready for translation
- **Missing Translations**: Filtered view of untranslated strings
- **High Priority**: Strings with high occurrence counts

## 🛠️ Technical Architecture

### Modular Design
```
StringZ/
├── src/stringZ/
│   ├── core/           # Processing engines (deduplication, correlation)
│   ├── models/         # Data models and structures
│   ├── validation/     # Game-specific validation logic
│   ├── export/         # Visualizer and export functionality
│   └── ui/             # Streamlit interface components
│       ├── config/     # App configuration and styling
│       ├── layouts/    # Page layouts and routing
│       ├── tabs/       # Individual tab implementations
│       └── components/ # Reusable UI components
└── streamlit_app.py    # Main application entry point
```

### Processing Pipeline
1. **Data Loading**: Excel parsing with language detection
2. **Deduplication**: Configurable strategies with occurrence tracking
3. **Correlation**: AI-powered similarity clustering
4. **Validation**: Game-specific format checking
5. **Export**: Multiple output formats for different workflows

## 🎮 Game-Specific Features

### Supported Game Elements
- **Color Tags**: `<color="#eadca2">damage</color>`
- **Skill Variables**: `{skm1}`, `{skm2}`, `{skm3}`
- **Ability References**: `[123]`, `[456]`
- **Formatting Tokens**: Line breaks `\\n`, tabs `\\t`
- **Special Characters**: Brackets, percentages, mathematical symbols

### Validation Checks
- **Token Consistency**: Ensures game elements match between source and target
- **Malformed Markup**: Detects extra characters and unmatched tags
- **Numeric Preservation**: Validates damage values and percentages
- **Punctuation Alignment**: Checks ending punctuation consistency

## 📊 Benefits for LQA Teams

### Efficiency Gains
- **No Duplicate Work**: Automatic detection saves review time
- **Contextual Review**: Similar strings grouped for consistency
- **Automated Validation**: Catches formatting errors instantly
- **Offline Capability**: Visualizer works without internet

### Quality Improvements
- **Consistency Checking**: AI grouping reveals translation inconsistencies
- **Error Prevention**: Game-specific validation prevents runtime issues
- **Progress Tracking**: Clear metrics for completion status
- **Team Collaboration**: Shared visualizers with review states

### Workflow Integration
- **Excel Compatibility**: Standard input/output formats
- **Flexible Export**: Multiple output options for different needs
- **Configurable Processing**: Adaptable to different project requirements
- **Professional Output**: Clean, production-ready files

## 🔧 Configuration Options

### Deduplication Strategies
- **Keep First**: Preserve first occurrence of duplicates
- **Keep Best**: Choose entry with longest/best translation
- **Keep with Occurrences**: Track how many times each string appears

### Similarity Algorithms
- **Hybrid**: Best of substring + semantic analysis (recommended)
- **Semantic**: AI-powered contextual similarity
- **Substring**: Fast pattern-based grouping
- **Alphabetical**: Simple sorting fallback

### Advanced Parameters
- **Similarity Threshold**: 0.5-0.9 (how similar strings must be to group)
- **Max Cluster Size**: 5-30 (maximum strings per similarity group)
- **Min Substring Length**: 3-15 (minimum characters for substring matching)

## 🚀 Roadmap

- [x] **Glossary Integration**: Terminology consistency checking
- [x] **Translation Memory**: Leverage previous translations
- [x] **Batch Processing**: Multiple file support
- [x] **API Integration**: Connect with CAT tools
- [x] **Advanced Analytics**: Translation quality metrics
- [x] **Custom Validation Rules**: Project-specific checks

## 🤝 Contributing

StringZ is designed for professional game localization workflows. Contributions welcome for:
- Additional validation rules
- Export format support
- Performance optimizations
- UI/UX improvements

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built for ZGAME Translation Teams** 🎮
*Streamline your localization workflow with intelligent automation*
