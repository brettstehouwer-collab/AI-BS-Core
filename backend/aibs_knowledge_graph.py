import json

class Entity:
    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type
        self.attributes = {}  # Add attribute dictionary
        self.relationships = []  # Update relationship list

    def add_attribute(self, key, value):
        self.attributes[key] = value

    def add_relationship(self, entity_id):
        if entity_id not in self.relationships:
            self.relationships.append(entity_id)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "attributes": self.attributes,
            "relationships": self.relationships
        }


class Relation:
    def __init__(self, entity_id1, entity_id2, type):
        self.entity_id1 = entity_id1
        self.entity_id2 = entity_id2
        self.type = type

    def encode(self):
        """
        Encodes the relationship into a dense vector array using the local Ollama stehouwer_llm embeddings API.
        Returns the vector serialized as JSON bytes for SQLite BLOB storage.
        """
        import requests
        
        # Semantic string representing the relationship
        semantic_text = f"{self.entity_id1} {self.type} {self.entity_id2}"
        
        url = "http://127.0.0.1:11434/api/embeddings"
        payload = {
            "model": "stehouwer_llm",
            "prompt": semantic_text
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                embedding_vector = resp.json().get("embedding", [])
                if embedding_vector:
                    return json.dumps(embedding_vector).encode("utf-8")
        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            
        # Fallback to empty array if embedding fails
        return json.dumps([]).encode("utf-8")
