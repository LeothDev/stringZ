# src/stringZ/core/processor.py

import logging
import time
from typing import Optional, Dict, Any

from ..models.data_models import TranslationDataset, ProcessingResult
from .deduplicator import Deduplicator, KeepFirstStrategy, KeepBestStrategy, KeepFirstWithOccurrencesStrategy
from .correlator import StringCorrelator, SemanticCorrelationStrategy, AlphabeticalStrategy, HybridCorrelationStrategy, SubstringCorrelationStrategy, OccurrenceBasedStrategy

logger = logging.getLogger(__name__)


class ProcessingConfig:
    """Configuration for processing pipeline"""
    
    def __init__(
        self,
        remove_duplicates: bool = True,
        deduplication_strategy: str = "keep_first_with_occurrences",
        sort_by_correlation: bool = True,
        correlation_strategy: str = "hybrid",
        similarity_threshold: float = 0.7,
        max_cluster_size: int = 15,
        min_substring_length: int = 5
    ):
        self.remove_duplicates = remove_duplicates
        self.deduplication_strategy = deduplication_strategy
        self.sort_by_correlation = sort_by_correlation
        self.correlation_strategy = correlation_strategy
        self.similarity_threshold = similarity_threshold
        self.max_cluster_size = max_cluster_size
        self.min_substring_length = min_substring_length
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'remove_duplicates': self.remove_duplicates,
            'deduplication_strategy': self.deduplication_strategy,
            'sort_by_correlation': self.sort_by_correlation,
            'correlation_strategy': self.correlation_strategy,
            'similarity_threshold': self.similarity_threshold,
            'max_cluster_size': self.max_cluster_size,
            'min_substring_length': self.min_substring_length
        }


