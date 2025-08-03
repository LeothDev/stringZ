import logging
from typing import List, Optional, Tuple, Dict
import numpy as np

from ..models.data_models import TranslationDataset, TranslationEntry, CorrelationCluster
from ..utils.similarity_utils import SimilarityCalculator

logger = logging.getLogger(__name__)


class CorrelationStrategy:
    """Base class for different correlation strategies"""
    
    def sort_entries(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[CorrelationCluster]]:
        raise NotImplementedError


class AlphabeticalStrategy(CorrelationStrategy):
    """Simple alphabetical sorting"""
    
    def sort_entries(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[CorrelationCluster]]:
        sorted_entries = sorted(entries, key=lambda e: e.source_text.lower())
        return sorted_entries, []


class OccurrenceBasedStrategy(CorrelationStrategy):
    """Sort by occurrences (highest first) then alphabetically"""
    
    def sort_entries(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[CorrelationCluster]]:
        sorted_entries = sorted(entries, key=lambda e: (-e.occurrences, e.source_text.lower()))
        return sorted_entries, []


class SubstringCorrelationStrategy(CorrelationStrategy):
    """Sort strings by substring relationships"""
    
    def __init__(self, min_substring_length: int = 5):
        self.min_substring_length = min_substring_length
    
    def sort_entries(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[CorrelationCluster]]:
        if len(entries) <= 1:
            return entries, []
        
        logger.info(f"Computing substring correlation for {len(entries)} entries")
        
        # Sort entries by length (shortest first)
        sorted_entries = sorted(entries, key=lambda e: len(e.source_text))
        clusters = []
        used_entries = set()
        cluster_id = 0
        
        for i, short_entry in enumerate(sorted_entries):
            if short_entry.str_id in used_entries:
                continue
                
            short_text = short_entry.source_text.strip()
            
            # Skip very short strings
            if len(short_text) < self.min_substring_length:
                continue
            
            # Find all entries that contain this short text
            related_entries = [short_entry]
            
            for long_entry in sorted_entries[i+1:]:
                if long_entry.str_id in used_entries:
                    continue
                    
                long_text = long_entry.source_text.strip()
                
                # Check if short text appears in long text
                if short_text.lower() in long_text.lower() and short_text != long_text:
                    related_entries.append(long_entry)
            
            # Create cluster if we found related entries
            if len(related_entries) > 1:
                for entry in related_entries:
                    used_entries.add(entry.str_id)
                
                clusters.append(CorrelationCluster(
                    entries=related_entries,
                    similarity_score=1.0,
                    cluster_id=cluster_id,
                    cluster_type="substring"
                ))
                cluster_id += 1
        
        # Create final sorted order
        result = []
        
        # Add clustered entries first
        for cluster in clusters:
            cluster_sorted = sorted(cluster.entries, key=lambda e: len(e.source_text))
            result.extend(cluster_sorted)
        
        # Add non-clustered entries
        unclustered = [entry for entry in entries if entry.str_id not in used_entries]
        unclustered_sorted = sorted(unclustered, key=lambda e: (len(e.source_text), e.source_text))
        result.extend(unclustered_sorted)
        
        logger.info(f"Created {len(clusters)} substring clusters")
        return result, clusters


class SemanticCorrelationStrategy(CorrelationStrategy):
    """Sort strings by semantic similarity"""
    
    def __init__(self, similarity_threshold: float = 0.7, max_cluster_size: int = 15):
        self.similarity_threshold = similarity_threshold
        self.max_cluster_size = max_cluster_size
        self.similarity_calc = SimilarityCalculator()
    
    def sort_entries(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[CorrelationCluster]]:
        if len(entries) <= 1:
            return entries, []
        
        logger.info(f"Computing semantic correlation for {len(entries)} entries")
        
        # Get source texts
        texts = [entry.source_text for entry in entries]
        
        # Calculate similarity matrix
        similarity_matrix = self.similarity_calc.calculate_similarity_matrix(texts)
        
        # Simple clustering: find pairs with high similarity
        clusters = []
        used_indices = set()
        cluster_id = 0
        
        for i in range(len(entries)):
            if i in used_indices:
                continue
                
            cluster_entries = [entries[i]]
            used_indices.add(i)
            
            # Find similar entries
            for j in range(i + 1, len(entries)):
                if j in used_indices:
                    continue
                    
                if similarity_matrix[i][j] > self.similarity_threshold:
                    cluster_entries.append(entries[j])
                    used_indices.add(j)
                    
                    # Limit cluster size
                    if len(cluster_entries) >= self.max_cluster_size:
                        break
            
            # Only create cluster if we have multiple entries
            if len(cluster_entries) > 1:
                avg_similarity = np.mean([similarity_matrix[i][j] 
                                        for i in range(len(cluster_entries))
                                        for j in range(i + 1, len(cluster_entries))])
                
                clusters.append(CorrelationCluster(
                    entries=cluster_entries,
                    similarity_score=float(avg_similarity),
                    cluster_id=cluster_id,
                    cluster_type="semantic"
                ))
                cluster_id += 1
        
        # Create final sorted order
        result = []
        clustered_ids = set()
        
        # Add clustered entries
        for cluster in sorted(clusters, key=lambda c: c.size, reverse=True):
            cluster_sorted = sorted(cluster.entries, key=lambda e: e.source_text)
            result.extend(cluster_sorted)
            clustered_ids.update(entry.str_id for entry in cluster.entries)
        
        # Add non-clustered entries
        unclustered = [entry for entry in entries if entry.str_id not in clustered_ids]
        unclustered_sorted = sorted(unclustered, key=lambda e: e.source_text)
        result.extend(unclustered_sorted)
        
        logger.info(f"Created {len(clusters)} semantic clusters")
        return result, clusters


