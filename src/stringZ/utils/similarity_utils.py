import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


class SimilarityCalculator:
    """Calculate text similarity using TF-IDF and cosine similarity.
    Necessary as replacement of Spacy (too large of a model to run fast)"""
    
    def __init__(self):
        """Initialize the similarity calculator"""
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),  # Use unigrams and bigrams
            max_features=5000,   # Limit features for performance
            min_df=1,            # Minimum document frequency
            max_df=0.95          # Maximum document frequency
        )
        logger.info("Initialized TF-IDF based similarity calculator")
    
    def calculate_similarity_matrix(self, texts):
        """
        Calculate similarity matrix for a list of texts
        
        Args:
            texts: List of strings to compare
            
        Returns:
            numpy.ndarray: Similarity matrix where entry [i,j] is similarity between texts[i] and texts[j]
        """
        if not texts or len(texts) < 2:
            return np.array([[1.0]])
        
        try:
            # Clean and prepare texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Convert texts to TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(cleaned_texts)
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            logger.info(f"Calculated similarity matrix for {len(texts)} texts")
            return similarity_matrix
            
        except Exception as e:
            logger.error(f"Error calculating similarity matrix: {str(e)}")
            # Fallback to identity matrix
            n = len(texts)
            return np.eye(n)
    
    def calculate_pairwise_similarity(self, text1, text2):
        """
        Calculate similarity between two texts
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            float: Similarity score between 0 and 1
        """
        try:
            # Use the matrix calculation for consistency
            matrix = self.calculate_similarity_matrix([text1, text2])
            return float(matrix[0, 1])
            
        except Exception as e:
            logger.error(f"Error calculating pairwise similarity: {str(e)}")
            return 0.0
    
    def _clean_text(self, text):
        """Clean and normalize text for better similarity calculation"""
        if not text:
            return ""
        
        # Convert to string and clean
        text = str(text).strip()
        
        # Remove common game/UI patterns that might interfere
        import re
        
        # Remove color tags
        text = re.sub(r'<color="[^"]*">(.*?)</color>', r'\1', text)
        
        # Remove other HTML-like tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()


def create_similarity_calculator():
    """Factory function to create similarity calculator"""
    return SimilarityCalculator()


# Alternative simple similarity function if you need a quick fallback
def simple_word_overlap_similarity(text1, text2):
    """
    Simple word overlap similarity as fallback
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        float: Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    words1 = set(str(text1).lower().split())
    words2 = set(str(text2).lower().split())
    
    # Calculate Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0
