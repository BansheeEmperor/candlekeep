"""Entity extractor using spaCy NER."""
from dataclasses import dataclass
from candlekeep.config import Settings


@dataclass
class Entity:
    name: str
    type: str
    source: str


class EntityExtractor:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                from spacy.cli import download
                download("en_core_web_sm")
                self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    def extract(self, text: str, source: str = "") -> dict:
        """Extract entities using spaCy NER."""
        doc = self.nlp(text)
        
        seen = set()
        entities = []
        for ent in doc.ents:
            if ent.text.lower() not in seen:
                seen.add(ent.text.lower())
                entities.append({"name": ent.text, "type": ent.label_, "source": source})
        
        return {"entities": entities}
