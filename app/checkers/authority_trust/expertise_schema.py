from __future__ import annotations

import json

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

EXPERTISE_TYPES = [
    "MedicalOrganization", "MedicalClinic", "Hospital", "Physician",
    "LegalService", "Attorney", "FinancialService", "AccountingService",
    "EducationalOrganization", "CollegeOrUniversity",
    "GovernmentOrganization", "ResearchOrganization",
]


class ExpertiseSchemaChecker(BaseChecker):
    check_id = "expertise_schema"
    check_number = 18
    name = "Schema for Expertise"
    layer = Layer.AUTHORITY_TRUST

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        scripts = crawl.soup.find_all("script", type="application/ld+json")
        if not scripts:
            findings.append("no_schema_markup")
            return self._make_result(0, findings)

        all_types: list[str] = []
        has_speakable = False
        has_credentials = False

        for script in scripts:
            try:
                data = json.loads(script.string or "")
                objects = []
                if isinstance(data, dict):
                    objects = data.get("@graph", [data])
                elif isinstance(data, list):
                    objects = data

                for obj in objects:
                    obj_type = obj.get("@type", "")
                    if isinstance(obj_type, list):
                        all_types.extend(obj_type)
                    else:
                        all_types.append(obj_type)

                    if obj.get("speakable"):
                        has_speakable = True
                    if obj.get("hasCredential") or obj.get("knowsAbout"):
                        has_credentials = True
            except (json.JSONDecodeError, TypeError):
                pass

        # Expertise schema types
        expertise_found = [t for t in all_types if t in EXPERTISE_TYPES]
        if expertise_found:
            score += 40
            findings.append(f"expertise_types:{','.join(expertise_found)}")
        else:
            # General schema still gets partial credit
            if all_types:
                score += 15
                findings.append("general_schema_only")
            else:
                findings.append("no_recognized_types")

        # Speakable property
        if has_speakable:
            score += 30
            findings.append("speakable_present")
        else:
            findings.append("no_speakable")

        # Credentials/knowsAbout
        if has_credentials:
            score += 30
            findings.append("credentials_in_schema")
        else:
            findings.append("no_credentials_in_schema")

        return self._make_result(score, findings, {"types": all_types})
