# memory/quality_filter.py
class MemoryQualityFilter:
    SCORE_WEIGHTS = {
        "has_cve": 0.3,
        "has_severity": 0.2,
        "has_reproduction_steps": 0.3,
        "is_unique": 0.2,
    }

    def score(self, finding: dict) -> float:
        score = 0
        if re.search(r'CVE-\d{4}-\d+', finding.get('content', '')):
            score += 0.3
        if finding.get('severity') in ['critical','high','medium']:
            score += 0.2
        if len(finding.get('steps', [])) > 0:
            score += 0.3
        if not self._is_duplicate(finding):
            score += 0.2
        return score

    def should_store(self, finding: dict, threshold=0.4) -> bool:
        return self.score(finding) >= threshold