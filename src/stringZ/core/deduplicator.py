import logging
from typing import List, Tuple, Dict
from collections import defaultdict

from ..models.data_models import TranslationDataset, TranslationEntry, DuplicateGroup, ProcessingResult

logger = logging.getLogger(__name__)


class DeduplicationStrategy:
    """Base class for deduplication strategies"""
    
    def deduplicate(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[DuplicateGroup]]:
        raise NotImplementedError


class KeepFirstWithOccurrencesStrategy(DeduplicationStrategy):
    """Keep first occurrence and add occurrences count - following your original logic exactly"""
    
    def deduplicate(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[DuplicateGroup]]:
        # Group by EN + target language combination
        groups = defaultdict(list)
        
        for entry in entries:
            en_text = entry.source_text.strip() if entry.source_text else ""
            target_text = entry.target_text.strip() if entry.target_text else ""
            
            # Handle null/empty values like your original script
            if not target_text:
                target_text = ""  # Treat None/empty as empty string
            
            key = (en_text, target_text)
            groups[key].append(entry)
        
        unique_entries = []
        duplicate_groups = []
        
        logger.info(f"Found {len(groups)} unique EN+target combinations from {len(entries)} entries")
        
        # Process each unique EN+target combination
        for (en_text, target_text), group_entries in groups.items():
            # Keep first entry but create a NEW entry with occurrences count
            first_entry = group_entries[0]
            occurrences_count = len(group_entries)
            
            # CRITICAL: Create new entry with occurrences count (don't modify existing dataclass)
            new_entry = TranslationEntry(
                str_id=first_entry.str_id,
                source_text=first_entry.source_text,
                target_text=first_entry.target_text,
                source_lang=first_entry.source_lang,
                target_lang=first_entry.target_lang,
                occurrences=occurrences_count
            )
            
            unique_entries.append(new_entry)
            
            if occurrences_count > 1:
                logger.info(f"Duplicate found: '{en_text[:30]}...' + '{target_text[:20]}...' appears {occurrences_count} times")
            
            # Record duplicate group if there are multiple occurrences
            if len(group_entries) > 1:
                duplicate_group = DuplicateGroup(
                    source_text=en_text,
                    entries=group_entries,
                    kept_entry=new_entry
                )
                duplicate_groups.append(duplicate_group)
        
        # Sort by occurrences (descending)
        unique_entries.sort(key=lambda e: e.occurrences, reverse=True)
        
        duplicates_removed = len(entries) - len(unique_entries)
        logger.info("Deduplication results:")
        logger.info(f"  Original entries: {len(entries)}")
        logger.info(f"  Unique EN+target combinations: {len(unique_entries)}")
        logger.info(f"  Duplicates removed: {duplicates_removed}")
        logger.info(f"  Duplicate groups found: {len(duplicate_groups)}")
        
        # Log sample with occurrences
        if unique_entries:
            sample = unique_entries[0]
            logger.info(f"  Sample entry with occurrences: {sample.str_id} has {sample.occurrences} occurrences")
        
        return unique_entries, duplicate_groups


class KeepFirstStrategy(DeduplicationStrategy):
    """Keep the first occurrence of duplicate entries (by EN text only)"""
    
    def deduplicate(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[DuplicateGroup]]:
        # Group entries by source text only
        text_groups = defaultdict(list)
        for entry in entries:
            text_groups[entry.source_text].append(entry)
        
        unique_entries = []
        duplicate_groups = []
        
        # Process each group
        for source_text, group_entries in text_groups.items():
            if len(group_entries) == 1:
                # No duplicates, keep the entry
                unique_entries.append(group_entries[0])
            else:
                # Duplicates found, keep first and record the group
                kept_entry = group_entries[0]
                unique_entries.append(kept_entry)
                
                duplicate_group = DuplicateGroup(
                    source_text=source_text,
                    entries=group_entries,
                    kept_entry=kept_entry
                )
                duplicate_groups.append(duplicate_group)
        
        return unique_entries, duplicate_groups


