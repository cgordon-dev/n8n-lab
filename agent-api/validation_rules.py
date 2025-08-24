"""
Validation Rules Framework for LLM Intent Extraction
Provides post-extraction validation and correction for common classification errors
"""

import re
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class IntentValidator:
    """Validates and corrects LLM-extracted intents using rule-based logic"""
    
    # Common integration mappings for normalization
    INTEGRATION_MAPPINGS = {
        # Email services
        "gmail": "Email",
        "outlook": "Email", 
        "email": "Email",
        "mail": "Email",
        
        # Database services
        "mysql": "Database",
        "postgresql": "Database",
        "postgres": "Database",
        "mongodb": "Database",
        "sqlite": "Database",
        
        # Storage services
        "dropbox": "Storage",
        "google drive": "Storage",
        "onedrive": "Storage",
        
        # Messaging services
        "teams": "Teams",
        "microsoft teams": "Teams",
        
        # Sheet services
        "google sheets": "Sheets",
        "excel": "Sheets",
        "spreadsheet": "Sheets",
    }
    
    # Webhook detection patterns
    WEBHOOK_PATTERNS = [
        r'\bwebhook\b',
        r'\bhook\b',
        r'\bhttp.*callback\b',
        r'\bevent.*trigger\b',
        r'\bpayload\b',
        r'\bpost.*endpoint\b',
        r'\bincoming.*data\b',
        r'\bapi.*call\b'
    ]
    
    # Form detection patterns  
    FORM_PATTERNS = [
        r'\bform\b',
        r'\bsubmission\b',
        r'\bsubmit\b',
        r'\bcontact.*form\b',
        r'\bform.*data\b',
        r'\buser.*input\b'
    ]
    
    # Schedule detection patterns
    SCHEDULE_PATTERNS = [
        r'\bschedule\b',
        r'\bdaily\b',
        r'\bweekly\b',
        r'\bmonthly\b',
        r'\bhourly\b',
        r'\bevery.*\b',
        r'\bcron\b',
        r'\btimer\b',
        r'\bautomated?\b',
        r'\bregular\b'
    ]
    
    # Trigger type indicators
    TRIGGER_INDICATORS = {
        'webhook': [
            r'\bwhen\s+\w+\s+happens?\b',
            r'\bon\s+\w+\s+submission\b',
            r'\bwebhook\b',
            r'\bform.*submit\b',
            r'\bincoming\b',
            r'\breceive.*data\b',
            r'\bapi.*call\b',
            r'\bevent.*trigger\b'
        ],
        'schedule': [
            r'\bevery\s+(day|hour|week|month)\b',
            r'\bdaily\b',
            r'\bweekly\b',
            r'\bmonthly\b',
            r'\bhourly\b',
            r'\bschedule\b',
            r'\bcron\b',
            r'\bautomatically.*\b',
            r'\bat\s+\d+:\d+\b'
        ],
        'manual': [
            r'\bmanually?\b',
            r'\blet\s+me\s+(run|start|trigger)\b',
            r'\bi\s+want\s+to\s+(run|start|trigger)\b',
            r'\bstart\s+manually?\b',
            r'\brun\s+on\s+demand\b'
        ]
    }
    
    def validate_and_correct_intent(self, intent: Dict[str, Any], user_request: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and correct extracted intent using rule-based logic
        
        Args:
            intent: Original extracted intent
            user_request: Original user message
            
        Returns:
            Tuple of (corrected_intent, list_of_corrections_made)
        """
        corrections = []
        corrected_intent = intent.copy()
        request_lower = user_request.lower()
        
        # Ensure integrations is a list
        if not isinstance(corrected_intent.get('integrations'), list):
            corrected_intent['integrations'] = []
        
        # 1. Webhook detection validation
        webhook_corrections = self._validate_webhook_detection(corrected_intent, request_lower)
        corrections.extend(webhook_corrections)
        
        # 2. Form detection validation
        form_corrections = self._validate_form_detection(corrected_intent, request_lower)
        corrections.extend(form_corrections)
        
        # 3. Schedule detection validation
        schedule_corrections = self._validate_schedule_detection(corrected_intent, request_lower)
        corrections.extend(schedule_corrections)
        
        # 4. Integration normalization
        normalization_corrections = self._normalize_integrations(corrected_intent, request_lower)
        corrections.extend(normalization_corrections)
        
        # 5. Trigger type validation and correction
        trigger_corrections = self._validate_trigger_type(corrected_intent, request_lower)
        corrections.extend(trigger_corrections)
        
        # 6. Remove duplicates from integrations
        if corrected_intent.get('integrations'):
            original_count = len(corrected_intent['integrations'])
            corrected_intent['integrations'] = list(set(corrected_intent['integrations']))
            if len(corrected_intent['integrations']) < original_count:
                corrections.append("Removed duplicate integrations")
        
        logger.info(f"Intent validation complete. Applied {len(corrections)} corrections: {corrections}")
        
        return corrected_intent, corrections
    
    def _validate_webhook_detection(self, intent: Dict[str, Any], request_lower: str) -> List[str]:
        """Validate and correct webhook detection"""
        corrections = []
        
        # Check if webhook should be detected
        webhook_mentioned = any(re.search(pattern, request_lower) for pattern in self.WEBHOOK_PATTERNS)
        
        if webhook_mentioned and "Webhook" not in intent.get('integrations', []):
            intent['integrations'].append("Webhook")
            corrections.append("Added missing Webhook integration")
        
        return corrections
    
    def _validate_form_detection(self, intent: Dict[str, Any], request_lower: str) -> List[str]:
        """Validate and correct form detection"""
        corrections = []
        
        # Check if form should be detected
        form_mentioned = any(re.search(pattern, request_lower) for pattern in self.FORM_PATTERNS)
        
        if form_mentioned and "Form" not in intent.get('integrations', []):
            intent['integrations'].append("Form")
            corrections.append("Added missing Form integration")
        
        return corrections
    
    def _validate_schedule_detection(self, intent: Dict[str, Any], request_lower: str) -> List[str]:
        """Validate and correct schedule detection"""
        corrections = []
        
        # Check if schedule should be detected
        schedule_mentioned = any(re.search(pattern, request_lower) for pattern in self.SCHEDULE_PATTERNS)
        
        if schedule_mentioned and "Schedule" not in intent.get('integrations', []):
            intent['integrations'].append("Schedule")
            corrections.append("Added missing Schedule integration")
        
        return corrections
    
    def _normalize_integrations(self, intent: Dict[str, Any], request_lower: str) -> List[str]:
        """Normalize integration names to generic forms"""
        corrections = []
        
        if not intent.get('integrations'):
            return corrections
        
        normalized_integrations = []
        
        for integration in intent['integrations']:
            integration_lower = integration.lower()
            
            # Check if integration should be normalized
            if integration_lower in self.INTEGRATION_MAPPINGS:
                normalized = self.INTEGRATION_MAPPINGS[integration_lower]
                normalized_integrations.append(normalized)
                corrections.append(f"Normalized '{integration}' to '{normalized}'")
            else:
                normalized_integrations.append(integration)
        
        intent['integrations'] = normalized_integrations
        return corrections
    
    def _validate_trigger_type(self, intent: Dict[str, Any], request_lower: str) -> List[str]:
        """Validate and correct trigger type classification"""
        corrections = []
        original_trigger = intent.get('trigger_type', '')
        
        # Score each trigger type based on pattern matches
        trigger_scores = {}
        for trigger_type, patterns in self.TRIGGER_INDICATORS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, request_lower))
            if score > 0:
                trigger_scores[trigger_type] = score
        
        if not trigger_scores:
            # No clear patterns detected, keep original
            return corrections
        
        # Get highest scoring trigger type
        best_trigger = max(trigger_scores.keys(), key=lambda k: trigger_scores[k])
        
        # Only correct if we have strong evidence (score > 1) or original was "manual" (common mistake)
        if trigger_scores[best_trigger] > 1 or (original_trigger == "manual" and trigger_scores[best_trigger] >= 1):
            if best_trigger != original_trigger:
                intent['trigger_type'] = best_trigger
                corrections.append(f"Corrected trigger type from '{original_trigger}' to '{best_trigger}'")
        
        return corrections
    
    def calculate_confidence_score(self, intent: Dict[str, Any], user_request: str) -> float:
        """
        Calculate confidence score for extracted intent
        
        Args:
            intent: Extracted intent
            user_request: Original user message
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        request_lower = user_request.lower()
        
        # Base score for valid structure
        if intent.get('integrations') and intent.get('trigger_type') and intent.get('action'):
            score += 0.3
        
        # Integration detection confidence
        integrations = intent.get('integrations', [])
        if integrations:
            # Check how many integrations have supporting evidence in the text
            evidence_count = 0
            for integration in integrations:
                integration_lower = integration.lower()
                if integration_lower in request_lower or any(keyword in request_lower 
                    for keyword in [integration_lower, integration_lower + 's']):
                    evidence_count += 1
            
            integration_confidence = evidence_count / len(integrations) if integrations else 0
            score += integration_confidence * 0.3
        
        # Trigger type confidence
        trigger_type = intent.get('trigger_type', '')
        if trigger_type in self.TRIGGER_INDICATORS:
            patterns = self.TRIGGER_INDICATORS[trigger_type]
            pattern_matches = sum(1 for pattern in patterns if re.search(pattern, request_lower))
            trigger_confidence = min(pattern_matches / 2, 1.0)  # Normalize to max 1.0
            score += trigger_confidence * 0.2
        
        # Action description quality
        action = intent.get('action', '')
        if action and len(action) > 10 and not action == user_request:
            score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0