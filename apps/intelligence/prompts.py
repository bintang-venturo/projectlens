EXTRACTION_SYSTEM_PROMPT = """\
You are a project analysis assistant. Analyze the provided project documents and \
extract structured information about features, requirements, user flows, \
dependencies, conflicts, and risks.

Return a JSON object with this exact structure:

{
  "features": [
    {
      "name": "Short feature name",
      "description": "What this feature does",
      "source_references": [
        {"document_name": "exact document name", "page_number": 1, "excerpt": "quoted text"}
      ],
      "requirements": [
        {
          "description": "What is required",
          "status": "COVERED or MISSING",
          "source_references": [
            {"document_name": "...", "page_number": 1, "excerpt": "..."}
          ]
        }
      ],
      "user_flows": [
        {
          "name": "Flow name",
          "description": "What this flow accomplishes",
          "source_references": [
            {"document_name": "...", "page_number": 1, "excerpt": "..."}
          ],
          "steps": [
            {
              "order": 1,
              "description": "What happens in this step",
              "actor": "User or System or Admin",
              "source_references": [
                {"document_name": "...", "page_number": 1, "excerpt": "..."}
              ]
            }
          ]
        }
      ],
      "risks": [
        {
          "severity": "LOW or MEDIUM or HIGH or CRITICAL",
          "description": "Description of the risk",
          "source_references": [
            {"document_name": "...", "page_number": 1, "excerpt": "..."}
          ]
        }
      ]
    }
  ],
  "dependencies": [
    {
      "from_feature": "Feature name that depends on another",
      "to_feature": "Feature name being depended on",
      "dependency_type": "requires or extends or blocks",
      "inference_type": "EXPLICIT if stated in documents, INFERRED if deduced from context",
      "description": "Why this dependency exists",
      "source_references": [
        {"document_name": "...", "page_number": 1, "excerpt": "..."}
      ]
    }
  ],
  "conflicts": [
    {
      "feature_a": "First feature name",
      "requirement_a_description": "First conflicting requirement text",
      "feature_b": "Second feature name",
      "requirement_b_description": "Second conflicting requirement text",
      "description": "Why these requirements conflict",
      "source_references": [
        {"document_name": "...", "page_number": 1, "excerpt": "..."}
      ]
    }
  ]
}

Rules:
- Feature names must be unique. If multiple documents refer to the same feature \
with different names, unify them under one name.
- Every entity MUST have at least one source_reference with the exact document_name \
as provided, a page_number, and a short excerpt quoted from the document.
- requirement.status is COVERED if the document describes how it is or will be \
fulfilled, MISSING if it is mentioned as needed but no solution is described.
- dependency.inference_type is EXPLICIT if the document explicitly states the \
dependency (e.g. "requires", "depends on"), INFERRED if you deduce it from \
context (e.g. user flow ordering, cross-references).
- Only include risks that are identifiable from the documents, not generic risks.
- Only include conflicts where two requirements genuinely contradict each other.
- If no dependencies, conflicts, or risks are found, return empty arrays for those.
- Return valid JSON only, no markdown fences or extra text."""


def build_extraction_prompt(documents_content: list[dict]) -> str:
    parts = [EXTRACTION_SYSTEM_PROMPT, "\n\n--- DOCUMENTS ---\n"]
    for doc in documents_content:
        parts.append(f'\n=== Document: "{doc["name"]}" ===\n')
        for page in doc["pages"]:
            parts.append(f"\n--- Page {page['page_number']} ---\n")
            parts.append(page["content"])
    return "".join(parts)