class TranslationProcessor:
    """Main processor that orchestrates deduplication and correlation sorting"""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize processors
        self.deduplicator = self._create_deduplicator()
        self.correlator = self._create_correlator()
    
    def _create_deduplicator(self) -> Deduplicator:
        """Create deduplicator with configured strategy"""
        if self.config.deduplication_strategy == "keep_best":
            strategy = KeepBestStrategy()
        elif self.config.deduplication_strategy == "keep_first_with_occurrences":
            strategy = KeepFirstWithOccurrencesStrategy()
        else:
            strategy = KeepFirstStrategy()
        
        return Deduplicator(strategy)
    
    def _create_correlator(self) -> StringCorrelator:
        """Create correlator with configured strategy"""
        if self.config.correlation_strategy == "semantic":
            strategy = SemanticCorrelationStrategy(
                similarity_threshold=self.config.similarity_threshold,
                max_cluster_size=self.config.max_cluster_size
            )
        elif self.config.correlation_strategy == "substring":
            strategy = SubstringCorrelationStrategy(
                min_substring_length=self.config.min_substring_length
            )
        elif self.config.correlation_strategy == "hybrid":
            strategy = HybridCorrelationStrategy(
                similarity_threshold=self.config.similarity_threshold,
                min_substring_length=self.config.min_substring_length,
                max_cluster_size=self.config.max_cluster_size
            )
        elif self.config.correlation_strategy == "occurrences":
            strategy = OccurrenceBasedStrategy()
        elif self.config.correlation_strategy == "alphabetical":
            strategy = AlphabeticalStrategy()
        else:
            strategy = HybridCorrelationStrategy()
        
        return StringCorrelator(strategy)
    
    def process(self, dataset: TranslationDataset) -> TranslationDataset:
        """
        Main processing pipeline: deduplication + correlation sorting
        """
        start_time = time.time()
        original_count = len(dataset)
        
        self.logger.info(f"Starting processing pipeline for {original_count} entries")
        self.logger.info(f"Config: {self.config.to_dict()}")
        
        try:
            processed_dataset = dataset
            duplicates_removed = 0
            clusters_found = 0
            
            # DEBUG: Log initial state
            self.logger.info(f"Initial dataset has {len(processed_dataset.entries)} entries")
            
            # Step 1: Deduplication
            if self.config.remove_duplicates:
                self.logger.info("Step 1: Removing duplicates...")
                self.logger.info(f"Using deduplication strategy: {self.config.deduplication_strategy}")
                
                before_dedup = len(processed_dataset)
                self.logger.info(f"Before deduplication: {before_dedup} entries")
                
                # Apply deduplication
                processed_dataset = self.deduplicator.process(processed_dataset)
                
                after_dedup = len(processed_dataset)
                duplicates_removed = before_dedup - after_dedup
                
                self.logger.info(f"After deduplication: {after_dedup} entries")
                self.logger.info(f"Duplicates removed: {duplicates_removed}")
                
                # DEBUG: Check if deduplication actually happened
                if duplicates_removed == 0:
                    self.logger.warning("⚠️ NO DUPLICATES WERE REMOVED!")
                    self.logger.warning("This might indicate:")
                    self.logger.warning("1. No actual duplicates in the data")
                    self.logger.warning("2. Deduplication strategy not working correctly")
                    self.logger.warning("3. Data format issue")
                    
                    # Let's check some sample data
                    if len(processed_dataset.entries) > 0:
                        sample_entry = processed_dataset.entries[0]
                        self.logger.warning(f"Sample entry: {sample_entry.str_id} | '{sample_entry.source_text}' | '{sample_entry.target_text}'")
            else:
                self.logger.info("Step 1: Skipping deduplication (disabled)")
            
            # Step 2: Correlation Sorting
            if self.config.sort_by_correlation:
                self.logger.info(f"Step 2: Applying {self.config.correlation_strategy} correlation sorting...")
                processed_dataset = self.correlator.process(processed_dataset)
                if processed_dataset.result and processed_dataset.result.correlation_clusters:
                    clusters_found = len(processed_dataset.result.correlation_clusters)
                self.logger.info(f"Correlation clusters created: {clusters_found}")
            else:
                self.logger.info("Step 2: Skipping correlation sorting (disabled)")
            
            # Create processing result
            processing_time = time.time() - start_time
            result = ProcessingResult(
                original_count=original_count,
                final_count=len(processed_dataset),
                duplicates_removed=duplicates_removed,
                clusters_found=clusters_found,
                processing_time=processing_time
            )
            
            # Copy over detailed results if available
            if processed_dataset.result:
                result.duplicate_groups = processed_dataset.result.duplicate_groups
                result.correlation_clusters = processed_dataset.result.correlation_clusters
                if hasattr(processed_dataset.result, 'substring_matches'):
                    result.substring_matches = processed_dataset.result.substring_matches
            
            processed_dataset.result = result
            
            self.logger.info(
                f"Processing completed in {processing_time:.2f}s: "
                f"{original_count} → {len(processed_dataset)} entries "
                f"({duplicates_removed} duplicates removed, {clusters_found} clusters)"
            )
            
            return processed_dataset
            
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def analyze_dataset(self, dataset: TranslationDataset) -> Dict[str, Any]:
        """Analyze dataset without processing it"""
        self.logger.info(f"Analyzing dataset with {len(dataset)} entries")
        
        analysis = {
            'total_entries': len(dataset),
            'completion_rate': dataset.get_completion_rate(),
            'source_language': dataset.source_lang,
            'target_language': dataset.target_lang,
        }
        
        # Duplicate analysis
        if self.config.remove_duplicates:
            duplicate_groups = dataset.get_duplicates()
            total_duplicates = sum(len(group.entries) - 1 for group in duplicate_groups)
            
            analysis['duplicates'] = {
                'duplicate_groups': len(duplicate_groups),
                'total_duplicates': total_duplicates,
                'largest_group_size': max((len(group.entries) for group in duplicate_groups), default=0),
                'potential_savings': total_duplicates
            }
        
        # Correlation analysis
        if self.config.sort_by_correlation:
            correlation_analysis = self.correlator.analyze_correlations(dataset)
            analysis['correlations'] = correlation_analysis
        
        return analysis
    
    def get_processing_stats(self, dataset: TranslationDataset) -> Dict[str, Any]:
        """Get detailed statistics about what processing would do"""
        if not dataset.result:
            return self.analyze_dataset(dataset)
        
        result = dataset.result
        stats = {
            'processing_summary': {
                'original_count': result.original_count,
                'final_count': result.final_count,
                'duplicates_removed': result.duplicates_removed,
                'clusters_created': result.clusters_found,
                'processing_time': f"{result.processing_time:.2f}s",
                'efficiency_gain': f"{(result.duplicates_removed / result.original_count * 100):.1f}%" if result.original_count > 0 else "0%"
            },
            'duplicate_details': [],
            'cluster_details': [],
            'substring_details': []
        }
        
        # Duplicate group details
        if result.duplicate_groups:
            for group in result.duplicate_groups[:10]:
                stats['duplicate_details'].append({
                    'source_text': group.source_text[:100] + "..." if len(group.source_text) > 100 else group.source_text,
                    'duplicate_count': group.count,
                    'str_ids': [entry.str_id for entry in group.entries]
                })
        
        # Cluster details
        if result.correlation_clusters:
            sorted_clusters = sorted(result.correlation_clusters, key=lambda c: c.size, reverse=True)
            for cluster in sorted_clusters[:10]:
                sample_texts = [entry.source_text[:50] + "..." if len(entry.source_text) > 50 else entry.source_text 
                              for entry in cluster.entries[:3]]
                
                stats['cluster_details'].append({
                    'cluster_id': cluster.cluster_id,
                    'cluster_type': cluster.cluster_type,
                    'size': cluster.size,
                    'similarity_score': f"{cluster.similarity_score:.3f}",
                    'sample_texts': sample_texts,
                    'str_ids': [entry.str_id for entry in cluster.entries]
                })
        
        # Substring match details
        if hasattr(result, 'substring_matches') and result.substring_matches:
            for match in result.substring_matches[:10]:
                stats['substring_details'].append({
                    'short_text': match.short_entry.source_text,
                    'long_text': match.long_entry.source_text[:80] + "..." if len(match.long_entry.source_text) > 80 else match.long_entry.source_text,
                    'consistency_score': f"{match.consistency_score:.2f}",
                    'short_translation': match.short_entry.target_text or "N/A",
                    'long_translation': (match.long_entry.target_text[:50] + "..." if match.long_entry.target_text and len(match.long_entry.target_text) > 50 else match.long_entry.target_text) or "N/A"
                })
        
        return stats
    
    def update_config(self, **kwargs) -> None:
        """Update processing configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"Updated config: {key} = {value}")
        
        # Recreate processors with new config
        self.deduplicator = self._create_deduplicator()
        self.correlator = self._create_correlator()


# Convenience functions for common processing scenarios
def quick_process(dataset: TranslationDataset, remove_duplicates: bool = True, sort_by_correlation: bool = True) -> TranslationDataset:
    """Quick processing with improved default settings"""
    config = ProcessingConfig(
        remove_duplicates=remove_duplicates,
        sort_by_correlation=sort_by_correlation,
        deduplication_strategy="keep_first_with_occurrences",
        correlation_strategy="hybrid"
    )
    processor = TranslationProcessor(config)
    return processor.process(dataset)


def deduplicate_only(dataset: TranslationDataset, strategy: str = "keep_first_with_occurrences") -> TranslationDataset:
    """Only apply deduplication with your original logic"""
    config = ProcessingConfig(
        remove_duplicates=True,
        deduplication_strategy=strategy,
        sort_by_correlation=False
    )
    processor = TranslationProcessor(config)
    return processor.process(dataset)


def correlate_only(dataset: TranslationDataset, strategy: str = "hybrid", similarity_threshold: float = 0.7) -> TranslationDataset:
    """Only apply correlation sorting with better defaults"""
    config = ProcessingConfig(
        remove_duplicates=False,
        sort_by_correlation=True,
        correlation_strategy=strategy,
        similarity_threshold=similarity_threshold
    )
    processor = TranslationProcessor(config)
    return processor.process(dataset)
