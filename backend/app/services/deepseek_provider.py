"""
DeepSeek AI Service Provider
Free/affordable AI provider with OpenAI-compatible API
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from app.services.ai_provider import AIServiceProvider
from app.config import settings

logger = logging.getLogger(__name__)


class DeepSeekProvider(AIServiceProvider):
    """
    DeepSeek AI provider implementation
    Uses OpenAI-compatible API: https://api.deepseek.com
    """

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.api_url = settings.deepseek_api_url
        self.model = settings.deepseek_model
        self.temperature = settings.deepseek_temperature
        self.max_tokens = settings.deepseek_max_tokens

    def is_enabled(self) -> bool:
        """Check if DeepSeek is configured and enabled"""
        return settings.deepseek_enabled and bool(self.api_key)

    async def _make_request(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make a request to DeepSeek API (OpenAI-compatible)
        """
        if not self.is_enabled():
            raise ValueError("DeepSeek is not enabled or not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                        raise Exception(f"DeepSeek API error: {response.status}")

                    result = await response.json()

                    # Extract response text (OpenAI format)
                    return result["choices"][0]["message"]["content"]

        except asyncio.TimeoutError:
            logger.error("DeepSeek API request timeout")
            raise Exception("DeepSeek API request timeout")
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}", exc_info=True)
            raise

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from response, cleaning markdown if present"""
        try:
            response_text = response_text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from DeepSeek response: {response_text}")
            raise

    # ========================================================================
    # EVENT ANALYSIS
    # ========================================================================

    async def analyze_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a security event and classify it
        """
        system_prompt = """You are a cybersecurity expert specializing in Windows infrastructure security event analysis.

Your task is to analyze the event and determine:
1. Is this a potential attack or suspicious activity
2. Event category (malware, intrusion, policy_violation, recon, lateral_movement, privilege_escalation, data_exfiltration, denial_of_service, normal_activity)
3. Threat score (0-100)
4. Brief description in Russian (1-2 sentences)
5. Confidence level (0-100)

Respond ONLY in JSON format:
{
  "is_attack": true/false,
  "score": 0-100,
  "category": "category",
  "description": "brief description in Russian",
  "confidence": 0-100
}
"""

        event_desc = f"""
Event source: {event_data.get('source_type', 'Unknown')}
Event code: {event_data.get('event_code', 'N/A')}
Severity: {event_data.get('severity', 0)}
Computer: {event_data.get('computer', 'Unknown')}
Time: {event_data.get('event_time', 'Unknown')}

User: {event_data.get('subject_user', 'N/A')} (domain: {event_data.get('subject_domain', 'N/A')})
Target user: {event_data.get('target_user', 'N/A')}

Process: {event_data.get('process_name', 'N/A')}
Command line: {event_data.get('process_command_line', 'N/A')}

Network:
- Source: {event_data.get('source_ip', 'N/A')}:{event_data.get('source_port', 'N/A')}
- Destination: {event_data.get('destination_ip', 'N/A')}:{event_data.get('destination_port', 'N/A')}

File: {event_data.get('file_path', 'N/A')}
Registry: {event_data.get('registry_path', 'N/A')}

Message: {event_data.get('message', 'N/A')}
"""

        try:
            response_text = await self._make_request(system_prompt, event_desc.strip())
            analysis = self._parse_json_response(response_text)

            return {
                "ai_processed": True,
                "ai_is_attack": analysis.get("is_attack", False),
                "ai_score": float(analysis.get("score", 0)),
                "ai_category": analysis.get("category", "unknown"),
                "ai_description": analysis.get("description", ""),
                "ai_confidence": float(analysis.get("confidence", 0))
            }

        except json.JSONDecodeError:
            return {
                "ai_processed": True,
                "ai_is_attack": False,
                "ai_score": 0.0,
                "ai_category": "unknown",
                "ai_description": "Не удалось разобрать ответ AI",
                "ai_confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Error analyzing event with DeepSeek: {e}", exc_info=True)
            return {
                "ai_processed": False,
                "ai_is_attack": None,
                "ai_score": None,
                "ai_category": None,
                "ai_description": f"Ошибка AI-анализа: {str(e)}",
                "ai_confidence": None
            }

    # ========================================================================
    # ALERT ANALYSIS
    # ========================================================================

    async def analyze_alert(self, alert_data: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze an alert and provide recommendations
        """
        system_prompt = """You are a cybersecurity expert analyzing security alerts.

Your task is to analyze the alert and provide:
1. Threat analysis
2. Response recommendations
3. Response priority (1-4)
4. Predicted next attacker steps

Respond ONLY in JSON format:
{
  "analysis": "detailed threat analysis in Russian",
  "recommendations": ["recommendation 1", "recommendation 2", ...],
  "priority": 1-4,
  "next_attacker_steps": ["possible step 1", "possible step 2", ...]
}
"""

        alert_desc = f"""
Alert: {alert_data.get('title', 'Unknown')}
Description: {alert_data.get('description', 'N/A')}
Category: {alert_data.get('category', 'N/A')}
Severity: {alert_data.get('severity', 0)}

Context:
- Computer: {alert_data.get('hostname', 'N/A')}
- User: {alert_data.get('username', 'N/A')}
- Source IP: {alert_data.get('source_ip', 'N/A')}
- Target IP: {alert_data.get('target_ip', 'N/A')}
- Process: {alert_data.get('process_name', 'N/A')}

MITRE ATT&CK:
- Tactic: {alert_data.get('mitre_attack_tactic', 'N/A')}
- Technique: {alert_data.get('mitre_attack_technique', 'N/A')}

Event count: {alert_data.get('event_count', 0)}
Time range: {alert_data.get('first_event_time', 'N/A')} - {alert_data.get('last_event_time', 'N/A')}

Related events (first 5):
"""

        for i, event in enumerate(events[:5], 1):
            alert_desc += f"\n{i}. {event.get('message', 'N/A')[:200]}"

        try:
            response_text = await self._make_request(system_prompt, alert_desc.strip())
            analysis = self._parse_json_response(response_text)

            return {
                "ai_analysis": {
                    "threat_analysis": analysis.get("analysis", ""),
                    "recommendations": analysis.get("recommendations", []),
                    "priority": analysis.get("priority", 2),
                    "next_attacker_steps": analysis.get("next_attacker_steps", [])
                },
                "ai_recommendations": "\n".join([
                    f"{i}. {rec}"
                    for i, rec in enumerate(analysis.get("recommendations", []), 1)
                ]),
                "ai_confidence": 75.0
            }

        except json.JSONDecodeError:
            return {
                "ai_analysis": {"error": "Не удалось разобрать ответ AI"},
                "ai_recommendations": "Ошибка анализа",
                "ai_confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Error analyzing alert with DeepSeek: {e}", exc_info=True)
            return {
                "ai_analysis": {"error": str(e)},
                "ai_recommendations": f"Ошибка AI-анализа: {str(e)}",
                "ai_confidence": 0.0
            }

    # ========================================================================
    # INCIDENT ANALYSIS
    # ========================================================================

    async def analyze_incident(
        self,
        incident_data: Dict[str, Any],
        alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze an incident and provide comprehensive assessment
        """
        system_prompt = """You are a senior cybersecurity expert conducting a security incident analysis.

Your task is to provide comprehensive incident analysis:
1. Executive summary (2-3 sentences in Russian)
2. Attack timeline description
3. Probable root cause
4. Impact assessment
5. Remediation steps

Respond ONLY in JSON format:
{
  "summary": "executive summary in Russian (2-3 sentences)",
  "timeline": "attack timeline description in Russian",
  "root_cause": "probable root cause in Russian",
  "impact_assessment": "impact assessment in Russian",
  "remediation_steps": ["step 1", "step 2", ...]
}
"""

        incident_desc = f"""
Incident: {incident_data.get('title', 'Unknown')}
Description: {incident_data.get('description', 'N/A')}
Category: {incident_data.get('category', 'N/A')}
Severity: {incident_data.get('severity', 0)}

Time range:
- Start: {incident_data.get('start_time', 'N/A')}
- End: {incident_data.get('end_time', 'N/A')}
- Detected: {incident_data.get('detected_at', 'N/A')}

Scope:
- Alerts: {incident_data.get('alert_count', 0)}
- Events: {incident_data.get('event_count', 0)}
- Affected systems: {incident_data.get('affected_assets', 0)}

MITRE ATT&CK:
- Tactics: {', '.join(incident_data.get('mitre_attack_tactics', []) or [])}
- Techniques: {', '.join(incident_data.get('mitre_attack_techniques', []) or [])}

Related alerts (top-5):
"""

        for i, alert in enumerate(alerts[:5], 1):
            incident_desc += f"\n{i}. [{alert.get('severity', 0)}] {alert.get('title', 'N/A')}"

        try:
            response_text = await self._make_request(
                system_prompt,
                incident_desc.strip(),
                max_tokens=2000
            )
            analysis = self._parse_json_response(response_text)

            return {
                "ai_summary": analysis.get("summary", ""),
                "ai_timeline": {"description": analysis.get("timeline", "")},
                "ai_root_cause": analysis.get("root_cause", ""),
                "ai_impact_assessment": analysis.get("impact_assessment", ""),
                "ai_recommendations": "\n".join([
                    f"{i}. {step}"
                    for i, step in enumerate(analysis.get("remediation_steps", []), 1)
                ])
            }

        except json.JSONDecodeError:
            return {
                "ai_summary": "Ошибка анализа инцидента",
                "ai_timeline": {"error": "Не удалось разобрать ответ AI"},
                "ai_root_cause": "Не определено",
                "ai_impact_assessment": "Не определено",
                "ai_recommendations": "Ошибка анализа"
            }
        except Exception as e:
            logger.error(f"Error analyzing incident with DeepSeek: {e}", exc_info=True)
            return {
                "ai_summary": f"Ошибка AI-анализа: {str(e)}",
                "ai_timeline": {"error": str(e)},
                "ai_root_cause": "Не определено",
                "ai_impact_assessment": "Не определено",
                "ai_recommendations": f"Ошибка AI-анализа: {str(e)}"
            }

    # ========================================================================
    # CBR REPORT GENERATION
    # ========================================================================

    async def generate_cbr_report(self, incident_data: Dict[str, Any]) -> str:
        """
        Generate incident report in format suitable for CBR (Central Bank of Russia)
        """
        system_prompt = """You are an expert in preparing security incident reports for the Central Bank of Russia (CBR).

Your task is to create a formal incident report for CBR in accordance with requirements 683-П, 716-П, 747-П.

The report should include:
1. Brief incident description
2. Date and time of detection
3. Operational risk category
4. Impact on organization activities
5. Actions taken
6. Damage assessment

Use formal business style, be specific and objective. Write in Russian.
"""

        incident_desc = f"""
Prepare CBR incident report:

Incident title: {incident_data.get('title', 'Unknown')}
Category: {incident_data.get('category', 'N/A')}
Severity: {incident_data.get('severity', 0)}

Timeline:
- Detection date/time: {incident_data.get('detected_at', 'N/A')}
- Incident start: {incident_data.get('start_time', 'N/A')}
- Incident end: {incident_data.get('end_time', 'N/A')}

Impact scope:
- Affected systems: {incident_data.get('affected_assets', 0)}
- Alerts: {incident_data.get('alert_count', 0)}

Operational risk category: {incident_data.get('operational_risk_category', 'Not defined')}
Estimated damage: {incident_data.get('estimated_damage_rub', 0)} RUB
Actual damage: {incident_data.get('actual_damage_rub', 0)} RUB

Description: {incident_data.get('description', 'N/A')}
"""

        try:
            report_text = await self._make_request(
                system_prompt,
                incident_desc.strip(),
                temperature=0.3,  # Lower temperature for formal report
                max_tokens=2000
            )
            return report_text.strip()

        except Exception as e:
            logger.error(f"Error generating CBR report with DeepSeek: {e}", exc_info=True)
            return f"Ошибка генерации отчёта для ЦБ РФ: {str(e)}"
