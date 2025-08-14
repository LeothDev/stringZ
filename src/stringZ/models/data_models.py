# src/zstringalign/models/data_models.py

from dataclasses import dataclass, field
from typing import List, Optional 
import pandas as pd


@dataclass
class TranslationEntry:
    """Single translation string with metadata"""
    str_id: str
    source_text: str
    supplementary_text: Optional[str] = None
    target_text: Optional[str] = None
    source_lang: str = "EN"
    supplementary_lang: Optional[str] = None
    target_lang: Optional[str] = None
    occurrences: int = 1
    
    def __post_init__(self):
        # Clean data
        self.source_text = str(self.source_text) if self.source_text else ""
        self.target_text = str(self.target_text) if self.target_text else None


@dataclass
class DuplicateGroup:
    """Group of duplicate entries"""
    source_text: str
    entries: List[TranslationEntry]
    kept_entry: Optional[TranslationEntry] = None
    
    @property
    def count(self) -> int:
        return len(self.entries)


@dataclass
class CorrelationCluster:
    """Cluster of correlated/similar strings"""
    entries: List[TranslationEntry]
    similarity_score: float
    cluster_id: int
    cluster_type: str = "semantic"  # "semantic", "substring", "alphabetical"
    
    @property
    def size(self) -> int:
        return len(self.entries)


@dataclass
class ProcessingResult:
    """Results from deduplication and correlation processing"""
    original_count: int
    final_count: int
    duplicates_removed: int
    clusters_found: int
    processing_time: float
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    correlation_clusters: List[CorrelationCluster] = field(default_factory=list)


@dataclass
class TranslationDataset:
    """Main container for translation data"""
    entries: List[TranslationEntry] = field(default_factory=list)
    str_id_col: str = "strId"
    supplementary_col: Optional[str] = None
    source_lang: str = "EN"
    target_lang: Optional[str] = None
    result: Optional[ProcessingResult] = None
    
    @classmethod
    def from_dataframe(
        cls, 
        df: pd.DataFrame, 
        source_col: str = "EN",
        supplementary_col: Optional[str] = None,
        target_col: Optional[str] = None,
        str_id_col: str = "strId"
    ) -> "TranslationDataset":
        """Create dataset from pandas DataFrame"""
        print("I WAS CALLED - FROM_DATAFRAME")
        
        # Auto-detect target language
        if target_col is None:
            possible_targets = [col for col in df.columns 
                             if col not in [str_id_col, source_col]]
            if possible_targets:
                target_col = possible_targets[0]
        
        print(f"SUPPLEMENTARY COL IN DATAFRAME: {supplementary_col}")
        entries = []
        for _, row in df.iterrows():
            print(f"ROW??: {row}")
            if pd.notna(row[str_id_col]) and pd.notna(row[source_col]):
                # CHECK FOR OCCURRENCES COLUMN PLEASEEEEEE
                occurrences = 1
                has_occurrences = 'Occurrences' in df.columns.tolist()
                if has_occurrences and pd.notna(row.get('Occurrences')):
                    occurrences = int(row['Occurrences'])

                entry = TranslationEntry(
                    str_id=str(row[str_id_col]),
                    source_text=str(row[source_col]),
                    supplementary_text=str(row[supplementary_col]) if supplementary_col and pd.notna(row.get(supplementary_col)) else None,
                    target_text=str(row[target_col]) if target_col and pd.notna(row[target_col]) else None,
                    source_lang=source_col,
                    supplementary_lang=supplementary_col,
                    target_lang=target_col,
                    occurrences=occurrences
                )
                print("OK I'M AFTER ENTRY TRANSLATIONENTRY")
                entries.append(entry)
        print("ENTRIES:", entries)
        
        display_source_lang = 'CN' if source_col == 'base' else source_col
        return cls(
            entries=entries,
            str_id_col=str_id_col,
            source_lang=display_source_lang,
            target_lang=target_col
        )
    def is_chinese_target(self) -> bool:
        """Check if this is a Chinese translation scenario"""
        return (self.target_lang in ['CNTraditional', 'CNSimplified'] and
                self.source_lang in ['base', 'CN'])

    def to_dataframe(self) -> pd.DataFrame:
        """Convert back to pandas DataFrame"""
        data = []
        for entry in self.entries:
            row = {
                self.str_id_col: entry.str_id,
                entry.source_lang: entry.source_text,
            }
            if entry.supplementary_text and entry.supplementary_lang:
                row[entry.supplementary_lang] = entry.supplementary_text

            if entry.target_lang and entry.target_text:
                row[entry.target_lang] = entry.target_text
        
            row['Occurrences'] = getattr(entry, 'occurrences', 1)
        
            data.append(row)
    
        df = pd.DataFrame(data)
    
        return df    

    def get_duplicates(self) -> List[DuplicateGroup]:
        """Find groups of entries with duplicate source text"""
        text_groups = {}
        
        for entry in self.entries:
            if entry.source_text in text_groups:
                text_groups[entry.source_text].append(entry)
            else:
                text_groups[entry.source_text] = [entry]
        
        # Return only groups with duplicates
        duplicate_groups = []
        for source_text, entries in text_groups.items():
            if len(entries) > 1:
                duplicate_groups.append(DuplicateGroup(
                    source_text=source_text,
                    entries=entries
                ))
        
        return duplicate_groups
    
    def get_completion_rate(self) -> float:
        """Calculate translation completion percentage"""
        if not self.entries:
            return 0.0
        
        completed = sum(1 for entry in self.entries 
                       if entry.target_text and entry.target_text.strip())
        return (completed / len(self.entries)) * 100
    
    def __len__(self) -> int:
        return len(self.entries)
