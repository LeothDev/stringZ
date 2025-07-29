# src/zstringalign/utils/similarity_utils.py

import logging
from typing import List, Optional
import numpy as np

# Try to import spaCy, fall back to TF-IDF if not available
try:
    import spacy
    from spacy.lang.en import English
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class SimilarityCalculator:
    """Handles different methods for calculating text similarity"""
    
    def __init__(self, use_spacy: bool = True, spacy_model: str = "en_core_web_lg"):
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        self.spacy_model_name = spacy_model
        self.nlp = None
        self.vectorizer = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the similarity calculation method"""
        if self.use_spacy:
            try:
                self.nlp = spacy.load(self.spacy_model_name)
                logger.info(f"Loaded spaCy model: {self.spacy_model_name}")
            except OSError:
                logger.warning(f"spaCy model '{self.spacy_model_name}' not found, falling back to TF-IDF")
                self.use_spacy = False
                self._initialize_tfidf()
        else:
            self._initialize_tfidf()
    
    def _initialize_tfidf(self):
        """Initialize TF-IDF vectorizer as fallback"""
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                max_features=5000,
                min_df=1,
                max_df=0.95
            )
            logger.info("Initialized TF-IDF similarity calculator")
        else:
            logger.error("Neither spaCy nor scikit-learn available for similarity calculation")
            raise ImportError("No similarity calculation method available")
    
    def calculate_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """Calculate similarity matrix for list of texts"""
        if self.use_spacy and self.nlp:
            return self._calculate_spacy_similarity(texts)
        elif self.vectorizer:
            return self._calculate_tfidf_similarity(texts)
        else:
            # Ultimate fallback: simple character-based similarity
            return self._calculate_simple_similarity(texts)
    
    def _calculate_spacy_similarity(self, texts: List[str]) -> np.ndarray:
        """Calculate similarity using spaCy word vectors"""
        # Process texts in batches to handle memory efficiently
        batch_size = 100
        docs = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_docs = list(self.nlp.pipe(batch, disable=["ner", "parser"]))
            docs.extend(batch_docs)
        
        n = len(docs)
        similarity_matrix = np.zeros((n, n))
        
        # Calculate similarities
        for i in range(n):
            similarity_matrix[i][i] = 1.0
            for j in range(i + 1, n):
                try:
                    sim = docs[i].similarity(docs[j])
                    similarity_matrix[i][j] = sim
                    similarity_matrix[j][i] = sim
                except Exception as e:
                    logger.debug(f"Similarity calculation failed for texts {i}, {j}: {e}")
                    similarity_matrix[i][j] = 0.0
                    similarity_matrix[j][i] = 0.0
        
        return similarity_matrix
    
    def _calculate_tfidf_similarity(self, texts: List[str]) -> np.ndarray:
        """Calculate similarity using TF-IDF + cosine similarity"""
        try:
            # Handle empty or very short texts
            processed_texts = []
            for text in texts:
                if len(text.strip()) < 2:
                    processed_texts.append("empty_text")
                else:
                    processed_texts.append(text)
            
            tfidf_matrix = self.vectorizer.fit_transform(processed_texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            return similarity_matrix
            
        except Exception as e:
            logger.error(f"TF-IDF calculation failed: {e}")
            return self._calculate_simple_similarity(texts)
    
    def _calculate_simple_similarity(self, texts: List[str]) -> np.ndarray:
        """Simple character-based similarity as ultimate fallback"""
        n = len(texts)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            similarity_matrix[i][i] = 1.0
            for j in range(i + 1, n):
                sim = self._simple_text_similarity(texts[i], texts[j])
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim
        
        return similarity_matrix
    
    def _simple_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity based on character overlap"""
        if not text1 or not text2:
            return 0.0
        
        # Jaccard similarity on character 3-grams
        def get_ngrams(text: str, n: int = 3) -> set:
            text = text.lower().strip()
            if len(text) < n:
                return {text}
            return {text[i:i+n] for i in range(len(text) - n + 1)}
        
        ngrams1 = get_ngrams(text1)
        ngrams2 = get_ngrams(text2)
        
        intersection = len(ngrams1.intersection(ngrams2))
        union = len(ngrams1.union(ngrams2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_pairwise_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two specific texts"""
        if self.use_spacy and self.nlp:
            try:
                doc1 = self.nlp(text1)
                doc2 = self.nlp(text2)
                return doc1.similarity(doc2)
            except Exception:
                pass
        
        # Fallback to simple similarity
        return self._simple_text_similarity(text1, text2)
    
    def get_method_info(self) -> dict:
        """Get information about the current similarity method"""
        if self.use_spacy and self.nlp:
            return {
                'method': 'spaCy',
                'model': self.spacy_model_name,
                'description': 'Semantic similarity using word vectors'
            }
        elif self.vectorizer:
            return {
                'method': 'TF-IDF',
                'description': 'Term frequency similarity with cosine distance'
            }
        else:
            return {
                'method': 'Simple',
                'description': 'Character n-gram Jaccard similarity'
            }


class SimilarityConfig:
    """Configuration for similarity calculation"""
    
    # spaCy models in order of preference
    SPACY_MODELS = [
        "en_core_web_trf"
        "en_core_web_md",  # Best quality with vectors
        "en_core_web_sm",  # Smaller but still good
        "en_core_web_lg",  # Largest, best quality but heavy
    ]
    
    # TF-IDF parameters
    TFIDF_CONFIG = {
        'ngram_range': (1, 2),
        'max_features': 5000,
        'min_df': 1,
        'max_df': 0.95,
        'stop_words': 'english'
    }
    
    @classmethod
    def get_best_spacy_model(cls) -> Optional[str]:
        """Find the best available spaCy model"""
        if not SPACY_AVAILABLE:
            return None
        
        for model_name in cls.SPACY_MODELS:
            try:
                spacy.load(model_name)
                return model_name
            except OSError:
                continue
        
        return None


def create_similarity_calculator(prefer_quality: bool = True) -> SimilarityCalculator:
    """Factory function to create the best available similarity calculator"""
    
    if prefer_quality:
        # Try to get the best spaCy model
        best_model = SimilarityConfig.get_best_spacy_model()
        if best_model:
            return SimilarityCalculator(use_spacy=True, spacy_model=best_model)
    
    # Fallback to any available method
    return SimilarityCalculator(use_spacy=False)
