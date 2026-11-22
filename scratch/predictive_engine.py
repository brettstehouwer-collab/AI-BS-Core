import json
import logging
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import numpy as np


try:
    import tensorflow as tf
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input, Embedding, LSTM, Dense
    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    class Tokenizer: pass
    class Model: pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

class MultiHeadLSTMModel:
    def __init__(self):
        self.tokenizer = Tokenizer(num_words=5000, oov_token="<OOV>")
        self.max_length = 50
        self.model = None
        self.is_trained = False
        self.lock = threading.Lock()
        
        self.intent_labels = ["General Conversation", "Code Generation", "Bug Fix", "Complex Request"]
        self.intent_to_idx = {label: idx for idx, label in enumerate(self.intent_labels)}
        self.idx_to_intent = {idx: label for label, idx in self.intent_to_idx.items()}
        
        self.sentiment_labels = ["Neutral", "Aggressive", "Humorous", "High-Stress"]
        self.sentiment_to_idx = {label: idx for idx, label in enumerate(self.sentiment_labels)}
        self.idx_to_sentiment = {idx: label for label, idx in self.sentiment_to_idx.items()}

    def _build_model(self, vocab_size, num_intents, num_sentiments):
        inputs = Input(shape=(self.max_length,), name="text_input")
        x = Embedding(input_dim=vocab_size, output_dim=64)(inputs)
        x = LSTM(64, return_sequences=False)(x)
        x = Dense(32, activation='relu')(x)
        
        intent_output = Dense(num_intents, activation='softmax', name='intent_output')(x)
        sentiment_output = Dense(num_sentiments, activation='softmax', name='sentiment_output')(x)
        
        model = Model(inputs=inputs, outputs=[intent_output, sentiment_output])
        model.compile(
            loss={'intent_output': 'sparse_categorical_crossentropy', 'sentiment_output': 'sparse_categorical_crossentropy'},
            optimizer='adam',
            metrics={'intent_output': 'accuracy', 'sentiment_output': 'accuracy'}
        )
        return model
        
    def _extract_intent(self, user_input, response):
        u = user_input.lower()
        if "error" in u or "bug" in u or "fix" in u:
            return "Bug Fix"
        if "```" in response:
            return "Code Generation"
        if len(u) > 200:
            return "Complex Request"
        return "General Conversation"

    def _extract_sentiment(self, user_input):
        u = user_input.lower()
        if "!!!" in u or "fuck" in u or "shit" in u or "hate" in u:
            return "Aggressive"
        if "urgent" in u or "asap" in u or "help me now" in u:
            return "High-Stress"
        if "lol" in u or "haha" in u or "lmao" in u or "joke" in u:
            return "Humorous"
        return "Neutral"

    def train(self, transcript_path):
        if not os.path.exists(transcript_path):
            logging.warning("Transcript file not found. Skipping training.")
            return False

        X_texts = []
        y_intents = []
        y_sentiments = []
        
        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                last_user_input = None
                for line in f:
                    if not line.strip(): continue
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "USER_INPUT":
                            last_user_input = entry.get("content", "")
                        elif entry.get("type") == "PLANNER_RESPONSE" and last_user_input:
                            intent = self._extract_intent(last_user_input, entry.get("content", ""))
                            sentiment = self._extract_sentiment(last_user_input)
                            
                            X_texts.append(last_user_input)
                            y_intents.append(self.intent_to_idx[intent])
                            y_sentiments.append(self.sentiment_to_idx[sentiment])
                            
                            last_user_input = None
                    except Exception:
                        pass
                        
            if not X_texts:
                X_texts = ["hello", "can you fix this error asap!!!", "write some code lol"]
                y_intents = [self.intent_to_idx["General Conversation"], self.intent_to_idx["Bug Fix"], self.intent_to_idx["Code Generation"]]
                y_sentiments = [self.sentiment_to_idx["Neutral"], self.sentiment_to_idx["High-Stress"], self.sentiment_to_idx["Humorous"]]
                
            with self.lock:
                self.tokenizer.fit_on_texts(X_texts)
                sequences = self.tokenizer.texts_to_sequences(X_texts)
                X_padded = pad_sequences(sequences, maxlen=self.max_length, padding='post', truncating='post')
                
                vocab_size = min(len(self.tokenizer.word_index) + 1, 5000)
                
                if self.model is None:
                    self.model = self._build_model(vocab_size, len(self.intent_labels), len(self.sentiment_labels))
                
                y_i = np.array(y_intents)
                y_s = np.array(y_sentiments)
                
                logging.info(f"Training Multi-Head LSTM on {len(X_texts)} samples...")
                self.model.fit(X_padded, {"intent_output": y_i, "sentiment_output": y_s}, epochs=10, batch_size=4, verbose=1)
                self.is_trained = True
                
            logging.info("LSTM model training complete.")
            return True
        except Exception as e:
            logging.error(f"LSTM Training failed: {e}")
            return False

    def predict(self, user_input: str):
        if not self.is_trained or self.model is None:
            return {"intent": "General Conversation", "intent_confidence": 0.0, "sentiment": "Neutral", "sentiment_confidence": 0.0}
            
        with self.lock:
            sequences = self.tokenizer.texts_to_sequences([user_input])
            X_padded = pad_sequences(sequences, maxlen=self.max_length, padding='post', truncating='post')
            
            predictions = self.model.predict(X_padded, verbose=0)
            intent_preds = predictions[0][0]
            sentiment_preds = predictions[1][0]
            
            max_intent_idx = np.argmax(intent_preds)
            max_sentiment_idx = np.argmax(sentiment_preds)
            
            pred_intent = self.idx_to_intent[max_intent_idx]
            pred_sentiment = self.idx_to_sentiment[max_sentiment_idx]
            
        return {
            "intent": pred_intent, 
            "intent_confidence": float(intent_preds[max_intent_idx]),
            "sentiment": pred_sentiment,
            "sentiment_confidence": float(sentiment_preds[max_sentiment_idx])
        }

predictive_model = MultiHeadLSTMModel()
TRANSCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "active_agent_transcript.jsonl")

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=predictive_model.train, args=(TRANSCRIPT_PATH,), daemon=True).start()

class PredictRequest(BaseModel):
    user_input: str

@app.post("/api/predict")
def predict_intent(req: PredictRequest):
    return predictive_model.predict(req.user_input)

@app.post("/api/train")
def trigger_training():
    threading.Thread(target=predictive_model.train, args=(TRANSCRIPT_PATH,), daemon=True).start()
    return {"status": "Training triggered in background"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)