class HybridCorrelationStrategy(CorrelationStrategy):
    """Simple hybrid strategy: substring clusters first, then semantic clusters"""
    
    def __init__(self, similarity_threshold: float = 0.7, min_substring_length: int = 5, max_cluster_size: int = 15):
        self.similarity_threshold = similarity_threshold
        self.min_substring_length = min_substring_length
        self.max_cluster_size = max_cluster_size
        self.similarity_calc = SimilarityCalculator()
    
    def sort_entries(self, entries: List[TranslationEntry]) -> Tuple[List[TranslationEntry], List[CorrelationCluster]]:
        if len(entries) <= 1:
            return entries, []
        
        logger.info(f"Computing simple hybrid correlation for {len(entries)} entries")
        
        # Find substring clusters (fast)
        substring_clusters, clustered_ids = self._create_substring_clusters(entries)
        logger.info(f"Found {len(substring_clusters)} substring clusters")
        
        # Find semantic clusters from remaining entries (slower)
        unclustered_entries = [e for e in entries if e.str_id not in clustered_ids]
        semantic_clusters = self._create_semantic_clusters(unclustered_entries)
        logger.info(f"Found {len(semantic_clusters)} semantic clusters")
        
        # Simple ordering - substring clusters first, then semantic
        all_clusters = substring_clusters + semantic_clusters
        sorted_entries = self._create_simple_order(entries, all_clusters)
        
        logger.info(f"Final result: {len(all_clusters)} total clusters")
        return sorted_entries, all_clusters
    
    def _create_substring_clusters(self, entries: List[TranslationEntry]) -> Tuple[List[CorrelationCluster], set]:
        """Find substring relationships - SIMPLE approach"""
        clusters = []
        used_ids = set()
        cluster_id = 0
        
        # Sort by length (shortest first) 
        entries_by_length = sorted(entries, key=lambda e: len(e.source_text))
        
        for i, short_entry in enumerate(entries_by_length):
            if short_entry.str_id in used_ids:
                continue
                
            short_text = short_entry.source_text.strip().lower()
            
            # Skip very short strings
            if len(short_text) < self.min_substring_length:
                continue
            
            # Find longer strings that contain this short string
            related_entries = [short_entry]
            
            for long_entry in entries_by_length[i+1:]:
                if long_entry.str_id in used_ids:
                    continue
                    
                long_text = long_entry.source_text.strip().lower()
                
                # Simple substring check
                if short_text in long_text and short_text != long_text:
                    related_entries.append(long_entry)
                    
                    # Limit cluster size
                    if len(related_entries) >= self.max_cluster_size:
                        break
            
            # Create cluster if we found relationships
            if len(related_entries) > 1:
                for entry in related_entries:
                    used_ids.add(entry.str_id)
                
                cluster = CorrelationCluster(
                    entries=related_entries,
                    similarity_score=1.0,  # Perfect match for substrings
                    cluster_id=cluster_id,
                    cluster_type="substring"
                )
                clusters.append(cluster)
                cluster_id += 1
        
        return clusters, used_ids
    
    def _create_semantic_clusters(self, entries: List[TranslationEntry]) -> List[CorrelationCluster]:
        """Find semantic relationships - ONLY for unclustered entries"""
        if len(entries) <= 1:
            return []
        
        texts = [entry.source_text for entry in entries]
        similarity_matrix = self.similarity_calc.calculate_similarity_matrix(texts)
        
        clusters = []
        used_indices = set()
        cluster_id = 1000
        
        for i in range(len(entries)):
            if i in used_indices:
                continue
                
            # Start new cluster
            cluster_entries = [entries[i]]
            used_indices.add(i)
            
            # Find similar entries
            for j in range(i + 1, len(entries)):
                if j in used_indices:
                    continue
                    
                # Check if similar enough
                if similarity_matrix[i][j] > self.similarity_threshold:
                    cluster_entries.append(entries[j])
                    used_indices.add(j)
                    
                    # Limit cluster size
                    if len(cluster_entries) >= self.max_cluster_size:
                        break
            
            # Only create cluster if multiple entries
            if len(cluster_entries) > 1:
                # Calculate average similarity for this cluster
                similarities = []
                for x in range(len(cluster_entries)):
                    for y in range(x + 1, len(cluster_entries)):
                        idx_x = entries.index(cluster_entries[x])
                        idx_y = entries.index(cluster_entries[y])
                        similarities.append(similarity_matrix[idx_x][idx_y])
                
                avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
                
                cluster = CorrelationCluster(
                    entries=cluster_entries,
                    similarity_score=avg_similarity,
                    cluster_id=cluster_id,
                    cluster_type="semantic"
                )
                clusters.append(cluster)
                cluster_id += 1
        
        return clusters
    
    def _create_simple_order(self, all_entries: List[TranslationEntry], clusters: List[CorrelationCluster]) -> List[TranslationEntry]:
        """Simple ordering: clusters first, then remaining entries"""
        result = []
        clustered_ids = set()
        
        # Sort clusters by size (biggest first) and type (substring first)
        def cluster_sort_key(cluster):
            type_priority = 0 if cluster.cluster_type == "substring" else 1
            return (type_priority, -cluster.size)  # negative size for descending
        
        sorted_clusters = sorted(clusters, key=cluster_sort_key)
        
        # Add all clustered entries
        for cluster in sorted_clusters:
            # Within each cluster: sort by length for substring, alphabetically for semantic
            if cluster.cluster_type == "substring":
                cluster_entries = sorted(cluster.entries, key=lambda e: len(e.source_text))
            else:
                cluster_entries = sorted(cluster.entries, key=lambda e: e.source_text.lower())
            
            result.extend(cluster_entries)
            clustered_ids.update(e.str_id for e in cluster.entries)
        
        # Add remaining unclustered entries at the end
        unclustered = [e for e in all_entries if e.str_id not in clustered_ids]
        unclustered_sorted = sorted(unclustered, key=lambda e: e.source_text.lower())
        result.extend(unclustered_sorted)
        
        return result

