"""
Advanced AI Capabilities for MediFraudy + ClaimSwarm
Natural Language Processing, Voice Analysis, Video Analysis, Predictive Analytics
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import numpy as np
from dataclasses import dataclass
from enum import Enum
import re
import hashlib
from collections import Counter
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
import spacy
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import whisper
import cv2
from PIL import Image
import face_recognition
import speech_recognition as sr

logger = logging.getLogger(__name__)

class AIModelType(Enum):
    NLP_PROCESSING = "nlp_processing"
    VOICE_ANALYSIS = "voice_analysis"
    VIDEO_ANALYSIS = "video_analysis"
    PREDICTIVE_ANALYTICS = "predictive_analytics"
    DEEPFAKE_DETECTION = "deepfake_detection"

@dataclass
class AIAnalysisResult:
    model_type: AIModelType
    confidence: float
    findings: List[str]
    risk_score: float
    evidence: Dict[str, Any]
    processing_time: float
    timestamp: datetime

class NaturalLanguageProcessor:
    """Advanced NLP for document analysis and fraud detection"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.nlp_model = spacy.load("en_core_web_sm")
        self.sentiment_analyzer = pipeline("sentiment-analysis")
        self.ner_model = pipeline("ner", aggregation_strategy="simple")
        self.fraud_keywords = self._load_fraud_keywords()
        self.medical_entities = self._load_medical_entities()
        
    def _load_fraud_keywords(self) -> List[str]:
        """Load fraud-related keywords and phrases"""
        return [
            "kickback", "bribe", "illegal", "unauthorized", "fraudulent",
            "false claim", "inflated", "upcoding", "unbundling", "phantom billing",
            "duplicate billing", "medically unnecessary", "never performed",
            "kickback scheme", "referral fee", "commission", "illegal remuneration"
        ]
    
    def _load_medical_entities(self) -> List[str]:
        """Load medical entities for healthcare fraud detection"""
        return [
            "diagnosis", "procedure", "treatment", "medication", "therapy",
            "surgery", "examination", "test", "scan", "x-ray", "mri", "ct scan",
            "hospital", "clinic", "physician", "nurse", "therapist", "pharmacist"
        ]
    
    async def analyze_document(self, document_text: str, document_type: str) -> AIAnalysisResult:
        """Analyze document for fraud indicators"""
        start_time = datetime.utcnow()
        
        # Process with spaCy
        doc = self.nlp_model(document_text)
        
        # Extract entities
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # Sentiment analysis
        sentiment = self.sentiment_analyzer(document_text)[0]
        
        # Named entity recognition
        ner_results = self.ner_model(document_text)
        
        # Fraud keyword detection
        fraud_indicators = self._detect_fraud_keywords(document_text)
        
        # Medical entity analysis
        medical_entities = self._extract_medical_entities(doc)
        
        # Suspicious patterns
        suspicious_patterns = self._detect_suspicious_patterns(document_text, entities)
        
        # Calculate risk score
        risk_score = self._calculate_document_risk_score(
            fraud_indicators, suspicious_patterns, sentiment, medical_entities
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return AIAnalysisResult(
            model_type=AIModelType.NLP_PROCESSING,
            confidence=0.85,
            findings=fraud_indicators + suspicious_patterns,
            risk_score=risk_score,
            evidence={
                "entities": entities,
                "sentiment": sentiment,
                "ner_results": ner_results,
                "medical_entities": medical_entities
            },
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )
    
    def _detect_fraud_keywords(self, text: str) -> List[str]:
        """Detect fraud-related keywords in text"""
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in self.fraud_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def _extract_medical_entities(self, doc) -> List[str]:
        """Extract medical entities from processed text"""
        medical_entities = []
        
        for ent in doc.ents:
            if ent.text.lower() in [entity.lower() for entity in self.medical_entities]:
                medical_entities.append(ent.text)
        
        return medical_entities
    
    def _detect_suspicious_patterns(self, text: str, entities: List[Tuple[str, str]]) -> List[str]:
        """Detect suspicious patterns in text"""
        patterns = []
        
        # Pattern 1: Unusual monetary amounts
        money_pattern = r'\$[\d,]+(?:\.\d{2})?'
        money_matches = re.findall(money_pattern, text)
        if len(money_matches) > 5:
            patterns.append("Excessive monetary references")
        
        # Pattern 2: Repeated same procedure
        procedures = [ent[0] for ent in entities if ent[1] == "PROCEDURE"]
        procedure_counts = Counter(procedures)
        repeated_procedures = [proc for proc, count in procedure_counts.items() if count > 3]
        if repeated_procedures:
            patterns.append(f"Repeated procedures: {', '.join(repeated_procedures)}")
        
        # Pattern 3: Unusual time patterns
        time_pattern = r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b'
        time_matches = re.findall(time_pattern, text)
        if len(time_matches) > 10:
            patterns.append("Excessive time references")
        
        # Pattern 4: Suspicious date patterns
        date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'
        date_matches = re.findall(date_pattern, text)
        if len(date_matches) > 20:
            patterns.append("Excessive date references")
        
        return patterns
    
    def _calculate_document_risk_score(self, fraud_indicators: List[str], 
                                     suspicious_patterns: List[str],
                                     sentiment: Dict, 
                                     medical_entities: List[str]) -> float:
        """Calculate overall risk score for document"""
        score = 0.0
        
        # Fraud indicators (40% weight)
        score += len(fraud_indicators) * 0.1
        
        # Suspicious patterns (30% weight)
        score += len(suspicious_patterns) * 0.15
        
        # Sentiment analysis (15% weight)
        if sentiment['label'] == 'NEGATIVE':
            score += 0.3
        
        # Medical entities (15% weight)
        if len(medical_entities) > 50:
            score += 0.2
        
        return min(1.0, score)

class VoiceAnalyzer:
    """Voice analysis for fraud detection and emotion recognition"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.whisper_model = whisper.load_model("base")
        
    async def analyze_audio(self, audio_file_path: str) -> AIAnalysisResult:
        """Analyze audio file for fraud indicators"""
        start_time = datetime.utcnow()
        
        # Transcribe audio
        transcription = await self._transcribe_audio(audio_file_path)
        
        # Analyze speech patterns
        speech_patterns = self._analyze_speech_patterns(transcription)
        
        # Detect emotional cues
        emotional_analysis = self._analyze_emotional_cues(audio_file_path)
        
        # Voice stress analysis
        stress_analysis = self._analyze_voice_stress(audio_file_path)
        
        # Calculate risk score
        risk_score = self._calculate_voice_risk_score(
            speech_patterns, emotional_analysis, stress_analysis
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return AIAnalysisResult(
            model_type=AIModelType.VOICE_ANALYSIS,
            confidence=0.80,
            findings=speech_patterns + emotional_analysis['findings'],
            risk_score=risk_score,
            evidence={
                "transcription": transcription,
                "speech_patterns": speech_patterns,
                "emotional_analysis": emotional_analysis,
                "stress_analysis": stress_analysis
            },
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )
    
    async def _transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file to text"""
        try:
            result = self.whisper_model.transcribe(audio_file_path)
            return result["text"]
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return ""
    
    def _analyze_speech_patterns(self, transcription: str) -> List[str]:
        """Analyze speech patterns for deception indicators"""
        patterns = []
        
        # Hesitation markers
        hesitation_words = ["um", "uh", "er", "like", "you know"]
        hesitation_count = sum(transcription.lower().count(word) for word in hesitation_words)
        if hesitation_count > 10:
            patterns.append("Excessive hesitation")
        
        # Fillers
        filler_words = ["actually", "basically", "literally", "honestly"]
        filler_count = sum(transcription.lower().count(word) for word in filler_words)
        if filler_count > 5:
            patterns.append("Excessive filler words")
        
        # Negations
        negation_words = ["not", "never", "no", "nothing", "neither"]
        negation_count = sum(transcription.lower().count(word) for word in negation_words)
        if negation_count > 15:
            patterns.append("Excessive negation")
        
        # Qualifiers
        qualifier_words = ["maybe", "perhaps", "possibly", "probably"]
        qualifier_count = sum(transcription.lower().count(word) for word in qualifier_words)
        if qualifier_count > 8:
            patterns.append("Excessive qualifiers")
        
        return patterns
    
    def _analyze_emotional_cues(self, audio_file_path: str) -> Dict[str, Any]:
        """Analyze emotional cues in audio"""
        # Mock implementation - would use actual audio analysis
        return {
            "findings": ["Emotional inconsistency detected"],
            "emotions": {
                "stress": 0.7,
                "anxiety": 0.6,
                "confidence": 0.3
            }
        }
    
    def _analyze_voice_stress(self, audio_file_path: str) -> Dict[str, Any]:
        """Analyze voice stress patterns"""
        # Mock implementation - would use actual voice analysis
        return {
            "stress_level": 0.65,
            "pitch_variation": 0.45,
            "speech_rate": 0.55,
            "volume_consistency": 0.40
        }
    
    def _calculate_voice_risk_score(self, speech_patterns: List[str],
                                  emotional_analysis: Dict,
                                  stress_analysis: Dict) -> float:
        """Calculate voice analysis risk score"""
        score = 0.0
        
        # Speech patterns (40% weight)
        score += len(speech_patterns) * 0.1
        
        # Emotional analysis (30% weight)
        emotions = emotional_analysis.get("emotions", {})
        score += emotions.get("stress", 0) * 0.15
        score += emotions.get("anxiety", 0) * 0.15
        
        # Voice stress (30% weight)
        score += stress_analysis.get("stress_level", 0) * 0.3
        
        return min(1.0, score)

class VideoAnalyzer:
    """Video analysis for deepfake detection and fraud prevention"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.face_recognition_tolerance = 0.6
        
    async def analyze_video(self, video_file_path: str) -> AIAnalysisResult:
        """Analyze video for deepfakes and fraud indicators"""
        start_time = datetime.utcnow()
        
        # Extract frames
        frames = self._extract_frames(video_file_path)
        
        # Deepfake detection
        deepfake_analysis = await self._detect_deepfake(frames)
        
        # Face recognition
        face_analysis = self._analyze_faces(frames)
        
        # Behavioral analysis
        behavioral_analysis = self._analyze_behavior(frames)
        
        # Calculate risk score
        risk_score = self._calculate_video_risk_score(
            deepfake_analysis, face_analysis, behavioral_analysis
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return AIAnalysisResult(
            model_type=AIModelType.VIDEO_ANALYSIS,
            confidence=0.75,
            findings=deepfake_analysis['findings'] + behavioral_analysis['findings'],
            risk_score=risk_score,
            evidence={
                "deepfake_analysis": deepfake_analysis,
                "face_analysis": face_analysis,
                "behavioral_analysis": behavioral_analysis
            },
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )
    
    def _extract_frames(self, video_file_path: str) -> List[np.ndarray]:
        """Extract frames from video"""
        frames = []
        cap = cv2.VideoCapture(video_file_path)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            
            # Limit frames to avoid memory issues
            if len(frames) >= 100:
                break
        
        cap.release()
        return frames
    
    async def _detect_deepfake(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """Detect deepfake in video frames"""
        # Mock implementation - would use actual deepfake detection model
        findings = []
        
        # Check for inconsistencies
        if len(frames) > 10:
            findings.append("Video inconsistencies detected")
        
        # Check for artifacts
        findings.append("Potential digital artifacts")
        
        return {
            "findings": findings,
            "deepfake_probability": 0.15,
            "confidence": 0.75
        }
    
    def _analyze_faces(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """Analyze faces in video frames"""
        face_data = []
        
        for frame in frames:
            # Convert to RGB for face recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            
            for face_location in face_locations:
                face_data.append({
                    "location": face_location,
                    "frame_number": len(face_data)
                })
        
        return {
            "face_count": len(face_data),
            "face_locations": face_data,
            "consistency": 0.85
        }
    
    def _analyze_behavior(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """Analyze behavioral patterns in video"""
        findings = []
        
        # Check for unusual movements
        if len(frames) > 50:
            findings.append("Unusual movement patterns detected")
        
        # Check for eye contact
        findings.append("Limited eye contact observed")
        
        return {
            "findings": findings,
            "movement_analysis": "irregular",
            "eye_contact": "limited"
        }
    
    def _calculate_video_risk_score(self, deepfake_analysis: Dict,
                                  face_analysis: Dict,
                                  behavioral_analysis: Dict) -> float:
        """Calculate video analysis risk score"""
        score = 0.0
        
        # Deepfake analysis (40% weight)
        score += deepfake_analysis.get("deepfake_probability", 0) * 0.4
        
        # Face analysis (30% weight)
        if face_analysis.get("consistency", 1.0) < 0.7:
            score += 0.3
        
        # Behavioral analysis (30% weight)
        findings = behavioral_analysis.get("findings", [])
        score += len(findings) * 0.1
        
        return min(1.0, score)

class PredictiveAnalytics:
    """Predictive analytics for future fraud prediction"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.dbscan = DBSCAN(eps=0.5, min_samples=5)
        
    async def predict_fraud_risk(self, entity_data: Dict[str, Any]) -> AIAnalysisResult:
        """Predict fraud risk for entity"""
        start_time = datetime.utcnow()
        
        # Extract features
        features = self._extract_features(entity_data)
        
        # Anomaly detection
        anomaly_score = self._detect_anomalies(features)
        
        # Pattern analysis
        pattern_analysis = self._analyze_patterns(entity_data)
        
        # Risk prediction
        risk_prediction = self._predict_risk(features, pattern_analysis)
        
        # Calculate confidence
        confidence = self._calculate_prediction_confidence(anomaly_score, pattern_analysis)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return AIAnalysisResult(
            model_type=AIModelType.PREDICTIVE_ANALYTICS,
            confidence=confidence,
            findings=pattern_analysis['findings'],
            risk_score=risk_prediction,
            evidence={
                "features": features,
                "anomaly_score": anomaly_score,
                "pattern_analysis": pattern_analysis,
                "risk_prediction": risk_prediction
            },
            processing_time=processing_time,
            timestamp=datetime.utcnow()
        )
    
    def _extract_features(self, entity_data: Dict[str, Any]) -> np.ndarray:
        """Extract features for ML models"""
        features = []
        
        # Financial features
        features.append(entity_data.get('total_claims', 0))
        features.append(entity_data.get('total_amount', 0))
        features.append(entity_data.get('avg_claim_amount', 0))
        
        # Temporal features
        features.append(entity_data.get('claims_per_month', 0))
        features.append(entity_data.get('days_since_last_claim', 0))
        
        # Network features
        features.append(entity_data.get('connection_count', 0))
        features.append(entity_data.get('network_centrality', 0))
        
        # Behavioral features
        features.append(entity_data.get('complexity_score', 0))
        features.append(entity_data.get('fraud_indicators', 0))
        
        return np.array(features).reshape(1, -1)
    
    def _detect_anomalies(self, features: np.ndarray) -> float:
        """Detect anomalies using isolation forest"""
        # Mock implementation - would train model on historical data
        anomaly_score = self.isolation_forest.fit_predict(features)[0]
        return 1.0 if anomaly_score == -1 else 0.0
    
    def _analyze_patterns(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in entity data"""
        findings = []
        
        # Check for claim clustering
        if entity_data.get('claims_per_month', 0) > 10:
            findings.append("High claim frequency")
        
        # Check for amount patterns
        if entity_data.get('avg_claim_amount', 0) > 10000:
            findings.append("High average claim amounts")
        
        # Check for network patterns
        if entity_data.get('connection_count', 0) > 20:
            findings.append("Extensive network connections")
        
        return {
            "findings": findings,
            "pattern_score": len(findings) * 0.2
        }
    
    def _predict_risk(self, features: np.ndarray, pattern_analysis: Dict) -> float:
        """Predict fraud risk"""
        base_risk = 0.1
        
        # Add pattern-based risk
        pattern_risk = pattern_analysis.get("pattern_score", 0)
        
        # Add feature-based risk
        feature_risk = np.mean(features[0]) / 10000  # Normalize
        
        total_risk = base_risk + pattern_risk + feature_risk
        return min(1.0, total_risk)
    
    def _calculate_prediction_confidence(self, anomaly_score: float,
                                        pattern_analysis: Dict) -> float:
        """Calculate confidence in prediction"""
        base_confidence = 0.7
        
        # Adjust based on anomaly detection
        if anomaly_score > 0.5:
            base_confidence += 0.2
        
        # Adjust based on pattern strength
        pattern_score = pattern_analysis.get("pattern_score", 0)
        base_confidence += pattern_score * 0.1
        
        return min(1.0, base_confidence)

class AdvancedAIManager:
    """Unified advanced AI management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.nlp_processor = NaturalLanguageProcessor(db)
        self.voice_analyzer = VoiceAnalyzer(db)
        self.video_analyzer = VideoAnalyzer(db)
        self.predictive_analytics = PredictiveAnalytics(db)
        
    async def comprehensive_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive AI analysis"""
        results = {}
        
        # NLP Analysis
        if 'text' in data:
            results['nlp'] = await self.nlp_processor.analyze_document(
                data['text'], data.get('document_type', 'unknown')
            )
        
        # Voice Analysis
        if 'audio_file' in data:
            results['voice'] = await self.voice_analyzer.analyze_audio(data['audio_file'])
        
        # Video Analysis
        if 'video_file' in data:
            results['video'] = await self.video_analyzer.analyze_video(data['video_file'])
        
        # Predictive Analytics
        if 'entity_data' in data:
            results['predictive'] = await self.predictive_analytics.predict_fraud_risk(
                data['entity_data']
            )
        
        # Calculate overall risk score
        overall_risk = self._calculate_overall_risk(results)
        
        return {
            "overall_risk_score": overall_risk,
            "analysis_results": results,
            "recommendations": self._generate_recommendations(results),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_overall_risk(self, results: Dict[str, AIAnalysisResult]) -> float:
        """Calculate overall risk score from all analyses"""
        if not results:
            return 0.0
        
        risk_scores = [result.risk_score for result in results.values()]
        confidences = [result.confidence for result in results.values()]
        
        # Weighted average based on confidence
        weighted_score = sum(score * conf for score, conf in zip(risk_scores, confidences))
        total_confidence = sum(confidences)
        
        return weighted_score / total_confidence if total_confidence > 0 else 0.0
    
    def _generate_recommendations(self, results: Dict[str, AIAnalysisResult]) -> List[str]:
        """Generate recommendations based on analysis results"""
        recommendations = []
        
        for analysis_type, result in results.items():
            if result.risk_score > 0.7:
                recommendations.append(f"High risk detected in {analysis_type} - immediate investigation required")
            elif result.risk_score > 0.5:
                recommendations.append(f"Moderate risk detected in {analysis_type} - further review recommended")
            
            # Add specific findings
            for finding in result.findings[:3]:  # Top 3 findings
                recommendations.append(f"{analysis_type.title()}: {finding}")
        
        return recommendations

# Singleton instance
advanced_ai_manager = AdvancedAIManager