class KeepBestStrategy(DeduplicationStrategy):
    """Keep the entry with the best quality (longest translation, non-empty)"""
    
    def deduplicate(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[DuplicateGroup]]:
        # Group entries by source text
        text_groups = defaultdict(list)
        for entry in entries:
            text_groups[entry.source_text].append(entry)
        
        unique_entries = []
        duplicate_groups = []
        
        # Process each group
        for source_text, group_entries in text_groups.items():
            if len(group_entries) == 1:
                # No duplicates, keep the entry
                unique_entries.append(group_entries[0])
            else:
                # Choose best entry based on translation quality
                best_entry = self._choose_best_entry(group_entries)
                unique_entries.append(best_entry)
                
                duplicate_group = DuplicateGroup(
                    source_text=source_text,
                    entries=group_entries,
                    kept_entry=best_entry
                )
                duplicate_groups.append(duplicate_group)
        
        return unique_entries, duplicate_groups
    
    def _choose_best_entry(self, entries: List[TranslationEntry]) -> TranslationEntry:
        """Choose the best entry from a group of duplicates"""
        
        def quality_score(entry: TranslationEntry) -> tuple:
            """Calculate quality score for an entry"""
            target_text = entry.target_text or ""
            
            # Priority: has translation > longer translation > first occurrence
            has_translation = bool(target_text.strip())
            translation_length = len(target_text.strip())
            
            return (has_translation, translation_length)
        
        # Sort by quality score (descending) and return the best
        return max(entries, key=quality_score)


class Deduplicator:
    """Main deduplication engine"""
    
    def __init__(self, strategy: DeduplicationStrategy = None):
        self.strategy = strategy or KeepFirstWithOccurrencesStrategy()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def process(self, dataset: TranslationDataset) -> TranslationDataset:
        """
        Process dataset to remove duplicates
        
        Args:
            dataset: Input translation dataset
            
        Returns:
            New dataset with duplicates removed
        """
        self.logger.info(f"Starting deduplication of {len(dataset)} entries")
        
        try:
            # Apply deduplication strategy
            unique_entries, duplicate_groups = self.strategy.deduplicate(dataset.entries)
            
            # Calculate statistics
            duplicates_removed = len(dataset.entries) - len(unique_entries)
            
            # Create new dataset with results
            result_dataset = TranslationDataset(
                entries=unique_entries,
                source_lang=dataset.source_lang,
                target_lang=dataset.target_lang
            )
            
            # Create processing result
            result = ProcessingResult(
                original_count=len(dataset.entries),
                final_count=len(unique_entries),
                duplicates_removed=duplicates_removed,
                clusters_found=0,  # Will be updated by correlator
                processing_time=0.0,  # Will be updated by main processor
                duplicate_groups=duplicate_groups
            )
            
            result_dataset.result = result
            
            self.logger.info(
                f"Deduplication completed: {len(dataset.entries)} → {len(unique_entries)} "
                f"({duplicates_removed} duplicates removed)"
            )
            
            return result_dataset
            
        except Exception as e:
            self.logger.error(f"Deduplication failed: {str(e)}")
            raise
    
    def analyze_duplicates(self, dataset: TranslationDataset) -> Dict[str, any]:
        """
        Analyze duplicate patterns without removing them
        
        Args:
            dataset: Input translation dataset
            
        Returns:
            Dictionary with duplicate analysis results
        """
        duplicate_groups = dataset.get_duplicates()
        
        analysis = {
            'total_duplicate_groups': len(duplicate_groups),
            'total_duplicate_entries': sum(len(group.entries) for group in duplicate_groups),
            'largest_group_size': max((len(group.entries) for group in duplicate_groups), default=0),
            'duplicate_patterns': {}
        }
        
        # Analyze patterns in duplicate groups
        for group in duplicate_groups:
            if len(group.entries) > 2:  # Focus on significant duplicates
                # Check if translations are consistent
                translations = [entry.target_text for entry in group.entries if entry.target_text]
                unique_translations = set(translations)
                
                analysis['duplicate_patterns'][group.source_text[:50]] = {
                    'count': len(group.entries),
                    'str_ids': [entry.str_id for entry in group.entries],
                    'unique_translations': len(unique_translations),
                    'consistent': len(unique_translations) <= 1
                }
        
        return analysis
    
    def set_strategy(self, strategy: DeduplicationStrategy) -> None:
        """Change deduplication strategy"""
        self.strategy = strategy
        self.logger.info(f"Deduplication strategy changed to {strategy.__class__.__name__}")


# Convenience functions for common use cases
def deduplicate_keep_first(dataset: TranslationDataset) -> TranslationDataset:
    """Quick deduplication keeping first occurrence"""
    deduplicator = Deduplicator(KeepFirstStrategy())
    return deduplicator.process(dataset)


def deduplicate_keep_best(dataset: TranslationDataset) -> TranslationDataset:
    """Quick deduplication keeping best quality translation"""
    deduplicator = Deduplicator(KeepBestStrategy())
    return deduplicator.process(dataset)


def deduplicate_with_occurrences(dataset: TranslationDataset) -> TranslationDataset:
    """Deduplication following your original logic with occurrences count"""
    deduplicator = Deduplicator(KeepFirstWithOccurrencesStrategy())
    return deduplicator.process(dataset)