class StringCorrelator:
    """Main string correlation engine"""
    
    def __init__(self, strategy: Optional[CorrelationStrategy] = None):
        self.strategy = strategy or HybridCorrelationStrategy()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def process(self, dataset: TranslationDataset) -> TranslationDataset:
        """Apply correlation sorting to dataset"""
        self.logger.info(f"Starting correlation sorting for {len(dataset)} entries")
        
        try:
            # Apply correlation strategy
            sorted_entries, clusters = self.strategy.sort_entries(dataset.entries)
            
            # Create new dataset with sorted entries
            result_dataset = TranslationDataset(
                entries=sorted_entries,
                source_lang=dataset.source_lang,
                target_lang=dataset.target_lang
            )
            
            # Update processing result
            if dataset.result:
                dataset.result.clusters_found = len(clusters)
                dataset.result.correlation_clusters = clusters
                result_dataset.result = dataset.result
            
            self.logger.info(f"Correlation sorting completed: {len(clusters)} clusters found")
            return result_dataset
            
        except Exception as e:
            self.logger.error(f"Correlation sorting failed: {str(e)}")
            raise
    
    def analyze_correlations(self, dataset: TranslationDataset) -> Dict[str, any]:
        """Analyze correlation patterns without sorting"""
        if len(dataset.entries) <= 1:
            return {"message": "Not enough entries for correlation analysis"}
        
        # Simple analysis
        analysis = {
            'total_entries': len(dataset.entries),
            'avg_text_length': np.mean([len(entry.source_text) for entry in dataset.entries]),
            'max_text_length': max(len(entry.source_text) for entry in dataset.entries),
            'min_text_length': min(len(entry.source_text) for entry in dataset.entries)
        }
        
        return analysis
    
    def set_strategy(self, strategy: CorrelationStrategy) -> None:
        """Change correlation strategy"""
        self.strategy = strategy
        self.logger.info(f"Correlation strategy changed to {strategy.__class__.__name__}")


# Convenience functions
def sort_by_substring_correlation(dataset: TranslationDataset, min_length: int = 5) -> TranslationDataset:
    """Quick substring correlation sorting"""
    correlator = StringCorrelator(SubstringCorrelationStrategy(min_length))
    return correlator.process(dataset)


def sort_by_semantic_correlation(dataset: TranslationDataset, similarity_threshold: float = 0.7) -> TranslationDataset:
    """Quick semantic correlation sorting"""
    correlator = StringCorrelator(SemanticCorrelationStrategy(similarity_threshold))
    return correlator.process(dataset)


def sort_by_hybrid_correlation(dataset: TranslationDataset) -> TranslationDataset:
    """Quick hybrid correlation sorting (recommended)"""
    correlator = StringCorrelator(HybridCorrelationStrategy())
    return correlator.process(dataset)


def sort_by_occurrences(dataset: TranslationDataset) -> TranslationDataset:
    """Sort by occurrences like your original script"""
    correlator = StringCorrelator(OccurrenceBasedStrategy())
    return correlator.process(dataset)
