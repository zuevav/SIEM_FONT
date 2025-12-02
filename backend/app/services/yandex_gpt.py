"""
Yandex GPT Service for AI-powered security event analysis
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class YandexGPTService:
    """
    Service for interacting with Yandex GPT API
    Provides AI-powered analysis of security events, alerts, and incidents
    """

    def __init__(self):
        self.api_key = settings.yandex_gpt_api_key
        self.folder_id = settings.yandex_gpt_folder_id
        self.model = settings.yandex_gpt_model
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.temperature = settings.yandex_gpt_temperature
        self.max_tokens = settings.yandex_gpt_max_tokens

    def is_enabled(self) -> bool:
        """Check if Yandex GPT is configured and enabled"""
        return settings.yandex_gpt_enabled and bool(self.api_key) and bool(self.folder_id)

    async def _make_request(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a request to Yandex GPT API
        """
        if not self.is_enabled():
            raise ValueError("Yandex GPT is not enabled or not configured")

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature or self.temperature,
                "maxTokens": max_tokens or self.max_tokens
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user",
                    "text": user_prompt
                }
            ]
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
                        logger.error(f"Yandex GPT API error: {response.status} - {error_text}")
                        raise Exception(f"Yandex GPT API error: {response.status}")

                    result = await response.json()
                    return result

        except asyncio.TimeoutError:
            logger.error("Yandex GPT API request timeout")
            raise Exception("Yandex GPT API request timeout")
        except Exception as e:
            logger.error(f"Error calling Yandex GPT API: {e}", exc_info=True)
            raise

    def _extract_response_text(self, response: Dict[str, Any]) -> str:
        """Extract text from Yandex GPT response"""
        try:
            return response["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"Error extracting response text: {e}")
            raise Exception("Invalid response format from Yandex GPT")

    # ========================================================================
    # EVENT ANALYSIS
    # ========================================================================

    async def analyze_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a security event and classify it
        Returns AI score, category, description, confidence, and threat assessment
        """
        system_prompt = """Ты - эксперт по информационной безопасности, специализирующийся на анализе событий безопасности в Windows-инфраструктуре.

Твоя задача - проанализировать событие и определить:
1. Является ли это событие потенциальной атакой или подозрительной активностью
2. Категорию события (malware, intrusion, policy_violation, recon, lateral_movement, privilege_escalation, data_exfiltration, denial_of_service, normal_activity)
3. Уровень опасности (0-100)
4. Краткое описание (1-2 предложения)
5. Уровень уверенности в оценке (0-100)

Отвечай ТОЛЬКО в формате JSON:
{
  "is_attack": true/false,
  "score": 0-100,
  "category": "категория",
  "description": "краткое описание на русском",
  "confidence": 0-100
}
"""

        # Build event description
        event_desc = f"""
Источник события: {event_data.get('source_type', 'Unknown')}
Код события: {event_data.get('event_code', 'N/A')}
Уровень важности: {event_data.get('severity', 0)}
Компьютер: {event_data.get('computer', 'Unknown')}
Время: {event_data.get('event_time', 'Unknown')}

Пользователь: {event_data.get('subject_user', 'N/A')} (домен: {event_data.get('subject_domain', 'N/A')})
Целевой пользователь: {event_data.get('target_user', 'N/A')}

Процесс: {event_data.get('process_name', 'N/A')}
Командная строка: {event_data.get('process_command_line', 'N/A')}

Сеть:
- Источник: {event_data.get('source_ip', 'N/A')}:{event_data.get('source_port', 'N/A')}
- Назначение: {event_data.get('destination_ip', 'N/A')}:{event_data.get('destination_port', 'N/A')}

Файл: {event_data.get('file_path', 'N/A')}
Реестр: {event_data.get('registry_path', 'N/A')}

Сообщение: {event_data.get('message', 'N/A')}
"""

        try:
            response = await self._make_request(system_prompt, event_desc.strip())
            response_text = self._extract_response_text(response)

            # Parse JSON response
            try:
                # Clean response (remove markdown code blocks if present)
                response_text = response_text.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text.rsplit("\n", 1)[0]
                response_text = response_text.strip()

                analysis = json.loads(response_text)

                return {
                    "ai_processed": True,
                    "ai_is_attack": analysis.get("is_attack", False),
                    "ai_score": float(analysis.get("score", 0)),
                    "ai_category": analysis.get("category", "unknown"),
                    "ai_description": analysis.get("description", ""),
                    "ai_confidence": float(analysis.get("confidence", 0))
                }

            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Yandex GPT response: {response_text}")
                # Fallback: return basic analysis
                return {
                    "ai_processed": True,
                    "ai_is_attack": False,
                    "ai_score": 0.0,
                    "ai_category": "unknown",
                    "ai_description": "Не удалось разобрать ответ AI",
                    "ai_confidence": 0.0
                }

        except Exception as e:
            logger.error(f"Error analyzing event with Yandex GPT: {e}", exc_info=True)
            # Return empty analysis on error
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
        system_prompt = """Ты - эксперт по информационной безопасности, анализирующий алерты системы безопасности.

Твоя задача - проанализировать алерт и предоставить:
1. Анализ угрозы
2. Рекомендации по реагированию
3. Приоритет реагирования (1-4)
4. Предполагаемые следующие шаги злоумышленника

Отвечай ТОЛЬКО в формате JSON:
{
  "analysis": "подробный анализ угрозы",
  "recommendations": ["рекомендация 1", "рекомендация 2", ...],
  "priority": 1-4,
  "next_attacker_steps": ["возможный шаг 1", "возможный шаг 2", ...]
}
"""

        alert_desc = f"""
Алерт: {alert_data.get('title', 'Unknown')}
Описание: {alert_data.get('description', 'N/A')}
Категория: {alert_data.get('category', 'N/A')}
Уровень важности: {alert_data.get('severity', 0)}

Контекст:
- Компьютер: {alert_data.get('hostname', 'N/A')}
- Пользователь: {alert_data.get('username', 'N/A')}
- Источник IP: {alert_data.get('source_ip', 'N/A')}
- Целевой IP: {alert_data.get('target_ip', 'N/A')}
- Процесс: {alert_data.get('process_name', 'N/A')}

MITRE ATT&CK:
- Тактика: {alert_data.get('mitre_attack_tactic', 'N/A')}
- Техника: {alert_data.get('mitre_attack_technique', 'N/A')}

Количество событий: {alert_data.get('event_count', 0)}
Временной диапазон: {alert_data.get('first_event_time', 'N/A')} - {alert_data.get('last_event_time', 'N/A')}

Связанные события (первые 5):
"""

        # Add event details
        for i, event in enumerate(events[:5], 1):
            alert_desc += f"\n{i}. {event.get('message', 'N/A')[:200]}"

        try:
            response = await self._make_request(system_prompt, alert_desc.strip())
            response_text = self._extract_response_text(response)

            # Parse JSON response
            try:
                response_text = response_text.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text.rsplit("\n", 1)[0]
                response_text = response_text.strip()

                analysis = json.loads(response_text)

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
                    "ai_confidence": 75.0  # Default confidence for alert analysis
                }

            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Yandex GPT response: {response_text}")
                return {
                    "ai_analysis": {"error": "Не удалось разобрать ответ AI"},
                    "ai_recommendations": "Ошибка анализа",
                    "ai_confidence": 0.0
                }

        except Exception as e:
            logger.error(f"Error analyzing alert with Yandex GPT: {e}", exc_info=True)
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
        system_prompt = """Ты - ведущий эксперт по информационной безопасности, проводящий анализ инцидента безопасности.

Твоя задача - предоставить комплексный анализ инцидента:
1. Краткое резюме инцидента (executive summary)
2. Временную шкалу атаки
3. Вероятную первопричину (root cause)
4. Оценку воздействия
5. Рекомендации по устранению

Отвечай ТОЛЬКО в формате JSON:
{
  "summary": "краткое резюме для руководства (2-3 предложения)",
  "timeline": "описание временной шкалы атаки",
  "root_cause": "предполагаемая первопричина",
  "impact_assessment": "оценка воздействия на организацию",
  "remediation_steps": ["шаг 1", "шаг 2", ...]
}
"""

        incident_desc = f"""
Инцидент: {incident_data.get('title', 'Unknown')}
Описание: {incident_data.get('description', 'N/A')}
Категория: {incident_data.get('category', 'N/A')}
Уровень важности: {incident_data.get('severity', 0)}

Временной диапазон:
- Начало: {incident_data.get('start_time', 'N/A')}
- Конец: {incident_data.get('end_time', 'N/A')}
- Обнаружено: {incident_data.get('detected_at', 'N/A')}

Масштаб:
- Количество алертов: {incident_data.get('alert_count', 0)}
- Количество событий: {incident_data.get('event_count', 0)}
- Затронуто систем: {incident_data.get('affected_assets', 0)}

MITRE ATT&CK:
- Тактики: {', '.join(incident_data.get('mitre_attack_tactics', []) or [])}
- Техники: {', '.join(incident_data.get('mitre_attack_techniques', []) or [])}

Связанные алерты (топ-5):
"""

        # Add alert details
        for i, alert in enumerate(alerts[:5], 1):
            incident_desc += f"\n{i}. [{alert.get('severity', 0)}] {alert.get('title', 'N/A')}"

        try:
            response = await self._make_request(
                system_prompt,
                incident_desc.strip(),
                max_tokens=2000  # More tokens for comprehensive analysis
            )
            response_text = self._extract_response_text(response)

            # Parse JSON response
            try:
                response_text = response_text.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text.rsplit("\n", 1)[0]
                response_text = response_text.strip()

                analysis = json.loads(response_text)

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
                logger.error(f"Failed to parse JSON from Yandex GPT response: {response_text}")
                return {
                    "ai_summary": "Ошибка анализа инцидента",
                    "ai_timeline": {"error": "Не удалось разобрать ответ AI"},
                    "ai_root_cause": "Не определено",
                    "ai_impact_assessment": "Не определено",
                    "ai_recommendations": "Ошибка анализа"
                }

        except Exception as e:
            logger.error(f"Error analyzing incident with Yandex GPT: {e}", exc_info=True)
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

    async def generate_cbr_report(
        self,
        incident_data: Dict[str, Any]
    ) -> str:
        """
        Generate incident report in format suitable for CBR (Central Bank of Russia)
        """
        system_prompt = """Ты - эксперт по подготовке отчётов для Центрального Банка РФ об инцидентах информационной безопасности.

Твоя задача - составить формальный отчёт об инциденте для ЦБ РФ в соответствии с требованиями 683-П, 716-П, 747-П.

Отчёт должен включать:
1. Краткое описание инцидента
2. Дату и время обнаружения
3. Категорию операционного риска
4. Описание воздействия на деятельность организации
5. Предпринятые меры
6. Оценку ущерба

Используй официально-деловой стиль, будь конкретен и объективен.
"""

        incident_desc = f"""
Подготовь отчёт об инциденте для ЦБ РФ:

Название инцидента: {incident_data.get('title', 'Unknown')}
Категория: {incident_data.get('category', 'N/A')}
Уровень критичности: {incident_data.get('severity', 0)}

Временные характеристики:
- Дата/время обнаружения: {incident_data.get('detected_at', 'N/A')}
- Начало инцидента: {incident_data.get('start_time', 'N/A')}
- Окончание: {incident_data.get('end_time', 'N/A')}

Масштаб воздействия:
- Количество затронутых систем: {incident_data.get('affected_assets', 0)}
- Количество алертов: {incident_data.get('alert_count', 0)}

Категория операционного риска: {incident_data.get('operational_risk_category', 'Не определена')}
Оценочный ущерб: {incident_data.get('estimated_damage_rub', 0)} руб.
Фактический ущерб: {incident_data.get('actual_damage_rub', 0)} руб.

Описание: {incident_data.get('description', 'N/A')}
"""

        try:
            response = await self._make_request(
                system_prompt,
                incident_desc.strip(),
                temperature=0.3,  # Lower temperature for formal report
                max_tokens=2000
            )
            report_text = self._extract_response_text(response)

            return report_text.strip()

        except Exception as e:
            logger.error(f"Error generating CBR report with Yandex GPT: {e}", exc_info=True)
            return f"Ошибка генерации отчёта для ЦБ РФ: {str(e)}"


# Singleton instance
_yandex_gpt_service = None


def get_yandex_gpt_service() -> YandexGPTService:
    """Get YandexGPT service singleton instance"""
    global _yandex_gpt_service
    if _yandex_gpt_service is None:
        _yandex_gpt_service = YandexGPTService()
    return _yandex_gpt_service
