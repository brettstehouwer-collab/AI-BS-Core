import os
import sys

class AIBSNLPAnalyzer:
    """
    Bridge to NLTK and spaCy for advanced Natural Language Processing.
    Fulfills the Stehouwer LLM claims regarding NLP architectures.
    """
    def __init__(self):
        try:
            import nltk
            self.nltk = nltk
            print("NLTK initialized.")
        except ImportError:
            print("NLTK not installed.")
            self.nltk = None
            
        try:
            import spacy
            self.spacy = spacy
            # Load the English model
            self.nlp = spacy.load("en_core_web_sm")
            print("spaCy initialized with en_core_web_sm.")
        except ImportError:
            print("spaCy not installed.")
            self.spacy = None
            self.nlp = None
        except OSError:
            print("spaCy en_core_web_sm model not found. Run 'python -m spacy download en_core_web_sm'.")
            self.nlp = None

    def nltk_tokenize(self, text):
        """Uses NLTK for word tokenization"""
        if self.nltk:
            from nltk.tokenize import word_tokenize
            try:
                return word_tokenize(text)
            except LookupError:
                self.nltk.download('punkt')
                self.nltk.download('punkt_tab')
                return word_tokenize(text)
        return []

    def spacy_process(self, text):
        """Uses spaCy for full pipeline NLP processing (NER, POS tagging, etc.)"""
        if self.nlp:
            doc = self.nlp(text)
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            tokens = [(token.text, token.pos_, token.dep_) for token in doc]
            return {"entities": entities, "tokens": tokens}
        return {}

if __name__ == "__main__":
    analyzer = AIBSNLPAnalyzer()
    print("Maximum NLP Capabilities Instantiated.")
